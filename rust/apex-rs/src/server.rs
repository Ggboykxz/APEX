use crate::agent::Agent;
use crate::api_key::KeyManager;
use crate::config::Config;
use crate::rate_limiter::{MemoryStorage, RateLimitConfig, RateLimiter};
use crate::tools;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Query, State};
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
    let mut limiter = state.rate_limiter.lock().await;
    let result = limiter.check_rate_limit(&key);
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

pub async fn serve(config: Config, port: u16) {
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
            get(|axum::extract::Path(id): axum::extract::Path<String>| async move {
                Json(serde_json::json!({"id": id, "name": id}))
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
        .route("/api/v1/agents", get(|| async {
            Json(serde_json::json!({"agents": [
                {"id":"build","name":"Build"},
                {"id":"plan","name":"Plan"}
            ]}))
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
        .route_layer(middleware::from_fn_with_state(state.clone(), rate_limit))
        // Auth wraps the limiter: Python's `_check_auth` runs before
        // `_check_rate_limit`, so rejected requests never consume budget.
        .route_layer(middleware::from_fn_with_state(state.clone(), require_auth))
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
