# APEX — Agent for Programming EXecution

*The last coding agent you'll ever need.*

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Version-0.6.0-purple.svg" alt="Version">
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
| Plugin system | ✅ | ❌ | ❌ | ❌ |
| Model switch mid-session | ✅ | ❌ | ❌ | ⚠️ |
| Token cost tracking | ✅ | ❌ | ❌ | ✅ |
| French/multilingual UI | ✅ | ❌ | ❌ | ❌ |

## Features

- **85+ Models** — Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more
- **Multi-Agent System** — Build, Plan, Explore, General agents with permission controls
- **31+ Tools** — File operations, git, web search, code execution, sandbox, MCP
- **Plugin System** — Extensible with custom tools and security scanner
- **Rich Terminal UI** — Syntax highlighting, markdown rendering, panels
- **Session Persistence** — Save and load conversations
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

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## License

MIT — Built in Gabon 🇬🇦 for the world.

---

<p align="center">
  Made with ❤️ in Gabon 🇬🇦
</p>