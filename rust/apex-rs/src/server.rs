use crate::agent::Agent;
use crate::api_key::KeyManager;
use crate::config::Config;
use crate::rate_limiter::{MemoryStorage, RateLimitConfig, RateLimiter};
use crate::tools;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Path, Query, State};
use axum::http::{header, HeaderMap, HeaderName, StatusCode};
use axum::middleware::{self, Next};
use axum::response::sse::{Event, Sse};
use axum::response::{IntoResponse, Response};
use axum::{
    routing::{get, post},
    Json, Router,
};
use futures::stream::StreamExt;
use serde::Serialize;
use sha2::Digest;
use std::convert::Infallible;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::Mutex;

#[derive(Clone)]
struct AppState {
    agent: Arc<Mutex<Agent>>,
    config: Config,
    /// Broadcast bus for TUI events (`chat_complete`, …), parity with Python's `event_bus`.
    events: tokio::sync::broadcast::Sender<String>,
    /// Per-key request limiter shared by every route except `/health`.
    rate_limiter: Arc<Mutex<RateLimiter>>,
    /// API key store for `APEX_REQUIRE_AUTH`.
    key_manager: Arc<KeyManager>,
    /// Auth is opt-in: the Rust `serve` is the TUI backend and the TUI sends
    /// no key, so the default stays off (Python's `apex serve` defaults on;
    /// documented divergence).
    require_auth: bool,
}

/// Chat request. The TUI sends `message`, the CLI/API docs use `prompt`.
#[derive(serde::Deserialize)]
struct ChatReq {
    #[serde(default)]
    prompt: Option<String>,
    #[serde(default)]
    message: Option<String>,
    #[serde(default)]
    model: Option<String>,
    // Accepted for API compatibility but not forwarded to the agent yet.
    // TODO(v2.6): select the requested agent in `/api/v1/chat`.
    #[serde(default)]
    #[allow(dead_code)]
    agent: Option<String>,
}

impl ChatReq {
    fn text(&self) -> String {
        self.prompt
            .clone()
            .or_else(|| self.message.clone())
            .unwrap_or_default()
    }
}

#[derive(Serialize)]
struct ChatResp {
    response: String,
    usage: serde_json::Value,
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0)
}

fn event(name: &str, data: serde_json::Value) -> String {
    serde_json::json!({
        "event": name,
        "data": data,
        "timestamp": now_ms(),
    })
    .to_string()
}

/// Recursively list files under `root`, relative paths, skipping VCS/build dirs.
fn list_files(root: &std::path::Path, max: usize) -> Vec<String> {
    const SKIP: [&str; 6] = [".git", "node_modules", "target", ".venv", "dist", "build"];
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(rd) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in rd.flatten() {
            if out.len() >= max {
                return out;
            }
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with('.') && name != ".env" && name != ".gitignore" {
                continue;
            }
            if path.is_dir() {
                if !SKIP.contains(&name.as_str()) {
                    stack.push(path);
                }
            } else if let Ok(rel) = path.strip_prefix(root) {
                // The HTTP API exposes POSIX-style paths on every platform.
                out.push(rel.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    out.sort();
    out
}

/// Subsequence fuzzy match (port of Python's `fuzzy_match` in
/// `api_find_file`): every character of `q` must appear in `name` in order.
fn fuzzy_subsequence(name: &str, q: &str) -> bool {
    let q_chars: Vec<char> = q.chars().collect();
    let mut qi = 0usize;
    for ch in name.chars() {
        if qi < q_chars.len() && ch == q_chars[qi] {
            qi += 1;
        }
    }
    qi == q_chars.len()
}

/// File search for `GET /find/file` (port of Python's `api_find_file`
/// walk: same ignore set, dot-part pruning, trailing `/` on directories,
/// match on the relative path, capped at `limit`).
fn find_file_matches(
    cwd: &std::path::Path,
    query: &str,
    file_type: &str,
    limit: usize,
) -> Vec<String> {
    const IGNORE: [&str; 13] = [
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "target",
        ".tox",
        "coverage",
        ".apex",
        ".opencode",
    ];
    let mut results: Vec<String> = Vec::new();
    let mut stack = vec![cwd.to_path_buf()];
    'walk: while let Some(dir) = stack.pop() {
        let Ok(rd) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in rd.flatten() {
            let path = entry.path();
            let Ok(rel) = path.strip_prefix(cwd) else {
                continue;
            };
            let parts: Vec<String> = rel
                .components()
                .map(|c| c.as_os_str().to_string_lossy().to_string())
                .collect();
            if parts.iter().any(|p| IGNORE.contains(&p.as_str())) {
                continue;
            }
            // Dot-prefixed parents are pruned (the final component may be a
            // dotfile, like Python's `parts[:-1]` check).
            let parent_len = parts.len().saturating_sub(1);
            if parts.iter().take(parent_len).any(|p| p.starts_with('.')) {
                continue;
            }
            let is_dir = path.is_dir();
            if file_type == "file" && is_dir {
                continue;
            }
            if file_type == "directory" && !is_dir {
                continue;
            }
            let mut rel_str = rel.to_string_lossy().replace('\\', "/");
            if is_dir {
                rel_str.push('/');
            }
            if fuzzy_subsequence(&rel_str.to_lowercase(), query) {
                results.push(rel_str);
                if results.len() >= limit {
                    break 'walk;
                }
            }
            if is_dir {
                stack.push(path);
            }
        }
    }
    results
}

/// Run `git <args>` in `cwd` with the same 30-second timeout as Python's
/// `_collect_diff` / `_restore_diff_path`. Non-zero exits are returned as
/// output (Python ignores them in `_collect_diff`); errors are spawn
/// failures and timeouts only.
async fn git_run(cwd: &std::path::Path, args: &[&str]) -> Result<std::process::Output, String> {
    tokio::time::timeout(
        std::time::Duration::from_secs(30),
        tokio::process::Command::new("git")
            .args(args)
            .current_dir(cwd)
            .output(),
    )
    .await
    .map_err(|_| format!("git timed out after 30s: {}", args.join(" ")))?
    .map_err(|e| e.to_string())
}

/// Port of Python's `_collect_diff`: (stat, diff, changed paths,
/// sha256 fingerprint of the diff text).
async fn collect_diff(
    cwd: &std::path::Path,
) -> Result<(String, String, Vec<String>, String), String> {
    let stat = git_run(cwd, &["diff", "--stat"]).await?;
    let diff = git_run(cwd, &["diff"]).await?;
    let names = git_run(cwd, &["diff", "--name-only"]).await?;
    let diff_text = String::from_utf8_lossy(&diff.stdout).to_string();
    let paths: Vec<String> = String::from_utf8_lossy(&names.stdout)
        .lines()
        .map(|line| line.trim().to_string())
        .filter(|line| !line.is_empty())
        .collect();
    let mut hasher = sha2::Sha256::new();
    sha2::Digest::update(&mut hasher, diff_text.as_bytes());
    let fingerprint = format!("{:x}", sha2::Digest::finalize(hasher));
    let stat = String::from_utf8_lossy(&stat.stdout).trim().to_string();
    Ok((stat, diff_text, paths, fingerprint))
}

/// Port of Python's `_normalize_diff_path`: repo-relative, POSIX-style,
/// without `..` (None when the raw value is not a usable path).
fn normalize_diff_path(raw: &serde_json::Value) -> Option<String> {
    let candidate = raw.as_str()?.trim().replace('\\', "/");
    if candidate.is_empty() || candidate.contains('\0') {
        return None;
    }
    if candidate.starts_with('/') {
        return None;
    }
    // Reject Windows drive-qualified paths even on POSIX hosts.
    let bytes = candidate.as_bytes();
    if bytes.len() >= 2 && bytes[1] == b':' {
        return None;
    }
    if candidate.split('/').any(|part| part == "..") {
        return None;
    }
    Some(candidate)
}

/// Python-style `repr()` of a JSON value, for `invalid path: …` errors.
fn python_repr(v: &serde_json::Value) -> String {
    match v {
        serde_json::Value::String(s) => {
            format!("'{}'", s.replace('\\', "\\\\").replace('\'', "\\'"))
        }
        serde_json::Value::Null => "None".to_string(),
        serde_json::Value::Bool(true) => "True".to_string(),
        serde_json::Value::Bool(false) => "False".to_string(),
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::Array(items) => format!(
            "[{}]",
            items.iter().map(python_repr).collect::<Vec<_>>().join(", ")
        ),
        serde_json::Value::Object(map) => format!(
            " {{{}}}",
            map.iter()
                .map(|(k, val)| {
                    format!(
                        "{}: {}",
                        python_repr(&serde_json::Value::String(k.clone())),
                        python_repr(val)
                    )
                })
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

/// Port of Python's `_diff_path_within`: true when the (already
/// normalized) path resolves inside the repository root.
fn diff_path_within(_root: &std::path::Path, relative_path: &str) -> bool {
    // `normalize_diff_path` already rejects absolute paths, drive letters and
    // `..`, so re-normalizing is the containment check (Python's
    // `resolve().relative_to(root)`).
    normalize_diff_path(&serde_json::json!(relative_path)).is_some()
}

/// Port of Python's `_restore_diff_path`: `git restore --worktree -- <path>`,
/// falling back to `git checkout -- <path>`. `None` means success.
async fn restore_diff_path(root: &std::path::Path, relative_path: &str) -> Option<String> {
    let mut last_error = String::new();
    let attempts: Vec<Vec<&str>> = vec![
        vec!["restore", "--worktree", "--", relative_path],
        vec!["checkout", "--", relative_path],
    ];
    for args in attempts {
        match git_run(root, &args).await {
            Err(e) => {
                last_error = e;
            }
            Ok(o) => {
                if o.status.success() {
                    return None;
                }
                let stderr = String::from_utf8_lossy(&o.stderr).trim().to_string();
                let stdout = String::from_utf8_lossy(&o.stdout).trim().to_string();
                last_error = if !stderr.is_empty() {
                    stderr
                } else if !stdout.is_empty() {
                    stdout
                } else {
                    format!("git exited with {}", o.status.code().unwrap_or(-1))
                };
            }
        }
    }
    if last_error.is_empty() {
        Some(format!("could not restore {relative_path}"))
    } else {
        Some(last_error)
    }
}

/// Query parameters shared by the `/api/v1/context/*` routes.
#[derive(serde::Deserialize)]
struct ContextQuery {
    /// Target directory; relative paths resolve against the server cwd.
    path: Option<String>,
    /// Max depth for the file tree.
    depth: Option<usize>,
    /// Glob pattern for the glob route.
    pattern: Option<String>,
}

/// Resolve the `?path=` parameter of the context routes: empty means the
/// server's working directory, relative paths join to it, absolute paths are
/// used as-is (same trust model as `/api/v1/files/read`).
fn context_target(cwd: &std::path::Path, path: Option<&str>) -> std::path::PathBuf {
    match path.map(str::trim).filter(|p| !p.is_empty()) {
        Some(p) => {
            let pb = std::path::PathBuf::from(p);
            if pb.is_absolute() {
                pb
            } else {
                cwd.join(pb)
            }
        }
        None => cwd.to_path_buf(),
    }
}

fn run_shell_capture(command: &str, cwd: &std::path::Path) -> serde_json::Value {
    // `/api/v1/bash` must not be a way around the same safety policy that
    // guards the `run_command` tool.
    let analysis = crate::shell_security::SHELL_ANALYZER.analyze(command);
    if !analysis.safe {
        return serde_json::json!({
            "error": "blocked by safety policy",
            "warnings": analysis.warnings,
        });
    }
    match crate::tools::shell_command(command)
        .current_dir(cwd)
        .output()
    {
        Ok(o) => serde_json::json!({
            "stdout": String::from_utf8_lossy(&o.stdout),
            "stderr": String::from_utf8_lossy(&o.stderr),
            "exit_code": o.status.code().unwrap_or(-1),
        }),
        Err(e) => serde_json::json!({"error": e.to_string()}),
    }
}

/// Rate-limit bucket for a caller: the validated key id when auth is on
/// (Python's `key:{key_id}`), otherwise the raw carrier (or `anonymous`).
#[derive(Clone)]
struct AuthenticatedKey(String);

fn request_rate_limit_key(request: &axum::extract::Request) -> String {
    if let Some(key) = request.extensions().get::<AuthenticatedKey>() {
        return format!("key:{}", key.0);
    }
    extract_api_key(request.headers(), request.uri()).unwrap_or_else(|| "anonymous".to_string())
}

/// Same key as `request_rate_limit_key`, computed from request parts only.
/// Handlers that also parse a JSON body cannot take a `Request` extractor
/// (`Request` and `Json` both consume the body, so only one may be the
/// final extractor); they use `HeaderMap`/`Uri`/`Extensions` instead.
fn request_rate_limit_key_from_parts(
    headers: &HeaderMap,
    uri: &axum::http::Uri,
    extensions: &axum::http::Extensions,
) -> String {
    if let Some(key) = extensions.get::<AuthenticatedKey>() {
        return format!("key:{}", key.0);
    }
    extract_api_key(headers, uri).unwrap_or_else(|| "anonymous".to_string())
}

/// Rate-limit middleware shared by every route except `/health`.
///
/// The key is the validated key id when auth is on, else the `X-API-Key`
/// value / `Authorization: Bearer …` token / `?api_key=` value, or
/// `anonymous` when none is present — mirroring Python's per-key limiting
/// with the in-memory backend the Rust port supports.
async fn rate_limit(
    State(state): State<AppState>,
    request: axum::extract::Request,
    next: Next,
) -> Response {
    // `/health` must stay probeable without consuming key budget.
    if request.uri().path() == "/health" {
        return next.run(request).await;
    }
    let key = request_rate_limit_key(&request);
    // The check runs under the lock; the guard is dropped *before* the
    // handler runs, because several routes (e.g. `GET /api/v1/rate-limit`,
    // `POST /chat`, `GET /metrics`) read the limiter's status while serving
    // the request and the tokio mutex is not reentrant.
    let result = {
        let mut limiter = state.rate_limiter.lock().await;
        limiter.check_rate_limit(&key)
    };
    if !result.allowed {
        let retry_after = result.retry_after.unwrap_or(60);
        let mut response = (
            StatusCode::TOO_MANY_REQUESTS,
            Json(serde_json::json!({
                "error": "Rate limit exceeded",
                "code": "RATE_LIMITED",
                "retry_after": result.retry_after,
                "remaining": {
                    "minute": result.remaining_minute,
                    "hour": result.remaining_hour,
                    "day": result.remaining_day,
                },
            })),
        )
            .into_response();
        response.headers_mut().insert(
            header::RETRY_AFTER,
            retry_after
                .to_string()
                .parse()
                .expect("retry-after is numeric"),
        );
        return response;
    }
    next.run(request).await
}

// ────────────────────────────────────────────────────────────
// Authentication (port of Python's AuthMiddleware + auth routes)
// ────────────────────────────────────────────────────────────

/// `APEX_REQUIRE_AUTH` truthy values: `1`, `true`, `yes`, `on`
/// (case-insensitive). Unset or anything else keeps auth off.
fn auth_required_from_env() -> bool {
    match std::env::var("APEX_REQUIRE_AUTH") {
        Ok(value) => matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        ),
        Err(_) => false,
    }
}

/// Python's `AuthMiddleware.authenticate` precedence:
/// `Authorization: Bearer …`, then `?api_key=`, then `X-API-Key`.
///
/// A Bearer prefix with an empty value is a failure (Python does not fall
/// back in that case either).
fn extract_api_key(headers: &HeaderMap, uri: &axum::http::Uri) -> Option<String> {
    if let Some(value) = headers
        .get(header::AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
    {
        if let Some(key) = value.strip_prefix("Bearer ") {
            // Python reads the token verbatim (`auth_header[7:]`) and treats
            // an empty value as a hard failure — it never falls back.
            return if key.is_empty() {
                None
            } else {
                Some(key.to_string())
            };
        }
    }
    if let Some(query) = uri.query() {
        for pair in query.split('&') {
            if let Some(raw) = pair.strip_prefix("api_key=") {
                let key = percent_decode(raw);
                if !key.is_empty() {
                    return Some(key);
                }
            }
        }
    }
    headers
        .get(HeaderName::from_static("x-api-key"))
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

/// Minimal query-value decoding: `%XX` escapes only (API keys are urlsafe).
fn percent_decode(value: &str) -> String {
    let bytes = value.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' && index + 2 < bytes.len() {
            if let (Some(high), Some(low)) =
                (hex_digit(bytes[index + 1]), hex_digit(bytes[index + 2]))
            {
                out.push(high * 16 + low);
                index += 3;
                continue;
            }
        }
        out.push(bytes[index]);
        index += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn hex_digit(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn unauthorized() -> Response {
    (
        StatusCode::UNAUTHORIZED,
        Json(serde_json::json!({
            "error": "Authentication required",
            "code": "AUTH_REQUIRED",
        })),
    )
        .into_response()
}

/// Require a valid API key on every route when `APEX_REQUIRE_AUTH` is on.
///
/// Exempt routes are the ones Python never guards with `_check_auth`:
/// `/health` and the WebSocket event stream (`/ws`, `/ws/events`). Unmatched
/// paths fall through to the 404 handler, like aiohttp's router.
async fn require_auth(
    State(state): State<AppState>,
    mut request: axum::extract::Request,
    next: Next,
) -> Response {
    if !state.require_auth {
        return next.run(request).await;
    }
    match request.uri().path() {
        "/health" | "/ws" | "/ws/events" => return next.run(request).await,
        _ => {}
    }
    let candidate = extract_api_key(request.headers(), request.uri());
    match candidate {
        Some(key) => match state.key_manager.validate_key(&key) {
            Ok(info) => {
                request
                    .extensions_mut()
                    .insert(AuthenticatedKey(info.key_id));
                next.run(request).await
            }
            Err(_) => unauthorized(),
        },
        None => unauthorized(),
    }
}

/// `_VALID_PROVIDERS` from Python's HTTP API (login accepts these only).
const VALID_PROVIDERS: [&str; 22] = [
    "ANTHROPIC",
    "OPENAI",
    "GEMINI",
    "DEEPSEEK",
    "MISTRAL",
    "COHERE",
    "GROQ",
    "XAI",
    "TOGETHER",
    "FIREWORKS",
    "CEREBRAS",
    "PERPLEXITY",
    "HF",
    "GITHUB",
    "NVIDIA",
    "CLOUDFLARE",
    "DASHSCOPE",
    "LLAMA",
    "OPENROUTER",
    "HUGGINGFACE",
    "BEDROCK",
    "AZURE",
];

/// `_API_KEY_ENV_VARS` from Python's HTTP API (status + provider-less logout).
const API_KEY_ENV_VARS: [&str; 19] = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "DASHSCOPE_API_KEY",
    "LLAMA_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "FIREWORKS_API_KEY",
    "TOGETHER_API_KEY",
    "HF_TOKEN",
    "PERPLEXITY_API_KEY",
    "NVIDIA_API_KEY",
    "CLOUDFLARE_API_KEY",
    "COHERE_API_KEY",
    "GITHUB_TOKEN",
];

/// Python's login/logout mapping: `{PROVIDER}_API_KEY`, with HF/GITHUB
/// special-cased.
fn provider_env_var(provider: &str) -> String {
    match provider {
        "HF" => "HF_TOKEN".to_string(),
        "GITHUB" => "GITHUB_TOKEN".to_string(),
        other => format!("{other}_API_KEY"),
    }
}

/// Python's display name: strip `_API_KEY`/`_TOKEN`, title-case words.
fn provider_display_name(env_var: &str) -> String {
    env_var
        .replace("_API_KEY", "")
        .replace("_TOKEN", "")
        .split('_')
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                Some(first) => {
                    let mut name = first.to_uppercase().to_string();
                    name.push_str(&chars.as_str().to_ascii_lowercase());
                    name
                }
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn provider_configured(env_var: &str) -> bool {
    let upper = std::env::var(env_var)
        .map(|value| !value.is_empty())
        .unwrap_or(false);
    upper
        || std::env::var(env_var.to_ascii_lowercase())
            .map(|value| !value.is_empty())
            .unwrap_or(false)
}

/// `POST /api/v1/auth/login` — store a provider key in the server process.
async fn auth_login(Json(request): Json<serde_json::Value>) -> Response {
    let provider = request
        .get("provider")
        .and_then(|value| value.as_str())
        .unwrap_or("")
        .to_uppercase()
        .replace(' ', "_");
    let api_key = request
        .get("api_key")
        .and_then(|value| value.as_str())
        .unwrap_or("");
    if provider.is_empty() || api_key.is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "provider and api_key required"})),
        )
            .into_response();
    }
    if !VALID_PROVIDERS.contains(&provider.as_str()) {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": format!("Unknown provider: {provider}")})),
        )
            .into_response();
    }
    let env_var = provider_env_var(&provider);
    std::env::set_var(&env_var, api_key);
    Json(serde_json::json!({
        "configured": true,
        "provider": provider,
        "env_var": env_var,
    }))
    .into_response()
}

/// `POST /api/v1/auth/logout` — remove one provider key, or every known one
/// when the body carries no provider.
async fn auth_logout(body: axum::body::Bytes) -> Json<serde_json::Value> {
    let data: serde_json::Value = if body.is_empty() {
        serde_json::json!({})
    } else {
        serde_json::from_slice(&body).unwrap_or_else(|_| serde_json::json!({}))
    };
    let provider = data
        .get("provider")
        .and_then(|value| value.as_str())
        .unwrap_or("")
        .to_uppercase()
        .replace(' ', "_");
    if !provider.is_empty() {
        let env_var = provider_env_var(&provider);
        std::env::remove_var(&env_var);
        std::env::remove_var(env_var.to_ascii_lowercase());
        return Json(serde_json::json!({"removed": true, "env_var": env_var}));
    }
    let mut removed = Vec::new();
    for env_var in API_KEY_ENV_VARS {
        for name in [env_var.to_string(), env_var.to_ascii_lowercase()] {
            if let Ok(value) = std::env::var(&name) {
                std::env::remove_var(&name);
                if !value.is_empty() {
                    removed.push(name);
                }
            }
        }
    }
    Json(serde_json::json!({"removed": true, "env_vars": removed}))
}

/// `GET /api/v1/auth/status` — which provider keys are set in this process.
///
/// Python derives the list from its model registry; the Rust port reports the
/// `_API_KEY_ENV_VARS` table (no model registry), same shape otherwise.
async fn auth_status() -> Json<serde_json::Value> {
    let providers: Vec<serde_json::Value> = API_KEY_ENV_VARS
        .iter()
        .map(|env_var| {
            serde_json::json!({
                "name": provider_display_name(env_var),
                "env_var": env_var,
                "configured": provider_configured(env_var),
            })
        })
        .collect();
    let configured_count = providers
        .iter()
        .filter(|provider| provider["configured"] == true)
        .count();
    Json(serde_json::json!({
        "providers": providers,
        "configured_count": configured_count,
        "any_configured": configured_count > 0,
    }))
}

/// API index page served on `GET /` (Python's `index` handler).
const INDEX_HTML: &str = r#"
        <!DOCTYPE html>
        <html>
        <head><title>APEX API</title></head>
        <body>
        <h1>APEX Agent API</h1>
        <h2>Authentication</h2>
        <p>Use <code>Authorization: Bearer YOUR_API_KEY</code> header or <code>?api_key=YOUR_API_KEY</code> query parameter.</p>
        <h2>Endpoints</h2>
        <ul>
            <li>POST /chat - Send a chat message</li>
            <li>GET /stream - SSE stream endpoint</li>
            <li>POST /chat/stream - Chat with streaming</li>
            <li>GET /models - List available models</li>
            <li>POST /session/save - Save session</li>
            <li>POST /session/load - Load session</li>
            <li>GET /metrics - Get usage metrics</li>
            <li>GET /health - Health check</li>
            <li>GET /rate-limit/status - Rate limit status</li>
            <li>GET /api/v1/config - Get config</li>
            <li>POST /api/v1/config - Update config</li>
            <li>GET /api/v1/agents - List agents</li>
            <li>GET /api/v1/agents/{name} - Get agent</li>
            <li>GET /api/v1/sessions - List sessions</li>
            <li>DELETE /api/v1/sessions/{id} - Delete session</li>
            <li>POST /api/v1/share - Share session</li>
            <li>POST /api/v1/unshare/{share_id} - Unshare session</li>
            <li>GET /api/v1/shares - List shared sessions</li>
            <li>GET /api/v1/themes - List themes</li>
            <li>POST /api/v1/themes - Set theme</li>
            <li>GET /api/v1/stats - Usage statistics</li>
            <li>GET /api/v1/formatters - List formatters</li>
            <li>POST /api/v1/format - Format code</li>
            <li>POST /api/v1/compact - Compact context</li>
            <li>POST /api/v1/models/refresh - Refresh models</li>
            <li>GET /api/v1/providers - List providers</li>
            <li>POST /api/v1/auth/login - Add API key</li>
            <li>POST /api/v1/auth/logout - Remove API key</li>
            <li>GET /api/v1/auth/status - Auth status</li>
            <li>POST /api/v1/commands/execute - Execute command</li>
            <li>GET /api/v1/commands - List commands</li>
            <li>POST /api/v1/undo - Undo</li>
            <li>POST /api/v1/redo - Redo</li>
            <li>POST /api/v1/init - Initialize project</li>
            <li>GET /api/v1/export/{session_id} - Export session</li>
            <li>POST /api/v1/import - Import session</li>
        </ul>
        </body>
        </html>
        "#;

pub async fn serve(config: Config, port: u16) {
    // Telemetry: record session + agent start for this server process.
    {
        let mut tl = crate::telemetry::logger().lock().unwrap();
        tl.log_session_start(config.cwd.to_str().unwrap_or(""));
        tl.log_agent_start(&config.model, "build");
    }
    // File watcher: start the global watcher on the project directory. It
    // honours `watcher` config (enabled defaults to false, so this is a no-op
    // unless the operator enables it). The callback is intentionally empty: the
    // watcher's value here is registering ignore patterns and tracking mtimes;
    // consumers can replace it with a real handler.
    {
        let w = crate::watcher::watcher();
        let cwd = config.cwd.clone();
        w.set_poll_interval(1.0);
        w.start(cwd, |_path| {});
    }
    let (events, _) = tokio::sync::broadcast::channel::<String>(256);
    let state = AppState {
        agent: Arc::new(Mutex::new(Agent::new(config.clone()))),
        config,
        events,
        rate_limiter: Arc::new(Mutex::new(RateLimiter::new(
            RateLimitConfig::from_env(),
            Box::new(MemoryStorage::default()),
        ))),
        key_manager: Arc::new(KeyManager::default_store()),
        require_auth: auth_required_from_env(),
    };

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/api/v1/tools", get(|| async {
            Json(serde_json::to_value(tools::tool_schemas()).unwrap())
        }))
        .route("/api/v1/security/analyze", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let command = req.get("command").and_then(|v| v.as_str()).unwrap_or("");
                let analysis = crate::shell_security::SHELL_ANALYZER.analyze(command);
                let mut verdict = analysis.to_json();
                verdict["allowed"] =
                    serde_json::json!(crate::shell_security::SHELL_ANALYZER.is_safe(command));
                Json(verdict)
            }
        }))
        .route("/api/v1/models", get(|State(st): State<AppState>| async move {
            let mut models = vec![st.config.model.clone()];
            for m in ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5", "claude-opus-4-1"] {
                if !models.iter().any(|x| x == m) {
                    models.push(m.to_string());
                }
            }
            Json(serde_json::json!({"models": models}))
        }))
        .route("/api/v1/sessions", get(|_st: State<AppState>| async move {
            Json(serde_json::json!({"sessions": crate::share::list_sessions()}))
        }))
        .route("/api/v1/files/read", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let path = req.get("path").and_then(|v| v.as_str()).unwrap_or("");
                match std::fs::read_to_string(path) {
                    Ok(c) => Json(serde_json::json!({"content": c})),
                    Err(e) => Json(serde_json::json!({"error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/files/write", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let path = req.get("path").and_then(|v| v.as_str()).unwrap_or("");
                let content = req.get("content").and_then(|v| v.as_str()).unwrap_or("");
                match std::fs::write(path, content) {
                    Ok(_) => Json(serde_json::json!({"ok": true})),
                    Err(e) => Json(serde_json::json!({"error": e.to_string()})),
                }
            }
        }))
        .route(
            "/api/v1/agents/:id",
            get(|State(st): State<AppState>, Path(id): Path<String>| async move {
                let mut reg = crate::agents::AgentRegistry::new();
                reg.load_markdown_agents_from(&st.config.cwd);
                match reg.get(&id) {
                    Some(agent) => {
                        let permission: serde_json::Map<String, serde_json::Value> = agent
                            .permission
                            .iter()
                            .map(|(k, v)| (k.clone(), serde_json::json!(v.as_str())))
                            .collect();
                        // The Rust `Agent` carries no `system_prompt`/`top_p`
                        // (documented divergence).
                        Json(serde_json::json!({
                            "name": agent.name,
                            "description": agent.description,
                            "system_prompt": serde_json::Value::Null,
                            "mode": agent.mode.as_str(),
                            "model": agent.model,
                            "temperature": agent.temperature,
                            "top_p": serde_json::Value::Null,
                            "max_steps": agent.max_steps,
                            "hidden": agent.hidden,
                            "disabled": agent.disabled,
                            "color": agent.color,
                            "permission": permission,
                        }))
                        .into_response()
                    }
                    None => (
                        StatusCode::NOT_FOUND,
                        Json(serde_json::json!({"error": format!("Agent '{id}' not found")})),
                    )
                        .into_response(),
                }
            }),
        )
        .route("/api/v1/plugins", get(|| async {
            let ps = crate::plugins::discover_plugins();
            let list: Vec<serde_json::Value> = ps
                .iter()
                .map(|p| {
                    let tools: Vec<serde_json::Value> = p
                        .tools()
                        .iter()
                        .map(|t| {
                            serde_json::json!({
                                "name": t.name,
                                "full_name": crate::plugins::tool_full_name(&p.name, &t.name),
                                "description": t.description,
                            })
                        })
                        .collect();
                    serde_json::json!({
                        "name": p.name,
                        "version": p.version(),
                        "description": p.description(),
                        "enabled": p.enabled(),
                        "has_manifest": p.manifest.is_some(),
                        "tools": tools,
                    })
                })
                .collect();
            let names: Vec<String> = ps.into_iter().map(|p| p.name).collect();
            Json(serde_json::json!({"plugins": names, "details": list}))
        }))
        .route("/api/v1/agents", get(|State(st): State<AppState>| async move {
            let mut reg = crate::agents::AgentRegistry::new();
            reg.load_markdown_agents_from(&st.config.cwd);
            let agents: Vec<serde_json::Value> = reg
                .list()
                .iter()
                .map(|agent| {
                    let permission: serde_json::Map<String, serde_json::Value> = agent
                        .permission
                        .iter()
                        .map(|(k, v)| (k.clone(), serde_json::json!(v.as_str())))
                        .collect();
                    serde_json::json!({
                        "name": agent.name,
                        "description": agent.description,
                        "mode": agent.mode.as_str(),
                        "model": agent.model,
                        "hidden": agent.hidden,
                        "disabled": agent.disabled,
                        "color": agent.color,
                        "permission": permission,
                    })
                })
                .collect();
            Json(serde_json::json!({"agents": agents}))
        }))
        .route("/api/v1/themes", get(|State(st): State<AppState>| async move {
            let themes = [
                ("default", "Default"),
                ("light", "Light"),
                ("dark", "Dark"),
                ("forest", "Forest"),
                ("sunset", "Sunset"),
            ];
            let list: Vec<serde_json::Value> = themes
                .iter()
                .map(|(id, name)| serde_json::json!({"id": id, "name": name}))
                .collect();
            Json(serde_json::json!({"themes": list, "current": st.config.theme}))
        }))
        .route("/api/v1/themes", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let name = req.get("theme").and_then(|v| v.as_str()).unwrap_or("");
                if name.is_empty() {
                    return (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "theme name required"})),
                    )
                        .into_response();
                }
                let mut a = state.agent.lock().await;
                a.config.theme = name.to_string();
                // Parity with Python's `event_bus.publish("theme_changed", …)`.
                let _ = state.events.send(event(
                    "theme_changed",
                    serde_json::json!({"theme": a.config.theme}),
                ));
                // Python returns the resolved theme object; the Rust port has
                // no theme resolver, so `resolved` is null (divergence).
                Json(serde_json::json!({
                    "theme": a.config.theme,
                    "resolved": serde_json::Value::Null,
                }))
                .into_response()
            }
        }))
        .route(
            "/api/v1/stats",
            get(|State(st): State<AppState>, request: axum::extract::Request| async move {
                let a = st.agent.lock().await;
                let usage = a.usage_json();
                let mut stats = serde_json::json!({
                    "sessions_count": crate::share::list_sessions().len(),
                    "current_model": a.config.model,
                    // The Rust Agent has no `current_agent` field.
                    "current_agent": "build",
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens").cloned().unwrap_or(serde_json::json!(0)),
                        "completion_tokens": usage.get("completion_tokens").cloned().unwrap_or(serde_json::json!(0)),
                        "total_tokens": usage.get("total_tokens").cloned().unwrap_or(serde_json::json!(0)),
                    },
                    "undo_available": crate::tools::can_undo(),
                    "redo_available": crate::tools::can_redo(),
                    "shares_count": crate::share::list_shares().len(),
                });
                drop(a);
                // Python adds `rate_limit` only for authenticated keys.
                if let Some(key) = request.extensions().get::<AuthenticatedKey>() {
                    let limiter = st.rate_limiter.lock().await;
                    stats["rate_limit"] = limiter.get_status(&format!("key:{}", key.0));
                }
                Json(stats)
            }),
        )
        .route("/api/v1/files", get(|State(st): State<AppState>| async move {
            let files = list_files(&st.config.cwd, 500);
            Json(serde_json::json!({"files": files}))
        }))
        .route("/api/v1/tui-config", get(|State(st): State<AppState>| async move {
            Json(serde_json::json!({
                "leader_timeout": 2000,
                "keybinds": st.config.keybinds,
                "theme": st.config.theme,
                "model": st.config.model,
            }))
        }))
        .route("/api/v1/config", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            Json(serde_json::json!({
                "model": a.config.model,
                "base_url": a.config.base_url,
                "theme": a.config.theme,
                "cwd": a.config.cwd.to_string_lossy(),
                "auto_compact": a.config.auto_compact,
                "compact_threshold": a.config.compact_threshold,
                "denied_tools": a.config.denied_tools,
            }))
        }))
        .route("/api/v1/config", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let mut a = state.agent.lock().await;
                if let Some(v) = req.get("model").and_then(|v| v.as_str()) {
                    a.config.model = v.to_string();
                }
                if let Some(v) = req.get("theme").and_then(|v| v.as_str()) {
                    a.config.theme = v.to_string();
                }
                if let Some(v) = req.get("auto_compact").and_then(|v| v.as_bool()) {
                    a.config.auto_compact = v;
                }
                if let Some(v) = req.get("compact_threshold").and_then(|v| v.as_u64()) {
                    a.config.compact_threshold = v as usize;
                }
                if let Some(arr) = req.get("denied_tools").and_then(|v| v.as_array()) {
                    a.config.denied_tools = arr
                        .iter()
                        .filter_map(|v| v.as_str().map(str::to_string))
                        .collect();
                }
                // Same shape as GET /api/v1/config (Python re-serves the full
                // sanitized apex config; the Rust Config has no other keys).
                Json(serde_json::json!({
                    "model": a.config.model,
                    "base_url": a.config.base_url,
                    "theme": a.config.theme,
                    "cwd": a.config.cwd.to_string_lossy(),
                    "auto_compact": a.config.auto_compact,
                    "compact_threshold": a.config.compact_threshold,
                    "denied_tools": a.config.denied_tools,
                }))
            }
        }))
        .route("/api/v1/undo", post(|| async {
            let msg = tools::undo_last_edit();
            let ok = !msg.starts_with("ERROR") && !msg.starts_with("Nothing");
            Json(serde_json::json!({"ok": ok, "detail": msg, "error": if ok { serde_json::Value::Null } else { serde_json::Value::String(msg.clone()) }}))
        }))
        .route("/api/v1/redo", post(|| async {
            let msg = tools::redo_last_edit();
            let ok = !msg.starts_with("ERROR") && !msg.starts_with("Nothing");
            Json(serde_json::json!({"ok": ok, "detail": msg, "error": if ok { serde_json::Value::Null } else { serde_json::Value::String(msg.clone()) }}))
        }))
        .route("/api/v1/compact", post({
            let state = state.clone();
            move || async move {
                let mut a = state.agent.lock().await;
                let removed = a.compact_context("summarize");
                Json(serde_json::json!({"ok": true, "removed": removed}))
            }
        }))
        .route("/api/v1/bash", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let command = req.get("command").and_then(|v| v.as_str()).unwrap_or("");
                Json(run_shell_capture(command, &state.config.cwd))
            }
        }))
        .route("/api/v1/sessions/:id", get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            match crate::share::load_session(&id) {
                Some(history) => Json(serde_json::json!({"id": id, "history": history})),
                None => Json(serde_json::json!({"id": id, "error": "session not found"})),
            }
        }))
        .route("/api/v1/sessions/:id/load", post({
            let state = state.clone();
            move |axum::extract::Path(id): axum::extract::Path<String>| async move {
                let mut a = state.agent.lock().await;
                match a.load_session(&id) {
                    Ok(_) => Json(serde_json::json!({"ok": true, "id": id, "messages": a.history.len()})),
                    Err(e) => Json(serde_json::json!({"ok": false, "error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/sessions/:id/save", post({
            let state = state.clone();
            move |axum::extract::Path(id): axum::extract::Path<String>| async move {
                let a = state.agent.lock().await;
                match a.save_session(&id) {
                    Ok(_) => Json(serde_json::json!({"ok": true, "id": id})),
                    Err(e) => Json(serde_json::json!({"ok": false, "error": e.to_string()})),
                }
            }
        }))
        .route("/api/v1/sessions/:id/history", get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            match crate::share::load_session(&id) {
                Some(data) => {
                    let history = crate::share::history_of(&data);
                    Json(serde_json::json!({
                        "id": id,
                        "model": data.get("model"),
                        "messages": history,
                    }))
                }
                None => Json(serde_json::json!({"id": id, "error": "session not found"})),
            }
        }))
        .route("/api/v1/sessions/:id/fork", post({
            move |Path(id): Path<String>, opt: Option<Json<serde_json::Value>>| async move {
                let req = opt.map(|j| j.0).unwrap_or_default();
                let branch_name = req
                    .get("branch_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                // Accept either `fork_point` or `from_turn` as the turn index.
                let fork_point = req
                    .get("fork_point")
                    .or_else(|| req.get("from_turn"))
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                // Child name follows the CLI convention: the branch name, or a
                // default derived from the parent id when none is given.
                let child_name = if branch_name.is_empty() {
                    let parent_safe = crate::share::safe_session_name(&id);
                    format!("{parent_safe}-fork")
                } else {
                    branch_name.clone()
                };
                match crate::share::fork_session(&id, &child_name, &branch_name, fork_point) {
                    Some((child_id, path)) => Json(serde_json::json!({
                        "ok": true,
                        "id": child_id,
                        "child_id": child_id,
                        "parent_id": id,
                        "branch_name": branch_name,
                        "fork_point": fork_point,
                        "path": path.to_string_lossy(),
                    })),
                    None => Json(serde_json::json!({
                        "ok": false,
                        "error": "session not found",
                        "parent_id": id,
                    })),
                }
            }
        }))
        .route("/api/v1/sessions/:id/branches", get({
            move |Path(id): Path<String>| async move {
                match crate::share::load_session(&id) {
                    Some(data) => Json(serde_json::json!({
                        "id": id,
                        "branches": crate::share::branch_history_json(&data),
                        "branch_history": crate::share::branch_history_json(&data),
                        "metadata": crate::share::metadata_json(&data),
                    })),
                    None => Json(serde_json::json!({
                        "id": id,
                        "error": "session not found",
                        "branches": [],
                        "branch_history": [],
                    })),
                }
            }
        }))
        .route("/api/v1/share", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let session_id = req.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let title = req.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let live = {
                    let a = state.agent.lock().await;
                    a.history.clone()
                };
                let (id, url) = crate::share::share_session(&session_id, &title, Some(live));
                Json(serde_json::json!({"ok": true, "id": id, "url": url}))
            }
        }))
        .route("/api/v1/share/:id", axum::routing::delete(|axum::extract::Path(id): axum::extract::Path<String>| async move {
            let ok = crate::share::unshare_session(&id);
            Json(serde_json::json!({"ok": ok, "id": id}))
        }))
        .route("/api/v1/shares", get(|| async {
            Json(serde_json::json!({"shares": crate::share::list_shares()}))
        }))
        .route("/api/v1/export", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let session_id = req.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let live = {
                    let a = state.agent.lock().await;
                    a.history.clone()
                };
                match crate::share::export_session(&session_id, &state.config.cwd, Some(live)) {
                    Some(path) => Json(serde_json::json!({"ok": true, "path": path.to_string_lossy()})),
                    None => Json(serde_json::json!({"ok": false, "error": "nothing to export"})),
                }
            }
        }))
        .route("/api/v1/chat", post({
            let state = state.clone();
            move |Json(req): Json<ChatReq>| async move {
                let mut a = state.agent.lock().await;
                if let Some(model) = req.model.clone().filter(|m| !m.is_empty()) {
                    a.config.model = model;
                }
                let resp = a
                    .chat(&req.text())
                    .await
                    .unwrap_or_else(|e| format!("ERROR: {e}"));
                let usage = a.usage_json();
                Json(ChatResp { response: resp, usage })
            }
        }))
        .route("/api/v1/cost", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            let mut cost = a.cost.get_session_cost();
            if let Some(obj) = cost.as_object_mut() {
                obj.insert("usage".to_string(), a.usage_json());
                obj.insert("model".to_string(), serde_json::json!(a.config.model));
            }
            Json(cost)
        }))
        .route("/api/v1/cost/history", get(|State(st): State<AppState>| async move {
            let a = st.agent.lock().await;
            Json(serde_json::json!({"history": a.cost.get_history()}))
        }))
        .route("/api/v1/cost/reset", post(|State(st): State<AppState>| async move {
            let mut a = st.agent.lock().await;
            a.cost.reset_session();
            Json(serde_json::json!({"ok": true}))
        }))
        .route("/api/v1/chat/stream", post(chat_stream_handler))
        .route("/chat/stream", post(chat_stream_handler))
        .route("/ws", get(ws_handler))
        .route("/ws/events", get(ws_handler))
        .route("/api/v1/context/repo-map", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                let map = crate::context::get_repo_map(&path);
                if map.starts_with("ERROR") {
                    Json(serde_json::json!({"error": map}))
                } else {
                    Json(serde_json::json!({"map": map}))
                }
            },
        ))
        .route("/api/v1/context/git", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                Json(serde_json::json!({"info": crate::context::get_git_info(&path)}))
            },
        ))
        .route("/api/v1/context/stats", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                Json(serde_json::json!({"stats": crate::context::get_language_stats(&path)}))
            },
        ))
        .route("/api/v1/context/ctags", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                let text = crate::context::generate_ctags(&path);
                if text.starts_with("ERROR") {
                    Json(serde_json::json!({"error": text}))
                } else {
                    let files: Vec<String> = text.lines().map(String::from).collect();
                    Json(serde_json::json!({"files": files}))
                }
            },
        ))
        .route("/api/v1/context/tree", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                let depth = q.depth.unwrap_or(3);
                match crate::context::file_tree(&path, depth) {
                    Ok(tree) => Json(serde_json::json!({"tree": tree})),
                    Err(e) => Json(serde_json::json!({"error": e})),
                }
            },
        ))
        .route("/api/v1/context/glob", get(
            |State(st): State<AppState>, Query(q): Query<ContextQuery>| async move {
                let path = context_target(&st.config.cwd, q.path.as_deref());
                let pattern = match q.pattern.as_deref() {
                    Some(p) if !p.trim().is_empty() => p.to_string(),
                    _ => return Json(serde_json::json!({"error": "pattern is required"})),
                };
                match crate::context::glob_search(&path, &pattern) {
                    Ok(matches) => Json(serde_json::json!({"matches": matches})),
                    Err(e) => Json(serde_json::json!({"error": e})),
                }
            },
        ))
        .route("/api/v1/auth/login", post(auth_login))
        .route("/api/v1/auth/logout", post(auth_logout))
        .route("/api/v1/auth/status", get(auth_status))
        .route(
            "/api/v1/rate-limit",
            get(|State(st): State<AppState>, request: axum::extract::Request| async move {
                let key = request_rate_limit_key(&request);
                let limiter = st.rate_limiter.lock().await;
                Json(limiter.get_status(&key))
            }),
        )
        // ── Python parity: index + OpenCode-compatible endpoints ──
        .route(
            "/",
            get(|| async {
                (
                    [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
                    INDEX_HTML,
                )
            }),
        )
        .route("/global/health", get(|| async {
            Json(serde_json::json!({
                "healthy": true,
                "version": env!("CARGO_PKG_VERSION"),
            }))
        }))
        .route("/api/v1/lsp", get(|| async { Json(serde_json::json!([])) }))
        .route("/api/v1/formatter", get(|| async {
            let available = crate::formatter::formatter_manager().list_available();
            let list: Vec<serde_json::Value> = available
                .iter()
                .map(|f| {
                    serde_json::json!({"name": f.name, "available": true, "extensions": f.extensions})
                })
                .collect();
            Json(serde_json::to_value(list).unwrap())
        }))
        .route("/api/v1/mcp", get(|| async {
            Json(crate::mcp_client::global_server_status())
        }))
        .route("/api/v1/formatters", get(|| async {
            let available = crate::formatter::formatter_manager().list_available();
            Json(serde_json::json!({
                "formatters": available.iter().map(|f| serde_json::json!({
                    "name": f.name,
                    "command": f.command,
                    "extensions": f.extensions,
                })).collect::<Vec<_>>()
            }))
        }))
        .route("/api/v1/format", post({
            move |Json(req): Json<serde_json::Value>| async move {
                let file_path = req
                    .get("file_path")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let code = req.get("code").and_then(|v| v.as_str()).unwrap_or("");
                let extension = req
                    .get("extension")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let manager = crate::formatter::formatter_manager();
                if !file_path.is_empty() {
                    if manager.format_file(file_path) {
                        Json(serde_json::json!({"formatted": true, "file": file_path}))
                            .into_response()
                    } else {
                        (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({
                                "error": "no formatter available for this file"
                            })),
                        )
                            .into_response()
                    }
                } else if !code.is_empty() {
                    let formatted = manager.format_code(code, extension);
                    Json(serde_json::json!({"formatted": true, "code": formatted})).into_response()
                } else {
                    (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "file_path or code required"})),
                    )
                        .into_response()
                }
            }
        }))
        .route(
            "/rate-limit/status",
            get(|State(st): State<AppState>, request: axum::extract::Request| async move {
                let key = request_rate_limit_key(&request);
                let limiter = st.rate_limiter.lock().await;
                Json(limiter.get_status(&key))
            }),
        )
        .route("/models", get(|| async {
            Json(serde_json::json!({"models": crate::models::models_list()}))
        }))
        .route("/api/v1/models/refresh", post(|| async {
            let models = crate::models::models_list();
            let count = models.len();
            Json(serde_json::json!({"models": models, "count": count}))
        }))
        .route("/api/v1/providers", get(|| async {
            Json(serde_json::json!({"providers": crate::models::configured_providers()}))
        }))
        .route(
            "/api/v1/session/:id/abort",
            post(|_id: axum::extract::Path<String>| async move {
                Json(serde_json::json!({"aborted": true}))
            }),
        )
        // ── Python parity: session lifecycle routes ──
        .route(
            "/api/v1/sessions/:id",
            axum::routing::delete(|Path(id): Path<String>| async move {
                // Python: sorted `*{id}*` filename match first, then a
                // `*.json` name/session_id scan. Both sorted, so the
                // deletion is deterministic across filesystems.
                let dir = crate::share::sessions_dir();
                let mut files: Vec<std::path::PathBuf> = match std::fs::read_dir(&dir) {
                    Ok(rd) => rd.flatten().map(|e| e.path()).collect(),
                    Err(_) => Vec::new(),
                };
                files.sort();
                let mut found = false;
                for p in &files {
                    let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    if name.contains(id.as_str()) && p.is_file() && !p.is_symlink() {
                        found = std::fs::remove_file(p).is_ok();
                        break;
                    }
                }
                if !found {
                    for p in &files {
                        if p.extension().and_then(|e| e.to_str()) != Some("json")
                            || p.is_symlink()
                        {
                            continue;
                        }
                        let data = match std::fs::read_to_string(p)
                            .ok()
                            .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
                        {
                            Some(d) => d,
                            None => continue,
                        };
                        let is_target = data
                            .get("name")
                            .or_else(|| data.get("session_id"))
                            .and_then(|v| v.as_str())
                            == Some(id.as_str());
                        if is_target {
                            found = std::fs::remove_file(p).is_ok();
                        }
                        break;
                    }
                }
                if found {
                    Json(serde_json::json!({"deleted": id})).into_response()
                } else {
                    (
                        StatusCode::NOT_FOUND,
                        Json(serde_json::json!({"error": "session not found"})),
                    )
                        .into_response()
                }
            }),
        )
        .route(
            "/session/save",
            post({
                let state = state.clone();
                move |Json(req): Json<serde_json::Value>| async move {
                    let name = req
                        .get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("http_session");
                    let live = {
                        let a = state.agent.lock().await;
                        (
                            a.config.model.clone(),
                            a.config.cwd.to_string_lossy().to_string(),
                            a.history.clone(),
                            a.usage_json(),
                        )
                    };
                    match crate::share::save_session(name, &live.0, &live.1, &live.2, &live.3) {
                        Some(path) => {
                            Json(serde_json::json!({"saved": path.to_string_lossy()})).into_response()
                        }
                        None => (
                            StatusCode::INTERNAL_SERVER_ERROR,
                            Json(serde_json::json!({"error": "failed to save session"})),
                        )
                            .into_response(),
                    }
                }
            }),
        )
        .route(
            "/session/load",
            post({
                let state = state.clone();
                move |Json(req): Json<serde_json::Value>| async move {
                    let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    if name.is_empty() {
                        return (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({"error": "name required"})),
                        )
                            .into_response();
                    }
                    if crate::share::load_session(name).is_none() {
                        return (
                            StatusCode::NOT_FOUND,
                            Json(serde_json::json!({"error": "session not found"})),
                        )
                            .into_response();
                    }
                    let mut a = state.agent.lock().await;
                    let _ = a.load_session(name);
                    Json(serde_json::json!({"loaded": name})).into_response()
                }
            }),
        )
        .route("/api/v1/export/:session_id", get(|Path(id): Path<String>| async move {
            match crate::share::export_session_data(&id) {
                Some(data) => Json(data).into_response(),
                None => (
                    StatusCode::NOT_FOUND,
                    Json(serde_json::json!({"error": "session not found"})),
                )
                    .into_response(),
            }
        }))
        .route("/api/v1/import", post(|Json(req): Json<serde_json::Value>| async move {
            let file_path = req.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
            if !file_path.is_empty() {
                return match crate::share::import_session(file_path) {
                    Some(id) => {
                        Json(serde_json::json!({"imported": true, "session_id": id})).into_response()
                    }
                    None => (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "import failed"})),
                    )
                        .into_response(),
                };
            }
            if let Some(session_data) = req.get("data").cloned().filter(|v| !v.is_null()) {
                let session_id = session_data
                    .get("session_id")
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty())
                    .map(str::to_string)
                    .unwrap_or_else(crate::share::random_hex12);
                let safe = crate::share::sanitize(&session_data);
                let dir = crate::share::sessions_dir();
                let (stamp, _) = crate::share::now_stamps();
                let path = dir.join(format!("{stamp}_imported_{session_id}.json"));
                return match std::fs::create_dir_all(&dir).and_then(|_| {
                    std::fs::write(&path, serde_json::to_string_pretty(&safe).unwrap_or_default())
                }) {
                    Ok(()) => {
                        Json(serde_json::json!({"imported": true, "session_id": session_id}))
                            .into_response()
                    }
                    Err(_) => (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(serde_json::json!({"error": "import failed"})),
                    )
                        .into_response(),
                };
            }
            (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"error": "file_path or data required"})),
            )
                .into_response()
        }))
        .route("/api/v1/unshare/:id", post(|Path(id): Path<String>| async move {
            if crate::share::unshare_session(&id) {
                Json(serde_json::json!({"unshared": id})).into_response()
            } else {
                (
                    StatusCode::NOT_FOUND,
                    Json(serde_json::json!({"error": "share not found"})),
                )
                    .into_response()
            }
        }))
        .route(
            "/api/v1/session/:id/fork",
            post({
                let state = state.clone();
                move |Path(id): Path<String>| async move {
                    let mut a = state.agent.lock().await;
                    a.history.clear();
                    Json(serde_json::json!({"forked": true, "session_id": id}))
                }
            }),
        )
        // ── Python parity: commands / init / slash / find ──
        .route("/api/v1/commands", get(|State(st): State<AppState>| async move {
            let mgr = crate::commands::command_manager(&st.config.cwd);
            let mut cmds = mgr.list();
            cmds.sort_by(|a, b| a.name.cmp(&b.name));
            let commands: Vec<serde_json::Value> = cmds
                .iter()
                .map(|c| {
                    serde_json::json!({
                        "name": c.name,
                        "description": c.description,
                        "agent": c.agent,
                        "model": c.model,
                        "subtask": c.subtask,
                    })
                })
                .collect();
            Json(serde_json::json!({"commands": commands}))
        }))
        .route("/api/v1/commands/execute", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
                if name.is_empty() {
                    return (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "command name required"})),
                    )
                        .into_response();
                }
                let name = name.to_string();
                let args: Vec<String> = req
                    .get("args")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(str::to_string))
                            .collect()
                    })
                    .unwrap_or_default();
                let cwd = state.config.cwd.clone();
                // Rendering can run inline shell (`!cmd`); keep it off the
                // async runtime like Python's synchronous `load_all` does.
                let rendered = tokio::task::spawn_blocking({
                    let name = name.clone();
                    move || {
                        let mgr = crate::commands::command_manager(&cwd);
                        mgr.get(&name)
                            .map(|cmd| (cmd.model.clone(), mgr.render(&name, &args, &cwd)))
                    }
                })
                .await
                .unwrap_or(None);
                let Some((model, prompt)) = rendered else {
                    return (
                        StatusCode::NOT_FOUND,
                        Json(serde_json::json!({"error": format!("Unknown command: {name}")})),
                    )
                        .into_response();
                };
                let prompt = prompt.unwrap_or_default();
                let mut a = state.agent.lock().await;
                // Python's `execute` switches the model when the command
                // defines one (agent switching has no Rust counterpart).
                if let Some(model) = model.filter(|m| !m.is_empty()) {
                    a.config.model = model;
                }
                let response = a
                    .chat(&prompt)
                    .await
                    .unwrap_or_else(|e| format!("ERROR: {e}"));
                Json(serde_json::json!({
                    "command": name,
                    "response": response,
                    "executed": true,
                }))
                .into_response()
            }
        }))
        .route("/api/v1/init", post({
            let state = state.clone();
            move |Json(req): Json<serde_json::Value>| async move {
                let cwd = req
                    .get("cwd")
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty())
                    .map(str::to_string)
                    .unwrap_or_else(|| state.config.cwd.to_string_lossy().to_string());
                // `analyze` + `create_context_file` both scan the tree
                // (Python does the same double analysis).
                let (path, analysis) =
                    match tokio::task::spawn_blocking(move || {
                        let initializer = crate::project::ProjectInitializer::new(&cwd);
                        let analysis = initializer.analyze();
                        let path = initializer.create_context_file();
                        (path, analysis)
                    })
                    .await
                {
                    Ok(v) => v,
                    Err(_) => {
                        return (
                            StatusCode::INTERNAL_SERVER_ERROR,
                            Json(serde_json::json!({"error": "initialization failed"})),
                        )
                            .into_response();
                    }
                };
                // Manual serialization: `ProjectAnalysis` has no Serialize
                // derive; the shape mirrors Python's `analyze()` dict.
                let analysis = serde_json::json!({
                    "language": analysis.language,
                    "package_manager": analysis.package_manager,
                    "test_framework": analysis.test_framework,
                    "lsp_server": analysis.lsp_server,
                    "formatters": analysis.formatters,
                    "build_system": analysis.build_system,
                    "structure": {
                        "src_dirs": analysis.structure.src_dirs,
                        "test_dirs": analysis.structure.test_dirs,
                        "config_files": analysis.structure.config_files,
                    },
                    "dependencies": analysis.dependencies,
                    "dev_dependencies": analysis.dev_dependencies,
                    "scripts": analysis.scripts,
                });
                Json(serde_json::json!({
                    "initialized": true,
                    "path": path,
                    "analysis": analysis,
                }))
                .into_response()
            }
        }))
        .route("/api/v1/command", post(|Json(req): Json<serde_json::Value>| async move {
            let command = req.get("command").and_then(|v| v.as_str()).unwrap_or("");
            if command.is_empty() {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(serde_json::json!({"error": "command required"})),
                )
                    .into_response();
            }
            let mgr = crate::slash::slash_command_manager();
            let handled = mgr.parse(command).is_some();
            let output = if handled { mgr.execute(command) } else { String::new() };
            Json(serde_json::json!({"handled": handled, "output": output})).into_response()
        }))
        .route(
            "/find/file",
            get(|State(st): State<AppState>, Query(q): Query<std::collections::HashMap<String, String>>| async move {
                let query = q.get("query").map(|s| s.as_str()).unwrap_or("");
                let file_type = q.get("type").cloned().unwrap_or_default();
                let limit: usize = q
                    .get("limit")
                    .and_then(|s| s.parse::<usize>().ok())
                    .map(|l| l.min(200))
                    .unwrap_or(50);
                if query.is_empty() {
                    return Json(serde_json::json!([])).into_response();
                }
                let query_lower = query.to_lowercase();
                let cwd = st.config.cwd.clone();
                let results = tokio::task::spawn_blocking(move || {
                    find_file_matches(&cwd, &query_lower, &file_type, limit)
                })
                .await
                .unwrap_or_default();
                Json(serde_json::to_value(&results).unwrap_or(serde_json::json!([]))).into_response()
            }),
        )
        // ── Python parity: diff / chat / stream / SSE / metrics ──
        .route(
            "/api/v1/session/:id/diff",
            get(|State(st): State<AppState>, Path(id): Path<String>| async move {
                let cwd = st.config.cwd.clone();
                match collect_diff(&cwd).await {
                    Ok((stat, diff_text, paths, fingerprint)) => Json(serde_json::json!({
                        "files": if stat.is_empty() { "(clean)" } else { stat.as_str() },
                        "diff": diff_text,
                        "session_id": id,
                        "fingerprint": fingerprint,
                        "paths": paths,
                    }))
                    .into_response(),
                    Err(e) => (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(serde_json::json!({"error": e})),
                    )
                        .into_response(),
                }
            }),
        )
        .route("/api/v1/session/:id/diff/decision", post({
            let state = state.clone();
            move |_id: Path<String>, body: axum::body::Bytes| async move {
                let data: serde_json::Value = match serde_json::from_slice(&body) {
                    Ok(v) => v,
                    Err(_) => {
                        return (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({"error": "invalid JSON body"})),
                        )
                            .into_response();
                    }
                };
                if !data.is_object() {
                    return (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "invalid JSON body"})),
                    )
                        .into_response();
                }
                let decision = data.get("decision").and_then(|v| v.as_str()).unwrap_or("");
                if decision != "accept" && decision != "reject" {
                    return (
                        StatusCode::BAD_REQUEST,
                        Json(serde_json::json!({"error": "decision must be 'accept' or 'reject'"})),
                    )
                        .into_response();
                }
                let requested: Option<Vec<String>> = match data.get("files") {
                    None => None,
                    Some(serde_json::Value::Array(items)) => {
                        let mut normalized: Vec<String> = Vec::new();
                        for raw in items {
                            match normalize_diff_path(raw) {
                                Some(p) => normalized.push(p),
                                None => {
                                    return (
                                        StatusCode::BAD_REQUEST,
                                        Json(serde_json::json!({
                                            "error": format!("invalid path: {}", python_repr(raw)),
                                        })),
                                    )
                                        .into_response();
                                }
                            }
                        }
                        // Preserve preview order, restore each path at most once.
                        let mut seen = std::collections::HashSet::new();
                        Some(
                            normalized
                                .into_iter()
                                .filter(|p| seen.insert(p.clone()))
                                .collect(),
                        )
                    }
                    Some(_) => {
                        return (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({"error": "files must be a list"})),
                        )
                            .into_response();
                    }
                };
                let cwd = state.config.cwd.clone();
                let (_stat, _diff_text, current_paths, fingerprint) = match collect_diff(&cwd).await
                {
                    Ok(v) => v,
                    Err(e) => {
                        return (
                            StatusCode::INTERNAL_SERVER_ERROR,
                            Json(serde_json::json!({"error": e})),
                        )
                            .into_response();
                    }
                };
                let selected: Vec<String> = match &requested {
                    None => current_paths.clone(),
                    Some(list) => list.clone(),
                };
                if decision == "reject" {
                    match data
                        .get("fingerprint")
                        .and_then(|v| v.as_str())
                        .filter(|s| !s.is_empty())
                    {
                        None => {
                            return (
                                StatusCode::BAD_REQUEST,
                                Json(serde_json::json!({"error": "fingerprint required"})),
                            )
                                .into_response();
                        }
                        Some(supplied) if supplied != fingerprint => {
                            return (
                                StatusCode::CONFLICT,
                                Json(serde_json::json!({
                                    "error": "diff_changed",
                                    "fingerprint": fingerprint,
                                })),
                            )
                                .into_response();
                        }
                        Some(_) => {}
                    }
                }
                let cwd_resolved = cwd.canonicalize().unwrap_or_else(|_| cwd.clone());
                let current_set: std::collections::HashSet<&str> =
                    current_paths.iter().map(String::as_str).collect();
                for path in &selected {
                    if !current_set.contains(path.as_str()) {
                        return (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({
                                "error": format!("path not in current diff: {path}"),
                            })),
                        )
                            .into_response();
                    }
                    if !diff_path_within(&cwd_resolved, path) {
                        return (
                            StatusCode::BAD_REQUEST,
                            Json(serde_json::json!({
                                "error": format!("path escapes working directory: {path}"),
                            })),
                        )
                            .into_response();
                    }
                }
                if decision == "accept" {
                    return Json(serde_json::json!({
                        "status": "accepted",
                        "files": selected,
                        "fingerprint": fingerprint,
                    }))
                    .into_response();
                }
                let mut reverted: Vec<String> = Vec::new();
                let mut failed: Vec<String> = Vec::new();
                for path in &selected {
                    if restore_diff_path(&cwd_resolved, path).await.is_none() {
                        reverted.push(path.clone());
                    } else {
                        failed.push(path.clone());
                    }
                }
                Json(serde_json::json!({
                    "status": "rejected",
                    "files": selected,
                    "reverted": reverted,
                    "failed": failed,
                    "fingerprint": fingerprint,
                }))
                .into_response()
            }
        }))
        .route("/chat", post({
            let state = state.clone();
            move |
                headers: HeaderMap,
                uri: axum::http::Uri,
                extensions: axum::http::Extensions,
                Json(req): Json<ChatReq>,
            | async move {
                let message = req.text();
                let (result, model, usage) = {
                    let mut a = state.agent.lock().await;
                    if let Some(model) = req.model.clone().filter(|m| !m.is_empty()) {
                        a.config.model = model;
                    }
                    let outcome = a
                        .chat(&message)
                        .await
                        .map_err(|e| e.to_string());
                    (outcome, a.config.model.clone(), a.usage_json())
                };
                let response = match result {
                    Ok(r) => r,
                    Err(e) => {
                        return (
                            StatusCode::INTERNAL_SERVER_ERROR,
                            Json(serde_json::json!({"error": e})),
                        )
                            .into_response();
                    }
                };
                // Read-only: the limiter middleware already counted this
                // request, so `get_status` mirrors Python's
                // `result.remaining_*` after the counting call.
                let status = {
                    let limiter = state.rate_limiter.lock().await;
                    limiter.get_status(&request_rate_limit_key_from_parts(
                        &headers, &uri, &extensions,
                    ))
                };
                let remaining = |window: &str| -> u64 {
                    let used = status
                        .get(window)
                        .and_then(|w| w.get("used"))
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    let limit = status
                        .get(window)
                        .and_then(|w| w.get("limit"))
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    limit.saturating_sub(used)
                };
                Json(serde_json::json!({
                    "response": response,
                    "model": model,
                    "usage": usage,
                    "rate_limit": {
                        "remaining_minute": remaining("minute"),
                        "remaining_hour": remaining("hour"),
                        "remaining_day": remaining("day"),
                    },
                }))
                .into_response()
            }
        }))
        .route("/stream", get(|State(state): State<AppState>| async move {
            // Python streams `chat_streaming("ping")` chunks. The Rust port
            // reuses the `/chat/stream` frame mapping, so `usage`/`done`
            // frames are emitted as well (documented divergence).
            let (tx, rx) = tokio::sync::mpsc::channel::<crate::agent::StreamEvent>(64);
            let agent = state.agent.clone();
            let events = state.events.clone();
            tokio::spawn(async move {
                let mut a = agent.lock().await;
                if let Err(e) = a.chat_stream("ping", tx.clone()).await {
                    let _ = tx
                        .send(crate::agent::StreamEvent::Error(e.to_string()))
                        .await;
                }
                let payload = event(
                    "chat_complete",
                    serde_json::json!({
                        "model": a.config.model,
                        "usage": a.last_usage_json(),
                    }),
                );
                let _ = events.send(payload);
            });
            let stream = tokio_stream::wrappers::ReceiverStream::new(rx).map(|ev| {
                let payload = match ev {
                    crate::agent::StreamEvent::Chunk(text) => serde_json::json!({"chunk": text}),
                    crate::agent::StreamEvent::Usage(usage) => serde_json::json!({"usage": usage}),
                    crate::agent::StreamEvent::Done => serde_json::json!({"done": true}),
                    crate::agent::StreamEvent::Error(message) => serde_json::json!({"error": message}),
                }
                .to_string();
                Ok::<_, Infallible>(Event::default().data(payload))
            });
            Sse::new(stream)
        }))
        .route("/global/event", get(|| async {
            let (tx, rx) = tokio::sync::mpsc::channel::<Result<Event, Infallible>>(8);
            tokio::spawn(async move {
                // Python: `data: {"event": "connected", "version": "__version__"}`.
                let connected = format!(
                    "{{\"event\": \"connected\", \"version\": \"{}\"}}",
                    env!("CARGO_PKG_VERSION")
                );
                if tx.send(Ok(Event::default().data(connected))).await.is_err() {
                    return;
                }
                loop {
                    // Python: a `: keepalive` comment every 30 seconds.
                    if tx
                        .send(Ok(Event::default().comment("keepalive")))
                        .await
                        .is_err()
                    {
                        return;
                    }
                    tokio::time::sleep(std::time::Duration::from_secs(30)).await;
                }
            });
            let stream = tokio_stream::wrappers::ReceiverStream::new(rx);
            Sse::new(stream)
        }))
        .route("/metrics", get(|State(st): State<AppState>, request: axum::extract::Request| async move {
            let (usage, model) = {
                let a = st.agent.lock().await;
                (a.usage_json(), a.config.model.clone())
            };
            let mut metrics = serde_json::json!({
                "prompt_tokens": usage.get("prompt_tokens").cloned().unwrap_or(serde_json::json!(0)),
                "completion_tokens": usage.get("completion_tokens").cloned().unwrap_or(serde_json::json!(0)),
                "total_tokens": usage.get("total_tokens").cloned().unwrap_or(serde_json::json!(0)),
                "model": model,
            });
            // Python adds rate limit + usage summary for authenticated keys.
            if let Some(key) = request.extensions().get::<AuthenticatedKey>() {
                let key_id = key.0.clone();
                metrics["rate_limit"] = {
                    let limiter = st.rate_limiter.lock().await;
                    limiter.get_status(&format!("key:{key_id}"))
                };
                // Divergence: Python keys billing by `workspace_id`; the Rust
                // billing manager has no workspaces, so it keys by key id.
                metrics["usage_summary"] =
                    crate::billing::billing_manager().lock().unwrap().get_usage_summary(&key_id);
            }
            Json(metrics)
        }))
        .route_layer(middleware::from_fn_with_state(state.clone(), rate_limit))
        // Auth wraps the limiter: Python's `_check_auth` runs before
        // `_check_rate_limit`, so rejected requests never consume budget.
        .route_layer(middleware::from_fn_with_state(state.clone(), require_auth))
        .route(
            "/api/v1/telemetry",
            get(|State(_st): State<AppState>| async move {
                let tl = crate::telemetry::logger().lock().unwrap().get_stats();
                let perf = crate::telemetry::perf_monitor()
                    .lock()
                    .unwrap()
                    .get_all_stats();
                Json(serde_json::json!({
                    "telemetry": tl,
                    "performance": serde_json::to_value(perf).unwrap_or(serde_json::json!({})),
                }))
            }),
        )
        .with_state(state);

    let addr = format!("127.0.0.1:{port}");
    println!("APEX (Rust) listening on {addr}");
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn chat_stream_handler(
    State(state): State<AppState>,
    Json(req): Json<ChatReq>,
) -> Sse<impl futures::Stream<Item = Result<Event, Infallible>>> {
    let (tx, rx) = tokio::sync::mpsc::channel::<crate::agent::StreamEvent>(64);
    let agent = state.agent.clone();
    let events = state.events.clone();
    let prompt = req.text();
    let model_override = req.model.clone().filter(|m| !m.is_empty());
    tokio::spawn(async move {
        let mut a = agent.lock().await;
        if let Some(model) = model_override {
            a.config.model = model;
        }
        if let Err(e) = a.chat_stream(&prompt, tx.clone()).await {
            let _ = tx
                .send(crate::agent::StreamEvent::Error(e.to_string()))
                .await;
        }
        // Parity with Python's event_bus.publish("chat_complete", {...}).
        // Usage is per request here (the TUI accumulates its own session totals).
        let payload = event(
            "chat_complete",
            serde_json::json!({
                "model": a.config.model,
                "usage": a.last_usage_json(),
            }),
        );
        let _ = events.send(payload);
    });
    let stream = tokio_stream::wrappers::ReceiverStream::new(rx).map(|ev| {
        // The TUI parses each SSE data line as JSON: `chunk` for text,
        // `usage` before completion, `done` when finished, `error` on failure.
        let payload = match ev {
            crate::agent::StreamEvent::Chunk(text) => serde_json::json!({"chunk": text}),
            crate::agent::StreamEvent::Usage(usage) => serde_json::json!({"usage": usage}),
            crate::agent::StreamEvent::Done => serde_json::json!({"done": true}),
            crate::agent::StreamEvent::Error(message) => serde_json::json!({"error": message}),
        }
        .to_string();
        Ok::<_, Infallible>(Event::default().data(payload))
    });
    Sse::new(stream)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl axum::response::IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    use futures::{SinkExt, StreamExt};
    let (mut sender, mut receiver) = socket.split();
    let (out_tx, out_rx) = tokio::sync::mpsc::unbounded_channel::<String>();

    // Outbound traffic = broadcast bus (chat_complete, …) + direct replies to
    // this client's messages, merged into a single sink task.
    let bcast_rx = state.events.subscribe();
    let send_task = tokio::spawn(async move {
        let bcast = futures::stream::unfold(bcast_rx, |mut rx| async move {
            loop {
                match rx.recv().await {
                    Ok(payload) => return Some((payload, rx)),
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => continue,
                    Err(_) => return None,
                }
            }
        });
        let outbound = tokio_stream::wrappers::UnboundedReceiverStream::new(out_rx);
        let merged = futures::stream::select(bcast, outbound);
        futures::pin_mut!(merged);
        while let Some(payload) = merged.next().await {
            if sender.send(Message::Text(payload)).await.is_err() {
                break;
            }
        }
    });

    let connected = event(
        "connected",
        serde_json::json!({
            "model": state.agent.lock().await.config.model,
            "agent": "build",
            "cwd": state.config.cwd.to_string_lossy(),
            "version": env!("CARGO_PKG_VERSION"),
        }),
    );
    if out_tx.send(connected).is_err() {
        send_task.abort();
        return;
    }

    while let Some(Ok(msg)) = receiver.next().await {
        let Message::Text(text) = msg else {
            if matches!(msg, Message::Close(_)) {
                break;
            }
            continue;
        };
        let v: serde_json::Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(_) => {
                let _ = out_tx.send(event(
                    "error",
                    serde_json::json!({"message": "invalid JSON"}),
                ));
                continue;
            }
        };
        let method = v.get("method").and_then(|m| m.as_str()).unwrap_or("");
        let out = match method {
            "ping" => Some(event("pong", serde_json::json!({}))),
            "state" => {
                let a = state.agent.lock().await;
                Some(event(
                    "state",
                    serde_json::json!({
                        "model": a.config.model,
                        "agent": "build",
                        "cwd": a.config.cwd.to_string_lossy(),
                        "historyLength": a.history.len(),
                        "usage": a.usage_json(),
                    }),
                ))
            }
            "cost" => {
                let a = state.agent.lock().await;
                Some(event(
                    "cost",
                    serde_json::json!({
                        "cost": a.cost.get_session_cost(),
                        "usage": a.usage_json(),
                    }),
                ))
            }
            "undo" => {
                let detail = tools::undo_last_edit();
                Some(event("undo", serde_json::json!({"detail": detail})))
            }
            "redo" => {
                let detail = tools::redo_last_edit();
                Some(event("redo", serde_json::json!({"detail": detail})))
            }
            "compact" => {
                let removed = state.agent.lock().await.compact_context("summarize");
                Some(event("compact", serde_json::json!({"removed": removed})))
            }
            "theme_changed" => {
                let theme = v
                    .get("params")
                    .and_then(|p| p.get("theme"))
                    .and_then(|t| t.as_str())
                    .unwrap_or("default");
                Some(event("theme_changed", serde_json::json!({"theme": theme})))
            }
            "" => None,
            other => Some(event(
                "error",
                serde_json::json!({"message": format!("unknown method: {other}")}),
            )),
        };
        if let Some(payload) = out {
            if out_tx.send(payload).is_err() {
                break;
            }
        }
    }
    drop(out_tx);
    send_task.abort();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chat_req_accepts_message_and_prompt() {
        let a: ChatReq = serde_json::from_str(r#"{"message":"hi"}"#).unwrap();
        assert_eq!(a.text(), "hi");
        let b: ChatReq = serde_json::from_str(r#"{"prompt":"yo"}"#).unwrap();
        assert_eq!(b.text(), "yo");
        let c: ChatReq = serde_json::from_str(r#"{"prompt":"p","message":"m"}"#).unwrap();
        assert_eq!(c.text(), "p");
    }

    #[test]
    fn shell_capture_works() {
        let dir = tempfile::tempdir().unwrap();
        let v = run_shell_capture("echo hello", dir.path());
        assert_eq!(v["stdout"].as_str().unwrap().trim(), "hello");
        assert_eq!(v["exit_code"], 0);
    }

    #[test]
    fn shell_capture_blocks_dangerous_commands() {
        let dir = tempfile::tempdir().unwrap();
        let marker = dir.path().join("marker.txt");
        let command = format!("echo hi > {} && rm -rf /", marker.display());
        let v = run_shell_capture(&command, dir.path());
        assert_eq!(v["error"], "blocked by safety policy");
        assert!(!marker.exists(), "blocked command must not execute");
    }

    #[test]
    fn list_files_skips_vcs_and_hidden() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.txt"), "x").unwrap();
        std::fs::create_dir(dir.path().join(".git")).unwrap();
        std::fs::write(dir.path().join(".git").join("HEAD"), "x").unwrap();
        std::fs::create_dir(dir.path().join("src")).unwrap();
        std::fs::write(dir.path().join("src").join("main.rs"), "x").unwrap();
        let files = list_files(dir.path(), 100);
        assert!(files.contains(&"a.txt".to_string()));
        assert!(files.contains(&"src/main.rs".to_string()));
        assert!(!files.iter().any(|f| f.contains(".git")));
    }

    #[test]
    fn context_target_resolves_against_cwd() {
        let cwd = std::path::Path::new("/work");
        assert_eq!(context_target(cwd, None), std::path::PathBuf::from("/work"));
        assert_eq!(
            context_target(cwd, Some("  ")),
            std::path::PathBuf::from("/work")
        );
        assert_eq!(
            context_target(cwd, Some("sub")),
            std::path::PathBuf::from("/work/sub")
        );
        assert_eq!(
            context_target(cwd, Some("a/b")),
            std::path::PathBuf::from("/work/a/b")
        );
        // Absolute paths pass through unchanged.
        let abs = if cfg!(windows) { "C:\\abs" } else { "/abs" };
        assert_eq!(
            context_target(cwd, Some(abs)),
            std::path::PathBuf::from(abs)
        );
    }

    #[tokio::test]
    async fn rate_limit_middleware_blocks_per_key() {
        let (events, _) = tokio::sync::broadcast::channel::<String>(256);
        let config = Config::from_env();
        let dir = tempfile::tempdir().unwrap();
        let state = AppState {
            agent: Arc::new(Mutex::new(Agent::new(config.clone()))),
            config,
            events,
            rate_limiter: Arc::new(Mutex::new(RateLimiter::new(
                RateLimitConfig {
                    requests_per_minute: 2,
                    requests_per_hour: 100,
                    requests_per_day: 1000,
                    burst_size: 10,
                },
                Box::new(MemoryStorage::default()),
            ))),
            key_manager: Arc::new(KeyManager::new(dir.path().join("api_keys.json"))),
            require_auth: false,
        };
        let app = Router::new()
            .route("/api/v1/rate-limit", get(|| async { "status" }))
            .route_layer(middleware::from_fn_with_state(state.clone(), rate_limit))
            .with_state(state);
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let client = reqwest::Client::new();
        let url = format!("http://{addr}/api/v1/rate-limit");
        // No key: the `anonymous` bucket gets two requests per minute.
        assert_eq!(client.get(&url).send().await.unwrap().status(), 200);
        assert_eq!(client.get(&url).send().await.unwrap().status(), 200);
        let third = client.get(&url).send().await.unwrap();
        assert_eq!(third.status(), 429);
        assert!(third.headers().get("retry-after").is_some());
        let body: serde_json::Value = third.json().await.unwrap();
        assert_eq!(body["error"], "Rate limit exceeded");
        assert_eq!(body["code"], "RATE_LIMITED");
        assert!(body["retry_after"].is_number());
        assert!(body["remaining"]["minute"].is_number());
        assert!(body["remaining"]["hour"].is_number());
        assert!(body["remaining"]["day"].is_number());
        // A different key has its own budget.
        let other = client
            .get(&url)
            .header("X-API-Key", "key-a")
            .send()
            .await
            .unwrap();
        assert_eq!(other.status(), 200);
        let via_bearer = client
            .get(&url)
            .header("Authorization", "Bearer key-b")
            .send()
            .await
            .unwrap();
        assert_eq!(via_bearer.status(), 200);
    }

    #[test]
    fn percent_decode_handles_escapes() {
        assert_eq!(percent_decode("a%2Db%5Fc"), "a-b_c");
        assert_eq!(percent_decode("plain"), "plain");
        // Malformed escapes survive verbatim, like aiohttp's lenient parsing.
        assert_eq!(percent_decode("bad%zz"), "bad%zz");
        assert_eq!(percent_decode("trailing%"), "trailing%");
    }

    #[test]
    fn extract_api_key_matches_python_precedence() {
        let uri: axum::http::Uri = "/x?api_key=query-key".parse().unwrap();
        let mut headers = HeaderMap::new();
        // No Authorization header: the query parameter wins.
        assert_eq!(
            extract_api_key(&headers, &uri).as_deref(),
            Some("query-key")
        );

        // Bearer wins over the query parameter.
        headers.insert(header::AUTHORIZATION, "Bearer bearer-key".parse().unwrap());
        assert_eq!(
            extract_api_key(&headers, &uri).as_deref(),
            Some("bearer-key")
        );

        // An empty Bearer is a hard failure, never a fallback (Python parity);
        // a whitespace-only token is passed through verbatim and fails
        // validation, exactly like `auth_header[7:]` in Python.
        headers.insert(header::AUTHORIZATION, "Bearer ".parse().unwrap());
        assert_eq!(extract_api_key(&headers, &uri), None);
        headers.insert(header::AUTHORIZATION, "Bearer  ".parse().unwrap());
        assert_eq!(extract_api_key(&headers, &uri).as_deref(), Some(" "));

        // Without Authorization and without a query value, `X-API-Key` is the
        // last carrier (Python: `query.get("api_key") or X-API-Key`).
        headers.remove(header::AUTHORIZATION);
        headers.insert("x-api-key", "header-key".parse().unwrap());
        let no_query: axum::http::Uri = "/x".parse().unwrap();
        assert_eq!(
            extract_api_key(&headers, &no_query).as_deref(),
            Some("header-key")
        );
        // The query parameter wins over the header.
        assert_eq!(
            extract_api_key(&headers, &uri).as_deref(),
            Some("query-key")
        );

        // A non-Bearer Authorization header is ignored, not rejected.
        headers.insert(header::AUTHORIZATION, "Basic abc".parse().unwrap());
        assert_eq!(
            extract_api_key(&headers, &uri).as_deref(),
            Some("query-key")
        );

        // Query values are percent-decoded.
        let encoded: axum::http::Uri = "/x?api_key=apex_a%2Db".parse().unwrap();
        assert_eq!(
            extract_api_key(&HeaderMap::new(), &encoded).as_deref(),
            Some("apex_a-b")
        );
    }

    #[test]
    fn provider_env_mapping_matches_python() {
        assert_eq!(provider_env_var("HF"), "HF_TOKEN");
        assert_eq!(provider_env_var("GITHUB"), "GITHUB_TOKEN");
        assert_eq!(provider_env_var("ANTHROPIC"), "ANTHROPIC_API_KEY");
        assert_eq!(provider_display_name("ANTHROPIC_API_KEY"), "Anthropic");
        assert_eq!(provider_display_name("HF_TOKEN"), "Hf");
        assert_eq!(provider_display_name("XAI_API_KEY"), "Xai");
    }

    #[test]
    fn auth_required_from_env_accepts_truthy_values() {
        let previous = std::env::var_os("APEX_REQUIRE_AUTH");
        for value in ["1", "true", "TRUE", " yes ", "On"] {
            std::env::set_var("APEX_REQUIRE_AUTH", value);
            assert!(auth_required_from_env(), "{value:?} should enable auth");
        }
        for value in ["", "0", "false", "no", "off", "enabled"] {
            std::env::set_var("APEX_REQUIRE_AUTH", value);
            assert!(!auth_required_from_env(), "{value:?} should leave auth off");
        }
        std::env::remove_var("APEX_REQUIRE_AUTH");
        assert!(!auth_required_from_env(), "unset means auth off");
        match previous {
            Some(value) => std::env::set_var("APEX_REQUIRE_AUTH", value),
            None => std::env::remove_var("APEX_REQUIRE_AUTH"),
        }
    }

    #[tokio::test]
    async fn auth_middleware_requires_a_valid_key() {
        let dir = tempfile::tempdir().unwrap();
        let manager = Arc::new(KeyManager::new(dir.path().join("api_keys.json")));
        let (key, info) = manager.create_key("middleware", None);
        let (revoked_key, revoked_info) = manager.create_key("revoked", None);
        assert!(manager.revoke_key(&revoked_info.key_id));

        let (events, _) = tokio::sync::broadcast::channel::<String>(256);
        let config = Config::from_env();
        let state = AppState {
            agent: Arc::new(Mutex::new(Agent::new(config.clone()))),
            config,
            events,
            rate_limiter: Arc::new(Mutex::new(RateLimiter::new(
                RateLimitConfig {
                    requests_per_minute: 100,
                    requests_per_hour: 1000,
                    requests_per_day: 10_000,
                    burst_size: 10,
                },
                Box::new(MemoryStorage::default()),
            ))),
            key_manager: manager.clone(),
            require_auth: true,
        };
        let app = Router::new()
            .route("/api/v1/protected", get(|| async { "ok" }))
            .route("/health", get(|| async { "ok" }))
            .route_layer(middleware::from_fn_with_state(state.clone(), require_auth))
            .with_state(state);
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            let _ = axum::serve(listener, app).await;
        });

        let client = reqwest::Client::new();
        let url = format!("http://{addr}/api/v1/protected");

        // No credentials: exact Python body and status.
        let denied = client.get(&url).send().await.unwrap();
        assert_eq!(denied.status(), 401);
        let body: serde_json::Value = denied.json().await.unwrap();
        assert_eq!(body["error"], "Authentication required");
        assert_eq!(body["code"], "AUTH_REQUIRED");

        // The three Python carriers all authenticate.
        for request in [
            client
                .get(&url)
                .header("Authorization", format!("Bearer {key}")),
            client.get(format!("{url}?api_key={key}")),
            client.get(&url).header("X-API-Key", &key),
        ] {
            assert_eq!(request.send().await.unwrap().status(), 200);
        }

        // An empty Bearer is covered by the unit test: the wire strips
        // trailing header whitespace, so it cannot be asserted over HTTP.

        // Revoked keys are rejected, and `/health` stays exempt.
        assert_eq!(
            client
                .get(&url)
                .header("X-API-Key", &revoked_key)
                .send()
                .await
                .unwrap()
                .status(),
            401
        );
        assert_eq!(
            client
                .get(format!("http://{addr}/health"))
                .send()
                .await
                .unwrap()
                .status(),
            200
        );

        // Unmatched paths are 404s from the router, never 401s.
        assert_eq!(
            client
                .get(format!("http://{addr}/nope"))
                .send()
                .await
                .unwrap()
                .status(),
            404
        );

        // A valid request updates the store exactly like Python's validate_key.
        let listed = manager.list_keys();
        let used = listed
            .iter()
            .find(|candidate| candidate.key_id == info.key_id)
            .unwrap();
        assert_eq!(used.request_count, 3);
        assert!(used.last_used.is_some());
    }
}
