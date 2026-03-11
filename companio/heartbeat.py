"""Heartbeat service - periodic agent wake-up to check for tasks."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger


class HeartbeatService:
    """
    Periodic heartbeat service that wakes the agent to check for tasks.

    Reads MEMORY.md and uses rule-based parsing to detect unchecked markdown
    checkboxes (active tasks).  When active tasks are found the ``on_execute``
    callback is invoked with a plain-text summary.
    """

    def __init__(
        self,
        workspace: Path,
        on_execute: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        on_notify: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        interval_s: int = 10 * 60,
        enabled: bool = True,
    ):
        self.workspace = workspace
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.interval_s = interval_s
        self.enabled = enabled
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / "HEARTBEAT.md"

    def _read_heartbeat_file(self) -> str | None:
        if self.heartbeat_file.exists():
            try:
                return self.heartbeat_file.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def _parse_active_tasks(self, text: str) -> list[str]:
        """Return a list of active (unchecked) task strings from MEMORY.md."""
        return re.findall(r'- \[ \] (.+)', text)

    async def start(self) -> None:
        """Start the heartbeat service."""
        if not self.enabled:
            logger.info("Heartbeat disabled")
            return
        if self._running:
            logger.warning("Heartbeat already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Heartbeat started (every {}s)", self.interval_s)

    def stop(self) -> None:
        """Stop the heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_s)
                if self._running:
                    await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: {}", e)

    async def _tick(self) -> None:
        """Execute a single heartbeat tick."""
        content = self._read_heartbeat_file()
        if not content:
            logger.debug("Heartbeat: HEARTBEAT.md missing or empty")
            return

        logger.info("Heartbeat: checking for tasks...")

        try:
            active_tasks = self._parse_active_tasks(content)

            if not active_tasks:
                logger.info("Heartbeat: OK (nothing to report)")
                return

            summary = "Active tasks:\n" + "\n".join(f"- {t}" for t in active_tasks)
            logger.info("Heartbeat: tasks found, executing...")
            if self.on_execute:
                response = await self.on_execute(summary)
                if response and self.on_notify:
                    logger.info("Heartbeat: completed, delivering response")
                    await self.on_notify(response)
        except Exception:
            logger.exception("Heartbeat execution failed")

    async def trigger_now(self) -> str | None:
        """Manually trigger a heartbeat."""
        content = self._read_heartbeat_file()
        if not content:
            return None
        active_tasks = self._parse_active_tasks(content)
        if not active_tasks or not self.on_execute:
            return None
        summary = "Active tasks:\n" + "\n".join(f"- {t}" for t in active_tasks)
        return await self.on_execute(summary)
