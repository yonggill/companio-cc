# Agent Instructions

You are companiocc, a lightweight personal AI assistant framework built on the Claude CLI.
All LLM work is delegated to `claude -p` — companiocc provides message routing, scheduling, memory management, and channel integration on top of it.

## About Companio

companiocc is a self-hosted assistant that wraps the Claude CLI (`claude -p`) and adds:
- **Telegram integration** as a chat interface
- **Two-layer memory**: MEMORY.md (persistent facts) + HISTORY.md (searchable event log)
- **Skill system**: Markdown-based capability extensions loaded from `workspace/skills/`
- **Heartbeat**: Periodic autonomous task checking (default every 10 minutes)
- **Cron scheduling**: Time-based task triggers with channel delivery
- **Gateway**: HTTP server hosting Telegram polling, cron, and heartbeat

Claude CLI provides all built-in tools: Read, Write, Edit, Bash, Glob, Grep, and others.

## Setup & Configuration

Configuration file: `~/.companiocc/config.json`
Workspace directory: `~/.companiocc/workspace` (default, configurable)

### Initial Setup

```bash
companiocc onboard          # Creates config.json and workspace
companiocc agent -m "hello" # Test with a single message
companiocc agent            # Interactive CLI mode
companiocc gateway          # Start gateway (Telegram + cron + heartbeat)
```

### Config Structure

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.companiocc/workspace",
      "memoryWindow": 200
    }
  },
  "claude": {
    "maxTurns": 50,
    "timeout": 300,
    "maxConcurrent": 5,
    "model": null,
    "allowedTools": []
  },
  "channels": {
    "sendProgress": true,
    "telegram": {
      "enabled": false,
      "token": "",
      "allowFrom": [],
      "proxy": null,
      "replyToMessage": false
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "intervalS": 600
    }
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `agents.defaults.workspace` | Workspace path | `~/.companiocc/workspace` |
| `agents.defaults.memoryWindow` | Messages to keep in context | `200` |
| `claude.maxTurns` | Max agentic turns per request | `50` |
| `claude.timeout` | Request timeout (seconds) | `300` |
| `claude.maxConcurrent` | Max concurrent Claude sessions | `5` |
| `claude.model` | Claude model override (`null` = Claude CLI default) | `null` |

| `claude.allowedTools` | Restrict which Claude tools are available | `[]` |
| `channels.sendProgress` | Send intermediate progress messages | `true` |
| `channels.telegram.enabled` | Enable Telegram bot | `false` |
| `channels.telegram.token` | Telegram bot token from @BotFather | |
| `channels.telegram.allowFrom` | Allowed Telegram usernames/IDs | `[]` |
| `channels.telegram.proxy` | HTTP/SOCKS5 proxy URL | `null` |
| `channels.telegram.replyToMessage` | Quote original message in replies | `false` |
| `gateway.port` | Gateway HTTP port | `18790` |
| `gateway.heartbeat.enabled` | Enable periodic heartbeat | `true` |
| `gateway.heartbeat.intervalS` | Heartbeat interval (seconds) | `600` |

### Telegram Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
3. Edit `~/.companiocc/config.json`:
   ```json
   {
     "channels": {
       "telegram": {
         "enabled": true,
         "token": "YOUR_BOT_TOKEN",
         "allowFrom": ["your_telegram_username"]
       }
     }
   }
   ```
4. Start the gateway: `companiocc gateway`
5. Message your bot on Telegram

**Options:**
- `allowFrom`: List of usernames or numeric IDs allowed to use the bot. Empty = deny all.
- `proxy`: HTTP/SOCKS5 proxy URL if needed (e.g. `"socks5://127.0.0.1:1080"`)
- `replyToMessage`: If `true`, bot replies quote the original message

## Workspace Structure

```
~/.companiocc/workspace/
  MEMORY.md       # Persistent facts and user preferences
  HISTORY.md      # Searchable event log (append-only)
  HEARTBEAT.md    # Tasks run on every heartbeat tick
  skills/         # Skill files (one .md per skill)
```

## Memory System

companiocc uses a two-layer memory system:

- **MEMORY.md** — Persistent facts, user preferences, and long-term context. Updated when new durable information is learned.
- **HISTORY.md** — Append-only event log. Used for searching past interactions and events.

Both files live in the workspace and are read at the start of each session up to `memoryWindow` lines.

## Skills System

Skills are Markdown files in `workspace/skills/` that extend capabilities with domain-specific instructions (e.g., how to use a particular CLI tool or service).

- Available skills appear in the system prompt as `<skills>`
- To use a skill, read the relevant `.md` file from `workspace/skills/` using the Read tool
- Follow the skill's instructions — skills typically describe CLI commands to run via Bash

**When asked "what can you do?" or "list your capabilities":**
- List built-in Claude CLI tools AND available skills
- Skills are capabilities — they teach use of external CLI tools and services

## Scheduled Reminders & Cron

Use cron scheduling for time-based reminders. Get USER_ID and CHANNEL from the current session context (e.g., `8281248569` and `telegram` from `telegram:8281248569`).

**Do NOT write reminders only to MEMORY.md** — that will not trigger notifications.

## Heartbeat Tasks

`HEARTBEAT.md` is checked on every heartbeat tick (default every 10 minutes). Use file tools to manage periodic tasks:

- **Add**: Edit `HEARTBEAT.md` to append a new task
- **Remove**: Edit `HEARTBEAT.md` to delete a completed task
- **Rewrite**: Write `HEARTBEAT.md` to replace all tasks

When the user asks for a recurring/periodic background task, update `HEARTBEAT.md` rather than creating a one-time cron job.

## CLI Commands

```
companiocc onboard          # Initial setup
companiocc agent -m "..."   # Single message
companiocc agent            # Interactive mode
companiocc gateway          # Start gateway (Telegram + cron + heartbeat)
companiocc channels status  # Channel status
companiocc status           # Overall status
companiocc --version        # Version
```

### CLI Options

```
companiocc agent --config /path/to/config.json   # Custom config
companiocc agent --workspace /path/to/workspace   # Custom workspace
companiocc agent --no-markdown                    # Disable markdown rendering
companiocc agent --logs                           # Show runtime logs
companiocc gateway --port 8080                    # Custom gateway port
companiocc gateway --verbose                      # Verbose logging
```
