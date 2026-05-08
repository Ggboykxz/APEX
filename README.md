# APEX — Agent for Programming EXecution

*The last coding agent you'll ever need.*

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Version-1.3.0-purple.svg" alt="Version">
  <img src="https://img.shields.io/github/stars/Ggboykxz/APEX?style=social" alt="Stars">
</p>

APEX is a production-grade, terminal-native AI coding agent built in **Gabon 🇬🇦 for the world**. It works with **any LLM** via litellm, making it the most flexible coding assistant available.

## Why APEX?

APEX is designed to be objectively better than OpenCode, Claude Code, Aider, and Cursor CLI combined:

| Feature | APEX | OpenCode | Claude Code | Aider |
|---------|:----:|:--------:|:-----------:|:-----:|
| All models via one CLI | ✅ | ⚠️ | ❌ | ⚠️ |
| No cloud lock-in | ✅ | ❌ | ❌ | ✅ |
| Offline (Ollama) | ✅ | ❌ | ❌ | ✅ |
| Rich syntax UI | ✅ | ✅ | ✅ | ❌ |
| Session persistence | ✅ | ❌ | ✅ | ❌ |
| Session sharing | ✅ | ✅ | ❌ | ❌ |
| Undo/Redo | ✅ | ✅ | ❌ | ❌ |
| LSP integration | ✅ | ✅ | ❌ | ❌ |
| Code actions/fixes | ✅ | ✅ | ❌ | ❌ |
| Plan approval workflow | ✅ | ✅ | ❌ | ❌ |
| Project initialization | ✅ | ✅ | ❌ | ❌ |
| Slash commands | ✅ | ✅ | ❌ | ❌ |
| @Mentions | ✅ | ✅ | ❌ | ❌ |
| Auto-completion | ✅ | ✅ | ❌ | ❌ |
| Persistent shell | ✅ | ❌ | ❌ | ❌ |
| Git branch ops | ✅ | ❌ | ❌ | ✅ |
| Inline editing | ✅ | ✅ | ❌ | ❌ |
| Plugin system | ✅ | ❌ | ❌ | ❌ |
| Model switch mid-session | ✅ | ❌ | ❌ | ⚠️ |
| Token cost tracking | ✅ | ❌ | ❌ | ✅ |
| Custom commands | ✅ | ✅ | ❌ | ❌ |
| Multi-file selection | ✅ | ❌ | ❌ | ❌ |
| French/multilingual UI | ✅ | ❌ | ❌ | ❌ |

## Features

- **85+ Models** — Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more
- **Multi-Agent System** — Build, Plan, Explore, General agents with permission controls
- **75+ Tools** — File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB, docs
- **LSP Integration** — Go to definition, references, hover, diagnostics, code actions
- **Project Initialization** — Analyze and create AGENTS.md with smart context
- **Undo/Redo** — Revert and reapply file changes
- **Session Sharing** — Share sessions via link for collaboration
- **Plan Approval** — Approve/reject plans before execution
- **Plugin System** — Extensible with custom tools and security scanner
- **Custom Commands** — Define reusable prompt templates
- **Persistent Shell** — Interactive shell sessions across commands
- **Multi-file Selection** — Select files by glob patterns for context
- **Slash Commands** — 20+ commands like /agent, /model, /git, /init
- **@Mentions** — @file for file context, @agent for subagents
- **Auto-completion** — Tab completion for files, commands, agents, models
- **Git Branch Operations** — Create, switch, delete branches, PR creation
- **Inline Editing** — Edit at specific line number
- **Skills System** — Reusable prompt templates
- **Diff Tool** — Compare files and 3-way merge
- **Search & Replace** — Regex replace across files
- **Code Analysis** — Functions, classes, complexity
- **Test Generation** — Auto-generate pytest/jest tests
- **Git Hooks** — Configure pre-commit hooks
- **Batch Operations** — Read/write multiple files at once
- **File Watching** — Watch for file changes in real-time
- **Retry with Backoff** — Automatic retry for failed operations
- **Tool Timeout** — Configure per-tool timeouts
- **Context Optimization** — Smart message prioritization
- **Shell Expansion** — Variable expansion in commands
- **Environment Manager** — Manage env variables per workspace
- **Task Queue** — Async task execution
- **History Search** — Fuzzy search conversation history
- **Workspace Validation** — Config and structure validation
- **Security Audit** — Scan for security vulnerabilities
- **Code Refactoring** — AI-powered refactoring (async, types, extract)
- **Database Models** — Generate SQLAlchemy models from schema
- **Docker Generation** — Dockerfile and docker-compose generator
- **API Client Generator** — Generate client from OpenAPI spec
- **Documentation Generator** — Auto-generate README, API docs
- **Performance Profiling** — Code complexity analysis
- **Optimization Suggestions** — AI-powered performance tips
- **File Caching** — Cache file reads for performance
- **Rich Terminal UI** — Syntax highlighting, markdown, panels
- **Session Persistence** — Save/load conversations
- **Token Cost Tracking** — Monitor usage and estimated costs
- **Workspace Awareness** — Git context, branch, PR information
- **One-shot Mode** — Run prompts non-interactively

## Installation

```bash
pip install apex-agent
# or
pipx install apex-agent
```

## Quick Start

```bash
# Interactive REPL
apex

# One-shot prompt
apex "fix the bug in app.py"

# Specific model
apex --model gpt-4o "write a hello world program"

# List available models
apex --list-models
```

## Configuration

Create `~/.apex/config.json`:
```json
{
  "model": "claude-4-sonnet",
  "cwd": "/home/user/projects",
  "max_tool_rounds": 20
}
```

Create `~/.apex/.env` with your API keys:
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=...
```

## Commands

| Command | Description |
|---------|-------------|
| `/agent [name]` | Switch agent (build/plan) |
| `/agents` | List all agents |
| `/subagents` | List subagents |
| `/model <alias>` | Switch model |
| `/models` | List all models |
| `/cwd <path>` | Change directory |
| `/map` | Show repository map |
| `/git` | Show git status |
| `/clear` | Clear history |
| `/save [name]` | Save session |
| `/load <name]` | Load session |
| `/help` | Show help |

## Architecture

```
User Input (prompt_toolkit)
       │
       ▼
  ┌─────────────┐
  │  main.py    │  ← Parses /commands, routes to agent
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐       ┌──────────────────┐
  │  agent.py   │──────▶│  litellm.completion│  ← All models unified
  └──────┬──────┘       └──────────────────┘
         │
         │  tool_calls? ──▶ ToolExecutor (tools.py)
         │                       ├── read_file
         │                       ├── write_file
         │                       ├── edit_file
         │                       ├── run_command
         │                       └── ... (31+ tools)
         │
         ▼
  ┌─────────────┐
  │    ui.py    │  ← Rich rendering
  └─────────────┘
```

## Tech Stack

- **Python 3.11+** — Core language
- **litellm** — Unified model interface (100+ models)
- **Rich** — Terminal UI
- **prompt_toolkit** — Interactive REPL

## Documentation

See the [docs/](docs/) directory for complete documentation:

| Document | Description |
|----------|-------------|
| [docs/installation.md](docs/installation.md) | Installation and setup |
| [docs/commands.md](docs/commands.md) | CLI commands and REPL shortcuts |
| [docs/configuration.md](docs/configuration.md) | Config file options |
| [docs/models.md](docs/models.md) | Supported models and aliases |
| [docs/tools.md](docs/tools.md) | Built-in tools reference |
| [docs/agents.md](docs/agents.md) | Multi-agent system |
| [docs/plugins.md](docs/plugins.md) | Plugin system |
| [docs/advanced.md](docs/advanced.md) | MCP, custom tools, workspace awareness |
| [docs/api.md](docs/api.md) | Python API |
| [docs/examples.md](docs/examples.md) | Complete config examples |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and solutions |

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## License

MIT — Built in Gabon 🇬🇦 for the world.

---

<p align="center">
  Made with ❤️ in Gabon 🇬🇦
</p>