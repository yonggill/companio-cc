# Tool Usage Notes

companiocc delegates all tool execution to Claude CLI (`claude -p`). Claude CLI's built-in tools (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, etc.) are available automatically — no configuration required.

## companiocc-Specific Tools

Two additional tools are injected by companiocc:

### `message`
- Sends a message to a specific chat channel (e.g., Telegram)
- Use this to proactively notify the user, such as from cron tasks or heartbeat events
- Requires a channel name and chat ID

### `cron`
- Schedules reminders and recurring tasks, managed by companiocc's CronService
- Three modes: reminder (direct message), task (agent executes), one-time (auto-deletes after firing)
- Scheduling options: `every_seconds`, `cron_expr` (with optional `tz`), `at` (ISO datetime)
- Refer to the cron skill for detailed usage

## Workspace Files

The following files in the workspace directory are managed by companiocc:
- `MEMORY.md` — persistent notes across sessions
- `HISTORY.md` — conversation history log
- `HEARTBEAT.md` — heartbeat task state
- `skills/` — skill definitions loaded into the system prompt

## Security

- **Secret filtering**: companiocc strips sensitive environment variables (API keys, tokens, passwords) before spawning Claude CLI, and also filters secrets from Claude CLI's output
- companiocc does not enforce workspace path restrictions — Claude CLI manages its own tool permissions
