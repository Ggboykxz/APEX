//! Cost tracking — port of `apex/cost_local.py` (`MODEL_PRICING` + `CostTracker`).
//!
//! Mirrors the Python reference: per-model pricing table (46 entries), cumulative
//! session token counters, per-model usage breakdown and a resettable history.

use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ModelPricing {
    pub per_1k_input: f64,
    pub per_1k_output: f64,
    pub currency: &'static str,
}

/// `(model, per_1k_input, per_1k_output)` — keep in sync with `apex/cost_local.py`.
pub static MODEL_PRICING: &[(&str, f64, f64)] = &[
    // ── OpenAI ──
    ("gpt-4o", 0.0025, 0.01),
    ("gpt-4o-mini", 0.00015, 0.0006),
    ("gpt-4.1", 0.002, 0.008),
    ("gpt-4.1-mini", 0.0004, 0.0016),
    ("gpt-4.1-nano", 0.0001, 0.0004),
    ("gpt-5", 0.00125, 0.01),
    ("gpt-5-mini", 0.00025, 0.002),
    ("gpt-5-nano", 0.00005, 0.0004),
    ("o3", 0.002, 0.008),
    ("o3-mini", 0.0011, 0.0044),
    ("o4-mini", 0.0011, 0.0044),
    // ── Anthropic ──
    ("claude-sonnet-4.6", 0.003, 0.015),
    ("claude-opus-4.7", 0.005, 0.025),
    ("claude-sonnet-4.5", 0.003, 0.015),
    ("claude-opus-4.5", 0.005, 0.025),
    ("claude-haiku-4.5", 0.001, 0.005),
    ("claude-3.5-haiku", 0.0008, 0.004),
    ("claude-3.5-sonnet", 0.003, 0.015),
    // ── Google ──
    ("gemini-2.5-pro", 0.00125, 0.01),
    ("gemini-2.5-flash", 0.0003, 0.0025),
    ("gemini-2.5-flash-lite", 0.0001, 0.0004),
    ("gemini-2.0-flash", 0.0001, 0.0004),
    ("gemini-3-pro", 0.002, 0.012),
    ("gemini-3-flash", 0.0005, 0.003),
    ("gemini-1.5-flash", 0.000075, 0.0003),
    ("gemini-1.5-pro", 0.00125, 0.005),
    // ── xAI ──
    ("grok-4", 0.003, 0.015),
    ("grok-4-fast", 0.0002, 0.0005),
    ("grok-3", 0.003, 0.015),
    ("grok-3-mini", 0.0003, 0.0005),
    // ── DeepSeek ──
    ("deepseek-chat", 0.00014, 0.00028),
    ("deepseek-reasoner", 0.00014, 0.00028),
    ("deepseek-v4-flash", 0.00014, 0.00028),
    ("deepseek-v4-pro", 0.00174, 0.00348),
    // ── Mistral ──
    ("mistral-large-latest", 0.0005, 0.0015),
    ("mistral-medium-latest", 0.002, 0.0075),
    ("mistral-small-latest", 0.00015, 0.0006),
    ("codestral", 0.0003, 0.0009),
    ("devstral", 0.0004, 0.002),
    // ── Alibaba ──
    ("qwen3-coder-plus", 0.001, 0.005),
    ("qwen-plus", 0.0004, 0.0012),
    ("qwq-plus", 0.0008, 0.0024),
    // ── Cohere ──
    ("command-a", 0.0025, 0.01),
    ("command-r", 0.00015, 0.0006),
    // ── Groq ──
    ("llama-groq-3.3-70b", 0.00059, 0.00079),
    // ── Local ──
    ("ollama", 0.0, 0.0),
];

/// Look up pricing for a model.
///
/// Exact match first (like Python's `MODEL_PRICING.get(model)`), then a fallback
/// that strips common provider prefixes (`openai/gpt-4o`, `anthropic:claude-…`).
pub fn model_pricing(model: &str) -> Option<ModelPricing> {
    let exact = MODEL_PRICING
        .iter()
        .find(|(name, _, _)| *name == model)
        .copied();
    let (_, per_1k_input, per_1k_output) = match exact {
        Some(hit) => hit,
        None => {
            let suffix = model.rsplit(['/', ':']).next().unwrap_or(model).to_string();
            MODEL_PRICING
                .iter()
                .find(|(name, _, _)| *name == suffix.as_str())
                .copied()?
        }
    };
    Some(ModelPricing {
        per_1k_input,
        per_1k_output,
        currency: "USD",
    })
}

/// Cumulative token counters (mirrors `Agent.usage` in Python).
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Usage {
    pub prompt_tokens: u64,
    pub completion_tokens: u64,
    pub total_tokens: u64,
}

impl Usage {
    pub fn add(&mut self, prompt: u64, completion: u64, total: u64) {
        self.prompt_tokens += prompt;
        self.completion_tokens += completion;
        self.total_tokens += total;
    }

    pub fn to_json(self) -> Value {
        json!({
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        })
    }
}

fn round6(x: f64) -> f64 {
    (x * 1e6).round() / 1e6
}

/// Track and estimate costs for model usage (port of `CostTracker`).
pub struct CostTracker {
    session_start: Instant,
    input_tokens: u64,
    output_tokens: u64,
    /// model -> (input, output)
    model_usage: BTreeMap<String, (u64, u64)>,
    session_costs: Vec<Value>,
}

impl Default for CostTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl CostTracker {
    pub fn new() -> Self {
        Self {
            session_start: Instant::now(),
            input_tokens: 0,
            output_tokens: 0,
            model_usage: BTreeMap::new(),
            session_costs: Vec::new(),
        }
    }

    /// Record token usage and return the cost of this call.
    pub fn record_usage(&mut self, model: &str, input_tokens: u64, output_tokens: u64) -> f64 {
        self.input_tokens += input_tokens;
        self.output_tokens += output_tokens;
        let entry = self.model_usage.entry(model.to_string()).or_insert((0, 0));
        entry.0 += input_tokens;
        entry.1 += output_tokens;

        let Some(pricing) = model_pricing(model) else {
            return 0.0;
        };
        (input_tokens as f64 / 1000.0) * pricing.per_1k_input
            + (output_tokens as f64 / 1000.0) * pricing.per_1k_output
    }

    /// Current session cost breakdown (same shape as Python's `get_session_cost`).
    pub fn get_session_cost(&self) -> Value {
        let mut input_cost = 0.0;
        let mut output_cost = 0.0;
        for (model, (input, output)) in &self.model_usage {
            if let Some(pricing) = model_pricing(model) {
                input_cost += (*input as f64 / 1000.0) * pricing.per_1k_input;
                output_cost += (*output as f64 / 1000.0) * pricing.per_1k_output;
            }
        }
        json!({
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "input_cost": round6(input_cost),
            "output_cost": round6(output_cost),
            "total_cost": round6(input_cost + output_cost),
            "currency": "USD",
            "session_duration": self.session_start.elapsed().as_secs(),
        })
    }

    /// Archive the current session and start a fresh one.
    pub fn reset_session(&mut self) {
        let mut snapshot = self.get_session_cost();
        if let Some(obj) = snapshot.as_object_mut() {
            obj.insert("timestamp".to_string(), json!(now_iso8601_micros()));
        }
        self.session_costs.push(snapshot);
        self.session_start = Instant::now();
        self.input_tokens = 0;
        self.output_tokens = 0;
        self.model_usage.clear();
    }

    pub fn get_history(&self) -> Vec<Value> {
        self.session_costs.clone()
    }
}

/// Timestamp with microsecond precision in the same shape as Python's
/// `datetime.now().isoformat()` (`2026-10-19T07:12:38.134721`), without
/// pulling a datetime crate.
pub fn now_iso8601_micros() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    let micros = now.subsec_micros();
    // 1970-01-01 based civil date conversion (Howard Hinnant's algorithm).
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (h, m, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let mth = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if mth <= 2 { y + 1 } else { y };
    format!("{y:04}-{mth:02}-{d:02}T{h:02}:{m:02}:{s:02}.{micros:06}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pricing_table_matches_python_reference() {
        // Spot checks across providers (values copied from apex/cost_local.py).
        assert_eq!(model_pricing("gpt-4o").unwrap().per_1k_input, 0.0025);
        assert_eq!(model_pricing("gpt-4o").unwrap().per_1k_output, 0.01);
        assert_eq!(model_pricing("gpt-5-nano").unwrap().per_1k_input, 0.00005);
        assert_eq!(
            model_pricing("claude-sonnet-4.5").unwrap().per_1k_output,
            0.015
        );
        assert_eq!(
            model_pricing("gemini-1.5-flash").unwrap().per_1k_input,
            0.000075
        );
        assert_eq!(
            model_pricing("deepseek-v4-pro").unwrap().per_1k_output,
            0.00348
        );
        assert_eq!(model_pricing("ollama").unwrap().per_1k_input, 0.0);
        assert_eq!(MODEL_PRICING.len(), 46);
        assert!(model_pricing("unknown-model").is_none());
        // Provider-prefixed ids fall back to the bare model name.
        assert_eq!(model_pricing("openai/gpt-4o").unwrap().per_1k_input, 0.0025);
        assert_eq!(
            model_pricing("anthropic:claude-opus-4.7")
                .unwrap()
                .per_1k_output,
            0.025
        );
    }

    #[test]
    fn record_usage_tracks_tokens_and_cost() {
        let mut t = CostTracker::new();
        let cost = t.record_usage("gpt-4o", 1000, 1000);
        assert!((cost - 0.0125).abs() < 1e-9);
        let s = t.get_session_cost();
        assert_eq!(s["input_tokens"], 1000);
        assert_eq!(s["output_tokens"], 1000);
        assert_eq!(s["total_tokens"], 2000);
        assert_eq!(s["total_cost"], 0.0125);
        assert_eq!(s["currency"], "USD");
    }

    #[test]
    fn unknown_model_counts_tokens_but_no_cost() {
        let mut t = CostTracker::new();
        let cost = t.record_usage("mystery-llm", 500, 500);
        assert_eq!(cost, 0.0);
        let s = t.get_session_cost();
        assert_eq!(s["total_tokens"], 1000);
        assert_eq!(s["total_cost"], 0.0);
    }

    #[test]
    fn reset_session_archives_history() {
        let mut t = CostTracker::new();
        t.record_usage("gpt-4o-mini", 2000, 500);
        t.reset_session();
        assert_eq!(t.get_history().len(), 1);
        let s = t.get_session_cost();
        assert_eq!(s["total_tokens"], 0);
        assert_eq!(s["total_cost"], 0.0);
    }

    #[test]
    fn iso_timestamp_has_python_shape() {
        let t = now_iso8601_micros();
        // "2026-10-19T07:12:38.134721"
        assert_eq!(t.len(), 26, "got {t}");
        assert_eq!(&t[4..5], "-");
        assert_eq!(&t[7..8], "-");
        assert_eq!(&t[10..11], "T");
        assert_eq!(&t[13..14], ":");
        assert_eq!(&t[19..20], ".");
    }

    #[test]
    fn usage_json_shape() {
        let mut u = Usage::default();
        u.add(10, 20, 30);
        let v = u.to_json();
        assert_eq!(v["prompt_tokens"], 10);
        assert_eq!(v["completion_tokens"], 20);
        assert_eq!(v["total_tokens"], 30);
    }
}
