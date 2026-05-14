# APEX — Agent for Programming EXecution v2.0.0

*Built in Gabon 🇬🇦 for the world.*

> **APEX** is an AI coding agent inspired by OpenCode, terminal-first. It orchestrates 170+ LLM models via litellm, executes tools with a granular permission system, protects each modification with reversible snapshots, and now delivers the full OpenCode user experience.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [UI Modes](#3-ui-modes)
4. [Agents](#4-agents)
5. [CLI Commands](#5-cli-commands)
6. [Chat Loop](#6-chat-loop)
7. [Event Bus](#7-event-bus)
8. [Structured Memory (Parts)](#8-structured-memory-parts)
9. [Tool Registry](#9-tool-registry)
10. [Permission System](#10-permission-system)
11. [Snapshots & Undo/Redo](#11-snapshots--undoredo)
12. [Providers](#12-providers)
13. [LSP Integration](#13-lsp-integration)
14. [MCP Support](#14-mcp-support)
15. [Sessions & Sharing](#15-sessions--sharing)
16. [CI/CD Mode](#16-cicd-mode)
17. [Custom Commands](#17-custom-commands)
18. [Theme System](#18-theme-system)
19. [Formatters](#19-formatters)
20. [File Watcher](#20-file-watcher)
21. [Configuration](#21-configuration)
22. [Security](#22-security)

---

## 1. Overview

APEX is an **autonomous agent** capable of:

- Analyzing an entire codebase
- Reading, creating, and modifying files with precision
- Executing shell commands and interpreting results
- Running tests, reading errors, iterating automatically
- Requesting confirmation before destructive actions
- Managing multiple sessions in parallel
- Sharing sessions via public URLs
- Formatting code automatically
- Watching files for changes

```
┌──────────────────────────────────────────────────────────┐
│                        APEX v2.0.0                       │
│                                                          │
│   Frontend (TUI / REPL / API / Web)                     │
│          ↕  HTTP / SSE / stdin                           │
│   Backend (Python)                                       │
│   ├── Agent Loop (chat, tools, permissions)              │
│   ├── 11 Specialized Agents                             │
│   ├── Session Manager (SQLite/Memory)                    │
│   ├── Event Bus (typed events)                           │
│   ├── Provider Abstraction (170+ LLM providers)          │
│   ├── Tool Registry (read, write, edit, bash...)         │
│   ├── LSP Client (language intelligence)                 │
│   ├── MCP Client (external protocols)                    │
│   ├── Snapshot System (undo/redo Git-powered)            │
│   ├── Theme System (12 themes, dark/light)               │
│   ├── Formatter System (11 auto-formatters)              │
│   ├── File Watcher (configurable ignore patterns)        │
│   └── Share System (public URLs with sanitization)       │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Architecture

### Core Components

| Component | Description |
|-----------|-------------|
| `main.py` | CLI entry point, 20+ subcommands, TUI launcher |
| `agent.py` | Agent core, chat loop, LLM interaction |
| `tools.py` | 75+ built-in tools |
| `session.py` | Session management, persistence |
| `permission.py` | Permission system (ALLOW/DENY/ASK) |
| `shell_security.py` | Shell command analysis |
| `rate_limiter.py` | Rate limiting |
| `api_key.py` | API key management |
| `billing.py` | Cost tracking |
| `http_api.py` | 56 HTTP API endpoints |
| `config_v2.py` | Hierarchical JSON/JSONC config system |
| `theme_manager.py` | 12 themes, dark/light, custom themes |
| `share.py` | Session sharing with public URLs |
| `formatter.py` | 11 auto-formatters |
| `watcher.py` | Configurable file watcher |
| `commands_manager.py` | Custom commands via markdown |

### TUI Architecture (Ink + React)

```
tui-frontend/src/
├── App.tsx                # Root — render ApexApp
├── components/
│   ├── ApexApp.tsx        # Main layout — titlebar, chat, leader keys, palettes
│   ├── ChatPanel.tsx      # Message thread with streaming, @refs, !bash
│   ├── StatusBar.tsx      # In/Out/Total tokens, ctx%, $spent, agent
│   ├── Sidebar.tsx        # Agent list, session info
├── data/
│   └── apex-data.ts      # 35+ models, 8 agents, keybinds
└── theme/
    └── apex.ts            # Base theme colors
```

**HTTP SSE Flow:**
```
TUI (Ink/React) --POST /chat/stream--> HTTP Server (main.py -> http_api.py)
                                                     |
                                                     v
                                              agent.chat_streaming()
                                                     |
                                                     v
                                    SSE: data:{"chunk": "..."}
                                    SSE: data:{"usage": {prompt_tokens, completion_tokens}}
```

---

## 3. UI Modes

### TUI (Terminal User Interface) — Default

```bash
apex              # Launch TUI
apex tui          # Explicit TUI
apex --tui        # Flag style
```

Full Ink + React terminal UI with:
- Real-time token streaming
- Live cost tracking
- Context percentage monitoring
- Agent switching via Tab
- Command palette (Ctrl+P)
- Leader keys (Ctrl+X)
- @ file references
- ! bash inline
- Model selector (Ctrl+K)
- Theme selector (Ctrl+X+T)
- Session sharing
- Help overlay (?)

### CLI REPL

```bash
apex              # Launch TUI (default)
```

### One-shot / CI/CD

```bash
apex -p "Fix the auth bug"          # Quick prompt
apex -p "Generate tests" -f json    # JSON output
apex -p "Review code" -q            # Quiet mode
```

---

## 4. Agents

APEX has **11 specialized agents** in three categories:

### Primary Agents (Tab to cycle)

| Agent | Color | Mode | Tools | Description |
|-------|-------|------|-------|-------------|
| **Build** | Cyan `#00e5ff` | primary | ALL | Full-access development agent |
| **Plan** | Purple `#a855f7` | primary | Read-only | Architecture & planning analysis |
| **Shell** | Orange `#f97316` | primary | ASK for edits | Infrastructure, DevOps, CI/CD |
| **Shell** | Orange `#f97316` | primary | ASK for edits | Infrastructure, DevOps, CI/CD |

### Subagents (@mention to invoke)

| Agent | Color | Mode | Tools | Description |
|-------|-------|------|-------|-------------|
| **@reviewer** | Green `#22c55e` | subagent | Read-only | Code review & audit |
| **@general** | Blue `#3b82f6` | subagent | ALL | Multi-task assistant |
| **@explore** | Teal `#14b8a6` | subagent | Read-only | Codebase exploration |
| **@scout** | Pink `#ec4899` | subagent | Read-only | External docs research |

### System Agents (automatic, hidden)

| Agent | Role |
|-------|------|
| **@compaction** | Context window compression |
| **@title** | Session title generation |
| **@summary** | Session summary generation |

### Custom Agents

Define agents via markdown files in `.apex/agents/*.md` or `~/.config/apex/agents/*.md`:

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-5
temperature: 0.1
permission:
  edit: deny
  bash: deny
---
You are a code review agent. Focus on security, performance, and maintainability.
```

Or via JSON config:

```json
{
  "agent": {
    "code-reviewer": {
      "description": "Reviews code",
      "mode": "subagent",
      "permission": { "edit": "deny" }
    }
  }
}
```

---

## 5. CLI Commands

### Core

| Command | Description |
|---------|-------------|
| `apex` | Launch TUI (default) |
| `apex tui` | Launch TUI |
| `apex` | Launch TUI (default) |
| `apex run <prompt>` | Non-interactive mode |
| `apex serve` | Headless HTTP API server |
| `apex web` | Server + web interface |
| `apex models [provider]` | List models |

### Authentication

| Command | Description |
|---------|-------------|
| `apex auth login` | Interactive provider login |
| `apex auth list` | List configured providers |
| `apex auth logout` | Remove provider config |
| `apex connect` | Interactive provider configuration |

### Agent Management

| Command | Description |
|---------|-------------|
| `apex agent create` | Interactive agent creation wizard |
| `apex agent list` | List all agents |

### Session Management

| Command | Description |
|---------|-------------|
| `apex session list` | List sessions |
| `apex session delete <id>` | Delete session |
| `apex export <id>` | Export session as JSON |
| `apex import <file|url>` | Import session |
| `apex compact` | Compact current session |

### System

| Command | Description |
|---------|-------------|
| `apex upgrade` | Upgrade APEX |
| `apex uninstall` | Remove APEX |
| `apex stats` | Token & cost statistics |
| `apex db path` | Database path |
| `apex init` | Initialize project (AGENTS.md) |

### Integrations

| Command | Description |
|---------|-------------|
| `apex mcp add` | Add MCP server |
| `apex mcp list` | List MCP servers |
| `apex mcp auth` | Authenticate MCP server |
| `apex pr <number>` | Fetch & checkout PR |
| `apex attach <url>` | Attach to remote backend |

### Toggles

| Command | Description |
|---------|-------------|
| `apex details` | Toggle tool execution details |
| `apex thinking` | Toggle reasoning blocks |

### Global Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--model` | `-m` | Model alias |
| `--cwd` | `-C` | Working directory |
| `--version` | `-v` | Version |
| `--agent` | | Agent to use |
| `--continue` | | Resume last session |
| `--session` | `-s` | Session ID |
| `--fork` | | Fork session |
| `--format` | `-f` | Output format (text/json) |
| `--quiet` | `-q` | Quiet mode |
| `--port` | | Server port |
| `--print-logs` | | Print logs |
| `--log-level` | | Log level |
| `--pure` | | No tools mode |

---

## 6. Chat Loop

The central `chat()` function orchestrates APEX's autonomy:

```
1. PROCESS INPUT
   └── Convert message + attached files into structured parts

2. CONTEXT MANAGEMENT
   └── Check if approaching token limit
       → If yes: auto-compact via lightweight model

3. AI CALL
   └── Send context + available tools to the LLM
       → Stream response token by token

4. TOOL EXECUTION
   └── If AI calls a tool:
       a. Check permissions (agent-specific)
       b. Create snapshot (backup before modification)
       c. Execute tool
       d. Return result to AI
       e. AI continues (loop until termination)

5. STATE UPDATE
   └── Persist everything to database
       → Publish events on the bus for frontends
```

---

## 7. Event Bus

APEX is built on a **strongly typed event bus**:

```python
from apex.tui.contexts.event_context import EventBus

bus = EventBus()

# Subscribe
bus.on("session_updated", handler_function)
bus.on("file_changed", on_file_change)

# Emit
bus.emit("session_updated", session_data)
bus.emit("file_changed", file_path="src/main.py")
```

### Typed Events

| Event | Description |
|-------|-------------|
| `session_updated` | Session modified |
| `session_created` | New session |
| `session_deleted` | Session deleted |
| `file_changed` | File modified |
| `message_added` | New message |
| `tool_executed` | Tool executed |
| `tool_error` | Tool error |
| `permission_requested` | Permission requested |
| `permission_granted` | Permission granted |
| `permission_denied` | Permission denied |
| `theme_changed` | Theme changed |
| `route_changed` | Route changed |
| `tui_ready` | TUI started |
| `tui_exit` | TUI closed |

---

## 8. Structured Memory (Parts)

Messages with typed parts:

```python
@dataclass
class MessagePart:
    part_type: str  # text, file, tool_call, tool_result, image
    content: Any

@dataclass
class Message:
    id: str
    role: str  # user, assistant, tool
    parts: List[MessagePart]
    token_usage: Optional[TokenUsage]
    cost_usd: Optional[float]
```

### Part Types

| Part | Description |
|------|-------------|
| `text` | Message text |
| `file` | Referenced file (path + content) |
| `tool_call` | Tool invocation (name + params) |
| `tool_result` | Tool result |
| `image` | Uploaded image |
| `snapshot` | Snapshot reference before modification |

---

## 9. Tool Registry

### Native Tools (75+)

| Tool | Description | Security |
|------|-------------|----------|
| `read_file` | Read a file | Binary detection, size limit |
| `write_file` | Create/overwrite a file | Permission + snapshot |
| `edit_file` | Surgical modification | Permission + snapshot |
| `bash` | Execute shell command | Security parsing, sandbox |
| `grep` | Search codebase | Read-only |
| `glob` | List files by pattern | Read-only |
| `read_directory` | List directory | Read-only |
| `search` | Web search | Read-only |
| `format_file` | Auto-format code | Via formatter system |
| `mcp_*` | MCP tools | Via MCP client |

### Tool Call Flow

```
AI → "I'll modify src/auth.ts"
  ↓
Tool Registry → check agent permission
  ↓ (if allowed)
Snapshot → create Git snapshot
  ↓
Tool Execute → modify file
  ↓
Formatter → auto-format if enabled
  ↓
LSP Client → diagnostics
  ↓
Bus.publish(FileChanged)
  ↓
Result → AI (with diagnostics)
  ↓
AI continues or terminates
```

---

## 10. Permission System

### Actions

| Action | Description |
|--------|-------------|
| `ALLOW` | Auto-approved without confirmation |
| `DENY` | Refused |
| `ASK` | Confirmation requested |

### Per-Agent Configuration

```python
from apex.agents import agent_manager

# Check if agent can execute a tool
can_execute, reason = agent_manager.can_execute_tool(
    "architect", "write_file"
)
# (False, "Tool 'write_file' is denied for agent 'architect'")
```

### Global Rules

```python
from apex.permission import permission_manager, PermissionAction

permission_manager.add_rule(
    "write_file",
    PermissionAction.ASK,
    pattern="/src/**"
)
```

### Bash Command Patterns

Glob patterns for fine-grained bash control:

```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git status *": "allow",
      "grep *": "allow"
    }
  }
}
```

---

## 11. Snapshots & Undo/Redo

Before each destructive action:

```python
from apex.snapshot import SnapshotManager

snapshot_mgr = SnapshotManager(cwd="/project")

# Create snapshot
snapshot_id = await snapshot_mgr.track()

# Get diff
patches = await snapshot_mgr.patch(snapshot_id)

# Restore if needed
await snapshot_mgr.restore(snapshot_id)
```

### Commands

```bash
/undo           # Undo last action
/redo           # Redo undone action
Ctrl+X + U      # Undo (TUI)
Ctrl+X + R      # Redo (TUI)
```

---

## 12. Providers

### Supported (170+)

| Provider | Models |
|----------|--------|
| Anthropic | claude-sonnet-4-5, claude-opus-4-5, claude-haiku-4-5 |
| OpenAI | gpt-4o, gpt-4o-mini, gpt-5, o1, o3, o4-mini |
| Google | gemini-2.5-pro, gemini-2.5-flash, gemini-3-flash |
| Groq | llama-groq-4, mixtral-groq, qwq-groq |
| DeepSeek | deepseek-chat, deepseek-reasoner, deepseek-v4 |
| xAI | grok-3, grok-4 |
| Mistral | codestral, pixtral, ministral, mixtral |
| Meta | llama-4-maverick, llama-4-scout |
| Qwen | qwen3-235b, qwen3-coder, qwq-plus |
| Cohere | command-a, command-a-reasoning |
| Ollama | llama3, codellama, deepseek-r1 (local) |
| OpenRouter | 200+ models via single API |
| And 100+ more via litellm |

### Configuration

```bash
# Environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GROQ_API_KEY=gsk_...

# CLI
apex --model claude-sonnet-4-5
apex --model gpt-4o
apex --model ollama-llama3  # Local, no API key

# Interactive
apex connect                 # Provider configuration wizard
apex auth login              # Interactive login
```

---

## 13. LSP Integration

LSP = Language Server Protocol for syntactic intelligence:

```python
from apex.lsp import LSPClient

lsp = LSPClient(cwd="/project")

# Diagnostics after modification
diagnostics = await lsp.get_diagnostics("src/main.ts")
# [{error: "Type 'string' not assignable to 'number'", line: 42}]

# References
refs = await lsp.find_references("src/utils.ts", symbol="helper")
```

**Impact**: After modification, APEX retrieves TypeScript/Lint errors and can fix them in the same iteration.

---

## 14. MCP Support

MCP = Model Context Protocol for external tools:

```python
# MCP Configuration
mcp_config = {
    "servers": [
        {
            "name": "github",
            "command": "npx @modelcontextprotocol/server-github"
        }
    ]
}
```

MCP tools available as native tools via `apex mcp add/list/auth`.

---

## 15. Sessions & Sharing

### Persistence

```python
from apex.session import SessionManager

manager = SessionManager()

# Create session
session = manager.create_session(project_path="/path/to/project")

# Save / Load / List
manager.save_session(session)
loaded = manager.load_session(session_id)
sessions = manager.list_sessions()
```

### Multi-session

```python
s1 = manager.create_session(project="/proj", name="feature-auth")
s2 = manager.create_session(project="/proj", name="refactor-payment")

# Switch
manager.switch_session(s2.id)
```

### Sharing

```bash
/share          # Create shareable URL → https://apex-ai.dev/s/abc123
/unshare        # Remove shared session
```

**3 modes**: `manual` (default), `auto`, `disabled` (configurable in `apex.json`)

**Export/Import**:
```bash
apex export <session_id>       # Export as JSON
apex import <file.json>        # Import from file
apex import https://apex-ai.dev/s/abc123  # Import from URL
```

---

## 16. CI/CD Mode

```bash
# Single prompt, JSON output
apex -p "Check this diff for security issues" -f json

# Non-interactive
apex run "Analyze this PR"

# With specific model/agent
apex -p "Generate changelog" --model gpt-4o -f json
apex run "Review this code" --agent reviewer
```

### Flags

| Flag | Description |
|------|-------------|
| `-p "prompt"` | Direct prompt without TUI |
| `-f json` | Structured JSON output |
| `-q` | Quiet mode |
| `--model` | Model to use |
| `--agent` | Agent to use |
| `--continue` | Continue last session |

---

## 17. Custom Commands

### Structure

```
~/.config/apex/commands/       # Global commands
.apex/commands/                # Project commands
```

### Command Format (Markdown)

```markdown
---
description: Run tests with coverage
agent: build
model: anthropic/claude-sonnet-4-5
---
Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

### Template Variables

- `$ARGUMENTS` — All arguments joined
- `$1`, `$2`, `$3` — Positional arguments
- `!command` — Inline shell execution
- `@file` — Include file content

### Built-in Commands

| Command | Description |
|---------|-------------|
| `/test` | Run tests with coverage |
| `/review` | Review current changes |
| `/commit` | Commit with AI message |
| `/docs` | Generate documentation |

All built-in commands can be overridden with custom markdown files.

---

## 18. Theme System

### Built-in Themes (12)

| Theme | Description |
|-------|-------------|
| `apex` | Default dark cyan theme |
| `nord` | Based on Nord palette |
| `catppuccin` | Catppuccin Mocha |
| `catppuccin-macchiato` | Catppuccin Macchiato |
| `tokyonight` | TokyoNight theme |
| `gruvbox` | Gruvbox dark |
| `everforest` | Everforest |
| `kanagawa` | Kanagawa |
| `ayu` | Ayu dark |
| `one-dark` | Atom One Dark |
| `matrix` | Hacker green-on-black |
| `system` | Adapts to terminal colors |

### Custom Themes

Create JSON files in `~/.config/apex/themes/` or `.apex/themes/`:

```json
{
  "theme": {
    "primary": { "dark": "#88C0D0", "light": "#5E81AC" },
    "text": { "dark": "#D8DEE9", "light": "#2E3440" },
    "background": { "dark": "#2E3440", "light": "#ECEFF4" }
  }
}
```

### Theme Colors

Each theme defines: primary, secondary, accent, error, warning, success, info, text, textMuted, background, backgroundPanel, backgroundElement, border, borderActive, diff colors, markdown colors, and syntax highlighting colors (comment, keyword, function, string, number, type).

### Switching

```bash
# TUI
Ctrl+X + T   # Theme selector

# Config
echo '{"theme": "nord"}' > ~/.config/apex/tui.json
```

---

## 19. Formatters

### Built-in Formatters (11)

| Language | Formatter | Command |
|----------|-----------|---------|
| Python | ruff | `ruff format $FILE` |
| JavaScript/TypeScript | prettier | `npx prettier --write $FILE` |
| JSON/YAML/Markdown | prettier | `npx prettier --write $FILE` |
| Rust | rustfmt | `rustfmt $FILE` |
| Go | gofmt | `gofmt -w $FILE` |
| Java | google-java-format | if available |
| C/C++ | clang-format | if available |
| Ruby | rubocop | `rubocop -a $FILE` |
| Scala | scalafmt | if available |
| Kotlin | ktlint | if available |
| Swift | swift-format | if available |
| Zig | zig fmt | `zig fmt $FILE` |

### Configuration

```json
{
  "formatter": true    // Enable all
}
```

```json
{
  "formatter": {
    "prettier": { "disabled": true },
    "custom-fmt": {
      "command": ["my-formatter", "--write", "$FILE"],
      "extensions": [".xyz"]
    }
  }
}
```

---

## 20. File Watcher

Background file watching with configurable ignore patterns:

### Default Ignore Patterns

```
**/node_modules/**
**/.git/**
**/__pycache__/**
**/.venv/**
**/venv/**
**/dist/**
**/build/**
**/.next/**
**/target/**
```

### Configuration

```json
{
  "watcher": {
    "ignore": ["**/node_modules/**", "**/.git/**", "custom_dir/**"]
  }
}
```

The watcher respects `.gitignore`, uses polling with 1s interval and 300ms debounce.

---

## 21. Configuration

### Hierarchical Config

```
Precedence (later overrides earlier):
  1. ~/.config/apex/apex.json(c)    Global config
  2. $APEX_CONFIG                    Custom path
  3. ./apex.json(c)                  Project config
  4. $APEX_CONFIG_CONTENT            Inline JSON
```

### TUI Config (separate)

`~/.config/apex/tui.json`:

```json
{
  "theme": "nord",
  "keybinds": { "leader": "ctrl+x", "command_list": "ctrl+p" },
  "scroll_speed": 3,
  "scroll_acceleration": { "enabled": false },
  "diff_style": "auto",
  "mouse": true,
  "leader_timeout": 2000
}
```

### Full apex.json Schema

```json
{
  "$schema": "https://apex-ai.dev/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "provider": { "anthropic": { "timeout": 600000 } },
  "agent": {},
  "command": {},
  "server": { "port": 8080, "hostname": "127.0.0.1" },
  "permission": {},
  "tools": {},
  "lsp": false,
  "mcp": {},
  "plugin": [],
  "formatter": false,
  "snapshot": true,
  "autoupdate": true,
  "share": "manual",
  "shell": "/bin/bash",
  "compaction": { "auto": false, "prune": false, "reserved": 10 },
  "watcher": { "ignore": ["**/node_modules/**", "**/.git/**"] },
  "theme": "apex",
  "keybinds": {},
  "instructions": [],
  "disabled_providers": [],
  "enabled_providers": [],
  "default_agent": "build"
}
```

### Variables

```json
{
  "model": "{env:APEX_MODEL}",
  "provider": {
    "anthropic": { "apiKey": "{file:~/.secrets/anthropic-key}" }
  }
}
```

---

## 22. Security

| Feature | Description |
|---------|-------------|
| Shell Security | Detects dangerous commands (rm -rf, curl|sh) |
| Permission System | ALLOW/DENY/ASK per tool, per agent |
| Rate Limiting | Per-key limits (minute/hour/day) |
| API Key Management | Keys with expiration |
| Billing | Cost tracking per session |
| Share Sanitization | API keys stripped from shared data |

### Shell Security

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
# safe: False, category: DANGEROUS
```

### Rate Limiting

```python
from apex.rate_limiter import create_rate_limiter
limiter = create_rate_limiter(use_sqlite=True)
result = limiter.check_rate_limit("user_123")
```

---

## Project Status

- **Version**: 1.5.0
- **Tests**: 2094 passing
- **License**: Proprietary — All rights reserved (see [LICENSE](LICENSE))

## Installation

```bash
pip install apex-ai
pipx install apex-ai
git clone https://github.com/Ggboykxz/APEX && cd APEX && pip install -e .
```

## Launch

```bash
apex                        # TUI (default)
apex "prompt"              # One-shot
apex                        # Launch TUI (default)
apex --model gpt-4o        # Specific model
apex --agent architect     # Read-only mode
apex -p "prompt" -f json   # CI/CD mode
```

### TUI — Live Metrics

| Metric | Location | Description |
|--------|----------|-------------|
| `msgs: 12 · 2.3% ctx · $0.05` | Title bar | Message count, ctx%, total cost |
| `In: 1234 Out: 567 Total: 1801 · 2.3% ctx · $0.05` | Status bar | Live tokens + ctx% + $total |
| `+42/+128 · $0.0023` | Chat message | Per-message tokens + cost |

### TUI Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle primary agents |
| `Ctrl+P` | Command palette |
| `Ctrl+K` | Model selector |
| `Ctrl+X` | Leader key (prefix) |
| `?` | Help panel |
| `@` | File references |
| `!` | Bash commands |
| `Ctrl+L` | Clear messages |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+Q` | Quit |
| `Ctrl+T` | Cycle reasoning |
| `Escape` | Close overlay |

---

*Made with ❤️ in Gabon 🇬🇦*
*APEX v2.0.0 — Inspired by OpenCode, built for everyone*
