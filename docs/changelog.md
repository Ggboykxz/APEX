# Changelog

All notable changes to APEX are documented in this file. The project follows [Semantic Versioning](https://semver.org/).

## Unreleased

### CI & automation

- **opencode AI maintainer** — `.github/workflows/opencode.yml` answers `/oc` / `/opencode` comments from maintainers only (`OWNER` / `MEMBER` / `COLLABORATOR`, bots rejected) on issues, PRs, and review lines. It uses OIDC app tokens, a 30-minute timeout, per-issue concurrency, no session sharing, and fails with a clear message when no provider key is configured. The archived upstream action is pinned to `github-v1.2.28` (`17b79f4e…`). Setup requires the `opencode-agent` GitHub App plus `DEEPSEEK_API_KEY` or `ANTHROPIC_API_KEY`; the `OPENCODE_MODEL` repository variable overrides the default DeepSeek model.

### v2.5 — Wave 1 (Repository Map, TUI streaming, governance)

- **Repository map** — new `apex/repomap.py` engine: symbol-level extraction (Python AST + JS/TS/Rust/Go heuristics), reference-based ranking, token budget, per-root cache, and a `repo_map` tool. 29 new tests.
- **TUI streaming & diff** — typed normalization of EventBus payloads, pure streaming reducer (assistant deltas, tool lifecycle, session isolation), unified-diff parser, `DiffPreview` overlay with local accept/reject, and `/diff`. 28 new tests.
- **Governance** — issue forms, PR template, CODEOWNERS, ADR-0004 (Rust distribution deferred), ADR-0005 (repo map design), v2.5 milestones/board, and a Delivery & Governance section in `AGENTS.md`.
- **Lint scope** — all first-party Python (`apex/`, `tests/`, `scripts/`) is linted; vendored `skills/` is explicitly excluded and audited separately.
- **Rust internal GA** — crate-level `#![allow(dead_code)]` removed in favor of 23 scoped allows with exit criteria; shell security wired into the CLI (`security check|allowed`), `POST /api/v1/security/analyze`, the `run_command` tool, and `/api/v1/bash`; hermetic `config::home_dir()`; `tests/cli_e2e.rs` (7 binary tests); new `rust/apex-rs/PARITY.md` matrix. No publishing (ADR-0004).

### v2.5 — Wave 2 (MCP server, vision, auto-commit, VS Code)

- **MCP server** — `apex mcp serve` exposes the native tool registry to any MCP client over JSON-RPC 2.0 on stdio (ADR-0006): `initialize`, `tools/list`, `tools/call`, `ping`, batches, and JSON-RPC error codes; `--cwd` and repeatable `--allow-tool` scope the session. Other MCP tooling remains client-side (`apex mcp add/list/auth`). 21 new tests.
- **Vision input** — `apex -p "…" -i shot.png` (repeatable) validates `png`/`jpg`/`jpeg`/`webp`/`gif` up to 10 MB, fails before the LLM call when the model lacks vision, and sends image content blocks. New `apex/vision.py`. 24 new tests.
- **Auto-commit** — `--auto-commit` commits a successful one-shot run with an AI-generated conventional-commit message; `-f json` gains an `auto_commit` object with `committed` / `no-changes` / `not-a-repo` / `error`. New `apex/auto_commit.py`. 24 new tests.
- **VS Code extension** — thin client in `integrations/vscode/` (ADR-0007): chat webview, explain/fix selection, working-tree diff review, SecretStorage API key, backend auto-start/restart; TypeScript build plus artifact-only `vsce package` (no publishing).
- **Docs** — new MCP server and VS Code reference pages, CLI reference for `--image`/`--auto-commit`, and the M1–M4 close-out in `AGENTS.md`.

### Rust Port (`rust/apex-rs`)

Full rewrite of the backend in Rust. The Python implementation stays the reference until parity is reached.

- **CLI** — `run`, `chat`, `serve`, `tools`, `plugins`, `call-tool`, `cost`, `memory`, `session`, `security`, `context`, `workspace`, `github`, `skill`, `key`.
- **Repository context** — `context.rs` mirrors `apex/context.py`: `apex-rs context repo-map|git|stats|ctags|tree|glob` and `GET /api/v1/context/*` (43 HTTP routes total), with `?path=`, `?depth=` and `?pattern=`.
- **Rate limiting** — `rate_limiter.rs` wired into `serve`: per-key in-memory limits (`X-API-Key` / `Authorization: Bearer` / `anonymous`) on every route except `/health`, 429 + `Retry-After` with the Python response body, `GET /api/v1/rate-limit` counters, and `APEX_RATE_LIMIT_*` env overrides.
- **Permission gate** — `permission.rs` enforced at both agent dispatch sites (one-shot and streaming): first-match rules, headless manager (`*` → ALLOW since there is no prompt surface, ASK refuses with the rule reason), and `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK` env rules. The interactive request/approve flow is ported but unwired.
- **Editing tools** — `edit_file` (first-occurrence replacement, Python-identical success/error strings) and `apply_patch` via the new `patch.rs`, a faithful port of `apex/apply_patch.py`: Codex-style and unified-diff dialects, full pre-write validation (path traversal, absolute paths, duplicate targets, 1 MB patch / 512 KB file limits, binary content), hunk matching with forward/backward fuzz and signed offset warnings, no-newline markers, and atomic temp-file + rename writes with best-effort rollback. `dry_run` previews without writing.
- **Context tools** — `get_repo_map` and `get_file_tree` expose the existing `context.rs` functions as registry tools (tool registry is now 43 schemas): the repository map from the working directory (Python ignores the tool's `path` argument; the Rust arm does the same) and an ASCII file tree with `max_depth` (default 3), directories first, dotfiles hidden, and Python's `ERROR: Path not found: …` on a missing path. `get_context_info` stays Missing (it needs the agent message state, which the stateless Rust dispatch does not keep).
- **Web tools** — `web_search` (Brave/Tavily/Exa/DuckDuckGo provider chain, identical to Python, with DuckDuckGo fallback and `ERROR: Web search failed: …`) and `fetch_url` (redirects followed, 30 s timeout, script/style/tag/`&[a-z]+;` cleaning in Python's exact order, 3000-char cap with `...`). New `web.rs`; HTTP runs on a dedicated thread with its own runtime, like `github::http_json`, so both tools work from the CLI and from inside the agent loop.
- **Task & plan tools** — `task` (validates `agent` against the 11 built-in names from `apex/agents.py` and returns `[Delegated to @{agent}]: {task}`, or `ERROR: Unknown agent: …`), `submit_task` / `list_tasks` / `get_task` backed by a new `task_queue.rs` porting the `TaskQueue` from `apex/extras.py` (in-memory, one background thread per task, `stdout or stderr` as the result, `completed` / `failed` statuses, 8-char ids in the shape of Python's `uuid4()[:8]`), and `plan_approve` / `plan_reject` (always `ERROR: No pending plan to …` — Python's `_plan_approval` is never set on the executor either). Tool registry is now 51 schemas.
- **GitHub CLI & skill authoring** — `github.rs` is wired through a `github` CLI group: `install` / `run` (Python `_cmd_github` parity: three info lines, then `Found N issues and M PRs` against the detected repo), `issue` / `issue-close` / `pr` / `pr-merge` over the REST `GitHubClient`, and `automate {create-pr,changes,issue,list,todos,close-completed}` over `GitHubAutomation` (credentials from `GITHUB_TOKEN` / `GH_TOKEN`, API root overridable with `APEX_GITHUB_API` — tests point it at a dead local port). `apex-rs skill {list,add,remove}` exposes `SkillManager::add`/`remove`; `add` persists to `.apex/skills/<name>.md` in the loader's exact format (Python's add/remove are in-memory and unwired there) and `remove` deletes the project file, so a fresh process sees the change. Skill names reject path separators and `..`. Five more dead-code allows removed (28 remain).
- **HTTP auth & route-level E2E** — opt-in API-key authentication (`APEX_REQUIRE_AUTH=1|true|yes|on`) on every `serve` route except `/health`, `/ws` and `/ws/events`, with Python's carrier precedence (`Authorization: Bearer …` → `?api_key=` → `X-API-Key`) and the exact 401 body (`{"error": "Authentication required", "code": "AUTH_REQUIRED"}`). New `api_key.rs` stores `apex_` + 32 random urlsafe-base64 bytes as sha256 in `~/.apex/api_keys.json` (`APEX_API_KEYS_FILE` overrides; Python uses SQLite), re-read on every request so `apex-rs key {create,list,revoke,delete}` reaches a running server. `POST /api/v1/auth/{login,logout}` and `GET /api/v1/auth/status` are wired and, when auth is on, protected like every other route; auth wraps the limiter so 401s never consume key budget. `GET /api/v1/rate-limit` now reports the minute-window `reset_at`, retiring the last `rate_limiter` allow (27 remain). Python's `apex serve` defaults auth on; the Rust port defaults off because the TUI backend sends no key (divergence recorded in `PARITY.md`).
- **Python-written session fixtures** — `tests/fixtures/session/` contains sessions encrypted by Python's `cryptography.fernet` (the library `apex/session.py` uses), plus a deterministic `generate.py`. The Rust loader decrypts them through both key schemes: the native 44-byte Fernet key and the legacy raw 32-byte key (`sha256(raw + b":fernet")`). Unit tests cover the crypto boundary and the binary E2E loads the fixtures through `session show`/`list` with a temporary `HOME`.
- **Workspace awareness** — new `workspace.rs` ports `apex/workspace.py`: Git branch, 8-char commit, dirty flag, `origin` URL and GitHub `owner/repo`, ahead/behind counts, `GITHUB_HEAD_REF`/`GITHUB_PR_NUMBER`, first five tags (5-second timeout per git call), plus language, package-manager and test-framework detection in Python's marker order. The `[WORKSPACE CONTEXT]` block is now appended to both agent system prompts (analyzed once per user turn) and exposed by `apex-rs workspace [PATH] [--json]`. Python exports the class but never wires it. Divergences: no `git fetch --dry-run` network call, empty tags on tagless repos, no global singleton. Unit tests use real repositories (dirty state, ahead/behind against a bare remote, GitHub remote parsing, tag cap); the binary E2E checks the prompt block and JSON in a dirty repo.
- **Tools** — read/write/edit/list, shell, git (status/diff/log/undo + stage/unstage/commit/branches/pre-commit/PR), search, format, undo, LSP (diagnostics, definition, references, hover), code generation (refactor, DB model, Dockerfile/compose, OpenAPI client, docs, profiler), skills & analysis (diff_files, list_skills, use_skill, replace_in_files, analyze_code, explain_code), repository context (get_repo_map, get_file_tree), web (web_search, fetch_url), task queue & plans (task, submit_task, get_task, list_tasks, plan_approve, plan_reject).
- **Agent loop** — OpenAI-compatible chat completions with tool calling, permission gate (`APEX_DENIED_TOOLS`), JSON session persistence (`~/.apex/sessions/`).
- **Compaction** — `prune` / `summarize` / `merge` strategies plus threshold-based auto-compaction.
- **`@mentions`** — text files inlined, images embedded as base64.
- **MCP** — `~/.apex/mcp.json` discovery, OpenAI-format tool schemas, fresh server process per call.
- **LSP** — JSON-RPC client with proper `Content-Length` framing, document open + readiness wait, server picked by extension (rust-analyzer, pyright, tsc, gopls) or explicit override.
- **HTTP/WS API** — chat (JSON + SSE), tools, models, sessions, files, agents, themes, tui-config, config, undo/redo, plugins, cost, `/ws` and `/ws/events`.
- **Plugins** — Rust-native manifests (`~/.apex/plugins/<name>/plugin.json`); Python `.py` plugins are listed but not executable without an interpreter.
- **Cost tracking** — `cost.rs` mirrors `apex/cost_local.py` (46-model pricing table verified identical, per-model usage, resettable history).
- **Memory** — `memory.rs` mirrors `apex/memory.py` (`~/.apex/memory.json`, same JSON shape and timestamps); `apex-rs memory …` and the REPL `/memory` command read and write the same file as Python.
- **Code generation** — `codegen.rs` mirrors `apex/codegen.py` (refactorer, DB/Docker/OpenAPI/docs generators, profiler) with Python-verified outputs.
- **GitHub** — `github.rs` mirrors `apex/github_integration.py` (issues, PRs, merge, branches, automation) over the REST API or `gh`; `git_create_pr` returns the real PR URL.
- **Skills & analysis** — `skills.rs` mirrors `apex/skills.py` (skill manifests, unified diff, regex search/replace, code analyzer) and exposes six tools (`diff_files`, `list_skills`, `use_skill`, `replace_in_files`, `analyze_code`, `explain_code`).
- **Tests** — 193 unit + 14 binary E2E passing (192 on Windows: the write-failure rollback test is POSIX-gated), including an MCP roundtrip against a fake server, plugin execution, streamed usage, JSON-RPC framing (line + `Content-Length`), a fake GitHub API, codegen parity fixtures, repository-context commands, the workspace analyzer (marker order, dirty state, ahead/behind against a real bare remote, GitHub remote parsing, PR environment, tag cap, prompt caching) and its CLI prompt block/JSON in a dirty repository, the per-key rate-limit middleware (429 + `Retry-After`, independent key budgets), the HTTP-auth middleware (carrier precedence, empty-Bearer handling, revoked/expired keys, `/health` exemption, 404-before-auth) and the full binary auth flow (CLI-created key, exact 401 body, login/logout/status, out-of-band revoke, 429 with 401s not consuming budget), Python-written Fernet session fixtures under both key schemes (unit crypto tests and the binary `session show`/`list` flow), the permission-gate refusal in the agent loop, the multi-file patch engine (both dialects, fuzz offset warnings, dry-run preview, write-failure rollback), the `get_repo_map` / `get_file_tree` tools (tree connectors, dotfile filter, `max_depth` cutoff, missing-path error), the web tools (urllib-style quoting, DuckDuckGo HTML parsing with snippet fallback and 5-result cap, Brave/Tavily/Exa JSON parsing with the 200-char Exa text cap, and `fetch_url` cleaning — script/style/tag strip, whitespace-before-entities order, 3000-char cap), the task/plan tools (submit → `completed` with `stdout or stderr`, spawn failure → `failed`, `No tasks` empty state, `Tasks:` header + insertion-order listing, `Task:`/`Status:`/`Result:`/`Error:` format, `ERROR: Task … not found`, `ERROR: Unknown agent: …`, and the always-`No pending plan` plan tools), the `github` CLI (install/run/usage parity, issue/PR/automate error paths against a dead local port, `No GitHub repository detected` for the write flows), and the hermetic `skill` lifecycle (add → fresh-process list → remove → `No skills found`, path-traversal name rejection, `ERROR: Skill not found` on double remove).

#### Fixed during the port

- **Nested-runtime panic** — MCP/LSP execution no longer creates a Tokio runtime inside the async runtime; both run on dedicated threads.
- **MCP schema format** — tools converted to OpenAI `function` schemas.
- **MCP process lifetime** — no leaked child processes; discovery shuts servers down, calls own their process.
- **Streamed usage dropped** — the SSE reader stopped at `finish_reason: stop`, never seeing the trailing `usage` chunk (real providers send it afterwards), so streamed answers always reported 0 tokens. Now read until `[DONE]`/EOF; regression test splits the SSE body across two chunks.
- **LSP client was not LSP** — requests were line-delimited JSON, but the protocol requires `Content-Length` framing; real servers ignored everything. Now framed (MCP keeps line mode), documents are opened before queries, readiness (`experimental/serverStatus {quiescent:true}`) is awaited with an idle fallback and a retry, and `lsp_definition` / `lsp_references` / `lsp_hover` join `lsp_diagnostics`. Verified with a real `rust-analyzer`.
- **`apex-rs chat` panic** — the REPL called `block_on` inside `#[tokio::main]`; it is async now.
- **`add_type_hints` never worked (Python)** — the regex it built had an unclosed group, so it always raised `missing ), unterminated subpattern`; fixed in `apex/codegen.py` and implemented correctly in Rust.
- **GitHub POST/PATCH bodies had no `Content-Type` (Python)** — the header was set on a dict `urllib.request.Request` had already copied; fixed and covered by a regression test.
- **GitHub branch creation (Python)** — `GitHubClient.create_branch` shells out to `gh git checkout …`, and `gh` has no `git` subcommand, so it always returned `False`; the Rust port uses plain `git` (Python left untouched to avoid tests creating branches in the user's repo).
- **`git_unstage` before the first commit (Rust)** — falls back to `git rm --cached -r .` when `git reset HEAD` cannot resolve an unborn `HEAD`.
- **Stale `xfail` markers** — nine tests were still marked expected-to-fail for already-fixed bugs; they now run normally.

### TUI ⇄ Rust backend integration

- **HTTP contract** — `/chat/stream` (SSE JSON), `bash`, `compact`, real `undo`/`redo`, `files`, `sessions` (metadata), `themes`, `tui-config`, `config`, `plugins`.
- **WebSocket** — `/ws/events` with `connected`/`pong`/`state`/`undo`/`redo`/`compact`/`theme_changed`/`error` events and RPC method handling.
- **Sessions** — `GET /api/v1/sessions/:id`, `POST /:id/load|save`, `GET /:id/history`; encrypted format shared with Python.
- **Sharing** — `POST /api/v1/share`, `DELETE /api/v1/share/:id`, `GET /api/v1/shares`, `POST /api/v1/export` with secret redaction.
- **TUI commands** — `/theme`, `/session`, `/export`, `/share`, `/unshare`, `/editor` are all functional (were dead).
- **Node < 22** — `WebSocket is not defined` fixed via the `ws` package fallback.
- **Streaming** — structured `Chunk`/`Done`/`Error` events; SSE emits `{"chunk":…}` / `{"done":true}` / `{"error":…}` (no more `[DONE]` text in answers).
- **Verified end-to-end** — TUI → SSE → Rust → upstream API → TUI; 42 Rust tests including the agent loop, permission gate, streaming and usage accounting. LSP verified against a real `rust-analyzer`.

### Cost tracking, usage reporting & Rust-native plugins

- **Cost parity** — `cost.rs` ports `apex/cost_local.py`: 46-model `MODEL_PRICING` table (verified identical to Python), `record_usage`, `get_session_cost` (6-decimal USD), `reset_session`, archived history; provider-prefixed model ids fall back to the bare name.
- **Agent usage** — non-streaming reads `data.usage`; streaming sets `stream_options.include_usage` and folds every round into the session counters (`Agent::usage`) and the cost tracker.
- **API** — SSE emits `{"usage":…}` before `{"done":true}`; `POST /api/v1/chat` returns `usage`; new `GET /api/v1/cost`, `GET /api/v1/cost/history`, `POST /api/v1/cost/reset`; WebSocket gains `cost` and `chat_complete`. SSE/`chat_complete` carry **per-request** usage (the TUI sums its own totals) while `/api/v1/cost` and `/api/v1/chat` keep the cumulative session values like Python.
- **Model switching** — the `model` field of chat requests switches the running model (Python `switch_model` parity); `/api/v1/config` reports the live model.
- **CLI** — `apex-rs cost`, REPL `/cost`, and `[usage] N tokens, cost $…` on stderr after `run`.
- **TUI accounting** — usage comes from a ref (no stale closure) and `chat_complete` is deduped, so SSE + WebSocket no longer double count; verified live at `In: 120 Out: 34 Total: 154 • $0.0006`.
- **Plugin manifests** — `plugin.json` tools become `plugin_<plugin>_<tool>` model tools: `command` templates (shell-escaped `{arg}` placeholders) or `args` argv without a shell, env vars `APEX_PLUGIN_NAME`/`APEX_PLUGIN_DIR`/`APEX_TOOL_NAME`/`APEX_PLUGIN_ARGS`, `enabled: false` honoured, `APEX_DENIED_TOOLS` applies, listed by `apex-rs plugins` and `GET /api/v1/plugins`. Injection through placeholder values is tested.

### Bug Fixes

- **Deterministic session deletion** — `DELETE /api/v1/sessions/{id}` now iterates matching files in sorted order, so duplicate sessions resolve the same way on every filesystem; the delete-loop regression test keys its mock on the file name instead of the call count.
- **Manual compaction now works** — `Agent.compact_context(strategy=...)` implemented (summarize/prune/merge), so `/compact` and `apex compact` no longer crash on the missing method.
- **MCP status endpoint fixed** — `/api/v1/mcp/status` no longer crashes; server entries are dicts, so access now uses dict keys.
- **Session cost math fixed** — `CostTracker.get_session_cost()` no longer multiplies costs by every model in `MODEL_PRICING`; costs now come from per-model usage.
- **Per-agent model & reasoning effort** — `Agent` resolves model from the current agent config and forwards temperature/top_p/reasoning_effort to litellm.
- **Auto-compaction wired** — chat loops now auto-compact when enabled.
- **MCP tooling exposed** — schemas include MCP/plugin tools; `mcp_*` dispatch via `mcp_manager`; name parsing fixed.
- **Plugin hooks wired** — `tool_call` hook triggered after successful tool calls.
- **Web search providers** — Brave/Tavily/Exa selected via env keys, fallback DuckDuckGo.
- **Real PR creation** — uses `gh` CLI or GitHub REST API.

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
