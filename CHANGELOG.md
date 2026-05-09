# Changelog

All notable changes to APEX will be documented in this file.

## [1.4.0] - 2026-05-09

### Security (Major)

- **Shell Command Analysis** — Dangerous commands automatically blocked
  - Pattern detection for `rm -rf /`, fork bombs, download-and-execute
  - Command classification by category (file, network, system, etc.)
  - Configurable allowlist/blocklist

- **Permission System** — Ruleset-based tool access control
  - `ALLOW`, `DENY`, `ASK` actions
  - Wildcard pattern matching
  - Request/approve flow for interactive confirmation
  - Remember decisions with expiration

- **Rate Limiting** — Database-backed request throttling
  - Memory or SQLite storage backends
  - Configurable limits (per minute/hour/day)
  - Per-key rate limiting for API

- **API Key Management** — Workspace-based authentication
  - Secure key generation with SHA-256 hashing
  - Expiration and rate limits per key
  - Workspace isolation

- **Billing System** — Cost tracking and quota management
  - Model-specific pricing (Claude, GPT-4, Gemini, etc.)
  - Usage history and summaries
  - Plan management (Free/Pro/Enterprise)

- **HTTP API Security** — Secure headless agent access
  - Bearer token or X-API-Key authentication
  - Rate limiting per endpoint
  - Automatic cost tracking
  - Shell security integration

### Documentation

- Enhanced SECURITY.md with full API documentation
- Security section in README.md
- Security API reference in docs/api.md
- Updated docs/index.md with security features

---

## [1.3.0] - 2026-05-09

### Added
- **100+ Model Support** via litellm integration
- **Multi-Agent System** with Build, Plan, Explore, General agents
- **75+ Tools** including file ops, git, web, sandbox, MCP, LSP
- **Plugin System** for extensibility
- **Skills System** for reusable prompt templates
- **Session Sharing** via link for collaboration
- **Command Palette** (Ctrl+K)
- **Auto-completion** for files, commands, agents, models
- **Rich Terminal UI** with Textual 8
- **Session persistence** with save/load
- **Token cost tracking** live
- **Slash commands** (20+)
- **@Mentions** for file/agent context

### Infrastructure
- **README.md** with 14 installation methods, comparison table, badges
- **pyproject.toml** with SEO keywords for PyPI
- **mkdocs.yml** with Material theme, dark cyan mode
- **GitHub Actions** CI/CD (CI, release, docs workflows)
- **GitHub Sponsors** configuration

---

*Built with ❤️ in Gabon 🇬🇦 for the world.*