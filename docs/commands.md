# Commands

APEX provides multiple ways to interact: **CLI subcommands**, **slash commands** (TUI), **keyboard shortcuts**, and **@mentions**.

## CLI Subcommands

| Subcommand | Description |
|---|---|
| `apex` | Launch TUI (default) |
| `apex tui` / `apex --tui` | Launch TUI |
| `apex` | Launch TUI (default) |
| `apex run <prompt>` | Non-interactive mode |
| `apex serve` | Start headless HTTP API server |
| `apex web` | Server + web interface |
| `apex models [provider]` | List models (`--refresh`, `--verbose`) |
| `apex auth login` | Interactive provider login |
| `apex auth list` | List configured providers |
| `apex auth logout [provider]` | Remove provider config |
| `apex connect` | Interactive provider configuration |
| `apex agent create` | Interactive agent creation wizard |
| `apex agent list` | List all agents |
| `apex session list` | List sessions (`-n`, `--format table\|json`) |
| `apex session delete <id>` | Delete a session |
| `apex stats` | Token usage & cost stats (`--days`, `--tools`, `--models`) |
| `apex export <id>` | Export session as JSON (`--sanitize`) |
| `apex import <file\|url>` | Import session |
| `apex upgrade [target]` | Upgrade APEX |
| `apex uninstall` | Remove APEX (`--keep-config`, `--keep-data`, `--dry-run`, `--force`) |
| `apex mcp add` | Add MCP server (interactive) |
| `apex mcp list` | List MCP servers |
| `apex mcp auth <name>` | Authenticate MCP server |
| `apex db path` | Show database path |
| `apex pr <number>` | Fetch & checkout a PR, then run APEX |
| `apex attach <url>` | Attach TUI to remote backend |
| `apex init` | Initialize project (create AGENTS.md) |
| `apex compact` | Compact current session |
| `apex details` | Toggle tool execution details |
| `apex thinking` | Toggle reasoning blocks display |
| `apex install-tui` | Install TUI dependencies |

### Global Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--model` | `-m` | Model alias to use |
| `--cwd` | `-C` | Working directory |
| `--version` | `-v` | Print version |
| `--agent` | | Agent to use |
| `--continue` | | Resume last session |
| `--session` | `-s` | Session ID to load |
| `--fork` | | Fork session |
| `--format` | `-f` | Output format (text/json) |
| `--quiet` | `-q` | Quiet mode |
| `--port` | | Server port |
| `--hostname` | | Server hostname |
| `--print-logs` | | Print logs |
| `--log-level` | | Log level |
| `--pure` | | No tools mode |
| `--file` | | Read prompt from file |

## Slash Commands (TUI)

### Session Commands

| Command | Description |
|---------|-------------|
| `/init` | Create/update AGENTS.md |
| `/new` or `/clear` | New session |
| `/save <name>` | Save session |
| `/load <name>` | Load session |
| `/sessions` | List saved sessions |
| `/compact` | Compact context |
| `/share` | Share session (creates URL) |
| `/unshare` | Unshare session |

### Agent Commands

| Command | Description |
|---------|-------------|
| `/agent` | Show/list agents |
| `/coder` | Switch to Coder |
| `/architect` | Switch to Architect |
| `/agents` | List all agents |
| `/subagents` | List subagents (@mention) |

### Model Commands

| Command | Description |
|---------|-------------|
| `/model <name>` | Switch model |
| `/models` | List available models |

### Navigation

| Command | Description |
|---------|-------------|
| `/undo` | Undo last action |
| `/redo` | Redo undone action |
| `/history` | Show conversation history |
| `/cwd [path]` | Show/change directory |

### System Commands

| Command | Description |
|---------|-------------|
| `/connect` | Add a provider |
| `/themes` | List/switch themes |
| `/thinking` | Toggle reasoning blocks |
| `/editor` | Open external editor |
| `/export` | Export to markdown |
| `/details` | Toggle tool output details |
| `/help` | Show help |
| `/exit` or `/quit` | Exit APEX |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/cost` | Session cost breakdown |
| `/memory` | Memory management |
| `/map` | Repository map |
| `/stats` | Language statistics |
| `/git` | Git status |
| `/skills` | Available skills |
| `/tasks` | Task queue |
| `/local` | Local execution settings |
| `/restore` | List/restore snapshots |
| `/revert` | Revert turns |

## Keyboard Shortcuts (TUI)

### Leader Key System (Ctrl+X)

Press `Ctrl+X`, then within `leader_timeout` (default 2s), press:

| Sequence | Action |
|----------|--------|
| `Ctrl+X N` | New session |
| `Ctrl+X U` | Undo |
| `Ctrl+X R` | Redo |
| `Ctrl+X C` | Compact context |
| `Ctrl+X M` | List models |
| `Ctrl+X T` | Theme selector |
| `Ctrl+X S` | Status overview |
| `Ctrl+X E` | Open editor |
| `Ctrl+X X` | Export session |
| `Ctrl+X B` | Toggle sidebar |
| `Ctrl+X A` | Agent list |
| `Ctrl+X L` | Sessions list |
| `Ctrl+X Q` | Quit |

### Direct Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Cycle primary agents |
| `Shift+Tab` | Cycle agents (reverse) |
| `Ctrl+P` | Command palette |
| `Ctrl+K` | Model selector |
| `Ctrl+L` | Clear messages |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+T` | Cycle reasoning variants |
| `Ctrl+Q` | Quit |
| `Escape` | Close overlay |
| `?` | Help panel |
| `@` | File references (fuzzy search) |
| `!` | Bash commands inline |
| `PageUp` / `PageDown` | Scroll messages |

## @mentions

Subagents can be invoked via `@mention` in your messages:

```
@reviewer review the changes in auth.ts
@general search for all API endpoints
@explore find all TypeScript type definitions
@scout check the React documentation
```

## Custom Commands

Define custom commands via markdown files:

```markdown
---
description: Run tests with coverage
agent: build
---
Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

Place in `~/.config/apex/commands/` (global) or `.apex/commands/` (project).
Filename becomes command name: `test.md` → `/test`.

### Template Variables

- `$ARGUMENTS` — All arguments joined
- `$1`, `$2`, `$3` — Positional arguments
- `!command` — Inline shell execution (output injected)
- `@file` — Include file content

### Built-in Defaults (overridable)

| Command | Description |
|---------|-------------|
| `/test` | Run tests with coverage |
| `/review` | Review current changes |
| `/commit` | Commit with AI message |
| `/docs` | Generate documentation |
