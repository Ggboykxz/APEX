# Rust / Python Parity

Internal GA baseline for `rust/apex-rs` (last updated for the v2.6
gateway increment). The reference is the Python package in `apex/` on `dev`.
"Parity" here means that a behaviour is reachable from the Rust binary, HTTP
server, or tool registry and has automated coverage - not that the
implementations are line-for-line equivalent.

Scale at this baseline: ~25,918 lines of Python in `apex/*.py` versus ~29,138
lines of Rust in `rust/apex-rs/src` (48 files). The Rust line count now
matches Python's, but the tables below still record the behaviour gaps.

## Status legend

| Status | Meaning |
| --- | --- |
| **Wired** | Reachable from the CLI, HTTP server, or tool registry, with tests. |
| **Partial** | A useful subset is reachable; the notes list the missing behaviour. |
| **Ported** | Code exists and is unit-tested, but has no production caller yet. |
| **Missing** | No Rust counterpart. |

## Public Rust surface

CLI (`apex-rs --help`):

```text
run, chat, serve, tools, plugins, call-tool, cost,
memory {list,add,search,context,remove,clear},
session {list,show,save},
security {check,allowed},
context {repo-map,git,stats,ctags,tree,glob},
github {install,run,issue,issue-close,pr,pr-merge,
        automate {create-pr,changes,issue,list,todos,close-completed}},
skill {list,add,remove},
key {create,list,revoke,delete},
gateway {start,key,status}
```

HTTP server (`serve`): 79 route registrations covering all 52 routes of
Python's `apex/http_api.py` (route parity table below) plus 26 Rust-only
extras. Includes `/health`, `/api/v1/tools`, `/api/v1/security/analyze`,
`/api/v1/auth/{login,logout,status}`, sessions, shares/export, files, models,
config, themes, cost, chat, chat streaming, context (`repo-map`, `git`,
`stats`, `ctags`, `tree`, `glob`), `/api/v1/rate-limit`, and WebSockets.
API-key auth is opt-in with
`APEX_REQUIRE_AUTH` (`/health` and the WebSocket routes exempt).

## Route parity (`http_api.py`)

Python's `http_api.py` registers 52 routes; all 52 are reachable on the Rust
`serve` router. The 79 registrations split as 53 covering the 52 Python
routes (`POST /chat/stream` is registered under both `/chat/stream` and
`/api/v1/chat/stream`) plus 26 Rust-only extras. The E2E tests
(`serve_exposes_python_parity_routes`, `serve_diff_preview_accepts_and_rejects`)
hit every route that does not require an LLM call; the three LLM-touching
routes (`POST /chat`, `GET /stream`, `POST /api/v1/commands/execute`) reuse
the `chat`/`chat_stream` code paths already covered by the streaming tests.

| Python route | Rust route | Notes |
| --- | --- | --- |
| `GET /` | `GET /` | Static index page with `text/html; charset=utf-8`. |
| `GET /health` | `GET /health` | Rate-limit and auth exempt. |
| `POST /chat` | `POST /chat` | `rate_limit` object always present (Python: only when its limiter returned a result); Python also records billing per key here, Rust does not on this route. |
| `GET /stream` | `GET /stream` | Reuses the `chat_stream` handler: additionally emits `usage` and `done` frames (Python emits `chunk` frames only). |
| `POST /chat/stream` | `POST /chat/stream` (+ `/api/v1/chat/stream`) | |
| `GET /models` | `GET /models` | `{"models": [...]}` from the static model table. |
| `POST /session/save` | `POST /session/save` | Name defaults to `http_session`; `{"saved": "<path>"}`. |
| `POST /session/load` | `POST /session/load` | `400` without a name; `404` for an unknown session. |
| `GET /metrics` | `GET /metrics` | `usage_summary` keyed by API key id (Python: `workspace_id`). |
| `GET /rate-limit/status` | `GET /rate-limit/status` | |
| `GET /api/v1/config` | `GET /api/v1/config` | |
| `POST /api/v1/config` | `POST /api/v1/config` | Returns the flat `GET` shape after applying. |
| `GET /api/v1/agents` | `GET /api/v1/agents` | |
| `GET /api/v1/agents/{name}` | `GET /api/v1/agents/:id` | `404 "Agent '{name}' not found"`; `system_prompt`/`top_p` are null (the Rust `Agent` does not store them). |
| `GET /api/v1/sessions` | `GET /api/v1/sessions` | |
| `DELETE /api/v1/sessions/{id}` | `DELETE /api/v1/sessions/:id` | Sorted `*{id}*` glob delete with `*.json` name/`session_id` fallback; `404 session not found`. |
| `POST /api/v1/share` | `POST /api/v1/share` | |
| `POST /api/v1/unshare/{share_id}` | `POST /api/v1/unshare/:id` | |
| `GET /api/v1/shares` | `GET /api/v1/shares` | |
| `GET /api/v1/themes` | `GET /api/v1/themes` | `resolved` is null. |
| `POST /api/v1/themes` | `POST /api/v1/themes` | Mutates the running config's theme; `400` without a name. |
| `GET /api/v1/stats` | `GET /api/v1/stats` | `current_agent` is always `build`; `rate_limit` only with an authenticated key. |
| `GET /api/v1/formatters` | `GET /api/v1/formatters` | Empty list unless formatters are configured (matches Python's default). |
| `POST /api/v1/format` | `POST /api/v1/format` | |
| `POST /api/v1/compact` | `POST /api/v1/compact` | |
| `POST /api/v1/models/refresh` | `POST /api/v1/models/refresh` | `{"models": [...], "count": N}`. |
| `GET /api/v1/providers` | `GET /api/v1/providers` | |
| `POST /api/v1/auth/login` | `POST /api/v1/auth/login` | |
| `POST /api/v1/auth/logout` | `POST /api/v1/auth/logout` | |
| `GET /api/v1/auth/status` | `GET /api/v1/auth/status` | Static 19-variable table (Python derives it from the model registry). |
| `POST /api/v1/commands/execute` | `POST /api/v1/commands/execute` | |
| `GET /api/v1/commands` | `GET /api/v1/commands` | |
| `POST /api/v1/undo` | `POST /api/v1/undo` | |
| `POST /api/v1/redo` | `POST /api/v1/redo` | |
| `GET /api/v1/files` | `GET /api/v1/files` | |
| `GET /find/file` | `GET /find/file` | Bare JSON array; fuzzy subsequence on the lowercased relative path, trailing `/` on directories, `min(limit, 200)` cap (default 50). |
| `POST /api/v1/bash` | `POST /api/v1/bash` | Shell-security guarded. |
| `POST /api/v1/command` | `POST /api/v1/command` | Runs through the slash-command manager: `handled` = whether the command parsed; Python's `handle_command` + CaptureUI has no Rust counterpart. |
| `GET /api/v1/tui-config` | `GET /api/v1/tui-config` | |
| `GET /global/health` | `GET /global/health` | `version` is `CARGO_PKG_VERSION` (`0.1.0`), Python reports `2.0.0`. |
| `POST /api/v1/init` | `POST /api/v1/init` | `ProjectInitializer` analysis + AGENTS.md creation. |
| `GET /api/v1/export/{session_id}` | `GET /api/v1/export/:session_id` | |
| `POST /api/v1/import` | `POST /api/v1/import` | The `data` branch writes a `{UTC stamp}_imported_{id}.json` file (Python uses local time). |
| `GET /global/event` | `GET /global/event` | SSE: `connected` frame, then `: keepalive` every 30 s. |
| `GET /api/v1/session/{id}/diff` | `GET /api/v1/session/:id/diff` | `git_run` errors only on spawn failure or the 30 s timeout; Python ignores git return codes. |
| `POST /api/v1/session/{id}/diff/decision` | `POST /api/v1/session/:id/diff/decision` | Full validation chain (body/decision/files/path checks) and `409 diff_changed` on a stale fingerprint; error messages use Python `repr` single quotes. |
| `POST /api/v1/session/{id}/fork` | `POST /api/v1/session/:id/fork` | |
| `POST /api/v1/session/{id}/abort` | `POST /api/v1/session/:id/abort` | |
| `GET /api/v1/lsp` | `GET /api/v1/lsp` | `[]` (no persistent LSP manager yet). |
| `GET /api/v1/formatter` | `GET /api/v1/formatter` | Bare array of available formatters. |
| `GET /api/v1/mcp` | `GET /api/v1/mcp` | `{}` when no MCP servers are configured. |
| `GET /ws/events` | `GET /ws/events` | |

Rust-only extras (no Python counterpart): `GET /api/v1/tools`,
`POST /api/v1/security/analyze`, `GET /api/v1/models`,
`POST /api/v1/files/read`, `POST /api/v1/files/write`, `GET /api/v1/plugins`,
`GET /api/v1/sessions/:id`, `POST /api/v1/sessions/:id/load`,
`POST /api/v1/sessions/:id/save`, `GET /api/v1/sessions/:id/history`,
`POST /api/v1/sessions/:id/fork`, `GET /api/v1/sessions/:id/branches`,
`DELETE /api/v1/share/:id`, `POST /api/v1/export`, `POST /api/v1/chat`,
`GET /api/v1/cost`, `GET /api/v1/cost/history`, `POST /api/v1/cost/reset`,
`GET /ws`, the six `GET /api/v1/context/*` routes, and
`GET /api/v1/rate-limit`.

Tool registry: 80 schemas. Python exposes 102 schema names in `apex/tools.py`.

## Module matrix

| Python | Rust | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py`, `__main__.py`, `main.py` | `main.rs` | Partial | Core CLI (`run`, `chat`, `serve`, tools, cost, memory, session, security, context, github, skill, key, gateway). Most of Python's command suite is not ported. |
| `apply_patch.py` | `patch.rs` | Wired | Multi-file patch engine reachable through the `apply_patch` tool (and `dry_run` preview): Codex-style and unified-diff dialects, pre-write validation (traversal, absolute, duplicate, size, binary), hunk matching with fuzz and signed offset warnings, no-newline markers, atomic temp-file + rename writes with best-effort rollback. |
| `agent.py` | `agent.rs` | Partial | One-shot run, streaming REPL, tool-call loop, cost reporting. HTTP: `POST /chat` (non-streaming, `rate_limit` always present), `GET /stream` (reuses `chat_stream`, adds `usage`/`done` frames), `GET /metrics` and `GET /api/v1/stats` (PR 349). Session forking/rewind and some prompt features are absent. |
| `agents.py` | `agents.rs` | Partial | Agent registry with 11 built-ins, markdown agent loading (`.apex/agents/*.md` and `~/.config/apex/agents/*.md`), per-agent permissions with glob patterns, merge rules for agent/env permissions, and `agent` CLI (`list`/`show`/`create`/`delete`). HTTP: `GET /api/v1/agents` and `GET /api/v1/agents/:id` (PR 349). Divergences: no Python system prompts/top_p, JSON config agents, or bash-specific permission helper; `Agent` does not store prompt body; env merge is agent-level rather than global permission manager. |
| `config.py`, `config_v2.py` | `config.rs` | Wired | Hierarchical config (4 levels: global ~/.config/apex/apex.json(c), $APEX_CONFIG, project ./apex.json(c), $APEX_CONFIG_CONTENT) with deep-merge, JSONC parsing (comments + trailing commas, strings preserved), `{env:VAR}` and `{file:PATH}` interpolation, schema validation with explicit errors, and CLI `config {show,validate,migrate}`. Divergences: no config watcher (auto-reload), no v1→v2 migration (absent in Python), tool-defined custom tools remain Missing. HTTP: `GET`/`POST /api/v1/config` (PR 349). |
| `config.py` (model table) | `models.rs` | Wired | Static `MODELS`/`MODEL_PROVIDERS` port (name, provider, context window, pricing, tags); backs `GET /models`, `POST /api/v1/models/refresh`, and `GET /api/v1/providers` (PR 349). |
| `config_tools.py` | - | Missing | No config-defined custom tools. |
| `context.py` | `context.rs` | Wired | CLI `context repo-map\|git\|stats\|ctags\|tree\|glob` and `GET /api/v1/context/*`: repo map, git info, language stats, ctags file list, file tree, glob search. `get_repo_map` and `get_file_tree` are also exposed as tools on top of the same functions. |
| `context_manager.py`, `context_tracking.py` | `context_tracking.rs` | Ported | Per-session token/message accounting, compaction trigger threshold (default 80% of 128k budget), compaction history (prune/summarize/merge), session add/remove/list. No Python system prompts/top_p; wiring into the agent loop/dispatch gate pending. See PR 334. |
| `cost_local.py` | `cost.rs` | Wired | Pricing table, usage, cost history; CLI `cost` and HTTP cost routes. |
| `codegen.py` | `codegen.rs` | Partial | Refactor, DB model, Dockerfile/compose, API client, docs, profile, optimize tools. Six helper operations remain test-only. |
| `formatter.py` | `formatter.rs` | Wired | FormatterManager with 19 built-in formatters (ruff, prettier, biome, rustfmt, gofmt, clang-format, etc.), config-driven enable/disable (`formatter: true|false|{name: {...}}` in apex.json), availability discovery (binary on PATH / npx/cargo / requirement files), per-extension formatter selection, `format_file`/`format_files`/`format_code` (tempfile), `build_command`. HTTP: `GET /api/v1/formatter(s)` and `POST /api/v1/format` (PR 349). Not yet wired into the agent dispatch / format-on-write pipeline. See PR 337. |
| `github_integration.py` | `github.rs` | Wired | `git_*` tools and `git_create_pr` work through `gh`/REST. The `github` CLI group exposes `install`/`run` (Python parity), `issue`/`issue-close`/`pr`/`pr-merge` through `GitHubClient`, and the six `GitHubAutomation` flows under `github automate`. API base overridable with `APEX_GITHUB_API` (tests). |
| hooks inside `plugins.py`/`tools.py` | `hooks.rs` | Wired | `trigger_hooks` runs on tool dispatch. Registration from config is not wired. |
| `http_api.py`, `server.py` | `server.rs` | Wired | All 52 `http_api.py` routes are reachable (route parity table above), plus 26 Rust-only extras. SSE/WebSocket streaming, shell guard, per-key rate limiting, opt-in API-key auth. Auth is enabled with `APEX_REQUIRE_AUTH` (`1`/`true`/`yes`/`on`); `/health`, `/ws` and `/ws/events` stay exempt. Carriers follow Python: `Authorization: Bearer …` → `?api_key=` → `X-API-Key`; `POST /api/v1/auth/{login,logout}` and `GET /api/v1/auth/status` are wired and auth-protected. Python's `apex serve` enables auth by default, the Rust port does not (the TUI backend sends no key) — documented divergence. The rate-limit middleware releases its lock before running the handler so routes that read limiter status in-request do not deadlock. |
| `lsp.py`, `lsp_diagnostics.py` | `lsp.rs` | Partial | Definition, references, hover, diagnostics tools. HTTP status stub `GET /api/v1/lsp` returns `[]` (PR 349). No persistent per-workspace manager or completion/code-action tools. |
| `mcp.py` | `mcp_client.rs`, `jsonrpc.rs` | Wired | Stdio JSON-RPC, server discovery, tool bridge, global registry; CLI and server use it. HTTP status route `GET /api/v1/mcp` (`{}` when unconfigured) — PR 349. |
| `memory.py` | `memory.rs` | Wired | CLI list/add/search/context/remove/clear, REPL `/memory`, session context injection. No automatic fact extraction. |
| `permission.py` | `permission.rs` | Wired | `dispatch_gate` enforces rules at both agent dispatch sites (one-shot and streaming). Headless manager: `*` → ALLOW (no prompt surface), ASK refuses with the rule reason. `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK` env rules. Interactive request/approve flow is unwired (no prompt surface). |
| `plugins.py` | `plugins.rs` | Wired | Manifest discovery, namespaced plugin tools, CLI/server listing and execution. Rust invokes declared tools; it does not execute Python plugin source in-process. |
| `rate_limiter.py` | `rate_limiter.rs` | Wired | Per-key in-memory limiter enforced by middleware on every `serve` route except `/health` (bucket is `key:{key_id}` once auth validates the key — Python parity — else the carrier from `Authorization`/`?api_key=`/`X-API-Key`, or `anonymous`; 429 + `Retry-After`). `GET /api/v1/rate-limit` exposes the caller's counters, limits and `reset_at`; limits via `APEX_RATE_LIMIT_*`. SQLite backend not ported. |
| `session.py` | `share.rs`, `session_crypto.rs`, `server.rs` | Wired | Fernet-compatible encrypted save/load/list, CLI and HTTP session routes. Python-written fixtures prove cross-language loading for both native and legacy key derivations. Adds fork/branch metadata: `fork_parent_id`, `branch_name`, `fork_point`, `branch_history`; CLI `apex-rs session fork <parent_id> [--branch-name]` and `session branch <name> [--from-turn]`; HTTP `POST /api/v1/sessions/{id}/fork` and `GET /api/v1/sessions/{id}/branches`. PR 349 added the remaining Python session routes: `POST /session/save`, `POST /session/load`, `DELETE /api/v1/sessions/:id`, `POST /api/v1/session/:id/{abort,fork}`, `GET /api/v1/session/:id/diff`, `POST /api/v1/session/:id/diff/decision`, `GET /api/v1/export/:session_id`, `POST /api/v1/import`, `POST /api/v1/unshare/:id`. Backward compatible (missing fields deserialise to None/empty). Divergences: sessions keyed by name not UUID; branch history is JSON-derived from the session itself (no separate branch file). |
| `share.py` | `share.rs`, `server.rs` | Wired | Redaction, share/unshare/list/export, CLI help through sessions, HTTP routes. |
| `shell_security.py` | `shell_security.rs` | Wired (increment 1) | CLI `security check/allowed`, `POST /api/v1/security/analyze`, `run_command` tool guard, and `/api/v1/bash` guard. |
| `skills.py`, `skills_system.py` | `skills.rs` | Partial | `list_skills`/`use_skill`, diffs, search/replace, code analysis tools. Skill authoring is wired through the `skill` CLI (`list`/`add`/`remove`); `add`/`remove` also persist to `.apex/skills/*.md` (Python's are in-memory only and unwired there). Three-way diff remains unwired. |
| `tools.py` | `tools.rs`, `shell_tools.rs`, `web.rs`, `task_queue.rs`, `files.rs`, `git_tools.rs`, `codegen_tools.rs`, `billing.rs`, `ux_tools.rs` | Partial | 80 tools: files, shell, git, codegen, LSP, skills, repository context, web, task queue & plans, billing, UX. Python exposes 102 schema names; the tool table below records the uncovered categories. |
| `git_undo.py` | `tools.rs` | Partial | `git_undo`, `undo_last_edit`, `redo_last_edit`. No stash-style undo/redo history (side-git workspace snapshots live in `workspace_rollback.rs`). |
| `advanced.py` | `server.rs` | Partial | SSE streaming exists. Retry, batching, and timeout policy are not ported. |
| `theme_manager.py` | `server.rs` | Partial | `GET /api/v1/themes` (list; `resolved` null) and `POST /api/v1/themes` (mutates the running config's theme, `400` without a name) — PR 349. No custom themes, or UI integration. |
| `commands.py`, `commands_manager.py` | `commands.rs`, `server.rs` | Wired | Custom markdown commands (`.apex/commands/`, `~/.config/apex/commands/`) with `$ARGUMENTS`/`$N`/`!cmd`/`@file` templating and built-in overrides. HTTP: `GET /api/v1/commands`, `POST /api/v1/commands/execute`, and the slash-command manager behind `POST /api/v1/command` (PR 349). Built-in clap subcommands unchanged. |
| `workspace.py` | `workspace.rs` | Wired | Git branch, 8-char commit, dirty flag, `origin` URL, GitHub `owner/repo`, ahead/behind counts, `GITHUB_HEAD_REF`/`GITHUB_PR_NUMBER`, first 5 tags; language, package-manager and test-framework detection in Python's marker order. `WorkspaceManager::get_system_prompt_context` produces the same `[WORKSPACE CONTEXT]` block, appended to both agent system prompts (one-shot and streaming, analyzed once per user turn) and exposed by `apex-rs workspace [PATH] [--json]`. Python exports the class but never wires it. Divergences: no `git fetch --dry-run` network call, empty tag list on tagless repos (Python returns `[""]`), and no process-global `workspace_manager` singleton. |
| `workspace_rollback.py` | `workspace_rollback.rs` | Wired | Side-git snapshots under `.apex/snapshots/`: metadata, `git diff --name-only` backup of tracked modifications (untracked files stay in `git_status.txt` only, like Python), status capture, restore with parent creation, sorted listing with missing-metadata defaults, delete, and `rollback_turn` clamping. `TurnTracker` persists `.apex/turns.json` and restores a recorded turn (`revert_turn` 0/overflow target the first turn, matching Python's `turns[-0]`/clamp). CLI `rollback {snapshot,list,restore,delete,turn,record,revert,history}`; Python only wires `/restore` and `/revert`, so Rust exposes the full surface. Divergences: UTC timestamps (Python uses local time), labels and snapshot names are validated as bare path components (Python joins them directly, so `../` can escape), `rollback turn 0` is a clear error (Python raises `IndexError`), and copies do not preserve modification times (`shutil.copy2` does). |
| `api_key.py` | `api_key.rs` | Partial | JSON-file key store (`~/.apex/api_keys.json`, overridable with `APEX_API_KEYS_FILE`; Python uses SQLite) re-read on every operation, so CLI changes reach a running server. `apex_` + 32 random bytes (urlsafe base64), sha256 at rest, expiry/active checks, `last_used`/`request_count`, CLI `key {create,list,revoke,delete}`. Python's per-key rate limits/permissions/metadata are carried in the schema but not enforced (its `validate_key` does not check them either); workspace CRUD is not ported (fixed `default` workspace). Writes are atomic (temp + rename) but not transactionally serialised across processes like SQLite. |
| `billing.py` | `billing.rs` | Wired | BillingManager with plan types (Free/Pro/Enterprise/Custom), model cost table, usage tracking, quota checking, and summary reporting. Tools: billing_cost, billing_quota, billing_usage, billing_plan, billing_summary. |
| `sandbox.py` | - | Missing | No isolated code execution. |
| `task_queue.py` | - | Missing | No durable background tasks. |
| `snapshot.py` | - | Missing | No snapshot system beyond the in-memory edit undo stack. |
| `watcher.py` | `watcher.rs` | Ported | Polling-based file watcher with debounced callbacks, gitignore-aware ignore patterns (`.gitignore` + configurable patterns), per-extension pattern matching, start/stop lifecycle. Not yet wired into the agent loop. See PR 338. |
| `project.py` | `project.rs` | Wired | ProjectInitializer: language/package-manager/test-framework/LSP/formatter/build-system detection, project structure analysis, dependency/script extraction, AGENTS.md generation. Wired to `POST /api/v1/init` (PR 349). See PR 340. |
| `mentions.py` | `mentions.rs` | Ported | `@file`/`@agent` mention expansion: MentionParser with regex identical to Python (`@boundary` and `in-word-with-dot`), case-insensitive agent dedup (build, plan, planner, reviewer, shell, general, explore, scout, compaction, title, summary), `resolve_file()` relative-to-cwd, `read_mentioned_files()` (capped at 5000 chars, skips unreadable), `FileMentionCompleter` with ignore list. Not yet wired into the agent message dispatch. See PR 335. |
| `slash.py` | `slash.rs` | Wired | Slash command manager: 20+ built-in commands (agent, model, cwd, clear, save, load, share, undo, redo, git, map, help, cost, agents, subagents, models, init, analyze, approve, reject, shell, commands), alias support, argument validation, `/name arg1 arg2` parsing. Wired to `POST /api/v1/command` (PR 349: `handled` = whether the command parsed, `output` = the handler result); not yet wired into the agent message dispatch. See PR 339. |
| `structured_message.py` | `structured_message.rs` | Ported | Structured message parts (text/file/tool_call/tool_result/image/snapshot) with MessagePart/Message/TokenUsage, to_dict/from_dict round-trip, factory `create_message`, serialize/deserialize helpers. Not yet wired into the agent message dispatch. See PR 336. |
| `task`/plan tooling in `tools.py` | `task_queue.rs`, `tools.rs` | Partial | `task` (delegates against the 11 built-in agent names; custom agents from `.apex/agents/*.md` are not scanned), `submit_task`/`list_tasks`/`get_task` (in-memory queue, one background thread per task - Python's `asyncio.run` actually cancels the spawned coroutine on loop teardown, so a task stays `pending` there), `plan_approve`/`plan_reject` (always `No pending plan` - Python's `_plan_approval` is never set on the executor either). `TaskQueue.cancel()` and the durable `task_queue.py` remain unported. |
| `ui.py`, `i18n.py` | - | Missing | No terminal UI or localisation; the TUI remains separate. |
| `telemetry.py` | - | Missing | No telemetry/logging pipeline. |
| `rlm.py` | - | Missing | No batched remote-model query support. |
| `extras.py` | `task_queue.rs` | Partial | `TaskQueue` (submit/list/get, in-memory, one background thread per task). Shell expansion, history search, env manager, and workspace validator are not ported. |
| `apex/gateway/*` (`config.py`, `auth.py`, `router.py`, `server.py`) | `gateway.rs` | Wired | Full port of the model gateway: `free`/`pro`/`unlimited` tiers (identical limits, model lists, 19/10/`*`), a JSON key/usage store at `~/.apex/gateway.json` (Python uses SQLite `~/.apex/gateway.db`) re-read on every access, `apex_` + 48-hex keys with 16-hex ids, a sliding 60 s per-key rate limiter, and all eight routes: `POST /v1/chat/completions` (Bearer key → tier model gate → rate → daily cap → upstream proxy; usage recorded per key/day and `usage.apex_gateway` injected on 200), `POST /v1/register` (413 above 4096 bytes, `Invalid tier: …` 400), `GET /v1/status`, `GET /v1/health`, `GET /v1/models` (sorted `free-`/`pro-` aliases with provider), and the `X-Admin-Key`-protected `/admin/keys`, `/admin/keys/generate`, `/admin/keys/revoke`. CLI `gateway {start,key,status}` mirrors Python's `_cmd_gateway` exactly, including the env-only start gate (`APEX_GATEWAY_KEY`/`OPENROUTER_API_KEY` unset → error + exit 1). Divergences: JSON store instead of SQLite (same data, no concurrent writers), `APEX_GATEWAY_UPSTREAM_BASE` env override (Python hardcodes `https://openrouter.ai/api/v1`) so tests run hermetic, a malformed chat body is 400 `Invalid JSON` (Python raises → 500), `usage.apex_gateway.tier` carries the tier *name* (Python stores the non-serializable `TierConfig` dataclass there, which breaks its own response), and re-revoking a known key returns 200 (SQLite `UPDATE` row-count parity) — only an unknown key is 404. |

## Tool coverage

| Category | Rust tools | Status | Notable Python tools not ported |
| --- | --- | --- | --- |
| Files | `read_file`, `write_file`, `edit_file`, `apply_patch`, `apply_edit`, `preview_edit`, `create_directory`, `delete_file`, `batch_read`, `batch_write`, `read_image`, `glob_search`, `list_files`, `search_in_files`, `replace_in_files`, `diff_files`, `get_file_tree` | Wired | - |
| Shell | `run_command` (guarded), `run_test`, `install_package` | Partial | `run_command_custom`, `run_shell`, `start_shell`, `close_shell`, `run_code` |
| Git | 11 `git_*` tools including `git_create_pr` and `git_undo`, plus `add_git_hook`, `git_status_enhanced`, `git_log_enhanced` | Wired | `run_command_custom`, `run_shell`, `start_shell`, `close_shell`, `run_code` |
| Codegen | `refactor_code`, DB/Docker/API-client/docs generators, `profile_code`, `optimize_code`, `generate_tests`, `inline_edit`, `apply_code_action` | Partial | - |
| LSP | `lsp_definition`, `lsp_references`, `lsp_hover`, `lsp_diagnostics`, `lsp_completions`, `lsp_code_actions`, `lsp_workspace_symbol` | Partial | - |
| Skills | `list_skills`, `use_skill` | Partial | skill authoring/removal now lives in the `skill` CLI (not a tool) |
| Context | `get_repo_map`, `get_file_tree` | Partial | `get_context_info` (needs the agent message state; the Rust dispatch is stateless) |
| Web | `web_search` (Brave/Tavily/Exa/DuckDuckGo provider chain with DuckDuckGo fallback), `fetch_url` (cleaned text, 3000-char cap) | Wired | - |
| Tasks/plans | `task`, `submit_task`, `get_task`, `list_tasks`, `plan_approve`, `plan_reject` | Partial | `TaskQueue.cancel()` (no Python tool exposes it either), durable `task_queue.py` |
| Session/shares | HTTP routes only | Partial | `share_session`, `bookmark_session`, `restore_bookmark` |
| Env/config | - | Missing | `get_env`, `set_env`, `list_env`, `set_theme`, `get_keybindings`, tool timeouts |
| Billing | `billing_cost`, `billing_quota`, `billing_usage`, `billing_plan`, `billing_summary` | Wired | cost-history limits, trial logic |
| UX/interaction | `ask_user`, `select_files`, `clipboard_read`, `clipboard_write`, `retry_last`, `retry_tool` | Partial | history search |

## Dead-code policy

1. The crate root must never contain `#![allow(dead_code)]`. The integration
   test `crate_root_has_no_global_dead_code_allow` enforces this.
2. Use `#[allow(dead_code)]` only for code that is genuinely unwired *and* has
   a named near-term milestone. Every attribute needs an adjacent comment with
   a one-line justification and a `TODO(v2.6)` (or later) exit criterion.
3. Prefer deleting duplicate or unused code over allow-listing it. Increment 1
   removed `Agent::session_path`, `lsp::get_lsp_manager`,
   `plugins::plugin_count`, `McpServerConfig::name`, `McpManager::all_tools`,
   and `Memory::path`.
4. Module-level allows are reserved for whole modules with no caller. Adding
   one requires an entry in this document. There is currently none: the
   `permission` module went live with the dispatch gate in this increment.
5. When an allow is removed: wire the code, add CLI/HTTP/tool or unit coverage,
   update the matrix above, and run all gates.
6. Do not add dependencies just to remove an allow.

### Current allow inventory (27 attributes)

| Scope | Location | Item(s) | Why it is unwired | Exit criterion |
| --- | --- | --- | --- | --- |
| Item | `codegen.rs` | `extract_method` | No refactor style | Add `extract_method` style |
| Item | `codegen.rs` | `convert_to_class` | No refactor style | Add `convert_to_class` style |
| Item | `codegen.rs` | `add_type_hints` | Tool only edits one signature | Add whole-file type-hint mode |
| Item | `codegen.rs` | `get_connection_string` | No DB connection surface | Expose DB scaffolding tool |
| Item | `codegen.rs` | `generate_queries` | No CRUD surface | Expose CRUD queries |
| Item | `codegen.rs` | `generate_curl` | No curl transport | Add `transport=curl` |
| Item | `hooks.rs` | `register_hook` | No config registration site | Load hooks at startup |
| Item | `hooks.rs` | `hook_count` | Not exposed in config API | Add hook count to `/api/v1/config` |
| Item | `memory.rs` | `list_facts` | CLI report needs tags | Add `memory list --names` |
| Item | `permission.rs` | `PermissionAction::value` | No CLI reads action strings yet | `apex-rs permission list` |
| Item | `permission.rs` | `PermissionRule::remember` | Consumed by the unwired request flow | Wire approval |
| Item | `permission.rs` | `PermissionRequest` (struct) | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `requests`, `request_id_counter` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `remove_rule` | No rule-management command | `permission rule remove` CLI |
| Item | `permission.rs` | `clear_rules` | No rule-management command | `permission rule clear` CLI |
| Item | `permission.rs` | `request_permission` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `approve_request` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `deny_request` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `get_pending_requests` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `get_request` | Request flow unwired: no prompt surface | Wire approval |
| Item | `permission.rs` | `get_tool_permission` | Consumed by the unwired request flow | Wire approval |
| Item | `permission.rs` | `PermissionRequestDenied` | Thrown by the unwired request flow | Wire approval |
| Item | `server.rs` | `ChatReq::agent` | Chat selects one agent | Select requested agent in `/api/v1/chat` |
| Item | `shell_security.rs` | `CommandCategory::Package` | Python never returns it | Classify pip/npm installs |
| Item | `skills.rs` | `three_way_diff` | No diff3 tool | Add `diff3_files` |
| Item | `skills.rs` | `get_skill_manager` | Tools construct managers directly | Share a cached manager |

There are currently no module-level allows; the 27 item-level attributes
are the complete inventory.

## Verification

Run from `rust/apex-rs`:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test
```

Current baseline: 327 unit tests + 19 binary E2E tests. The E2E suite runs
`tests/cli_e2e.rs` against `CARGO_BIN_EXE_apex-rs`, overrides `HOME` and
`USERPROFILE` with a temporary directory, and requires no network or API key.
It covers `--help`, tool schemas, cost, memory lifecycle, session lifecycle
(including encrypted files, JSON output, and loading Python-written Fernet
fixtures under both key schemes), security verdicts plus the
`run_command` guard, the context CLI commands, the `workspace` CLI (prompt
block and JSON in a dirty git repository), the `serve` context HTTP
routes with auth off by default, the rollback CLI
(snapshot/list/restore/delete and record/revert/history against real
repositories), the `github` CLI (install/run/usage parity and
issue/PR/automate error paths against a dead local port), the `skill`
add/list/remove lifecycle, the full HTTP-auth flow (CLI-created key, the three
carriers, exact 401 body, protected auth routes, out-of-band revoke, 429 +
`Retry-After` with 401s not consuming budget), the gateway lifecycle against
a local fake OpenRouter upstream (PR 350: CLI key generation and status, all
eight routes, the tier model gate, usage counters, the admin trio, and an
out-of-band revoke), and the absence of the
crate-level allow. PR 349 adds two E2E tests:
`serve_exposes_python_parity_routes` (hits every Python-parity route that
does not require an LLM call, plus the SSE `connected` frame and the
diff/decision error paths) and `serve_diff_preview_accepts_and_rejects`
(full diff preview lifecycle against a real git repository: clean tree,
modified tree, fingerprint change, `409 diff_changed` on a stale
fingerprint, and reject/restore of a working-tree change).

## Next increments

1. Port Python's remaining session metadata beyond `name`/`timestamp`/`model`/`cwd`/`history`/`usage` (already partially done via session forks/branches).
2. Remaining items: missing tools (80→102 schemas) and the Rust-only surface that still lacks a Python counterpart.
