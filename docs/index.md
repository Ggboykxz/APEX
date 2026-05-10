# APEX — Agent for Programming EXecution

*Built in Gabon 🇬🇦 for the world.*

APEX is a production-grade, terminal-native AI coding agent that works with **any LLM** via a unified interface powered by litellm.

## Features

### Core
- **100+ Models** — Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more
- **Multi-Agent System** — Coder, Architect, Reviewer, DevOps, Analyst with permission controls
- **75+ Tools** — File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB
- **Rich Terminal UI** — Syntax highlighting, markdown rendering, panels
- **Session Persistence** — Save and load conversations
- **Token Cost Tracking** — Monitor usage and estimated costs

### Security
- **Shell Command Analysis** — Dangerous commands blocked automatically
- **Permission System** — Ruleset-based tool access control (allow/deny/ask)
- **Rate Limiting** — Per-key limits with SQLite persistence
- **API Key Management** — Workspace-based keys with expiration
- **Billing System** — Cost tracking and quota management

### TUI Modes
- **New OpenTUI-like TUI** — Route-based navigation with themes and keymaps
- **Classic Textual TUI** — Original APEX UI
- **Bun-based OpenTUI** — JavaScript frontend

```bash
apex --new-tui  # New Python TUI (recommended)
apex --ui       # Original Textual TUI
apex --tui      # Bun-based OpenTUI
```

## Why APEX?

| Feature | APEX | OpenCode | Claude Code | Aider |
|---------|:----:|:--------:|:-----------:|:-----:|
| All models via one CLI | ✅ | ⚠️ | ❌ | ⚠️ |
| Shell security analysis | ✅ | ❌ | ❌ | ❌ |
| Permission system | ✅ | ❌ | ❌ | ❌ |
| API key management | ✅ | ❌ | ❌ | ❌ |
| Rate limiting | ✅ | ❌ | ❌ | ❌ |
| Billing & cost tracking | ✅ | ❌ | ❌ | ⚠️ |
| OpenTUI-like TUI | ✅ | ❌ | ❌ | ❌ |
| 6 built-in themes | ✅ | ❌ | ❌ | ❌ |
| Offline (Ollama) | ✅ | ❌ | ❌ | ✅ |
| Rich syntax UI | ✅ | ✅ | ✅ | ❌ |
| Session persistence | ✅ | ❌ | ✅ | ❌ |
| Model switch mid-session | ✅ | ❌ | ❌ | ⚠️ |

## Installation

```bash
pip install apex-ai
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

## Security Quick Start

APEX includes comprehensive security features:

```bash
# Run with restrictive permissions
apex --permission-mode strict

# Run with API authentication
export APEX_API_KEY=your_key
apex --http-api --require-auth
```

### Shell Security

APEX analyzes shell commands before execution:

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
print(analysis.safe)  # False
print(analysis.category)  # CommandCategory.DANGEROUS
```

**Blocked commands:**
- `rm -rf /` — System deletion
- `curl | sh` — Download and execute
- Fork bombs, direct disk writes

### Permission System

```python
from apex.permission import permission_manager, PermissionAction

# Default: allow safe tools, ask for dangerous ones
permission_manager.add_rule("run_command", PermissionAction.ASK)

# Check before execution
can_execute, reason = permission_manager.can_execute_tool("run_command")
```

### Rate Limiting

```python
from apex.rate_limiter import create_rate_limiter

limiter = create_rate_limiter(use_sqlite=True)
result = limiter.check_rate_limit("user_123")
```

### API Keys

```python
from apex.api_key import create_key_manager

manager = create_key_manager()
workspace = manager.create_workspace("my-project", "user_123")
api_key, info = manager.create_key(workspace.workspace_id, "prod-key")
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
- **Security-first** — Multiple layers of protection

## Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](quickstart.md) | Get running in 5 minutes |
| [Installation](installation.md) | Setup guide |
| [Commands](commands.md) | Slash commands, @mentions, shortcuts |
| [Configuration](configuration.md) | Config file options |
| [Models](models.md) | 100+ supported models |
| [Tools](tools.md) | 75+ built-in tools reference |
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

---

*Made with ❤️ in Gabon 🇬🇦*