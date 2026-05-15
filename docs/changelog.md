# Changelog

All notable changes to APEX are documented in this file. The project follows [Semantic Versioning](https://semver.org/).

## v2.0.0 (Current) — 2026-05-16

### 🚀 OpenCode Architecture & Production Hardening

APEX v2.0.0 brings the OpenCode-inspired architecture to the TUI, production hardening with 12 critical bug fixes, TUI audit fixes, and a major dependency cleanup.

### OpenCode-like TUI Architecture

- **WebSocket EventBus** — Real-time bidirectional communication between the Python backend and Ink TUI frontend, replacing simple HTTP polling with event-driven state synchronization
- **Random Port Binding** — Backend HTTP server now binds to a random available localhost port (instead of fixed 8080), preventing port conflicts when running multiple APEX instances
- **State Directory** — Standardized `~/.apex/state/` directory for runtime state, PID files, and port discovery
- **Port Discovery** — TUI frontend automatically discovers the backend port via shared state file, eliminating manual configuration

### Bug Fixes (12 Critical/High/Medium/Low)

- **Fernet Encryption Fix** — Session encryption now handles padding errors gracefully instead of crashing
- **Symlink Race Condition** — File operations no longer follow symlinks, preventing TOCTOU attacks
- **Glob Relative Paths** — Glob tool correctly resolves relative paths against the workspace root
- **Config.json Blocking** — Config files no longer block tool execution when malformed
- **Duplicate Pass Fix** — Permission system correctly handles duplicate pass-through rules
- **Dangerous Pattern Regex** — Shell security regex patterns fixed to prevent ReDoS and false negatives
- **React 18 Downgrade** — TUI frontend uses React 18 for compatibility with ink's react-reconciler@0.29
- **Ink Subprocess Passthrough** — TUI subprocess now uses passthrough stdio instead of captured pipes
- **Rate Limiting Fix** — Increased from 10 req/min to 60 req/min for TUI operations
- **CORS Headers** — Added proper CORS headers to all HTTP API endpoints
- **Unhandled Fetch Rejection** — TUI frontend `.catch()` handlers added to all fetch calls
- **Dead Import Cleanup** — Removed unused `threading` and `time` imports from main.py

### TUI Audit Fixes

- **Missing /api/v1/* Routes** — Added 8 missing API endpoints that TUI frontend expected (tui-config, undo, redo, compact, bash, files, themes, sessions)
- **Subprocess PIPEs → Passthrough** — TUI process stdio now uses passthrough for proper terminal rendering
- **@opentui → Ink Check** — Replaced OpenTUI detection with proper Ink dependency verification
- **Slow Fallback Logic** — Optimized TUI runtime detection fallback chain
- **Install-TUI Overwrite Protection** — TUI installation no longer overwrites existing configurations

### Dependency Management

- **10 Dependabot PRs Merged** — CI actions updates (checkout v6, setup-node v6, setup-python v6, setup-buildx v4, build-push v7, codeql v4), Python cryptography range expanded, lucide-react, react-day-picker minor bumps
- **7 Dangerous PRs Closed** — react-reconciler 0.33 (breaks Ink), Prisma 7 (breaking), mdxeditor 4 (removes Sandpack), Node 26 (too new), @types/node 25 (mismatch), and others

### CI/CD

- **All 10 GitHub Actions Workflows Passing** — CI, TUI Build/Lint/TypeScript, Security, Coverage, Build Check, Release, Docs, PR Checks
- **Node.js 24** — All workflows updated to use Node.js 24

## v1.3.0 — 2026-05-11

### CLI
- **Subcommand Support**: `apex tui`, `apex ui`, `apex models`, `apex install-tui` now work as natural subcommands
- **Help Text**: `apex --help` now shows a subcommands section
- Backward compatible: `apex --tui`, `apex --list-models` still work

### TUI
- **Pip Install Fix**: TUI now works after `pip install apex-ai` via auto-setup
- **Auto Bun Install**: Bun runtime is automatically installed if not found
- **Auto Dependency Install**: TUI npm dependencies are installed on first run
- **`apex install-tui`**: One-time TUI setup command
- **`python -m apex`**: Now supported

### Website
- **Official Provider Logos**: Real brand logos for all 21 AI providers (Simple Icons)
- **Website Content Fixes**: Corrected inconsistencies across all documentation and site pages

### CI/CD
- Fixed Docker build failure (removed data-files from pyproject.toml)
- Fixed 7 failing CI workflows + codegen/UI test failures

## v1.2.0 — 2026-05-11

- **Version bump**: 1.1.0 → 1.2.0
- **Dockerfile fix**: Corrected Python site-packages path from `python3.12` to `python3.13` to match the `python:3.13-slim` base image

## v1.1.0 — 2026-05-10

### TUI (Ink React)

- **HTTP SSE Backend**: TUI connects to a local HTTP server (`127.0.0.1:8080`) via Server-Sent Events instead of stdin/stdout IPC
- **Real-Time Token Streaming**: Live prompt/completion token counts update as tokens arrive from the LLM
- **Per-Message Cost Tracking**: Each message shows `+prompt/+completion · $cost` with model-specific pricing
- **Context Percentage**: Live context window utilization (`X.X% ctx`) based on model's context limit
- **Session Metrics**: Title bar shows message count, context %, and total spent. Status bar shows In/Out/Total tokens
- **Agent-Colored Theming**: Title bar, status bar, and panel borders dynamically change color per agent (Coder, Architect, Planner, Reviewer, Shell)
- **Model Switch via HTTP**: Ctrl+K model selector sends model changes through HTTP API
- **Connection Error Banner**: Shows specific server error messages, auto-dismisses after 5 seconds
- **Ctrl+L to Clear**: Resets all messages and zeros out prompt/completion/spent metrics

### Backend

- **Unified HTTP Server**: `start_tui_server()` / `stop_tui_server()` moved from `main.py` to `http_api.py`
- **Model Validation**: HTTP server returns `400 {"error": "Unknown model: xxx"}` for invalid model IDs
- **8 Models Added**: `claude-3.7-sonnet`, `llama-3.3-70b`, `mistral-medium`, `mistral-large`, `grok-3-mini`, `qwen3-32b`, `qwen2.5-coder-32b`, `phi-4`

## v1.0.0 — 2026-05-10

- First stable release
- 170+ LLM models via litellm (Anthropic, OpenAI, Google, Groq, Mistral, DeepSeek, Ollama, xAI, Qwen, Cohere, etc.)
- 5 specialized agents (Coder, Architect, Planner, Reviewer, Shell)
- 75+ built-in tools (File, Code, Shell, Git, Web, Database, Docker, K8s, Cloud, Security)
- Ink + React terminal interface
- MCP (Model Context Protocol) support
- LSP (Language Server Protocol) integration
- Shell security analysis (blocks dangerous commands)
- Permission system (ALLOW/DENY/ASK per pattern)
- Rate limiting and API key management
- Session persistence
- HTTP API with SSE streaming
- `pip install apex-ai`
