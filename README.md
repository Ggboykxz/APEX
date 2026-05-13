<div align="center">

# ◆ APEX v1.5.0

**The universal AI coding agent. Every model. One terminal.**

[![PyPI version](https://img.shields.io/pypi/v/apex-ai?color=00e5ff&style=flat-square)](https://pypi.org/project/apex-ai)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-00e5ff?style=flat-square)](https://python.org)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-ff4444?style=flat-square)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-00e5ff?style=flat-square)](https://github.com/Ggboykxz/APEX/pkgs/container/apex)
[![Stars](https://img.shields.io/github/stars/Ggboykxz/APEX?color=ffaa00&style=flat-square)](https://github.com/Ggboykxz/APEX/stargazers)

<br/>

[**Install**](#-installation) ·
[**Docs**](https://apex-ai.dev/docs) ·
[**CLI**](#-cli-commands) ·
[**Security**](#-security) ·
[**Models**](#-supported-models) ·
[**Sponsor**](#-sponsors)

</div>

---

> APEX runs **any LLM** in your terminal as a coding agent — Anthropic, OpenAI,
> Google, Groq, Mistral, DeepSeek, Ollama (local), and 170+ more via litellm.
> Switch models mid-session. Track costs live. Never leave your terminal.

---

## ✨ Why APEX?

| | APEX | OpenCode | Claude Code | Aider |
|---|:---:|:---:|:---:|:---:|
| Every model (170+) | ✅ | ⚠️ | ❌ | ⚠️ |
| 11 specialized agents | ✅ | ✅ | ❌ | ❌ |
| Primary + Subagent system | ✅ | ✅ | ❌ | ❌ |
| Hierarchical JSON config | ✅ | ✅ | ❌ | ❌ |
| 12 themes (dark/light) | ✅ | ✅ | ❌ | ❌ |
| Session sharing (URL) | ✅ | ✅ | ❌ | ❌ |
| Auto-formatting | ✅ | ✅ | ❌ | ❌ |
| Custom commands (.md) | ✅ | ✅ | ❌ | ❌ |
| Switch model mid-session | ✅ | ❌ | ❌ | ❌ |
| Works offline (Ollama) | ✅ | ❌ | ❌ | ✅ |
| Leader key shortcuts | ✅ | ✅ | ❌ | ❌ |
| Command palette (Ctrl+P) | ✅ | ✅ | ❌ | ❌ |
| @file references / !bash | ✅ | ✅ | ❌ | ❌ |
| Beautiful Ink TUI | ✅ | ✅ | ✅ | ❌ |
| Live token cost tracker | ✅ | ❌ | ❌ | ✅ |
| Shell security analysis | ✅ | ❌ | ❌ | ❌ |
| File watcher with ignores | ✅ | ✅ | ❌ | ❌ |
| `pip install` | ✅ | ❌ | ❌ | ✅ |
| Built in Africa 🇬🇦 | ✅ | ❌ | ❌ | ❌ |

---

## 🚀 Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Launch APEX (TUI auto-starts)
apex

# 3. Ask anything
> fix the authentication bug in auth.py
> add TypeScript types to all functions
> write tests for the payment module
```

### Switch models / agents anytime:

```bash
apex --model gpt-4o            # Start with GPT-4o
apex --model ollama-llama3      # Local, no API key needed
apex --agent architect          # Start in read-only architect mode
apex --continue                 # Resume last session
apex --session mysession        # Load a specific session
```

---

## 🎨 TUI — Terminal User Interface

APEX features a modern terminal UI built with [Ink](https://github.com/vadimdemedes/ink) (React for terminals). The TUI connects to the APEX backend via HTTP SSE for real-time token streaming, live cost tracking, and context percentage monitoring.

```bash
apex              # Launch TUI (default)
apex --model gpt-4o            # Start with GPT-4o
```

### Keybindings

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Cycle agents |
| `Ctrl+P` | Command palette |
| `Ctrl+K` | Model selector |
| `Ctrl+X` | Leader key (prefix) |
| `Ctrl+X N` | New session |
| `Ctrl+X U` | Undo |
| `Ctrl+X R` | Redo |
| `Ctrl+X C` | Compact context |
| `Ctrl+X M` | List models |
| `Ctrl+X T` | Theme selector |
| `Ctrl+X S` | Status overview |
| `Ctrl+X A` | Agent list |
| `Ctrl+X L` | Sessions list |
| `Ctrl+X B` | Toggle sidebar |
| `Ctrl+X E` | Open editor |
| `Ctrl+X X` | Export session |
| `Ctrl+X Q` | Quit |
| `@` | File references (fuzzy search) |
| `!` | Bash commands inline |
| `?` | Help panel |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+L` | Clear messages |
| `Ctrl+T` | Cycle reasoning variants |
| `Escape` | Close overlay |
| `Ctrl+Q` | Quit |

### Features
- **11 Agents**: 4 primary (Tab) + 4 subagents (@mention) + 3 system
- **170+ Models**: OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, xAI, etc.
- **Live Metrics**: Token streaming, per-message cost, total spent, context %
- **12 Themes**: apex, nord, catppuccin, tokyonight, gruvbox, matrix, etc.
- **Agent Theming**: Title bar and status bar change color per agent
- **75+ Tools**: File, Code, Shell, Git, Web, Database, Docker, K8s, Security
- **MCP/LSP**: Server status monitoring
- **Leader Keys**: Ctrl+X + mnemonic for all actions
- **Command Palette**: Ctrl+P with fuzzy search
- **@ References**: Fuzzy file search with `@filename`
- **! Bash**: Run shell commands inline with `!command`
- **HTTP Backend**: Local SSE server on port 8080

---

## 🎮 Agents

APEX has **11 specialized agents** organized by type:

### Primary Agents (Tab to cycle)
| Agent | Color | Description |
|-------|-------|-------------|
| **Coder** | Cyan | Full-access development agent with all tools |
| **Architect** | Purple | Architecture analysis & design (read-only) |
| **Planner** | Yellow | Planning & strategy (read-only) |
| **Shell** | Orange | Infrastructure, DevOps, CI/CD |

### Subagents (@mention to invoke)
| Agent | Description |
|-------|-------------|
| **@reviewer** | Code review & audit specialist |
| **@general** | General-purpose multi-task assistant |
| **@explore** | Fast read-only codebase exploration |
| **@scout** | External docs & dependency research |

### System Agents (automatic, hidden)
| Agent | Role |
|-------|------|
| **@compaction** | Context window compression |
| **@title** | Session title generation |
| **@summary** | Session summary generation |

Custom agents via Markdown files in `.apex/agents/*.md` or `~/.config/apex/agents/*.md`.

---

## 📋 CLI Commands

```bash
apex                          # Launch TUI (default)
apex run <prompt>             # Non-interactive mode
apex serve                    # Start headless HTTP API server
apex web                      # Server + web interface
apex gateway start            # Start APEX Gateway (proxy + auth + rate limits)
apex gateway key <tier>       # Generate a gateway API key
apex gateway status           # Show gateway keys and usage
apex auth login               # Interactive provider login
apex auth list                # List configured providers
apex auth logout              # Remove provider config
apex agent create             # Interactive agent wizard
apex agent list               # List all agents
apex session list             # List sessions
apex session delete <id>      # Delete a session
apex stats                    # Token usage & cost stats
apex export <id>              # Export session as JSON
apex import <file|url>        # Import session
apex upgrade                  # Upgrade APEX
apex uninstall                # Remove APEX
apex mcp add                  # Add MCP server
apex mcp list                 # List MCP servers
apex mcp auth <name>          # Authenticate MCP server
apex db path                  # Show database path
apex pr <number>              # Fetch & checkout PR
apex attach <url>             # Attach to remote backend
apex connect                  # Interactive provider config
apex init                     # Initialize project
apex compact                  # Compact context
apex details                  # Toggle tool output
apex thinking                 # Toggle reasoning blocks
apex models [provider]        # List models
apex --model <name>           # Set model
apex --agent <name>           # Set agent
apex --continue               # Resume last session
```

---

## 🔧 Configuration

APEX uses hierarchical JSON/JSONC config (like OpenCode):

```bash
# Global config
~/.config/apex/apex.json       # Main config
~/.config/apex/tui.json        # TUI-specific config

# Project config (overrides global)
./apex.json
./apex.jsonc

# Env vars (inline override)
APEX_CONFIG=./custom.json
APEX_CONFIG_CONTENT='{"model": "gpt-4o"}'
```

### apex.json schema

```json
{
  "$schema": "https://apex-ai.dev/config.json",
  "model": "claude-sonnet-4-5",
  "theme": "nord",
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices",
      "mode": "subagent",
      "permission": { "edit": "deny" }
    }
  },
  "command": {
    "test": {
      "template": "Run tests with coverage",
      "description": "Run tests"
    }
  },
  "permission": { "edit": "ask", "bash": "ask" },
  "formatter": true,
  "lsp": true,
  "share": "manual",
  "snapshot": true,
  "server": { "port": 8080, "hostname": "127.0.0.1" },
  "watcher": {
    "ignore": ["**/node_modules/**", "**/.git/**"]
  }
}
```

### Variables in config

```json
{
  "model": "{env:APEX_MODEL}",
  "provider": {
    "anthropic": { "apiKey": "{file:~/.secrets/anthropic-key}" }
  }
}
```

---

## 🛠️ What APEX Can Do

- **Read & edit files** — understands your whole codebase
- **Run commands** — tests, builds, installs, git
- **Search code** — grep-style across your project
- **11 agents** — specialized for different tasks
- **Subagents** — invoke via @mention for parallel tasks
- **Custom commands** — define via `.apex/commands/*.md`
- **Auto-formatting** — ruff, prettier, gofmt, rustfmt, etc.
- **File watching** — configurable ignore patterns
- **Session sharing** — public URLs for collaboration
- **Fix bugs** — diagnoses, patches, and verifies
- **Write features** — complete implementations
- **Refactor code** — preserves your style
- **Write tests** — pytest, jest, go test, and more
- **Explain code** — line by line if needed

---

## 🎭 Themes

12 built-in themes with dark/light mode support:

```
apex          ayu           catppuccin    catppuccin-macchiato
everforest    gruvbox       kanagawa      matrix
nord          one-dark      system        tokyonight
```

```bash
# Via TUI
Ctrl+X T         # Theme selector

# Via config
echo '{"theme": "nord"}' > ~/.config/apex/tui.json
```

Custom themes in `~/.config/apex/themes/*.json` or `.apex/themes/*.json`.

---

## 🔗 Session Sharing

Share conversations with your team:

```bash
/share          # Create shareable URL → https://apex-ai.dev/s/abc123
/unshare        # Remove shared session
```

Modes: `manual` (default) | `auto` | `disabled` (set in config)

---

## 🎨 Formatters

Auto-formatting support for 11 languages:

```
Python:     ruff
JS/TS/JSON: prettier
Rust:       rustfmt
Go:         gofmt
Java:       google-java-format
C/C++:      clang-format
Ruby:       rubocop
Scala:      scalafmt
Kotlin:     ktlint
Swift:      swift-format
Zig:        zig fmt
```

```bash
# Enable all formatters
echo '{"formatter": true}' > apex.json

# Per-formatter config
echo '{"formatter": {"prettier": {"disabled": true}}}' > apex.json
```

---

## 🔒 Security

APEX includes comprehensive security features:

### Shell Command Analysis
Blocks dangerous patterns: `rm -rf /`, `curl | sh`, fork bombs, disk writes.

### Permission System
Fine-grained ALLOW/DENY/ASK per tool with glob pattern support.

### Rate Limiting & API Keys
Database-backed rate limiting with workspace-based API keys.

### HTTP API Security
Bearer token auth on all endpoints, configurable via config.

---

## ⚡ Installation

### One-line install

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.ps1 | iex
```

### Package managers

| Method | Command |
|--------|---------|
| **uv** (fastest) | `uv tool install apex-ai` |
| **pipx** (isolated) | `pipx install apex-ai` |
| **pip** | `pip install apex-ai` |
| **Docker** | `docker run -it -v $(pwd):/workspace ghcr.io/ggboykxz/apex` |

### From source

```bash
git clone https://github.com/Ggboykxz/APEX
cd APEX
pip install -e ".[dev]"
```

---

## ⚡ APEX Gateway (Zero-Config Free Models)

APEX Gateway is a built-in proxy server that gives you access to free + paid models **without configuring API keys**.

```bash
# 1. Get your free OpenRouter API key
#    → https://openrouter.ai/keys (no credit card needed)

# 2. Add it to .env
echo "OPENROUTER_API_KEY=sk-or-v1-..." >> .env

# 3. Start the gateway
apex gateway start
# → Gateway running on http://127.0.0.1:9090

# 4. Generate user keys
apex gateway key free "alice"      # Free tier: 50 req/day
apex gateway key pro "bob"         # Pro tier: 500 req/day
```

### Tiers

| Tier | Req/day | Tokens/day | Req/min | Models |
|------|---------|------------|---------|--------|
| **Free** | 50 | 500K | 10 | Qwen3 Coder, Nemotron Super, DeepSeek R1, Gemma 4, Ring 2.6 1T... |
| **Pro** | 500 | 5M | 60 | GLM-5.1, Kimi K2.6, MiniMax M2.7, DeepSeek V4 Pro... |
| **Unlimited** | ∞ | ∞ | 300 | All models |

### API

```bash
# Register a new user
curl -X POST http://127.0.0.1:9090/v1/register \
  -H "Content-Type: application/json" \
  -d '{"tier": "free", "label": "new-user"}'

# Chat via gateway
curl -X POST http://127.0.0.1:9090/v1/chat/completions \
  -H "Authorization: Bearer apex_..." \
  -H "Content-Type: application/json" \
  -d '{"model": "free-or-qwen3-coder", "messages": [{"role": "user", "content": "Hello"}]}'

# Check usage
curl -H "Authorization: Bearer apex_..." http://127.0.0.1:9090/v1/status
```

---

## 🤖 Supported Models (170+)

### Bring Your Own Key (BYOK)

Use your own API keys from any provider:

<details>
<summary>Anthropic (Claude)</summary>

```bash
export ANTHROPIC_API_KEY=sk-ant-...
apex --model claude-sonnet-4-5   # Recommended
apex --model claude-opus-4-5     # Most powerful
apex --model claude-haiku-4-5    # Fastest
apex --model claude-sonnet-4-6   # Latest
apex --model claude-opus-4-7     # Most advanced
```
</details>

<details>
<summary>OpenAI (GPT / o-series)</summary>

```bash
export OPENAI_API_KEY=sk-...
apex --model gpt-4o
apex --model gpt-4o-mini
apex --model gpt-5
apex --model o3
apex --model o4-mini
```
</details>

<details>
<summary>Google (Gemini / Gemma)</summary>

```bash
export GEMINI_API_KEY=...
apex --model gemini-2.5-pro
apex --model gemini-2.5-flash
apex --model gemini-3-flash
apex --model gemma-4-31b
```
</details>

<details>
<summary>Groq (Ultra-fast inference)</summary>

```bash
export GROQ_API_KEY=gsk_...
apex --model llama-groq-4-maverick
apex --model mixtral-groq-8x7b
apex --model qwq-groq-32b
```
</details>

<details>
<summary>🔒 Ollama (100% local, no API key)</summary>

```bash
ollama pull llama3
apex --model ollama-llama3
apex --model ollama-deepseek-r1
apex --model ollama-qwen2.5-coder
```
</details>

<details>
<summary>DeepSeek</summary>

```bash
export DEEPSEEK_API_KEY=...
apex --model deepseek-chat
apex --model deepseek-reasoner
apex --model deepseek-v4-flash
apex --model deepseek-v4-pro
```
</details>

<details>
<summary>More providers</summary>

- **xAI**: grok-3, grok-4, grok-4-fast
- **Mistral**: codestral, pixtral, ministral, mixtral
- **Meta**: llama-4-maverick, llama-4-scout
- **Qwen**: qwen3-235b, qwen3-coder, qwq-plus
- **Cohere**: command-a, command-a-reasoning
- **Cerebras**: ultra-fast inference
- **Fireworks AI**: deepseek, qwen, kimi
- **Together AI**: deepseek, llama, qwen
- **Hugging Face**: open models
- **Perplexity**: sonar models
- **NVIDIA NIM**: enterprise models
- **Cloudflare Workers AI**: edge inference
- **OpenRouter**: 200+ models via single API
</details>

---

## 💖 Sponsors

APEX is free and open source. If it saves you time, consider sponsoring.

<div align="center">

### 🥇 Gold Sponsors
*Your logo here — [become a sponsor](https://github.com/sponsors/ggboykxz)*

### 🥈 Silver Sponsors
*Your logo here*

### 🥉 Individual Backers
*[Sponsor APEX →](https://github.com/sponsors/ggboykxz)*

</div>

---

## 🤝 Contributing

```bash
git clone https://github.com/Ggboykxz/APEX
cd APEX
pip install -e ".[dev]"
pytest
```

Customize with commands in `.apex/commands/*.md`, agents in `.apex/agents/*.md`, and themes in `.apex/themes/*.json`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

**Proprietary** — All rights reserved by Ggboykxz.

See [LICENSE](LICENSE) for full terms.

---

<div align="center">
<sub>If APEX helps you, please ⭐ the repo — it means everything to an indie developer.</sub>
</div>
