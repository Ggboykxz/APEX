# Rust / Python Parity

Internal GA baseline for `rust/apex-rs` (last updated for the v2.6
HTTP-auth increment). The reference is the Python package in `apex/` on `dev`.
"Parity" here means that a behaviour is reachable from the Rust binary, HTTP
server, or tool registry and has automated coverage - not that the
implementations are line-for-line equivalent.

Scale at this baseline: ~22,715 lines of Python in `apex/*.py` versus ~13,950
lines of Rust in `rust/apex-rs/src`. Rust is deliberately a smaller surface;
the tables below record the difference instead of implying full coverage.

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
key {create,list,revoke,delete}
```

HTTP server (`serve`): 43 routes, including `/health`, `/api/v1/tools`,
`/api/v1/security/analyze`, `/api/v1/auth/{login,logout,status}`, sessions,
shares/export, files, models, config, themes, cost, chat, chat streaming,
context (`repo-map`, `git`, `stats`, `ctags`, `tree`, `glob`),
`/api/v1/rate-limit`, and WebSockets. API-key auth is opt-in with
`APEX_REQUIRE_AUTH` (`/health` and the WebSocket routes exempt).

Tool registry: 51 schemas. Python exposes 102 schema names in `apex/tools.py`.

## Module matrix

| Python | Rust | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py`, `__main__.py`, `main.py` | `main.rs` | Partial | Core CLI (`run`, `chat`, `serve`, tools, cost, memory, session, security, context, github, skill, key). Most of Python's command suite is not ported. |
| `apply_patch.py` | `patch.rs` | Wired | Multi-file patch engine reachable through the `apply_patch` tool (and `dry_run` preview): Codex-style and unified-diff dialects, pre-write validation (traversal, absolute, duplicate, size, binary), hunk matching with fuzz and signed offset warnings, no-newline markers, atomic temp-file + rename writes with best-effort rollback. |
| `agent.py` | `agent.rs` | Partial | One-shot run, streaming REPL, tool-call loop, cost reporting. Session forking/rewind and some prompt features are absent. |
| `agents.py` | - | Missing | No subagent registry, markdown agent loading, or parallel orchestration. |
| `config.py`, `config_v2.py` | `config.rs` | Partial | Env/model/cwd config and shared home resolution. No JSONC hierarchy, migration, or validation layer. |
| `config_tools.py` | - | Missing | No config-defined custom tools. |
| `context.py` | `context.rs` | Wired | CLI `context repo-map\|git\|stats\|ctags\|tree\|glob` and `GET /api/v1/context/*`: repo map, git info, language stats, ctags file list, file tree, glob search. `get_repo_map` and `get_file_tree` are also exposed as tools on top of the same functions. |
| `context_manager.py`, `context_tracking.py` | - | Missing | No summarisation/compaction accounting. |
| `cost_local.py` | `cost.rs` | Wired | Pricing table, usage, cost history; CLI `cost` and HTTP cost routes. |
| `codegen.py` | `codegen.rs` | Partial | Refactor, DB model, Dockerfile/compose, API client, docs, profile, optimize tools. Six helper operations remain test-only. |
| `formatter.py` | `formatter.rs` | Partial | `format_file` tool only. No format-on-write pipeline or formatter discovery parity. |
| `github_integration.py` | `github.rs` | Wired | `git_*` tools and `git_create_pr` work through `gh`/REST. The `github` CLI group exposes `install`/`run` (Python parity), `issue`/`issue-close`/`pr`/`pr-merge` through `GitHubClient`, and the six `GitHubAutomation` flows under `github automate`. API base overridable with `APEX_GITHUB_API` (tests). |
| hooks inside `plugins.py`/`tools.py` | `hooks.rs` | Wired | `trigger_hooks` runs on tool dispatch. Registration from config is not wired. |
| `http_api.py`, `server.py` | `server.rs` | Partial | 43 routes, SSE/WebSocket streaming, shell guard, per-key rate limiting, opt-in API-key auth. Auth is enabled with `APEX_REQUIRE_AUTH` (`1`/`true`/`yes`/`on`); `/health`, `/ws` and `/ws/events` stay exempt. Carriers follow Python: `Authorization: Bearer …` → `?api_key=` → `X-API-Key`; `POST /api/v1/auth/{login,logout}` and `GET /api/v1/auth/status` are wired and auth-protected. Python's `apex serve` enables auth by default, the Rust port does not (the TUI backend sends no key) — documented divergence. Full route parity is still missing. |
| `lsp.py`, `lsp_diagnostics.py` | `lsp.rs` | Partial | Definition, references, hover, diagnostics tools. No persistent per-workspace manager or completion/code-action tools. |
| `mcp.py` | `mcp_client.rs`, `jsonrpc.rs` | Wired | Stdio JSON-RPC, server discovery, tool bridge, global registry; CLI and server use it. |
| `memory.py` | `memory.rs` | Wired | CLI list/add/search/context/remove/clear, REPL `/memory`, session context injection. No automatic fact extraction. |
| `permission.py` | `permission.rs` | Wired | `dispatch_gate` enforces rules at both agent dispatch sites (one-shot and streaming). Headless manager: `*` → ALLOW (no prompt surface), ASK refuses with the rule reason. `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK` env rules. Interactive request/approve flow is unwired (no prompt surface). |
| `plugins.py` | `plugins.rs` | Wired | Manifest discovery, namespaced plugin tools, CLI/server listing and execution. Rust invokes declared tools; it does not execute Python plugin source in-process. |
| `rate_limiter.py` | `rate_limiter.rs` | Wired | Per-key in-memory limiter enforced by middleware on every `serve` route except `/health` (bucket is `key:{key_id}` once auth validates the key — Python parity — else the carrier from `Authorization`/`?api_key=`/`X-API-Key`, or `anonymous`; 429 + `Retry-After`). `GET /api/v1/rate-limit` exposes the caller's counters, limits and `reset_at`; limits via `APEX_RATE_LIMIT_*`. SQLite backend not ported. |
| `session.py` | `share.rs`, `session_crypto.rs`, `server.rs` | Partial | Fernet-compatible encrypted save/load/list, CLI and HTTP session routes. Branching and all Python session metadata are absent. |
| `share.py` | `share.rs`, `server.rs` | Wired | Redaction, share/unshare/list/export, CLI help through sessions, HTTP routes. |
| `shell_security.py` | `shell_security.rs` | Wired (increment 1) | CLI `security check/allowed`, `POST /api/v1/security/analyze`, `run_command` tool guard, and `/api/v1/bash` guard. |
| `skills.py`, `skills_system.py` | `skills.rs` | Partial | `list_skills`/`use_skill`, diffs, search/replace, code analysis tools. Skill authoring is wired through the `skill` CLI (`list`/`add`/`remove`); `add`/`remove` also persist to `.apex/skills/*.md` (Python's are in-memory only and unwired there). Three-way diff remains unwired. |
| `tools.py` | `tools.rs`, `web.rs`, `task_queue.rs` | Partial | 51 tools: files, shell, git, codegen, LSP, skills, repository context, web, task queue & plans. Python exposes 102 schema names; the tool table below records the uncovered categories. |
| `git_undo.py` | `tools.rs` | Partial | `git_undo`, `undo_last_edit`, `redo_last_edit`. No snapshot history or workspace rollback. |
| `advanced.py` | `server.rs` | Partial | SSE streaming exists. Retry, batching, and timeout policy are not ported. |
| `theme_manager.py` | `server.rs` | Partial | Read-only `/api/v1/themes` route. No theme mutation, custom themes, or UI integration. |
| `commands.py`, `commands_manager.py` | `main.rs` | Partial | Built-in clap subcommands only. No user/project custom command loading. |
| `workspace.py`, `workspace_rollback.py` | - | Missing | No workspace awareness, side-git snapshots, or `/restore`. |
| `api_key.py` | `api_key.rs` | Partial | JSON-file key store (`~/.apex/api_keys.json`, overridable with `APEX_API_KEYS_FILE`; Python uses SQLite) re-read on every operation, so CLI changes reach a running server. `apex_` + 32 random bytes (urlsafe base64), sha256 at rest, expiry/active checks, `last_used`/`request_count`, CLI `key {create,list,revoke,delete}`. Python's per-key rate limits/permissions/metadata are carried in the schema but not enforced (its `validate_key` does not check them either); workspace CRUD is not ported (fixed `default` workspace). Writes are atomic (temp + rename) but not transactionally serialised across processes like SQLite. |
| `billing.py` | - | Missing | No billing, cost-history limits, or trial logic. |
| `sandbox.py` | - | Missing | No isolated code execution. |
| `task_queue.py` | - | Missing | No durable background tasks. |
| `snapshot.py` | - | Missing | No snapshot system beyond the in-memory edit undo stack. |
| `watcher.py` | - | Missing | No file watcher. |
| `project.py` | - | Missing | No project initialisation/analysis. |
| `mentions.py` | - | Missing | No `@file`/`@agent` mention expansion. |
| `slash.py` | - | Missing | No slash-command system. |
| `structured_message.py` | - | Missing | Messages are plain strings/JSON, not structured parts. |
| `task`/plan tooling in `tools.py` | `task_queue.rs`, `tools.rs` | Partial | `task` (delegates against the 11 built-in agent names; custom agents from `.apex/agents/*.md` are not scanned), `submit_task`/`list_tasks`/`get_task` (in-memory queue, one background thread per task - Python's `asyncio.run` actually cancels the spawned coroutine on loop teardown, so a task stays `pending` there), `plan_approve`/`plan_reject` (always `No pending plan` - Python's `_plan_approval` is never set on the executor either). `TaskQueue.cancel()` and the durable `task_queue.py` remain unported. |
| `ui.py`, `i18n.py` | - | Missing | No terminal UI or localisation; the TUI remains separate. |
| `telemetry.py` | - | Missing | No telemetry/logging pipeline. |
| `rlm.py` | - | Missing | No batched remote-model query support. |
| `extras.py` | `task_queue.rs` | Partial | `TaskQueue` (submit/list/get, in-memory, one background thread per task). Shell expansion, history search, env manager, and workspace validator are not ported. |
| `apex/gateway/*` | - | Missing | No gateway auth/router/server. |

## Tool coverage

| Category | Rust tools | Status | Notable Python tools not ported |
| --- | --- | --- | --- |
| Files | `read_file`, `write_file`, `edit_file`, `apply_patch`, `list_files`, `search_in_files`, `replace_in_files`, `diff_files`, `get_file_tree` | Partial | `apply_edit`, `preview_edit`, `create_directory`, `delete_file`, `batch_read`, `batch_write`, `read_image`, `glob_search` |
| Shell | `run_command` (guarded) | Partial | `run_command_custom`, `run_shell`, `start_shell`, `close_shell`, `install_package`, `run_code`, `run_test` |
| Git | 11 `git_*` tools including `git_create_pr` and `git_undo` | Partial | `add_git_hook`, richer status/log helpers |
| Codegen | `refactor_code`, DB/Docker/API-client/docs generators, `profile_code`, `optimize_code` | Partial | `generate_tests`, `inline_edit`, `apply_code_action` |
| LSP | `lsp_definition`, `lsp_references`, `lsp_hover`, `lsp_diagnostics` | Partial | completions, code actions, workspace-symbol search |
| Skills | `list_skills`, `use_skill` | Partial | skill authoring/removal now lives in the `skill` CLI (not a tool) |
| Context | `get_repo_map`, `get_file_tree` | Partial | `get_context_info` (needs the agent message state; the Rust dispatch is stateless) |
| Web | `web_search` (Brave/Tavily/Exa/DuckDuckGo provider chain with DuckDuckGo fallback), `fetch_url` (cleaned text, 3000-char cap) | Wired | - |
| Tasks/plans | `task`, `submit_task`, `get_task`, `list_tasks`, `plan_approve`, `plan_reject` | Partial | `TaskQueue.cancel()` (no Python tool exposes it either), durable `task_queue.py` |
| Session/shares | HTTP routes only | Partial | `share_session`, `bookmark_session`, `restore_bookmark` |
| Env/config | - | Missing | `get_env`, `set_env`, `list_env`, `set_theme`, `get_keybindings`, tool timeouts |
| UX/interaction | - | Missing | `ask_user`, `select_files`, clipboard, history search, retry |

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

Current baseline: 171 unit tests (170 on Windows - the atomic-write rollback
test is POSIX-gated) + 12 binary E2E tests. The E2E suite runs
`tests/cli_e2e.rs` against `CARGO_BIN_EXE_apex-rs`, overrides `HOME` and
`USERPROFILE` with a temporary directory, and requires no network or API key.
It covers `--help`, tool schemas, cost, memory lifecycle, session lifecycle
(including encrypted files and JSON output), security verdicts plus the
`run_command` guard, the context CLI commands, the `serve` context HTTP
routes with auth off by default, the `github` CLI (install/run/usage parity
and issue/PR/automate error paths against a dead local port), the `skill`
add/list/remove lifecycle, the full HTTP-auth flow (CLI-created key, the three
carriers, exact 401 body, protected auth routes, out-of-band revoke, 429 +
`Retry-After` with 401s not consuming budget), and the absence of the
crate-level allow.

## Next increments

1. Add a Python-written Fernet session fixture to prove cross-language
   compatibility, not just self-round-tripping.
2. Port the workspace/key-workspace layer (`workspace.py`, key scoping) or
   record why it stays out of the Rust port.
