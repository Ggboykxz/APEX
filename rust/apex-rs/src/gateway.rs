//! APEX Gateway — AI model proxy with auth, rate limiting, and usage tracking.
//!
//! Port of `apex/gateway/*` (`config.py`, `auth.py`, `router.py`,
//! `server.py`). The gateway fronts an OpenRouter-compatible upstream,
//! authenticates caller keys (free/pro/unlimited tiers), enforces
//! per-minute and daily limits, and records usage per key and day.
//!
//! Divergences from Python (recorded in PARITY.md):
//! - The key/usage store is a JSON file (`~/.apex/gateway.json`) instead of
//!   Python's SQLite `~/.apex/gateway.db` — same data, same re-read-on-access
//!   pattern as `api_keys.json`; concurrent writers are not supported.
//! - `APEX_GATEWAY_UPSTREAM_BASE` overrides the upstream root (Python hardcodes
//!   `https://openrouter.ai/api/v1`); tests point it at a local fake.
//! - `POST /v1/chat/completions` with an invalid JSON body returns 400 (Python
//!   raises → 500), and the 200 path emits the tier *name* in
//!   `usage.apex_gateway` (Python stores a non-serializable `TierConfig`
//!   dataclass there, which breaks the response).

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::models::MODELS;

// ──────────────────────────────────────────────────────────────────────────
// Tiers (config.py)
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub struct TierConfig {
    pub daily_requests: u64,
    pub daily_tokens: u64,
    pub rate_per_minute: u32,
    pub monthly_value_usd: f64,
    pub max_concurrent: u32,
    pub models: Vec<String>,
}

/// `DEFAULT_TIERS` in `apex/gateway/config.py`.
pub fn default_tiers() -> HashMap<String, TierConfig> {
    let mut tiers = HashMap::new();
    tiers.insert(
        "free".to_string(),
        TierConfig {
            daily_requests: 50,
            daily_tokens: 500_000,
            rate_per_minute: 10,
            monthly_value_usd: 0.0,
            max_concurrent: 1,
            models: vec![
                "free-or-qwen3-235b",
                "free-or-qwen3-coder",
                "free-or-qwen3-next-80b",
                "free-or-nemotron-super",
                "free-or-nemotron-nano",
                "free-or-gemma-4-26b",
                "free-or-gemma-4-31b",
                "free-or-ring-2.6",
                "free-or-deepseek-v3.2",
                "free-or-deepseek-r1",
                "free-or-llama-3.3-70b",
                "free-or-minimax-m2.5",
                "free-or-glm-4.6",
                "free-or-poolside-laguna-m",
                "free-or-poolside-laguna-xs",
                "free-or-gpt-oss-120b",
                "free-or-gpt-oss-20b",
                "free-or-liquid-thinking",
                "free-or-router",
            ]
            .into_iter()
            .map(String::from)
            .collect(),
        },
    );
    tiers.insert(
        "pro".to_string(),
        TierConfig {
            daily_requests: 500,
            daily_tokens: 5_000_000,
            rate_per_minute: 60,
            monthly_value_usd: 60.0,
            max_concurrent: 3,
            models: vec![
                "pro-glm-5",
                "pro-glm-5.1",
                "pro-kimi-k2.5",
                "pro-kimi-k2.6",
                "pro-minimax-m2.5",
                "pro-minimax-m2.7",
                "pro-qwen3.5-plus",
                "pro-qwen3.6-plus",
                "pro-deepseek-v4-pro",
                "pro-deepseek-v4-flash",
            ]
            .into_iter()
            .map(String::from)
            .collect(),
        },
    );
    tiers.insert(
        "unlimited".to_string(),
        TierConfig {
            daily_requests: 999_999,
            daily_tokens: 100_000_000,
            rate_per_minute: 300,
            monthly_value_usd: 999.0,
            max_concurrent: 10,
            models: vec!["*".to_string()],
        },
    );
    tiers
}

// ──────────────────────────────────────────────────────────────────────────
// Config (config.py)
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct GatewayConfig {
    pub host: String,
    pub port: u16,
    pub db_path: PathBuf,
    pub data_dir: PathBuf,
    pub tiers: HashMap<String, TierConfig>,
    pub upstream_base: String,
    pub upstream_api_key: Option<String>,
    pub default_tier: String,
    pub admin_key: Option<String>,
    pub register_enabled: bool,
}

impl Default for GatewayConfig {
    fn default() -> Self {
        let home = crate::config::home_dir().unwrap_or_else(|| PathBuf::from("."));
        Self {
            host: "127.0.0.1".to_string(),
            port: 9090,
            db_path: home.join(".apex").join("gateway.json"),
            data_dir: home.join(".apex").join("gateway"),
            tiers: default_tiers(),
            upstream_base: "https://openrouter.ai/api/v1".to_string(),
            upstream_api_key: None,
            default_tier: "free".to_string(),
            admin_key: None,
            register_enabled: true,
        }
    }
}

impl GatewayConfig {
    /// `GatewayConfig.from_env` plus the `APEX_GATEWAY_UPSTREAM_BASE`
    /// override (divergence; Python hardcodes the upstream root).
    pub fn from_env() -> Self {
        let mut c = Self::default();
        if let Ok(host) = std::env::var("APEX_GATEWAY_HOST") {
            if !host.trim().is_empty() {
                c.host = host;
            }
        }
        if let Ok(port) = std::env::var("APEX_GATEWAY_PORT") {
            if let Ok(p) = port.parse::<u16>() {
                c.port = p;
            }
        }
        if let Ok(base) = std::env::var("APEX_GATEWAY_UPSTREAM_BASE") {
            if !base.trim().is_empty() {
                c.upstream_base = base;
            }
        }
        // Python: `os.environ.get("APEX_GATEWAY_KEY") or
        // os.environ.get("OPENROUTER_API_KEY")`.
        if let Ok(key) = std::env::var("APEX_GATEWAY_KEY") {
            if !key.is_empty() {
                c.upstream_api_key = Some(key);
            }
        }
        if c.upstream_api_key.is_none() {
            if let Ok(key) = std::env::var("OPENROUTER_API_KEY") {
                if !key.is_empty() {
                    c.upstream_api_key = Some(key);
                }
            }
        }
        // Python fallback: `~/.config/apex/auth.json` → `openrouter.api_key`.
        if c.upstream_api_key.is_none() {
            if let Some(home) = crate::config::home_dir() {
                let auth_path = home.join(".config").join("apex").join("auth.json");
                if let Ok(text) = std::fs::read_to_string(auth_path) {
                    if let Ok(auth) = serde_json::from_str::<serde_json::Value>(&text) {
                        if let Some(key) = auth
                            .get("openrouter")
                            .and_then(|o| o.get("api_key"))
                            .and_then(|k| k.as_str())
                            .filter(|k| !k.is_empty())
                        {
                            c.upstream_api_key = Some(key.to_string());
                        }
                    }
                }
            }
        }
        if let Ok(admin) = std::env::var("APEX_GATEWAY_ADMIN_KEY") {
            if !admin.is_empty() {
                c.admin_key = Some(admin);
            }
        }
        c
    }

    /// Python's `_get_tier`: unknown tiers fall back to `free`.
    pub fn tier(&self, name: &str) -> &TierConfig {
        self.tiers.get(name).unwrap_or_else(|| &self.tiers["free"])
    }
}

// ──────────────────────────────────────────────────────────────────────────
// Key/usage store (auth.py) — JSON file instead of Python's SQLite
// ──────────────────────────────────────────────────────────────────────────

fn active_default() -> bool {
    true
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GatewayKey {
    pub key_id: String,
    pub api_key: String,
    pub tier: String,
    #[serde(default)]
    pub label: String,
    pub created_at: f64,
    #[serde(default)]
    pub last_used_at: Option<f64>,
    #[serde(default = "active_default")]
    pub is_active: bool,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize)]
pub struct DayUsage {
    pub requests: u64,
    pub tokens: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GatewayStore {
    #[serde(default)]
    pub keys: Vec<GatewayKey>,
    #[serde(default)]
    pub usage: HashMap<String, DayUsage>,
}

fn usage_key(key_id: &str, date: &str) -> String {
    format!("{key_id}|{date}")
}

fn now_secs() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn today_utc() -> String {
    chrono::Utc::now().format("%Y-%m-%d").to_string()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// `AuthManager` — same surface as Python's, backed by a JSON file. Every
/// method re-reads the file, so a `gateway key` run in another process is
/// visible to a running `gateway start` without a restart (like
/// `api_keys.json`).
pub struct GatewayAuth {
    pub path: PathBuf,
    _guard: Mutex<()>,
}

impl GatewayAuth {
    pub fn new(path: PathBuf) -> Self {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if !path.exists() {
            Self::save_store(&path, &GatewayStore::default());
        }
        Self {
            path,
            _guard: Mutex::new(()),
        }
    }

    fn load(&self) -> GatewayStore {
        match std::fs::read_to_string(&self.path) {
            Ok(text) if !text.trim().is_empty() => serde_json::from_str(&text).unwrap_or_default(),
            _ => GatewayStore::default(),
        }
    }

    fn save_store(path: &Path, store: &GatewayStore) {
        if let Ok(text) = serde_json::to_string(store) {
            let _ = std::fs::write(path, text);
        }
    }

    /// Python's `generate_key`: `apex_` + 48 hex chars (`token_hex(24)`),
    /// with a 16-hex-char id (`token_hex(8)`).
    pub fn generate_key(&self, tier: &str, label: &str) -> String {
        let _guard = self._guard.lock().unwrap();
        let mut api = [0u8; 24];
        let mut id = [0u8; 8];
        getrandom::getrandom(&mut api).expect("key material");
        getrandom::getrandom(&mut id).expect("key material");
        let api_key = format!("apex_{}", hex(&api));
        let key_id = hex(&id);
        let mut store = self.load();
        store.keys.push(GatewayKey {
            key_id,
            api_key: api_key.clone(),
            tier: tier.to_string(),
            label: label.to_string(),
            created_at: now_secs(),
            last_used_at: None,
            is_active: true,
        });
        Self::save_store(&self.path, &store);
        api_key
    }

    /// Python's `validate_key`: `(key_id, tier)` for a live key; also
    /// touches `last_used_at`.
    pub fn validate_key(&self, api_key: &str) -> Option<(String, String)> {
        let _guard = self._guard.lock().unwrap();
        let mut store = self.load();
        let idx = store.keys.iter().position(|k| k.api_key == api_key)?;
        if !store.keys[idx].is_active {
            return None;
        }
        store.keys[idx].last_used_at = Some(now_secs());
        Self::save_store(&self.path, &store);
        Some((store.keys[idx].key_id.clone(), store.keys[idx].tier.clone()))
    }

    /// Python's `list_keys`: newest first, as the JSON rows the admin
    /// routes emit.
    pub fn list_keys(&self) -> Vec<serde_json::Value> {
        let _guard = self._guard.lock().unwrap();
        let store = self.load();
        let mut keys: Vec<&GatewayKey> = store.keys.iter().collect();
        keys.sort_by(|a, b| {
            b.created_at
                .partial_cmp(&a.created_at)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        keys.iter()
            .map(|k| {
                json!({
                    "key_id": k.key_id,
                    "tier": k.tier,
                    "label": k.label,
                    "created_at": k.created_at,
                    "last_used_at": k.last_used_at,
                    "is_active": k.is_active,
                })
            })
            .collect()
    }

    /// Python's `revoke_key`: `UPDATE keys SET is_active = 0 WHERE
    /// api_key = ?` returns the row count — so a key that exists is
    /// "found" even if it was already revoked, and only an unknown key
    /// reports false.
    pub fn revoke_key(&self, api_key: &str) -> bool {
        let _guard = self._guard.lock().unwrap();
        let mut store = self.load();
        let mut found = false;
        let mut changed = false;
        for k in &mut store.keys {
            if k.api_key == api_key {
                found = true;
                if k.is_active {
                    k.is_active = false;
                    changed = true;
                }
            }
        }
        if changed {
            Self::save_store(&self.path, &store);
        }
        found
    }

    pub fn get_day_usage(&self, key_id: &str, date: &str) -> (u64, u64) {
        let _guard = self._guard.lock().unwrap();
        match self.load().usage.get(&usage_key(key_id, date)) {
            Some(u) => (u.requests, u.tokens),
            None => (0, 0),
        }
    }

    /// Python's `record_usage`: additive upsert on `(key_id, date)`.
    pub fn record_usage(&self, key_id: &str, date: &str, requests: u64, tokens: u64) {
        let _guard = self._guard.lock().unwrap();
        let mut store = self.load();
        let entry = store.usage.entry(usage_key(key_id, date)).or_default();
        entry.requests += requests;
        entry.tokens += tokens;
        Self::save_store(&self.path, &store);
    }
}

// ──────────────────────────────────────────────────────────────────────────
// Rate limiter (router.py) — sliding 60 s window per key
// ──────────────────────────────────────────────────────────────────────────

#[derive(Default)]
pub struct RateLimiter {
    buckets: Mutex<HashMap<String, Vec<f64>>>,
}

impl RateLimiter {
    pub fn new() -> Self {
        Self::default()
    }

    /// Python's `RateLimiter.check`: prune entries older than 60 s, allow
    /// while under the limit (recording now), else deny.
    pub fn check(&self, key: &str, max_per_minute: u32) -> bool {
        let mut buckets = self.buckets.lock().unwrap();
        let bucket = buckets.entry(key.to_string()).or_default();
        let now = now_secs();
        bucket.retain(|t| now - t < 60.0);
        if bucket.len() >= max_per_minute as usize {
            return false;
        }
        bucket.push(now);
        true
    }
}

// ──────────────────────────────────────────────────────────────────────────
// Server (server.py) — axum router for the gateway endpoints
// ──────────────────────────────────────────────────────────────────────────

#[derive(Clone)]
pub struct GatewayState {
    pub config: GatewayConfig,
    pub auth: Arc<GatewayAuth>,
    pub rate_limiter: Arc<RateLimiter>,
    pub http: reqwest::Client,
}

impl GatewayState {
    pub fn new(config: GatewayConfig) -> Self {
        // Python's `GatewayServer.__init__` creates the data dir.
        let _ = std::fs::create_dir_all(&config.data_dir);
        let auth = Arc::new(GatewayAuth::new(config.db_path.clone()));
        let http = reqwest::Client::builder()
            .timeout(Duration::from_secs(120))
            .build()
            .expect("http client");
        Self {
            config,
            auth,
            rate_limiter: Arc::new(RateLimiter::new()),
            http,
        }
    }
}

pub fn router() -> Router<GatewayState> {
    Router::new()
        .route("/v1/chat/completions", post(chat_completions))
        .route("/v1/register", post(register))
        .route("/v1/status", get(status))
        .route("/v1/health", get(health))
        .route("/v1/models", get(models))
        .route("/admin/keys", get(admin_list_keys))
        .route("/admin/keys/generate", post(admin_generate_key))
        .route("/admin/keys/revoke", post(admin_revoke_key))
}

fn json_error(status: StatusCode, message: &str) -> Response {
    (status, Json(json!({ "error": message }))).into_response()
}

fn bearer_token(headers: &HeaderMap) -> Option<&str> {
    headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
}

/// Python's `_check_admin`: only a matching non-empty admin key passes.
fn admin_ok(headers: &HeaderMap, config: &GatewayConfig) -> bool {
    match config.admin_key {
        Some(ref expected) if !expected.is_empty() => {
            headers.get("x-admin-key").and_then(|v| v.to_str().ok()) == Some(expected.as_str())
        }
        _ => false,
    }
}

/// Python's `_model_allowed`: the `unlimited` tier uses `["*"]`.
pub fn model_allowed(model: &str, tier: &TierConfig) -> bool {
    if tier.models.iter().any(|m| m == "*") {
        return true;
    }
    tier.models.iter().any(|m| m == model)
}

/// `POST /v1/chat/completions` — auth → tier model check → per-minute
/// rate → daily cap → proxy to the upstream (router.py's `proxy_request`).
async fn chat_completions(
    State(st): State<GatewayState>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    let Some(api_key) = bearer_token(&headers) else {
        return json_error(
            StatusCode::UNAUTHORIZED,
            "Missing or invalid Authorization header",
        );
    };
    let Some((key_id, tier_name)) = st.auth.validate_key(api_key) else {
        return json_error(StatusCode::UNAUTHORIZED, "Invalid or revoked API key");
    };
    // Python parses the body after auth (`request.json()`); an invalid body
    // raises there (→ 500). The Rust port answers 400 instead.
    let Ok(body) = serde_json::from_slice::<serde_json::Value>(&body) else {
        return json_error(StatusCode::BAD_REQUEST, "Invalid JSON");
    };
    let model = body
        .get("model")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let tier = st.config.tier(&tier_name).clone();
    if !model_allowed(&model, &tier) {
        return json_error(
            StatusCode::FORBIDDEN,
            &format!("Model '{model}' not available in '{tier_name}' tier"),
        );
    }
    let rate_key = format!("{key_id}:{tier_name}");
    if !st.rate_limiter.check(&rate_key, tier.rate_per_minute) {
        return json_error(
            StatusCode::TOO_MANY_REQUESTS,
            &format!("Rate limit exceeded ({}/minute)", tier.rate_per_minute),
        );
    }
    let today = today_utc();
    let (day_requests, _) = st.auth.get_day_usage(&key_id, &today);
    if day_requests >= tier.daily_requests {
        return json_error(
            StatusCode::TOO_MANY_REQUESTS,
            &format!("Daily request limit reached ({})", tier.daily_requests),
        );
    }
    proxy_upstream(&st, &key_id, &tier_name, &today, &body).await
}

/// `router.py`'s `_proxy_to_upstream`.
async fn proxy_upstream(
    st: &GatewayState,
    key_id: &str,
    tier_name: &str,
    today: &str,
    body: &serde_json::Value,
) -> Response {
    let url = format!("{}{}", st.config.upstream_base, "/chat/completions");
    let request = st
        .http
        .post(&url)
        .header(
            "Authorization",
            format!(
                "Bearer {}",
                st.config.upstream_api_key.as_deref().unwrap_or("")
            ),
        )
        .header("Content-Type", "application/json")
        .json(body);
    let response = match request.send().await {
        Ok(r) => r,
        Err(e) if e.is_timeout() => {
            return json_error(StatusCode::GATEWAY_TIMEOUT, "Upstream request timed out");
        }
        Err(e) => {
            return json_error(StatusCode::BAD_GATEWAY, &format!("Upstream error: {e}"));
        }
    };
    let status = response.status();
    let Ok(mut upstream) = response.json::<serde_json::Value>().await else {
        return json_error(
            StatusCode::BAD_GATEWAY,
            "Upstream error: invalid JSON response",
        );
    };
    if status.as_u16() != 200 {
        return (
            StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::BAD_GATEWAY),
            Json(upstream),
        )
            .into_response();
    }
    let usage = upstream.get("usage").cloned().unwrap_or_else(|| json!({}));
    let prompt_tokens = usage
        .get("prompt_tokens")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let completion_tokens = usage
        .get("completion_tokens")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    st.auth
        .record_usage(key_id, today, 1, prompt_tokens + completion_tokens);
    if let Some(obj) = upstream.get_mut("usage").and_then(|v| v.as_object_mut()) {
        // Python stores the TierConfig dataclass here (not JSON-serializable);
        // the Rust port emits the tier name.
        obj.insert(
            "apex_gateway".to_string(),
            json!({ "tier": tier_name, "requests_today": 1 }),
        );
    }
    Json(upstream).into_response()
}

/// `POST /v1/register`.
async fn register(State(st): State<GatewayState>, headers: HeaderMap, body: Bytes) -> Response {
    if !st.config.register_enabled {
        return json_error(StatusCode::FORBIDDEN, "Registration disabled");
    }
    // Python checks the declared `Content-Length` (a conforming client
    // sends exactly the body bytes, so checking both is equivalent or
    // stricter).
    let declared = headers
        .get("content-length")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(body.len());
    if declared > 4096 || body.len() > 4096 {
        return json_error(StatusCode::PAYLOAD_TOO_LARGE, "Payload too large");
    }
    let Ok(data) = serde_json::from_slice::<serde_json::Value>(&body) else {
        return json_error(StatusCode::BAD_REQUEST, "Invalid JSON");
    };
    let tier = data
        .get("tier")
        .and_then(|v| v.as_str())
        .unwrap_or(st.config.default_tier.as_str())
        .to_string();
    let label = data
        .get("label")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    if !st.config.tiers.contains_key(&tier) {
        return json_error(StatusCode::BAD_REQUEST, &format!("Invalid tier: {tier}"));
    }
    let t = &st.config.tiers[&tier];
    let api_key = st.auth.generate_key(&tier, &label);
    Json(json!({
        "api_key": api_key,
        "tier": tier,
        "label": label,
        "limits": {
            "daily_requests": t.daily_requests,
            "daily_tokens": t.daily_tokens,
            "rate_per_minute": t.rate_per_minute,
            "monthly_value_usd": t.monthly_value_usd,
            "max_concurrent": t.max_concurrent,
        }
    }))
    .into_response()
}

/// `GET /v1/status`.
async fn status(State(st): State<GatewayState>, headers: HeaderMap) -> Response {
    let Some(api_key) = bearer_token(&headers) else {
        return json_error(StatusCode::UNAUTHORIZED, "Unauthorized");
    };
    let Some((key_id, tier_name)) = st.auth.validate_key(api_key) else {
        return json_error(StatusCode::UNAUTHORIZED, "Invalid key");
    };
    let tier = st.config.tier(&tier_name);
    let (requests, tokens) = st.auth.get_day_usage(&key_id, &today_utc());
    Json(json!({
        "tier": tier_name,
        "requests_today": requests,
        "requests_limit": tier.daily_requests,
        "tokens_today": tokens,
        "tokens_limit": tier.daily_tokens,
        "rate_per_minute": tier.rate_per_minute,
        "monthly_value_usd": tier.monthly_value_usd,
        "max_concurrent": tier.max_concurrent,
    }))
    .into_response()
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok", "service": "apex-gateway" }))
}

/// `GET /v1/models` — the `free-*` / `pro-*` aliases of the static model
/// table, sorted by alias, with the provider prefix.
async fn models() -> Json<serde_json::Value> {
    let mut pairs: Vec<(&str, &str)> = MODELS
        .iter()
        .copied()
        .filter(|(alias, _)| alias.starts_with("free-") || alias.starts_with("pro-"))
        .collect();
    pairs.sort_unstable_by(|a, b| a.0.cmp(b.0));
    let list: Vec<serde_json::Value> = pairs
        .into_iter()
        .map(|(alias, full)| {
            json!({ "id": alias, "provider": full.split('/').next().unwrap_or("") })
        })
        .collect();
    Json(json!({ "models": list }))
}

async fn admin_list_keys(State(st): State<GatewayState>, headers: HeaderMap) -> Response {
    if !admin_ok(&headers, &st.config) {
        return json_error(StatusCode::UNAUTHORIZED, "Unauthorized");
    }
    Json(json!({ "keys": st.auth.list_keys() })).into_response()
}

async fn admin_generate_key(
    State(st): State<GatewayState>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    if !admin_ok(&headers, &st.config) {
        return json_error(StatusCode::UNAUTHORIZED, "Unauthorized");
    }
    let Ok(data) = serde_json::from_slice::<serde_json::Value>(&body) else {
        return json_error(StatusCode::BAD_REQUEST, "Invalid JSON");
    };
    // Python's admin route does not validate the tier name.
    let tier = data
        .get("tier")
        .and_then(|v| v.as_str())
        .unwrap_or("free")
        .to_string();
    let label = data
        .get("label")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let api_key = st.auth.generate_key(&tier, &label);
    Json(json!({ "api_key": api_key, "tier": tier, "label": label })).into_response()
}

async fn admin_revoke_key(
    State(st): State<GatewayState>,
    headers: HeaderMap,
    body: Bytes,
) -> Response {
    if !admin_ok(&headers, &st.config) {
        return json_error(StatusCode::UNAUTHORIZED, "Unauthorized");
    }
    let Ok(data) = serde_json::from_slice::<serde_json::Value>(&body) else {
        return json_error(StatusCode::BAD_REQUEST, "Invalid JSON");
    };
    let api_key = data
        .get("api_key")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    if st.auth.revoke_key(&api_key) {
        Json(json!({ "status": "revoked" })).into_response()
    } else {
        json_error(StatusCode::NOT_FOUND, "Key not found")
    }
}

// ──────────────────────────────────────────────────────────────────────────
// `gateway start`
// ──────────────────────────────────────────────────────────────────────────

/// Bind `host:port` and serve until the process ends (Python keeps the
/// event loop alive with `run_forever`; the Rust binary blocks on
/// `axum::serve`, same as `serve`).
pub async fn start(config: GatewayConfig) {
    let state = GatewayState::new(config.clone());
    let app = router().with_state(state);
    let addr = format!("{}:{}", config.host, config.port);
    let listener = match tokio::net::TcpListener::bind(&addr).await {
        Ok(l) => l,
        Err(e) => {
            eprintln!("ERROR: cannot bind {addr}: {e}");
            return;
        }
    };
    println!("APEX Gateway running on http://{addr}");
    println!("Register: POST /v1/register");
    println!("Chat:     POST /v1/chat/completions");
    println!("Press Ctrl+C to stop");
    let _ = axum::serve(listener, app).await;
}

// ──────────────────────────────────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_tiers_match_python() {
        let tiers = default_tiers();
        let free = &tiers["free"];
        assert_eq!(
            (free.daily_requests, free.daily_tokens, free.rate_per_minute),
            (50, 500_000, 10)
        );
        assert_eq!(free.monthly_value_usd, 0.0);
        assert_eq!(free.max_concurrent, 1);
        assert_eq!(free.models.len(), 19);
        assert!(free.models.iter().any(|m| m == "free-or-qwen3-coder"));
        assert!(free.models.iter().any(|m| m == "free-or-qwen3-235b"));
        assert!(free.models.iter().any(|m| m == "free-or-router"));
        assert!(!free.models.iter().any(|m| m == "pro-glm-5"));
        let pro = &tiers["pro"];
        assert_eq!(
            (pro.daily_requests, pro.daily_tokens, pro.rate_per_minute),
            (500, 5_000_000, 60)
        );
        assert_eq!(pro.monthly_value_usd, 60.0);
        assert_eq!(pro.max_concurrent, 3);
        assert_eq!(pro.models.len(), 10);
        assert!(pro.models.iter().any(|m| m == "pro-glm-5"));
        assert!(pro.models.iter().any(|m| m == "pro-deepseek-v4-pro"));
        let unlimited = &tiers["unlimited"];
        assert_eq!(
            (
                unlimited.daily_requests,
                unlimited.daily_tokens,
                unlimited.rate_per_minute
            ),
            (999_999, 100_000_000, 300)
        );
        assert_eq!(unlimited.monthly_value_usd, 999.0);
        assert_eq!(unlimited.max_concurrent, 10);
        assert_eq!(unlimited.models, vec!["*"]);
    }

    #[test]
    fn config_defaults_match_python() {
        let cfg = GatewayConfig::default();
        assert_eq!(cfg.host, "127.0.0.1");
        assert_eq!(cfg.port, 9090);
        assert_eq!(cfg.default_tier, "free");
        assert!(cfg.register_enabled);
        assert_eq!(cfg.upstream_base, "https://openrouter.ai/api/v1");
        assert!(cfg.tiers.contains_key("free"));
        assert!(cfg.tiers.contains_key("pro"));
        assert!(cfg.tiers.contains_key("unlimited"));
        // Unknown tiers fall back to `free` (Python's `_get_tier`).
        assert_eq!(cfg.tier("bogus").daily_requests, 50);
    }

    #[test]
    fn key_lifecycle() {
        let dir = tempfile::tempdir().unwrap();
        let auth = GatewayAuth::new(dir.path().join("gateway.json"));
        let key = auth.generate_key("pro", "alice");
        assert!(key.starts_with("apex_"));
        assert_eq!(key.len(), 5 + 48); // `apex_` + `token_hex(24)`
        assert!(auth.validate_key("bogus").is_none());
        let Some((key_id, tier)) = auth.validate_key(&key) else {
            panic!("valid key must validate");
        };
        assert_eq!(tier, "pro");
        assert_eq!(key_id.len(), 16); // `token_hex(8)`
        let rows = auth.list_keys();
        assert!(rows
            .iter()
            .any(|k| k["key_id"] == key_id && k["tier"] == "pro" && k["label"] == "alice"));
        assert!(auth.revoke_key(&key));
        assert!(auth.validate_key(&key).is_none());
        // Python's UPDATE reports the row even when it is already
        // inactive, so revoking twice in a row still counts as found.
        assert!(auth.revoke_key(&key));
        assert!(!auth.revoke_key("nonexistent"));
    }

    #[test]
    fn key_listing_is_newest_first() {
        let dir = tempfile::tempdir().unwrap();
        let auth = GatewayAuth::new(dir.path().join("gateway.json"));
        auth.generate_key("free", "first");
        // Ensure a distinguishable `created_at` (SQLite parity: ORDER BY
        // created_at DESC).
        std::thread::sleep(Duration::from_millis(5));
        auth.generate_key("free", "second");
        let rows = auth.list_keys();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0]["label"], "second");
        assert_eq!(rows[1]["label"], "first");
    }

    #[test]
    fn usage_tracking() {
        let dir = tempfile::tempdir().unwrap();
        let auth = GatewayAuth::new(dir.path().join("gateway.json"));
        let key = auth.generate_key("free", "");
        let (key_id, _) = auth.validate_key(&key).unwrap();
        assert_eq!(auth.get_day_usage(&key_id, "2026-01-01"), (0, 0));
        auth.record_usage(&key_id, "2026-01-01", 3, 150);
        assert_eq!(auth.get_day_usage(&key_id, "2026-01-01"), (3, 150));
        auth.record_usage(&key_id, "2026-01-01", 1, 50);
        assert_eq!(auth.get_day_usage(&key_id, "2026-01-01"), (4, 200));
        auth.record_usage(&key_id, "2026-01-02", 5, 0);
        assert_eq!(auth.get_day_usage(&key_id, "2026-01-01"), (4, 200));
        assert_eq!(auth.get_day_usage(&key_id, "2026-01-02"), (5, 0));
    }

    #[test]
    fn store_persists_across_instances() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("gateway.json");
        let key = {
            let auth = GatewayAuth::new(path.clone());
            auth.generate_key("free", "persist")
        };
        let auth2 = GatewayAuth::new(path);
        assert!(auth2.validate_key(&key).is_some());
    }

    #[test]
    fn rate_limiter_windows() {
        let rl = RateLimiter::new();
        for _ in 0..5 {
            assert!(rl.check("a:free", 10));
        }
        for _ in 0..3 {
            assert!(rl.check("b:pro", 3));
        }
        assert!(!rl.check("b:pro", 3));
        // A different key has its own bucket.
        assert!(rl.check("c:free", 5));
        // Expired entries are pruned before the check.
        let mut buckets = rl.buckets.lock().unwrap();
        buckets
            .entry("d:free".to_string())
            .or_default()
            .push(now_secs() - 120.0);
        drop(buckets);
        assert!(rl.check("d:free", 10));
        assert_eq!(rl.buckets.lock().unwrap().get("d:free").unwrap().len(), 1);
    }

    #[test]
    fn model_allowed_follows_tiers() {
        let tiers = default_tiers();
        let free = &tiers["free"];
        let pro = &tiers["pro"];
        let unlimited = &tiers["unlimited"];
        assert!(model_allowed("free-or-qwen3-coder", free));
        assert!(!model_allowed("pro-glm-5", free));
        assert!(model_allowed("pro-glm-5", pro));
        assert!(!model_allowed("free-or-qwen3-coder", pro));
        assert!(model_allowed("anything-at-all", unlimited));
    }
}
