<div align="center">

# ◆ APEX

**The universal AI coding agent. Every model. One terminal.**

[![PyPI version](https://img.shields.io/pypi/v/apex-agent?color=00e5ff&style=flat-square)](https://pypi.org/project/apex-agent)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-00e5ff?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-00ff88?style=flat-square)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-00e5ff?style=flat-square)](https://github.com/Ggboykxz/APEX/pkgs/container/apex)
[![Stars](https://img.shields.io/github/stars/Ggboykxz/APEX?color=ffaa00&style=flat-square)](https://github.com/Ggboykxz/APEX/stargazers)

<br/>

[**Install**](#-installation) ·
[**Docs**](https://apex-agent.dev/docs) ·
[**Security**](#-security) ·
[**Models**](#-supported-models) ·
[**Sponsor**](#-sponsors)

</div>

---

> APEX runs **any LLM** in your terminal as a coding agent — Anthropic, OpenAI,
> Google, Groq, Mistral, DeepSeek, Ollama (local), and 100+ more via litellm.
> Switch models mid-session. Track costs live. Never leave your terminal.

---

## ✨ Why APEX?

| | APEX | OpenCode | Claude Code | Aider |
|---|:---:|:---:|:---:|:---:|
| Every model (100+) | ✅ | ⚠️ | ❌ | ⚠️ |
| Switch model mid-session | ✅ | ❌ | ❌ | ❌ |
| Works offline (Ollama) | ✅ | ❌ | ❌ | ✅ |
| Beautiful TUI | ✅ | ✅ | ✅ | ❌ |
| File tree + tool log | ✅ | ❌ | ❌ | ❌ |
| Command palette (⌘K) | ✅ | ❌ | ❌ | ❌ |
| Live token cost tracker | ✅ | ❌ | ❌ | ✅ |
| Session persistence | ✅ | ❌ | ✅ | ❌ |
| **Shell security** | ✅ | ❌ | ❌ | ❌ |
| **OpenTUI + React TUI** | ✅ | ❌ | ❌ | ❌ |
| **6 themes** (dracula, nord, etc.) | ✅ | ❌ | ❌ | ❌ |
| **Permission system** | ✅ | ❌ | ❌ | ❌ |
| **Rate limiting** | ✅ | ❌ | ❌ | ❌ |
| **API key management** | ✅ | ❌ | ❌ | ❌ |
| `pip install` | ✅ | ❌ | ❌ | ✅ |
| Built in Africa 🇬🇦 | ✅ | ❌ | ❌ | ❌ |

---

## 🎨 TUI

APEX features a modern terminal UI built with [OpenTUI](https://github.com/anomalyco/opentui) + React:

```bash
# Launch the TUI
apex --tui

# Or via npm
bun run tui

# Or directly
cd tui-frontend && bun run start
```

### Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Switch agent |
| `Ctrl+K` | Model selector |
| `Ctrl+O` | Toggle sidebar |
| `Ctrl+T` | Toggle tools panel |
| `?` | Help panel |
| `Escape` | Close overlay |
| `Ctrl+Q` | Quit APEX |

### Features
- **5 Agents**: Coder, Architect, Reviewer, DevOps, Analyst
- **100+ Models**: OpenAI, Anthropic, Google, Meta, Mistral, DeepSeek, xAI, etc.
- **75+ Tools**: File, Code, Shell, Git, Web, Database, Docker, K8s, Cloud, Security
- **MCP/LSP**: Server status monitoring
- **Theme**: Dark (#0d1117), Cyan (#00e5ff), Green (#00ff88)

---

## 🔒 Security

APEX includes comprehensive security features to protect your system:

### Shell Command Analysis

APEX analyzes shell commands before execution and blocks dangerous patterns:

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
# safe: False, category: DANGEROUS, warnings: [...]
```

**Blocked patterns:**
- `rm -rf /` — System-wide deletion
- `curl | sh` — Download and execute
- Fork bombs, direct disk writes

### Permission System

Ruleset-based permission control for tool execution:

```python
from apex.permission import permission_manager, PermissionAction

# Add custom rules
permission_manager.add_rule("run_command", PermissionAction.ASK)

# Check permission
can_execute, reason = permission_manager.can_execute_tool("run_command")
```

### Rate Limiting & API Keys

Database-backed rate limiting with workspace-based API keys:

```python
from apex.rate_limiter import create_rate_limiter
from apex.api_key import create_key_manager

limiter = create_rate_limiter(use_sqlite=True)
manager = create_key_manager()

# Create API key
workspace = manager.create_workspace("my-project", "user_123")
api_key, info = manager.create_key(workspace.workspace_id, "prod")
```

### HTTP API Security

```python
from apex.http_api import HTTPServer

server = HTTPServer(
    host="127.0.0.1",
    port=8080,
    require_auth=True,  # API key required
)
```

See [SECURITY.md](SECURITY.md) for full documentation.

---

## ⚡ Installation

### One-line install (recommended)

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
| **uv** (fastest) | `uv tool install apex-agent` |
| **pipx** (isolated) | `pipx install apex-agent` |
| **pip** | `pip install apex-agent` |
| **Homebrew** | `brew install apex-agent` |
| **Docker** | `docker run -it -v $(pwd):/workspace ghcr.io/ggboykxz/apex` |

### From source

```bash
git clone https://github.com/Ggboykxz/APEX
cd APEX
pip install -e ".[dev]"
```

### GitHub Codespaces

APEX is pre-configured in `.devcontainer.json` — just open the repo in Codespaces!

---

## 🚀 Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Launch APEX
apex

# 3. Ask anything
> fix the authentication bug in auth.py
> add TypeScript types to all functions
> write tests for the payment module
```

Switch models anytime:
```bash
apex --model gpt-4o        # Start with GPT-4o
apex --model gemini-2      # Start with Gemini 2
apex --model ollama-llama3 # Local, no API key needed
apex --tui                 # Launch with Terminal UI
```

---

## 🤖 Supported Models

<details>
<summary>Anthropic (Claude)</summary>

```bash
export ANTHROPIC_API_KEY=sk-ant-...
apex --model claude-sonnet   # Recommended
apex --model claude-opus     # Most powerful
apex --model claude-haiku    # Fastest
```
</details>

<details>
<summary>OpenAI</summary>

```bash
export OPENAI_API_KEY=sk-...
apex --model gpt-4o
apex --model o1
apex --model o3-mini
```
</details>

<details>
<summary>Google Gemini</summary>

```bash
export GEMINI_API_KEY=...
apex --model gemini-2
apex --model gemini-flash
```
</details>

<details>
<summary>Groq (Ultra-fast inference)</summary>

```bash
export GROQ_API_KEY=gsk_...
apex --model llama-groq
apex --model mixtral-groq
```
</details>

<details>
<summary>🔒 Ollama (100% local, no API key)</summary>

```bash
# Install Ollama first: https://ollama.com
ollama pull llama3
apex --model ollama-llama3   # No API key needed!
```
</details>

<details>
<summary>DeepSeek</summary>

```bash
export DEEPSEEK_API_KEY=...
apex --model deepseek-chat
apex --model deepseek-coder
```
</details>

<details>
<summary>Meta Llama</summary>

```bash
apex --model llama-3
apex --model llama-3.1
```
</details>

<details>
<summary>Mistral & Mixtral</summary>

```bash
export MISTRAL_API_KEY=...
apex --model mistral
apex --model mixtral
```
</details>

<details>
<summary>Qwen</summary>

```bash
apex --model qwen2
apex --model qwen2.5
```
</details>

---

## 🛠️ What APEX Can Do

- **Read & edit files** — understands your whole codebase
- **Run commands** — tests, builds, installs, git
- **Search code** — grep-style across your project
- **Fix bugs** — diagnoses, patches, and verifies
- **Write features** — complete implementations
- **Refactor code** — preserves your style
- **Write tests** — pytest, jest, go test, and more
- **Explain code** — line by line if needed

---

## 🎨 Configuration

```bash
# ~/.apex/config.json
{
  "model": "claude-sonnet",
  "theme": "apex-dark",
  "auto_commit": false,
  "max_tool_rounds": 20
}
```

```bash
# .env (project or ~/.apex/.env)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

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
bun run tui:dev    # Launch TUI in dev mode
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT — built with ❤️ in Gabon 🇬🇦 by [@Ggboykxz](https://github.com/Ggboykxz)

---

<div align="center">
<sub>If APEX helps you, please ⭐ the repo — it means everything to an indie developer.</sub>
</div>
