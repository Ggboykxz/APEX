//! rlm — Remote Language Model query and rate limiting ported from `apex/rlm.py`.
//!
//! Note: The Python version depends on `litellm` for LLM calls. The Rust port
//! provides the rate-limit manager and query structure; actual LLM invocation
//! is a stub since there is no direct litellm equivalent in Rust.
//!
//! Wired into the CLI via `apex-rs rlm` (per-key rate-limit check/increment).

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use serde_json::Value;

/// Configuration for rate limiting.
#[derive(Debug, Clone, PartialEq)]
pub struct RLMConfig {
    pub requests_per_minute: i64,
    pub requests_per_hour: i64,
    pub requests_per_day: i64,
}

impl Default for RLMConfig {
    fn default() -> Self {
        Self {
            requests_per_minute: 60,
            requests_per_hour: 1000,
            requests_per_day: 10000,
        }
    }
}

/// Rate Limit Manager — tracks and enforces per-key rate limits.
#[allow(clippy::upper_case_acronyms)] // Python parity name: RLM
pub struct RLM {
    config: RLMConfig,
    counts: HashMap<String, HashMap<String, (i64, f64)>>,
}

impl RLM {
    const WINDOWS: [(&str, f64); 3] = [("minute", 60.0), ("hour", 3600.0), ("day", 86400.0)];

    pub fn new(config: Option<RLMConfig>) -> Self {
        Self {
            config: config.unwrap_or_default(),
            counts: HashMap::new(),
        }
    }

    fn ensure_key(&mut self, key: &str) -> &mut HashMap<String, (i64, f64)> {
        self.counts.entry(key.to_string()).or_insert_with(|| {
            Self::WINDOWS
                .iter()
                .map(|(w, _)| (w.to_string(), (0, 0.0)))
                .collect()
        })
    }

    pub fn check_rate_limit(&self, key: &str) -> serde_json::Value {
        let windows = match self.counts.get(key) {
            Some(w) => w,
            None => {
                return serde_json::json!({
                    "allowed": true,
                    "retry_after": 0,
                    "remaining_minute": self.config.requests_per_minute,
                    "remaining_hour": self.config.requests_per_hour,
                    "remaining_day": self.config.requests_per_day,
                });
            }
        };
        let now = time_now();
        let mut result = serde_json::json!({
            "allowed": true,
            "retry_after": 0,
        });

        for (window, window_secs) in Self::WINDOWS {
            let limit = match window {
                "minute" => self.config.requests_per_minute,
                "hour" => self.config.requests_per_hour,
                "day" => self.config.requests_per_day,
                _ => 0,
            };
            let (count, timestamp) = windows.get(window).copied().unwrap_or((0, 0.0));

            let remaining = if now - timestamp < window_secs {
                limit - count
            } else {
                limit
            };

            if remaining <= 0 {
                result["allowed"] = Value::Bool(false);
                let retry = (window_secs - (now - timestamp)).max(0.0) as i64;
                let current_retry = result["retry_after"].as_i64().unwrap_or(0);
                result["retry_after"] = Value::Number((retry.max(current_retry)).into());
            }

            result[format!("remaining_{}", window)] = Value::Number(remaining.max(0).into());
        }

        result
    }

    pub fn increment(&mut self, key: &str) -> serde_json::Value {
        let windows = self.ensure_key(key);
        let now = time_now();

        for (window, window_secs) in Self::WINDOWS {
            let (count, timestamp) = windows.get(window).copied().unwrap_or((0, 0.0));
            let new_entry = if now - timestamp >= window_secs {
                (1, now)
            } else {
                (count + 1, timestamp)
            };
            windows.insert(window.to_string(), new_entry);
        }

        self.check_rate_limit(key)
    }

    #[allow(dead_code)] // TODO(v2.6): wire a public reset API
    pub fn reset(&mut self, key: &str) {
        self.counts.remove(key);
    }

    #[allow(dead_code)] // TODO(v2.6): expose RLM state via CLI/HTTP
    pub fn to_dict(&self) -> serde_json::Value {
        let mut counts_map = serde_json::Map::new();
        for (k, wins) in &self.counts {
            let mut wins_map = serde_json::Map::new();
            for (w, v) in wins {
                wins_map.insert(
                    w.clone(),
                    Value::Array(vec![
                        Value::Number(serde_json::Number::from(v.0)),
                        Value::Number(
                            serde_json::Number::from_f64(v.1)
                                .unwrap_or(serde_json::Number::from(0)),
                        ),
                    ]),
                );
            }
            counts_map.insert(k.clone(), Value::Object(wins_map));
        }

        serde_json::json!({
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "requests_per_day": self.config.requests_per_day,
            },
            "counts": counts_map,
        })
    }

    #[allow(dead_code)] // TODO(v2.6): load RLM state from persisted config
    pub fn from_dict(data: &serde_json::Value) -> Self {
        let config = RLMConfig {
            requests_per_minute: data["config"]["requests_per_minute"].as_i64().unwrap_or(60),
            requests_per_hour: data["config"]["requests_per_hour"].as_i64().unwrap_or(1000),
            requests_per_day: data["config"]["requests_per_day"].as_i64().unwrap_or(10000),
        };
        let mut rlm = Self::new(Some(config));
        if let Some(counts) = data.get("counts").and_then(|v| v.as_object()) {
            for (k, wins) in counts {
                let mut wins_map = HashMap::new();
                if let Some(wins_obj) = wins.as_object() {
                    for (w, v) in wins_obj {
                        if let Some(arr) = v.as_array() {
                            if arr.len() >= 2 {
                                let count = arr[0].as_i64().unwrap_or(0);
                                let timestamp = arr[1].as_f64().unwrap_or(0.0);
                                wins_map.insert(w.clone(), (count, timestamp));
                            }
                        }
                    }
                }
                rlm.counts.insert(k.clone(), wins_map);
            }
        }
        rlm
    }
}

/// Remote Language Model query for batched cheap analysis.
/// Note: The Python version uses `litellm` for actual LLM calls. The Rust port
/// provides the query structure; LLM invocation returns an error stub.
#[allow(dead_code)] // LLM stubs; TODO(v2.6): wire a litellm-style client
pub struct RLMQuery {
    cheap_model: String,
    expensive_model: String,
    max_parallel: i64,
}

impl Default for RLMQuery {
    fn default() -> Self {
        Self {
            cheap_model: "gpt-4o-mini".to_string(),
            expensive_model: "gpt-4o".to_string(),
            max_parallel: 10,
        }
    }
}

#[allow(dead_code)] // LLM stubs; see struct-level allow
impl RLMQuery {
    pub fn new() -> Self {
        Self::default()
    }

    /// Query a single prompt (stub — no litellm equivalent in Rust).
    pub fn query(&self, _prompt: &str, _use_cheap: bool, _kwargs: &serde_json::Value) -> String {
        "ERROR: LLM invocation not available in Rust port (litellm dependency)".to_string()
    }

    /// Batch query multiple prompts (stub).
    #[allow(clippy::type_complexity)] // callback fn signature is a single-purpose FFI-style hook
    pub fn batch_query(
        &self,
        _prompts: &[String],
        _use_cheap: bool,
        _callback: Option<&dyn Fn(usize, &str)>,
    ) -> Vec<String> {
        vec!["ERROR: LLM invocation not available in Rust port".to_string(); _prompts.len()]
    }

    /// Classify a batch of items into categories (stub).
    pub fn classify_batch(
        &self,
        _items: &[String],
        _criteria: &str,
        _categories: &[String],
    ) -> HashMap<String, Vec<usize>> {
        let mut result: HashMap<String, Vec<usize>> = HashMap::new();
        for cat in _categories {
            result.insert(cat.clone(), Vec::new());
        }
        result
    }

    /// Summarize each item in a batch (stub).
    pub fn summarize_batch(&self, _items: &[String], _max_length: i64) -> Vec<String> {
        vec!["ERROR: LLM invocation not available".to_string(); _items.len()]
    }

    /// Extract information from a batch using a pattern (stub).
    pub fn extract_batch(&self, _items: &[String], _extract_pattern: &str) -> Vec<Vec<String>> {
        vec![Vec::new(); _items.len()]
    }

    /// Route query to appropriate model based on complexity (stub).
    pub fn route_query(&self, _prompt: &str, _complexity_hint: &str) -> String {
        "ERROR: LLM invocation not available in Rust port".to_string()
    }
}

fn time_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

#[allow(dead_code)] // LLM stub singleton; see struct-level allow
static RLM_QUERY: OnceLock<Mutex<RLMQuery>> = OnceLock::new();

#[allow(dead_code)] // LLM stub singleton accessor; see struct-level allow
pub fn rlm_query() -> &'static Mutex<RLMQuery> {
    RLM_QUERY.get_or_init(|| Mutex::new(RLMQuery::new()))
}
