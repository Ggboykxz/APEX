# Changelog

All notable changes to APEX are documented in this file. The project follows [Semantic Versioning](https://semver.org/).

## Unreleased

### Rust migration — Phase 2c (custom tools + durable tasks)

- **Ported `apex/config_tools.py`** as a new Rust module
  (`rust/apex-rs/src/config_tools.rs`): the 34-command `ALLOWED_COMMANDS`
  allowlist, the dangerous-pattern blocklist (`$( `, backtick, `rm -rf`,
  `chmod 777`), `CustomToolManager` (register/get/list/execute/get_schemas),
  the one-shot `ensure_tools_loaded` directory scan, the YAML `custom_tools:`
  loader, `{key}`/`{{ }}` command templating (`ERROR: '{key}'` on a missing
  key), and the 30 s capped execution returning `stdout or stderr or
  "[no output]"`. Wired into the registry: `tool_schemas()` (the `tools` CLI
  and the agent's tool list) appends the manager's schemas after the
  built-ins, and `execute_tool` dispatches unknown names through the manager
  before `ERROR: Unknown tool '…'` (Python's `ToolExecutor.execute` order).
- **Divergence (documented)**: Python's `load_tools_from_dirs` imports
  `*.py` modules exposing a `TOOL_DEFINITION` with a callable handler; Rust
  cannot import Python, so the same four directories
  (`~/.config/opencode/tools`, `./.opencode/tools`, `~/.config/apex/tools`,
  `./.apex/tools`) are scanned for `*.json` definitions
  (`{name?, description?, parameters?, command, cwd?}`) that run through the
  same allowlist/pattern/timeout pipeline. The dispatch keys by the defined
  name, so a `custom_{name}` schema call is unreachable — Python has the same
  gap (its manager also keys by the defined name).
- **Ported `apex/task_queue.py`** as a new Rust module
  (`rust/apex-rs/src/durable_tasks.rs`): `TaskStatus` (5 lowercase values),
  `Task` (10 fields, same JSON shape on disk), and `TaskQueue` (enqueue with
  `task_{YYYYmmddHHMMSS}_{n}` ids, get, list newest-first with status filter
  and limit, cancel PENDING only, clear_completed, delete, persistence to
  `~/.apex/tasks/tasks.json` rewritten on every mutation). Python's only
  production consumer is the TUI REPL `/tasks` command (excluded from the
  Rust port), so — like the snapshot manager — the Rust server is the
  production surface:
  - `serve` holds one `TaskQueue` in `AppState`.
  - Six new routes: `POST /api/v1/tasks` (enqueue), `GET /api/v1/tasks`
    (`?status=&limit=`, default 100, newest first), `GET
    /api/v1/tasks/:id`, `DELETE /api/v1/tasks/:id`, `POST
    /api/v1/tasks/:id/cancel` and `POST /api/v1/tasks/clear`. All answer 200
    with an `ok` flag (no 4xx).
  - Divergences: `get` returns a snapshot copy (Python returns a live
    reference); a corrupt `tasks.json` resets the queue to empty (Python
    additionally crashes on an invalid status string); `stop_workers` joins
    each thread instead of `join(timeout=1)`. `start_worker`/`stop_workers`
    are dead in Python too (production never starts a worker) and stay
    item-scoped.
- Tests: 38 new unit tests (allowlist/blocklist, shlex quoting, templating,
  timeouts, tool-dir scanning, task lifecycle, persistence/rehydration) and
  two E2E tests: `custom_tools_via_cli` (`.apex/tools/*.json` registration,
  `call-tool` execution of the defined command, the `custom_` schema in the
  `tools` listing, a blocked `sudo` command not registering) and
  `serve_durable_tasks_lifecycle` (enqueue/list/filter, cancel and delete
  idempotence, clear, and persistence across a server restart in the same
  sandbox HOME).
- PARITY.md: `config_tools.py` and `task_queue.py` Missing → Wired; route
  parity counters updated (94 production registrations = 53 Python + 41
  Rust-only extras); item-level allow inventory 114 → 119 (two in
  `config_tools.rs`, three in `durable_tasks.rs`); baseline 383 unit + 29
  E2E tests.

### Rust migration — Phase 2b (snapshot manager)

- **Ported `apex/snapshot.py`** as a new Rust module (`rust/apex-rs/src/snapshot.rs`):
  `ActionType` (6 variants with Python's values), `FileChange`, `Snapshot`
  + `to_dict`, and `SnapshotManager` (track, add_file_change, track_file,
  naive line diff, get_snapshot, restore, undo, redo, can_undo/can_redo,
  get_history with Python's `[-limit:]` semantics, clear), plus a side git
  repo under `.apex/snapshots/` (best-effort `git init`, like Python's
  captured subprocesses). Python exports `SnapshotManager` but never calls
  it (its `/undo` and `/redo` routes use a separate `session.UndoManager`),
  so — like `workspace.rs` — the Rust server is now its production surface:
  - `serve` holds one `SnapshotManager` in `AppState` (rooted at the server
    cwd).
  - Seven new routes: `POST /api/v1/snapshot/{track,track-file,undo,redo,restore}`
    and `GET /api/v1/snapshot/{history,status}`. All answer 200 with an `ok`
    flag (no 4xx), mirroring `/api/v1/undo`/`/api/v1/redo`. `history` takes
    `?limit=` (Python's default of 50; `0` returns all, matching Python's
    `[-0:]` slice).
- **Fixed a latent Python bug (documented divergence)**: Python's `undo()`
  pops the snapshot and then calls `restore(id)`, which looks it up in the
  undo stack where it no longer exists — so Python's undo never restored
  any file. The port applies the popped snapshot's file changes directly;
  `restore(id)` stays the lookup API.
- `track_file` captures only `before` (`after` stays null), so a redo after
  `track_file` rewrites nothing (Python parity). `file_hash`,
  `save_snapshot_to_git` and `clear` remain item-scoped (dead in Python too).
- Tests: 10 unit tests (action types, diff, tracking, undo/redo, restore,
  history, `to_dict` shape, snapshots dir) and the E2E
  `serve_snapshot_undo_redo_lifecycle` (track-file → modify → undo → status
  → no-op redo → history → empty-stack undo, against a running server).
- PARITY.md: `snapshot.py` Missing → Wired; route parity counters updated
  (88 production registrations = 53 Python + 35 Rust-only extras);
  item-level allow inventory 111 → 114 (three in `snapshot.rs`).

### Rust migration — Phase 2 (context tracking + mentions)

- **Wired the last two Ported modules** in `rust/apex-rs` (`context_tracking`
  and `mentions`), leaving no ported-but-unwired module in the parity matrix:
  - `context_tracking` — every `Agent` now carries a `ContextTracker`
    (`default_with_budget`: 128k token budget, 80% threshold).
    `record_api_usage` feeds `record_usage`, and the auto-compact gate in
    `chat`/`chat_stream` now also fires on `should_compact` (token budget)
    alongside the existing message-count threshold. New route
    `GET /api/v1/context/tracking` exposes the budget, threshold and
    per-session stats. `record_compaction`, `remove` and the compaction
    history stay item-scoped until `Agent::compact_context` records them.
  - `mentions` — `Agent::expand_mentions` (both `chat` and `chat_stream`)
    now parses input with `MentionParser::parse` + `resolve_file` instead of
    `split_whitespace`, faithful to `apex/mentions.py` (boundary `@file.py`
    and in-word `src@file.py` forms, case-insensitive agent dedup). File
    mentions are inlined with the same `[File: …]` format as before (images
    as base64, uncapped); agent mentions are recognized but not inlined
    (subagent routing is a TUI concern, Python parity). `read_mentioned_files`
    and `FileMentionCompleter` remain item-scoped (TUI surface).
- Dead-code inventory: item-level allows dropped from 115 to 111
  (`context_tracking.rs` 5 → 4, `mentions.rs` 6 → 3, scoped more precisely);
  the stale `sandbox.rs` count in the inventory (5) is corrected to 6.
- New tests: unit coverage for mention expansion (file, missing file, image
  base64, agent mentions) and context-tracker wiring, plus the E2E
  `serve_exposes_context_tracking_route`. Route parity counters updated in
  PARITY.md (81 registrations = 53 Python + 28 Rust-only extras, including
  the previously uncounted `GET /api/v1/telemetry`).

### Rust migration — Phase 1 (wire the remaining backend modules)

- **Wired 10 of the 10 PR-#348 modules** in `rust/apex-rs`:
  - `i18n` — new CLI `apex-rs locale [--lang]` reports the active locale and
    prints a localized welcome string; fixed a latent bug (the lookup used
    `LOCALES` instead of `STRINGS` and the type declared 13 strings per locale
    while every locale has 14). The module was never compiled before because
    `mod i18n` was not declared in `main.rs` — now wired.
  - `telemetry` — `serve` records session and agent start at bootstrap, and a
    new `GET /api/v1/telemetry` route exposes event statistics and performance
    metrics.
  - `sandbox` — `CodeSandbox::run_code` exposed as the new `run_code` tool
    (python/javascript/bash/ruby/go/rust/php) with output truncation and
    exit-code reporting; unsupported languages fail deterministically.
  - `watcher` — new CLI `apex-rs watch [PATH]` lists the non-ignored files of
    a tree (config + `.gitignore` patterns); `serve` now starts the global
    `FileWatcher` on the project directory at bootstrap (disabled by default
    via `WatcherConfig.enabled`).
  - `structured_message` — new CLI `apex-rs message <role> <content>` builds a
    structured message (typed parts) and prints it as JSON.
  - `rlm` — new CLI `apex-rs rlm <key> [--inc]` reports (or increments) the
    per-key minute/hour/day rate limits as JSON. `RLMQuery` (batched LLM
    queries) remains an error stub (no litellm equivalent in Rust).
  - `formatter`, `billing`, `project`, `slash` were already reachable from the
    tool registry / HTTP server; their stale module-level
    `#![allow(dead_code)]` attributes were removed and their secondary APIs
    scoped to item-level allows with `TODO(v2.6)` exit criteria.
- Removed all 10 module-level dead-code allows: no module in `rust/apex-rs`
  carries a module-level `#![allow(dead_code)]` anymore. Updated the dead-code
  inventory and module matrix in `rust/apex-rs/PARITY.md` and AGENTS.md.
- Workflows: `pr-checks.yml` now detects `rust/**` (plus root `Cargo.toml`)
  in its changed-paths filter, alongside python/tui/website/docs.
- New E2E tests: `cli_locale_command_works`,
  `serve_exposes_telemetry_route`,
  `run_code_tool_is_hermetic_and_rejects_unsupported_language`,
  `cli_message_command_builds_structured_message`,
  `cli_watch_lists_non_ignored_files` and
  `cli_rlm_reports_rate_limits`. Clippy fixes
  exposed by removing module-level
  `clippy::all` allows (billing collapsible-if/str-replace, telemetry
  sort-by-key/iter-kv-map).

### Docs & governance

- **README overhaul** — rewrote `README.md` to realign with the current codebase: corrected the primary-agent table (`build`/`plan`/`planner`/`shell`, matching `apex/agents.py`), fixed the model-section TOC fragment, corrected the sample `--agent plan` flag, updated the tool count to 100+, and expanded the Rust-backend section to cover shell security, HTTP auth, rate limiting, the permission gate, the gateway, and route parity. Update to `CHANGELOG.md` and `docs/changelog.md` alongside.

### CI & automation

- **opencode AI maintainer** — `.github/workflows/opencode.yml` answers `/oc` / `/opencode` comments from maintainers only (`OWNER` / `MEMBER` / `COLLABORATOR`, bots rejected) on issues, PRs, and review lines. It uses OIDC app tokens, a 30-minute timeout, per-issue concurrency, no session sharing, and fails with a clear message when no provider key is configured. The archived upstream action is pinned to `github-v1.2.28` (`17b79f4e…`). Setup requires the `opencode-agent` GitHub App plus `DEEPSEEK_API_KEY` or `ANTHROPIC_API_KEY`; the `OPENCODE_MODEL` repository variable overrides the default DeepSeek model.
- **Stale workflow** — dependency PRs are exempt from the `stale` workflow (`dependencies` joins `pinned`, `security` and `keep-open`), so Dependabot updates are never auto-closed for inactivity.
- **Merge queue & Dependabot auto-merge** — `merge_group` is enabled on `CI`, `Security` and `TUI`; repository auto-merge is enabled. A new `dependabot-auto-merge` workflow auto-approves and enables auto-merge for Dependabot patch/minor updates. PR metadata workflows (`commitlint`, `pr-checks`, `labeler`, `welcome`, `dependency-review`, `release-drafter`) remain PR-event only.

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

- **CLI** — `run`, `chat`, `serve`, `tools`, `plugins`, `call-tool`, `cost`, `memory`, `session`, `security`, `context`, `workspace`, `rollback`, `github`, `skill`, `key`, `gateway`.
- **Repository context** — `context.rs` mirrors `apex/context.py`: `apex-rs context repo-map|git|stats|ctags|tree|glob` and `GET /api/v1/context/*` (79 route registrations covering all 52 `apex/http_api.py` routes), with `?path=`, `?depth=` and `?pattern=`.
- **Rate limiting** — `rate_limiter.rs` wired into `serve`: per-key in-memory limits (`X-API-Key` / `Authorization: Bearer` / `anonymous`) on every route except `/health`, 429 + `Retry-After` with the Python response body, `GET /api/v1/rate-limit` counters, and `APEX_RATE_LIMIT_*` env overrides.
- **Permission gate** — `permission.rs` enforced at both agent dispatch sites (one-shot and streaming): first-match rules, headless manager (`*` → ALLOW since there is no prompt surface, ASK refuses with the rule reason), and `APEX_PERMISSION_DENY` / `APEX_PERMISSION_ASK` env rules. The interactive request/approve flow is ported but unwired.
- **Editing tools** — `edit_file` (first-occurrence replacement, Python-identical success/error strings) and `apply_patch` via the new `patch.rs`, a faithful port of `apex/apply_patch.py`: Codex-style and unified-diff dialects, full pre-write validation (path traversal, absolute paths, duplicate targets, 1 MB patch / 512 KB file limits, binary content), hunk matching with forward/backward fuzz and signed offset warnings, no-newline markers, and atomic temp-file + rename writes with best-effort rollback. `dry_run` previews without writing.
- **Context tools** — `get_repo_map` and `get_file_tree` expose the existing `context.rs` functions as registry tools (tool registry is now 43 schemas): the repository map from the working directory (Python ignores the tool's `path` argument; the Rust arm does the same) and an ASCII file tree with `max_depth` (default 3), directories first, dotfiles hidden, and Python's `ERROR: Path not found: …` on a missing path. `get_context_info` stays Missing (it needs the agent message state, which the stateless Rust dispatch does not keep).
- **Web tools** — `web_search` (Brave/Tavily/Exa/DuckDuckGo provider chain, identical to Python, with DuckDuckGo fallback and `ERROR: Web search failed: …`) and `fetch_url` (redirects followed, 30 s timeout, script/style/tag/`&[a-z]+;` cleaning in Python's exact order, 3000-char cap with `...`). New `web.rs`; HTTP runs on a dedicated thread with its own runtime, like `github::http_json`, so both tools work from the CLI and from inside the agent loop.
- **Task & plan tools** — `task` (validates `agent` against the 11 built-in names from `apex/agents.py` and returns `[Delegated to @{agent}]: {task}`, or `ERROR: Unknown agent: …`), `submit_task` / `list_tasks` / `get_task` backed by a new `task_queue.rs` porting the `TaskQueue` from `apex/extras.py` (in-memory, one background thread per task, `stdout or stderr` as the result, `completed` / `failed` statuses, 8-char ids in the shape of Python's `uuid4()[:8]`), and `plan_approve` / `plan_reject` (always `ERROR: No pending plan to …` — Python's `_plan_approval` is never set on the executor either). Tool registry is now 80 schemas.
- **GitHub CLI & skill authoring** — `github.rs` is wired through a `github` CLI group: `install` / `run` (Python `_cmd_github` parity: three info lines, then `Found N issues and M PRs` against the detected repo), `issue` / `issue-close` / `pr` / `pr-merge` over the REST `GitHubClient`, and `automate {create-pr,changes,issue,list,todos,close-completed}` over `GitHubAutomation` (credentials from `GITHUB_TOKEN` / `GH_TOKEN`, API root overridable with `APEX_GITHUB_API` — tests point it at a dead local port). `apex-rs skill {list,add,remove}` exposes `SkillManager::add`/`remove`; `add` persists to `.apex/skills/<name>.md` in the loader's exact format (Python's add/remove are in-memory and unwired there) and `remove` deletes the project file, so a fresh process sees the change. Skill names reject path separators and `..`. Five more dead-code allows removed (28 remain).
- **HTTP auth & route-level E2E** — opt-in API-key authentication (`APEX_REQUIRE_AUTH=1|true|yes|on`) on every `serve` route except `/health`, `/ws` and `/ws/events`, with Python's carrier precedence (`Authorization: Bearer …` → `?api_key=` → `X-API-Key`) and the exact 401 body (`{"error": "Authentication required", "code": "AUTH_REQUIRED"}`). New `api_key.rs` stores `apex_` + 32 random urlsafe-base64 bytes as sha256 in `~/.apex/api_keys.json` (`APEX_API_KEYS_FILE` overrides; Python uses SQLite), re-read on every request so `apex-rs key {create,list,revoke,delete}` reaches a running server. `POST /api/v1/auth/{login,logout}` and `GET /api/v1/auth/status` are wired and, when auth is on, protected like every other route; auth wraps the limiter so 401s never consume key budget. `GET /api/v1/rate-limit` now reports the minute-window `reset_at`, retiring the last `rate_limiter` allow (27 remain). Python's `apex serve` defaults auth on; the Rust port defaults off because the TUI backend sends no key (divergence recorded in `PARITY.md`).
- **HTTP route parity** — the `serve` router now covers all 52 routes of `apex/http_api.py` (79 route registrations total, plus 26 Rust-only extras): `GET /`, `POST /chat`, `GET /stream`, `GET /models` + `POST /api/v1/models/refresh` + `GET /api/v1/providers`, `POST /session/save|load`, `GET /metrics`, `GET /rate-limit/status`, `GET/POST /api/v1/config`, `GET /api/v1/agents{,/:id}`, `DELETE /api/v1/sessions/:id`, `POST /api/v1/unshare/:id`, `GET/POST /api/v1/themes`, `GET /api/v1/stats`, `GET /api/v1/formatters` + `POST /api/v1/format`, `GET /api/v1/commands` + `POST /api/v1/commands/execute`, `GET /find/file`, `POST /api/v1/command`, `GET /global/health`, `POST /api/v1/init`, `GET /api/v1/export/:session_id`, `POST /api/v1/import`, `GET /global/event` (SSE with 30 s keepalive), `GET /api/v1/session/:id/diff` + `POST .../diff/decision` (fingerprint-validated accept/reject, `409 diff_changed`), `POST /api/v1/session/:id/{fork,abort}`, and the LSP/formatter/MCP status routes. New `models.rs` (static model/provider table) and `commands.rs` (markdown custom-command manager with `$ARGUMENTS`/`$N`/`!cmd`/`@file` templating) back the ported routes. The rate-limit middleware now releases its lock before running the handler, fixing a latent deadlock on every route that reads limiter status in-request. Two new binary E2E tests cover every non-LLM route and the full diff preview lifecycle (clean tree → modified tree → fingerprint change → stale-fingerprint `409` → reject/restore). Divergences (versions, `rate_limit` presence, UTC import stamps, key-id billing key, extra `usage`/`done` SSE frames, ...) are recorded in `PARITY.md`'s route parity table.
- **Gateway** — `gateway.rs` ports `apex/gateway/*`: the OpenRouter model proxy with the `free` / `pro` / `unlimited` tiers (identical limits and model lists, unknown names fall back to `free`), `apex_` + 48-hex keys with 16-hex ids stored in `~/.apex/gateway.json` (Python uses SQLite `~/.apex/gateway.db`), re-read on every access so an admin or CLI revoke reaches a running server without a restart, and a sliding 60 s per-key rate limiter. All eight routes are wired — `POST /v1/chat/completions` (Bearer key → tier model gate → rate limit → daily request/token caps → upstream proxy with `usage.apex_gateway` injected on 200), `POST /v1/register` (413 above 4096 bytes, `Invalid tier: …`), `GET /v1/status`, `GET /v1/health`, `GET /v1/models` (sorted `free-`/`pro-` aliases with provider), and the `X-Admin-Key`-protected `/admin/keys`, `/admin/keys/generate`, `/admin/keys/revoke` — with Python's exact rejection strings. CLI: `apex-rs gateway {start,key,status}` mirrors `_cmd_gateway` including the env-only start gate (no `APEX_GATEWAY_KEY` / `OPENROUTER_API_KEY` → error + exit 1). `APEX_GATEWAY_UPSTREAM_BASE` overrides Python's hardcoded `https://openrouter.ai/api/v1` so the binary E2E (`gateway_proxy_lifecycle_is_hermetic`) runs hermetic against a local fake upstream. Divergences (JSON store, 400 `Invalid JSON` on a malformed chat body, tier *name* in `usage.apex_gateway`, re-revoking a known key returns 200) are recorded in `PARITY.md`.
- **Session metadata (usage)** — session saves now persist the real usage counters: `Agent::save_session` and `POST /session/save` write the live `{prompt_tokens, completion_tokens, total_tokens}` (Python's `SessionManager.save` writes `agent.usage`); the CLI `session save` has no agent state, so it persists the idle-agent zeros. `Agent::load_session` now restores model (default `claude-sonnet`) and cwd (default `.`) exactly like Python's `SessionManager.load`; usage is intentionally not restored (Python's counters start fresh on load). Rust-only extension: a fork carries the parent's `usage` over, falling back to the idle-agent zeros when the parent payload has no `usage` object (Python's fork path copies model/cwd/history only). Five new unit tests (usage roundtrip, fork usage carry-over, fork zero fallback, model/cwd/history restore with usage left fresh, Python defaults) plus the extended hermetic E2E session lifecycle (`session show` after a CLI save reports the three zero counters).
- **Python-written session fixtures** — `tests/fixtures/session/` contains sessions encrypted by Python's `cryptography.fernet` (the library `apex/session.py` uses), plus a deterministic `generate.py`. The Rust loader decrypts them through both key schemes: the native 44-byte Fernet key and the legacy raw 32-byte key (`sha256(raw + b":fernet")`). Unit tests cover the crypto boundary and the binary E2E loads the fixtures through `session show`/`list` with a temporary `HOME`.
- **Workspace awareness** — new `workspace.rs` ports `apex/workspace.py`: Git branch, 8-char commit, dirty flag, `origin` URL and GitHub `owner/repo`, ahead/behind counts, `GITHUB_HEAD_REF`/`GITHUB_PR_NUMBER`, first five tags (5-second timeout per git call), plus language, package-manager and test-framework detection in Python's marker order. The `[WORKSPACE CONTEXT]` block is now appended to both agent system prompts (analyzed once per user turn) and exposed by `apex-rs workspace [PATH] [--json]`. Python exports the class but never wires it. Divergences: no `git fetch --dry-run` network call, empty tags on tagless repos, no global singleton. Unit tests use real repositories (dirty state, ahead/behind against a bare remote, GitHub remote parsing, tag cap); the binary E2E checks the prompt block and JSON in a dirty repo.
- **Workspace rollback** — new `workspace_rollback.rs` ports `apex/workspace_rollback.py`: snapshots under `.apex/snapshots/` capture metadata, `git status --porcelain`, and byte copies of tracked modifications from `git diff --name-only` (untracked files stay in the status file only), with sorted listing, restore (parents recreated), delete, and clamped `rollback_turn`. `TurnTracker` persists `.apex/turns.json` and restores recorded turns. Wired as `apex-rs rollback {snapshot,list,restore,delete,turn,record,revert,history}` (Python only wires `/restore` and `/revert`). Divergences: UTC timestamps, bare-name validation for labels and snapshot names (Python's join allows `../` escapes), `turn 0` is an error instead of `IndexError`, and modification times are not preserved.
- **Tools** — read/write/edit/list, shell (`run_command` guarded, `run_test`, `install_package`), git (status/diff/log/undo + stage/unstage/commit/branches/pre-commit/PR), search, format, undo, LSP (diagnostics, definition, references, hover, completions, code_actions, workspace_symbol), code generation (refactor, DB model, Dockerfile/compose, OpenAPI client, docs, profiler, generate_tests, inline_edit, apply_code_action), skills & analysis (diff_files, list_skills, use_skill, replace_in_files, analyze_code, explain_code), repository context (get_repo_map, get_file_tree), web (web_search, fetch_url), task queue & plans (task, submit_task, get_task, list_tasks, plan_approve, plan_reject), **files (apply_edit, preview_edit, create_directory, delete_file, batch_read, batch_write, read_image, glob_search)**, **UX (ask_user, select_files, clipboard_read, clipboard_write, retry_last, retry_tool)**, **billing (billing_cost, billing_quota, billing_usage, billing_plan, billing_summary)**.
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
- **Tests** — 332 unit + 19 binary E2E passing (all on Windows), including an MCP roundtrip against a fake server, plugin execution, streamed usage, JSON-RPC framing (line + `Content-Length`), a fake GitHub API, codegen parity fixtures, repository-context commands, the workspace analyzer (marker order, dirty state, ahead/behind against a real bare remote, GitHub remote parsing, PR environment, tag cap, prompt caching) and its CLI prompt block/JSON in a dirty repository, the rollback snapshot/turn lifecycles (tracked-file backup, untracked-file exclusion, restore, delete, clamping, persistence, traversal rejection), the per-key rate-limit middleware (429 + `Retry-After`, independent key budgets), the HTTP-auth middleware (carrier precedence, empty-Bearer handling, revoked/expired keys, `/health` exemption, 404-before-auth) and the full binary auth flow (CLI-created key, exact 401 body, login/logout/status, out-of-band revoke, 429 with 401s not consuming budget), Python-written Fernet session fixtures under both key schemes (unit crypto tests and the binary `session show`/`list` flow), the PR 351 session-metadata roundtrip (CLI save persists the idle-agent zero counters, the agent save path persists live counters, a fork carries the parent usage with a zero fallback, and `apply_loaded_session` restores model/cwd/history with usage left fresh), the permission-gate refusal in the agent loop, the multi-file patch engine (both dialects, fuzz offset warnings, dry-run preview, write-failure rollback), the `get_repo_map` / `get_file_tree` tools (tree connectors, dotfile filter, `max_depth` cutoff, missing-path error), the web tools (urllib-style quoting, DuckDuckGo HTML parsing with snippet fallback and 5-result cap, Brave/Tavily/Exa JSON parsing with the 200-char Exa text cap, and `fetch_url` cleaning — script/style/tag strip, whitespace-before-entities order, 3000-char cap), the task/plan tools (submit → `completed` with `stdout or stderr`, spawn failure → `failed`, `No tasks` empty state, `Tasks:` header + insertion-order listing, `Task:`/`Status:`/`Result:`/`Error:` format, `ERROR: Task … not found`, `ERROR: Unknown agent: …`, and the always-`No pending plan` plan tools), the `github` CLI (install/run/usage parity, issue/PR/automate error paths against a dead local port, `No GitHub repository detected` for the write flows), and the hermetic `skill` lifecycle (add → fresh-process list → remove → `No skills found`, path-traversal name rejection, `ERROR: Skill not found` on double remove), and the gateway lifecycle against a local fake OpenRouter upstream (all eight routes, the tier model gate, usage counters, the admin trio, and an out-of-band revoke).

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
