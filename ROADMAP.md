# APEX Public Roadmap

## ✅ v1.0.0 — First Stable Release (released May 10, 2026)
- 100+ model support via litellm
- 5 specialized agents (Coder, Architect, Reviewer, DevOps, Analyst)
- 75+ built-in tools
- Beautiful TUI (OpenTUI + React)
- `pip install apex-ai`
- Session persistence
- Plugin system
- Command palette
- Auto-completion
- Shell security analysis
- Permission system (ALLOW/DENY/ASK)
- Rate limiting
- API key management
- Docker image (ghcr.io/ggboykxz/apex)
- CI/CD pipeline (7 workflows)

## ✅ v1.1.0 — TUI & Agent Update (released May 11, 2026)
- HTTP SSE backend for TUI (replaces stdin/stdout IPC)
- Real-time token streaming (prompt/completion counts)
- Per-message cost tracking with model-specific pricing
- Context percentage monitoring (live context window utilization)
- Agent-colored theming (titlebar, statusbar, borders per agent)
- Model switch via HTTP API with error feedback
- 8 models added (claude-3.7-sonnet, llama-3.3-70b, mistral-large, etc.)
- Agent rename: DevOps → Shell, Analyst → Planner
- Architect agent (distinct primary, read-only)
- Reviewer reclassified as subagent
- Unified HTTP server (start_tui_server/stop_tui_server)

## ✅ v1.2.0 — Security & CI Hardening (released May 11, 2026)
- API key validation hardening (try/except on SQLite errors)
- Sandbox secure permissions (0o700 on dirs, 0o600 on files)
- License field fix (PEP 639 compliant)
- Removed broken `/cost` command
- Fixed 7 failing CI workflows (Markdown Lint, Next.js Build, Coverage, Build check, TUI Build/Lint/TypeScript, Release Docker, Security Audit, CI Lint, CI Test)
- 13 Dependabot PRs merged
- 2,842 tests passing, 0 failures
- Dockerfile Python 3.13-slim base image
- Branch protection on main (no force push, PR reviews required, 5 status checks)

## 🎯 v2.0.0 — Intelligence
- Repo map (understand full codebase structure)
- Vision support (send screenshots to vision models)
- Auto-commit mode
- VS Code extension
- MCP server mode

## 🌍 v2.5.0 — Enterprise
- Full test suite (>80% coverage)
- Windows installer (.exe)
- macOS app wrapper
- Enterprise features (SSO, audit logs)
- APEX Cloud (hosted version)

---

## Want to contribute?

Check out our [CONTRIBUTING.md](CONTRIBUTING.md) and help us build the future of AI coding agents!

- 🐛 **Report bugs**: [GitHub Issues](https://github.com/Ggboykxz/APEX/issues)
- 💡 **Request features**: [GitHub Discussions](https://github.com/Ggboykxz/APEX/discussions)
- ⭐ **Star the repo**: [GitHub](https://github.com/Ggboykxz/APEX)
- 💖 **Sponsor**: [GitHub Sponsors](https://github.com/sponsors/ggboykxz)

---

*Built with ❤️ in Gabon 🇬🇦 for the world.*
