# APEX — Agent for Programming EXecution

*Built in Gabon 🇬🇦 for the world.*

APEX is a production-grade, terminal-native AI coding agent that works with **any LLM** via a unified interface powered by litellm.

## Features

- **85+ Models** — Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more
- **Multi-Agent System** — Build, Plan, Explore, General with permission controls
- **75+ Tools** — File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB
- **Rich Terminal UI** — Syntax highlighting, markdown rendering, panels
- **Session Persistence** — Save and load conversations
- **Token Cost Tracking** — Monitor usage and estimated costs
- **Plugin System** — Extensible with custom tools
- **Undo/Redo** — Revert and reapply changes
- **LSP Integration** — Go to definition, references, hover, diagnostics
- **Custom Commands** — Define reusable prompt templates

## Why APEX?

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

## Installation

```bash
pip install apex-agent
```

## Quick Start

```bash
# Interactive REPL
apex

# One-shot prompt
apex "write a hello world program"

# Specific model
apex --model gpt-4o "explain this code"
```

## Development

```bash
# Clone and setup
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
pip install -e .

# Run tests
pytest

# Run with coverage
pytest --cov=apex --cov-report=term-missing

# Lint check
ruff check apex/
```

## Philosophy

APEX is built by a Gabonese developer for the world. Every developer deserves a world-class coding agent — regardless of which model they can afford.

- **Complete code, no truncation** — Never use `...rest of file...`
- **Production-ready** — Full error handling, tests, type hints
- **Language-agnostic** — Python, JavaScript, Rust, Go, etc.
- **Senior developer mindset** — Opinionated, but effective
- **Testable by default** — 572 tests, 52% coverage on refactored modules

## Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](quickstart.md) | Get running in 5 minutes |
| [Installation](installation.md) | Setup guide |
| [Commands](commands.md) | Slash commands, @mentions, shortcuts |
| [Configuration](configuration.md) | Config file options |
| [Models](models.md) | 85+ supported models |
| [Tools](tools.md) | 40+ built-in tools reference |
| [Agents](agents.md) | Multi-agent system |
| [Plugins](plugins.md) | Plugin system |
| [Advanced](advanced.md) | MCP, custom tools, workspace |
| [API Reference](api.md) | Python API |
| [Examples](examples.md) | Complete config examples |
| [Troubleshooting](troubleshooting.md) | Common issues |

## Contributing

| File | Description |
|------|-------------|
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |
| [CHANGELOG.md](../CHANGELOG.md) | Version history |
| [SECURITY.md](../SECURITY.md) | Security policy |