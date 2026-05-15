# APEX v2.0.0 — Agent for Programming EXecution

*Built in Gabon 🇬🇦 for the world.*

APEX is a production-grade, terminal-native AI coding agent that works with **any LLM** via a unified interface powered by litellm. Now featuring the full OpenCode user experience with WebSocket EventBus, random port binding, and real-time state synchronization.

## Features

### Core
- **170+ Models** — Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more
- **11 Specialized Agents** — 4 primary + 4 subagents + 3 system agents
- **75+ Tools** — File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB
- **Rich Terminal UI** — Ink + React with WebSocket EventBus, syntax highlighting, markdown rendering
- **Session Persistence** — Save, load, and share conversations
- **Token Cost Tracking** — Monitor usage and estimated costs

### OpenCode-like UX
- **Hierarchical JSON/JSONC Config** — Global → project → inline, with `{env:}` and `{file:}` variables
- **20+ CLI Subcommands** — serve, web, auth, agent create, session, stats, and more
- **Leader Keys** — Ctrl+X + mnemonic for all actions
- **Command Palette** — Ctrl+P with fuzzy search across 17+ commands
- **@ File References** — Fuzzy file search with `@filename`
- **! Bash Inline** — Run shell commands inline
- **12 Themes** — dark/light mode, custom themes
- **Session Sharing** — Public URLs for collaboration
- **11 Auto-Formatters** — ruff, prettier, gofmt, rustfmt, etc.
- **File Watcher** — Configurable ignore patterns

### Security
- **Shell Command Analysis** — Dangerous commands blocked automatically
- **Permission System** — Ruleset-based tool access control (allow/deny/ask)
- **Rate Limiting** — Per-key limits with SQLite persistence
- **API Key Management** — Workspace-based keys with expiration
- **Billing System** — Cost tracking and quota management
- **Share Sanitization** — API keys stripped from shared sessions

### TUI
- **Ink + React TUI** — Modern terminal UI with agent-colored theming, live metrics, WebSocket EventBus, and HTTP SSE backend
- **OpenCode Architecture** — Worker thread backend with random port, Event Bus for real-time sync, SQLite session storage
- **Leader Key System** — Ctrl+X prefix for all actions
- **Command Palette** — Ctrl+P fuzzy search
- **@ File References** — Fuzzy file search
- **! Bash Inline** — Shell command execution
- **Model Selector** — Ctrl+K overlay
- **Theme Selector** — Ctrl+X+T

```bash
apex                  # Launch TUI (default)
apex --model gpt-4o   # Specific model
apex --agent plan     # Read-only mode
apex serve            # HTTP API server
apex run "fix bugs"   # One-shot mode
```

## Quick Start

```bash
# 1. Install
pip install apex-ai

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Launch APEX
apex

# 4. Start coding
> fix the authentication bug in auth.py
> add TypeScript types to all functions
> write tests for the payment module

# 5. Share your session
/share
```

## Documentation

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Agents](agents.md)
- [Commands](commands.md)
- [Tools](tools.md)
- [API Reference](api.md)
- [Troubleshooting](troubleshooting.md)
