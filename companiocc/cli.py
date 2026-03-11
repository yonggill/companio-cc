"""CLI commands for companiocc."""

import asyncio
import os
import select
import signal
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        os.environ["PYTHONIOENCODING"] = "utf-8"
        # Re-open stdout/stderr with UTF-8 encoding
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from companiocc import __logo__, __version__
from companiocc.config.schema import Config
from companiocc.helpers import sync_workspace_templates

app = typer.Typer(
    name="companiocc",
    help=f"{__logo__} companiocc - Personal AI Assistant",
    no_args_is_help=True,
)

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input: prompt_toolkit for editing, paste, history, and display
# ---------------------------------------------------------------------------

_PROMPT_SESSION: PromptSession | None = None
_SAVED_TERM_ATTRS = None  # original termios settings, restored on exit


def _flush_pending_tty_input() -> None:
    """Drop unread keypresses typed while the model was generating output."""
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return

    try:
        import termios

        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _restore_terminal() -> None:
    """Restore terminal to its original state (echo, line buffering, etc.)."""
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios

        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _init_prompt_session() -> None:
    """Create the prompt_toolkit session with persistent file history."""
    global _PROMPT_SESSION, _SAVED_TERM_ATTRS

    # Save terminal state so we can restore it on exit
    try:
        import termios

        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    from companiocc.config.paths import get_cli_history_path

    history_file = get_cli_history_path()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    _PROMPT_SESSION = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,  # Enter submits (single line mode)
    )


def _print_agent_response(response: str, render_markdown: bool) -> None:
    """Render assistant response with consistent terminal styling."""
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(f"[cyan]{__logo__} companiocc[/cyan]")
    console.print(body)
    console.print()


def _is_exit_command(command: str) -> bool:
    """Return True when input should end interactive chat."""
    return command.lower() in EXIT_COMMANDS


async def _read_interactive_input_async() -> str:
    """Read user input using prompt_toolkit (handles paste, history, display).

    prompt_toolkit natively handles:
    - Multiline paste (bracketed paste mode)
    - History navigation (up/down arrows)
    - Clean display (no ghost characters or artifacts)
    """
    if _PROMPT_SESSION is None:
        raise RuntimeError("Call _init_prompt_session() first")
    try:
        with patch_stdout():
            return await _PROMPT_SESSION.prompt_async(
                HTML("<b fg='ansiblue'>You:</b> "),
            )
    except EOFError as exc:
        raise KeyboardInterrupt from exc


def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} companiocc v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True),
):
    """companiocc - Personal AI Assistant."""
    pass


# ============================================================================
# Onboard / Setup
# ============================================================================


@app.command()
def onboard():
    """Initialize companiocc configuration and workspace."""
    from companiocc.config.loader import get_config_path, load_config, save_config
    from companiocc.config.schema import Config
    from companiocc.core.claude_cli import verify_claude_cli

    config_path = get_config_path()

    # If config already exists, ask what to do
    if config_path.exists():
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        if not typer.confirm("Re-run setup? (existing values will be used as defaults)", default=False):
            console.print("Aborted.")
            return
        config = load_config()
    else:
        config = Config()

    console.print(f"\n{__logo__} [bold]companiocc setup[/bold]\n")

    # --- Check Claude CLI ---
    console.print("[bold cyan]Step 1:[/bold cyan] Claude CLI")
    try:
        version = verify_claude_cli()
        console.print(f"  [green]✓[/green] Claude CLI found: {version}")
    except RuntimeError as exc:
        console.print(f"  [red]✗[/red] {exc}")
        console.print("  Install Claude CLI: https://claude.ai/code")
        console.print("  [dim]companiocc requires Claude CLI to be installed and authenticated.[/dim]\n")

    # --- Optional dependency check ---
    import shutil

    _OPTIONAL_DEPS = [
        {
            "name": "Node.js (npx)",
            "check": "npx",
            "install": "brew install node  (or https://nodejs.org/)",
            "used_by": "MCP servers (Playwright, GitHub, Slack, Filesystem)",
        },
        {
            "name": "Google Workspace CLI",
            "check": "gws",
            "install": "npm install -g @googleworkspace/cli",
            "used_by": "Google Workspace skill (Gmail, Drive, Calendar, Sheets)",
        },
    ]

    missing_deps = []
    for dep in _OPTIONAL_DEPS:
        if not shutil.which(dep["check"]):
            missing_deps.append(dep)

    if missing_deps:
        console.print("[bold yellow]Optional dependencies not found:[/bold yellow]\n")
        for dep in missing_deps:
            console.print(f"  [yellow]•[/yellow] [bold]{dep['name']}[/bold]")
            console.print(f"    Used by: {dep['used_by']}")
            console.print(f"    Install: [cyan]{dep['install']}[/cyan]")
        console.print("\n  [dim]These are optional — companiocc works without them, but related features will be unavailable.[/dim]\n")
    else:
        console.print("[green]✓[/green] All optional dependencies found.\n")

    # --- Step 2: Workspace ---
    console.print("\n[bold cyan]Step 2:[/bold cyan] Workspace")

    config.agents.defaults.workspace = typer.prompt(
        "  Workspace path",
        default=config.agents.defaults.workspace,
    )
    config.agents.defaults.memory_window = int(typer.prompt(
        "  Memory window (messages)",
        default=str(config.agents.defaults.memory_window),
    ))

    # --- Step 3: Telegram ---
    console.print("\n[bold cyan]Step 3:[/bold cyan] Telegram Integration")
    if typer.confirm("  Enable Telegram bot?", default=config.channels.telegram.enabled):
        config.channels.telegram.enabled = True
        token = typer.prompt(
            "  Bot token (from @BotFather)",
            default=config.channels.telegram.token or "",
            show_default=False,
        )
        if token:
            config.channels.telegram.token = token

        allow_from_str = typer.prompt(
            "  Allowed usernames (comma-separated)",
            default=",".join(config.channels.telegram.allow_from) if config.channels.telegram.allow_from else "",
            show_default=False,
        )
        if allow_from_str:
            config.channels.telegram.allow_from = [u.strip() for u in allow_from_str.split(",") if u.strip()]

        config.channels.telegram.reply_to_message = typer.confirm(
            "  Reply with quote?", default=config.channels.telegram.reply_to_message
        )
    else:
        config.channels.telegram.enabled = False

    # --- Step 4: Channel behavior ---
    console.print("\n[bold cyan]Step 4:[/bold cyan] Channel Behavior")
    config.channels.send_progress = typer.confirm(
        "  Stream text progress to channel?", default=config.channels.send_progress
    )
    config.channels.send_tool_hints = typer.confirm(
        "  Stream tool-call hints?", default=config.channels.send_tool_hints
    )

    # --- Save config ---
    save_config(config)
    console.print(f"\n[green]✓[/green] Config saved to {config_path}")

    # Create workspace
    workspace = config.workspace_path
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created workspace at {workspace}")

    sync_workspace_templates(workspace)

    # Done
    console.print(f"\n{__logo__} [bold green]companiocc is ready![/bold green]")
    console.print(f"\n  Config: [cyan]{config_path}[/cyan]")
    console.print(f"  Workspace: [cyan]{workspace}[/cyan]")

    if config.channels.telegram.enabled:
        console.print('\n  Start gateway: [cyan]companiocc gateway[/cyan]')
    console.print('  Chat: [cyan]companiocc agent -m "Hello!"[/cyan]')


def _load_runtime_config(config: str | None = None, workspace: str | None = None) -> Config:
    """Load config and optionally override the active workspace."""
    from companiocc.config.loader import load_config, set_config_path

    config_path = None
    if config:
        config_path = Path(config).expanduser().resolve()
        if not config_path.exists():
            console.print(f"[red]Error: Config file not found: {config_path}[/red]")
            raise typer.Exit(1)
        set_config_path(config_path)
        console.print(f"[dim]Using config: {config_path}[/dim]")

    loaded = load_config(config_path)
    if workspace:
        loaded.agents.defaults.workspace = workspace
    return loaded


# ============================================================================
# Gateway / Server
# ============================================================================


@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway port"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Start the companiocc gateway."""
    from companiocc.bus import MessageBus
    from companiocc.channels.manager import ChannelManager
    from companiocc.config.paths import get_cron_dir
    from companiocc.core.claude_cli import ClaudeCLI, verify_claude_cli
    from companiocc.core.loop import AgentLoop
    from companiocc.cron import CronJob, CronService
    from companiocc.heartbeat import HeartbeatService
    from companiocc.session import SessionManager

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # Warn if running from home directory — Claude CLI would have access to everything under ~/
    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    if cwd == home or cwd == home / ".":
        console.print(
            "[bold yellow]Warning:[/bold yellow] Running gateway from your home directory (~/).\n"
            "  Claude CLI will use this as its working directory, giving it access to all files under ~/.\n"
            "  Consider running from a more specific directory (e.g., your workspace)."
        )
        if not typer.confirm("  Continue anyway?", default=False):
            raise typer.Exit(0)

    config = _load_runtime_config(config, workspace)

    verify_claude_cli()  # fails fast if claude not installed

    console.print(f"{__logo__} Starting companiocc gateway on port {port}...")
    sync_workspace_templates(config.workspace_path)
    bus = MessageBus()

    claude = ClaudeCLI(
        max_turns=config.claude.max_turns,
        timeout=config.claude.timeout,
        max_concurrent=config.claude.max_concurrent,
        model=config.claude.model,

        allowed_tools=config.claude.allowed_tools,
    )

    session_manager = SessionManager(config.workspace_path)

    # Create cron service first (callback set after agent creation)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    # Create agent with cron service
    agent = AgentLoop(
        bus=bus,
        claude=claude,
        workspace=config.workspace_path,
        memory_window=config.agents.defaults.memory_window,
        cron_service=cron,
        session_manager=session_manager,
    )

    # Set cron callback (needs agent)
    async def on_cron_job(job: CronJob) -> str | None:
        """Execute a cron job through the agent."""
        reminder_note = (
            "[Scheduled Task] Timer finished.\n\n"
            f"Task '{job.name}' has been triggered.\n"
            f"Scheduled instruction: {job.payload.message}"
        )

        response = await agent.process_direct(
            reminder_note,
            session_key=f"cron:{job.id}",
            channel=job.payload.channel or "cli",
            chat_id=job.payload.to or "direct",
        )

        if agent.message_sender._sent_in_turn:
            return response

        if job.payload.deliver and job.payload.to and response:
            from companiocc.bus import OutboundMessage

            await bus.publish_outbound(
                OutboundMessage(
                    channel=job.payload.channel or "cli", chat_id=job.payload.to, content=response
                )
            )
        return response

    cron.on_job = on_cron_job

    # Create channel manager
    channels = ChannelManager(config, bus)

    def _pick_heartbeat_target() -> tuple[str, str]:
        """Pick a routable channel/chat target for heartbeat-triggered messages."""
        # Fallback: no session listing available, use cli channel
        return "cli", "direct"

    # Create heartbeat service
    async def on_heartbeat_execute(tasks: str) -> str:
        """Phase 2: execute heartbeat tasks through the full agent loop."""
        channel, chat_id = _pick_heartbeat_target()

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
        )

    async def on_heartbeat_notify(response: str) -> None:
        """Deliver a heartbeat response to the user's channel."""
        from companiocc.bus import OutboundMessage

        channel, chat_id = _pick_heartbeat_target()
        if channel == "cli":
            return  # No external channel available to deliver to
        await bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=response)
        )

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )

    if channels.enabled_channels:
        console.print(f"[green]✓[/green] Channels enabled: {', '.join(channels.enabled_channels)}")
    else:
        console.print("[yellow]Warning: No channels enabled[/yellow]")

    cron_status = cron.status()
    if cron_status["jobs"] > 0:
        console.print(f"[green]✓[/green] Cron: {cron_status['jobs']} scheduled jobs")

    console.print(f"[green]✓[/green] Heartbeat: every {hb_cfg.interval_s}s")

    async def run():
        try:
            await cron.start()
            await heartbeat.start()
            await asyncio.gather(
                agent.run(),
                channels.start_all(),
            )
        except KeyboardInterrupt:
            console.print("\nShutting down...")
        finally:
            heartbeat.stop()
            cron.stop()
            agent.stop()
            await channels.stop_all()

    asyncio.run(run())


# ============================================================================
# Agent Commands
# ============================================================================


@app.command()
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the agent"),
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    markdown: bool = typer.Option(
        True, "--markdown/--no-markdown", help="Render assistant output as Markdown"
    ),
    logs: bool = typer.Option(
        False, "--logs/--no-logs", help="Show companiocc runtime logs during chat"
    ),
):
    """Interact with the agent directly."""
    from loguru import logger

    from companiocc.bus import MessageBus
    from companiocc.config.paths import get_cron_dir
    from companiocc.core.claude_cli import ClaudeCLI, verify_claude_cli
    from companiocc.core.loop import AgentLoop
    from companiocc.cron import CronService

    config = _load_runtime_config(config, workspace)
    sync_workspace_templates(config.workspace_path)

    verify_claude_cli()  # fails fast if claude not installed

    bus = MessageBus()

    claude = ClaudeCLI(
        max_turns=config.claude.max_turns,
        timeout=config.claude.timeout,
        max_concurrent=config.claude.max_concurrent,
        model=config.claude.model,

        allowed_tools=config.claude.allowed_tools,
    )

    # Create cron service for tool usage (no callback needed for CLI unless running)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    if logs:
        logger.enable("companiocc")
    else:
        logger.disable("companiocc")

    agent_loop = AgentLoop(
        bus=bus,
        claude=claude,
        workspace=config.workspace_path,
        memory_window=config.agents.defaults.memory_window,
        cron_service=cron,
    )

    # Show spinner when logs are off (no output to miss); skip when logs are on
    def _thinking_ctx():
        if logs:
            from contextlib import nullcontext

            return nullcontext()
        # Animated spinner is safe to use with prompt_toolkit input handling
        return console.status("[dim]companiocc is thinking...[/dim]", spinner="dots")

    if message:
        # Single message mode -- direct call, no bus needed
        async def run_once():
            with _thinking_ctx():
                response = await agent_loop.process_direct(
                    message, session_id
                )
            _print_agent_response(response, render_markdown=markdown)

        asyncio.run(run_once())
    else:
        # Interactive mode -- route through bus like other channels
        from companiocc.bus import InboundMessage

        _init_prompt_session()
        console.print(
            f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n"
        )

        if ":" in session_id:
            cli_channel, cli_chat_id = session_id.split(":", 1)
        else:
            cli_channel, cli_chat_id = "cli", session_id

        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            _restore_terminal()
            console.print(f"\nReceived {sig_name}, goodbye!")
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        # SIGHUP is not available on Windows
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, _handle_signal)
        # Ignore SIGPIPE to prevent silent process termination when writing to closed pipes
        # SIGPIPE is not available on Windows
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        async def run_interactive():
            bus_task = asyncio.create_task(agent_loop.run())
            turn_done = asyncio.Event()
            turn_done.set()
            turn_response: list[str] = []

            async def _consume_outbound():
                while True:
                    try:
                        msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
                        if msg.metadata.get("_progress"):
                            console.print(f"  [dim]↳ {msg.content}[/dim]")
                        elif not turn_done.is_set():
                            if msg.content:
                                turn_response.append(msg.content)
                            turn_done.set()
                        elif msg.content:
                            console.print()
                            _print_agent_response(msg.content, render_markdown=markdown)
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        break

            outbound_task = asyncio.create_task(_consume_outbound())

            try:
                while True:
                    try:
                        _flush_pending_tty_input()
                        user_input = await _read_interactive_input_async()
                        command = user_input.strip()
                        if not command:
                            continue

                        if _is_exit_command(command):
                            _restore_terminal()
                            console.print("\nGoodbye!")
                            break

                        turn_done.clear()
                        turn_response.clear()

                        await bus.publish_inbound(
                            InboundMessage(
                                channel=cli_channel,
                                sender_id="user",
                                chat_id=cli_chat_id,
                                content=user_input,
                            )
                        )

                        with _thinking_ctx():
                            await turn_done.wait()

                        if turn_response:
                            _print_agent_response(turn_response[0], render_markdown=markdown)
                    except KeyboardInterrupt:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
                    except EOFError:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
            finally:
                agent_loop.stop()
                outbound_task.cancel()
                await asyncio.gather(bus_task, outbound_task, return_exceptions=True)

        asyncio.run(run_interactive())


# ============================================================================
# Channel Commands
# ============================================================================


channels_app = typer.Typer(help="Manage channels")
app.add_typer(channels_app, name="channels")


@channels_app.command("status")
def channels_status():
    """Show channel status."""
    from companiocc.config.loader import load_config

    config = load_config()

    table = Table(title="Channel Status")
    table.add_column("Channel", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Configuration", style="yellow")

    # Telegram
    tg = config.channels.telegram
    tg_config = f"token: {tg.token[:10]}..." if tg.token else "[dim]not configured[/dim]"
    table.add_row("Telegram", "✓" if tg.enabled else "✗", tg_config)

    console.print(table)


# ============================================================================
# Status Commands
# ============================================================================


@app.command()
def status():
    """Show companiocc status."""
    import shutil
    import subprocess

    from companiocc.config.loader import get_config_path, load_config

    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path

    console.print(f"{__logo__} companiocc Status\n")

    console.print(
        f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}"
    )
    console.print(
        f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}"
    )

    if config_path.exists():
        # Claude CLI status
        claude_path = shutil.which("claude")
        if claude_path:
            try:
                proc = subprocess.run(
                    [claude_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                claude_version = proc.stdout.strip() or proc.stderr.strip() or "unknown"
                console.print(f"Claude CLI: [green]✓ {claude_version}[/green]")
            except Exception:
                console.print("Claude CLI: [yellow]found but version check failed[/yellow]")
        else:
            console.print("Claude CLI: [red]✗ not found[/red]")
            console.print("  Install: https://claude.ai/code")


if __name__ == "__main__":
    app()
