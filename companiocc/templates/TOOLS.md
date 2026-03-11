# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents non-obvious constraints and usage patterns.

## Available Tools

### File Tools (`read_file`, `write_file`, `edit_file`, `list_dir`)
- Read, create, modify, and list files in the workspace
- When `restrictToWorkspace` is `true` (default), all paths are confined to the workspace directory
- Path traversal (`../`) outside workspace is blocked
- `read_file` has a size limit; large files are truncated
- Always read a file before modifying it

### Shell Execution (`exec`)
- Runs shell commands with configurable timeout (default 60s)
- **Blocked commands**: `rm -rf /`, `format`, `mkfs`, `dd`, fork bombs, `shutdown`, `reboot`
- Output is truncated at 10,000 characters
- **Security**: API keys and secrets are NOT passed to child process environment
- When `restrictToWorkspace` is `true`, the working directory is set to the workspace

### Web Search (`web_search`)
- Searches the web using Brave Search API
- Requires `tools.web.search.apiKey` in config
- Returns up to `maxResults` (default 5) results with title, URL, and snippet

### Web Fetch (`web_fetch`)
- Fetches content from a URL and returns text
- **SSRF protection**: Internal/private IP addresses are blocked (10.x, 172.16.x, 192.168.x, 127.x, link-local, etc.)
- Only `http://` and `https://` schemes are allowed
- Supports proxy via `tools.web.proxy` config

### Message (`message`)
- Sends a message to a specific chat channel (e.g., Telegram)
- Requires channel name and chat ID
- Use this to proactively notify the user (e.g., from cron tasks or heartbeat)

### Sub-agent (`spawn`)
- Creates a background sub-agent for independent tasks
- Sub-agents have a reduced iteration limit (15 vs 40)
- Useful for parallel work or tasks that shouldn't block the main conversation

### Cron (`cron`)
- Schedule reminders and recurring tasks
- Three modes: reminder (direct message), task (agent executes), one-time (auto-deletes)
- Supports: `every_seconds`, `cron_expr` (with optional `tz`), `at` (ISO datetime)
- Please refer to the cron skill for detailed usage

### MCP Tools
- External tools connected via Model Context Protocol
- Configured in `tools.mcpServers` section of config
- Supports stdio and HTTP transports
- Each tool has a configurable timeout (default 30s)

## Safety Constraints

1. **Workspace restriction** (default ON): File tools cannot access paths outside the workspace
2. **Secret filtering**: Shell execution strips sensitive environment variables (API keys, tokens, passwords)
3. **SSRF defense**: Web fetch blocks internal network addresses
4. **Command blocking**: Destructive shell commands are rejected
5. **Output truncation**: Large tool outputs are truncated to prevent context overflow
