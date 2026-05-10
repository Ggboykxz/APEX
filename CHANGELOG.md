# Changelog

All notable changes to APEX will be documented in this file.

## [1.0.0] - 2026-05-10

The first stable release of APEX — the universal AI coding agent. Every model, one terminal.

### Core

- **100+ LLM Models** via litellm — Anthropic, OpenAI, Google, Groq, Mistral, DeepSeek, Ollama (local), xAI, Qwen, and more
- **5 Built-in Agents** — Coder, Architect, Reviewer, DevOps, Analyst — each with specialized system prompts and tool access
- **75+ Tools** — File read/write/edit, code search, shell execution, git operations, web scraping, database queries, Docker, K8s, cloud management, and security auditing
- **MCP (Model Context Protocol)** — Connect external tool servers dynamically with automatic capability discovery
- **LSP (Language Server Protocol)** — Real-time diagnostics, completions, and code intelligence for 20+ languages
- **Multi-Agent Orchestration** — Switch agents mid-session, route tasks to specialized agents, coordinate parallel workflows
- **Session Persistence** — Save and resume coding sessions with full conversation history and context
- **Auto-Commit** — Automatic git commits after successful task completion with descriptive messages

### TUI (Terminal User Interface)

- **OpenTUI + React** — Modern terminal UI built on the OpenTUI framework with React components
- **5-Panel Layout** — Agent selector, sidebar (file tree + tools), chat area, model selector overlay, help panel
- **Keyboard-Driven** — Tab to switch agents, Ctrl+K model selector, Ctrl+O sidebar, Ctrl+T tools, ? for help, Ctrl+Q quit
- **Real-Time MCP/LSP Status** — Live server connection monitoring in sidebar
- **Visual Charter** — Dark (#0d1117), Cyan (#00e5ff), Green (#00ff88)

### Security

- **Shell Command Analysis** — Dangerous commands (rm -rf /, curl | sh, fork bombs) automatically blocked before execution
- **Permission System** — Ruleset-based ALLOW/DENY/ASK flow for tool execution with wildcard pattern matching
- **Rate Limiting** — Database-backed request throttling (memory or SQLite) with per-minute/hour/day limits
- **API Key Management** — Workspace-based authentication with secure SHA-256 hashing, expiration, and rate limits
- **HTTP API** — Headless agent access with Bearer token or X-API-Key authentication, per-endpoint rate limiting
- **Billing System** — Cost tracking and quota management with model-specific pricing

### Architecture

- **Structured Message System** — Messages with typed parts (text, file, tool_call, tool_result, image, snapshot)
- **Snapshot System** — Git-based undo/redo with diff computation between before/after states
- **Event Bus** — 25+ typed events for session, file, tool, permission, LSP, and undo/redo operations
- **Plugin System** — Extensible plugin architecture with hooks and custom tool registration
- **Skills System** — Reusable prompt templates with diff application, search-replace, and code analysis
- **Custom Commands** — User and project-level slash commands with template variable expansion
- **Session Sharing** — Base64-encoded shareable session links in `apex://share/{id}` format

### Installation

- **pip** — `pip install apex-ai`
- **pipx** — `pipx install apex-ai` (isolated environment)
- **uv** — `uv tool install apex-ai` (fastest)
- **Docker** — `docker run -it ghcr.io/ggboykxz/apex`
- **curl install script** — `curl -fsSL https://apex-ai.dev/install.sh | bash` (macOS/Linux)
- **PowerShell install** — `irm https://apex-ai.dev/install.ps1 | iex` (Windows)
- **Homebrew** — Not yet available (coming soon)
- **From source** — `git clone && pip install -e ".[dev]"`
- **DevContainer** — Pre-configured `.devcontainer.json` for GitHub Codespaces

### CI/CD

- **CI** — Python 3.11/3.12 lint (ruff), type check (mypy), test (pytest) on every push/PR
- **TUI** — TypeScript check + build for `tui-frontend/` on every push/PR
- **Website** — Next.js ESLint + build + Vercel deploy on main
- **Release** — PyPI publish + Docker build/push + GitHub Release on tag `v*`
- **Security** — CodeQL, pip-audit, npm-audit, Bandit, TruffleHog scans
- **Docs** — MkDocs Material build + deploy to GitHub Pages
- **PR Checks** — Conventional commits, size labels, changed path detection

### Infrastructure

- **Dockerfile** — Multi-stage build (Python backend + Bun/TUI + final image) with health check
- **Caddyfile** — Reverse proxy configuration for production deployment
- **mkdocs.yml** — Documentation site with Material theme
- **Comprehensive .gitignore** — Python, Node, IDE, OS, build artifacts
