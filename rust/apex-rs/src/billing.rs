//! Billing — port of `apex/billing.py`.
//!
//! Implements: BillingManager, PlanType, CostConfig, BillingAccount,
//! UsageRecord, and the `billing_manager` global singleton.
//!
//! Tools exposed: billing_cost, billing_quota, billing_usage, billing_plan,
//! billing_summary.

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use serde_json::Value;

/// `InsufficientBalanceError` — raised when account balance is insufficient.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InsufficientBalanceError;

/// `TrialExpiredError` — raised when trial period has expired.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TrialExpiredError;

/// `QuotaExceededError` — raised when a quota is exceeded.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QuotaExceededError;

/// `PlanType` — billing plan tier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PlanType {
    Free,
    Pro,
    Enterprise,
    Custom,
}

impl PlanType {
    pub fn as_str(&self) -> &'static str {
        match self {
            PlanType::Free => "free",
            PlanType::Pro => "pro",
            PlanType::Enterprise => "enterprise",
            PlanType::Custom => "custom",
        }
    }
}

/// `CostConfig` — pricing configuration for a model.
#[derive(Debug, Clone, PartialEq)]
pub struct CostConfig {
    pub input_cost_per_1k: f64,
    pub output_cost_per_1k: f64,
    pub input_cost_per_1k_vision: f64,
    pub cache_read_cost_per_1m: f64,
    pub store_cost_per_1k: f64,
}

const DEFAULT_COST_CONFIG: CostConfig = CostConfig {
    input_cost_per_1k: 0.0,
    output_cost_per_1k: 0.0,
    input_cost_per_1k_vision: 0.0,
    cache_read_cost_per_1m: 0.0,
    store_cost_per_1k: 0.0,
};

/// `MODEL_COSTS` — model pricing table, mirrored from Python's `MODEL_COSTS`.
pub const MODEL_COSTS: &[(&str, CostConfig)] = &[
    // ── Anthropic ──
    (
        "claude_opus_4_7",
        CostConfig {
            input_cost_per_1k: 0.005,
            output_cost_per_1k: 0.025,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_sonnet_4_6",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_opus_4_5",
        CostConfig {
            input_cost_per_1k: 0.005,
            output_cost_per_1k: 0.025,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_sonnet_4_5",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_haiku_4_5",
        CostConfig {
            input_cost_per_1k: 0.001,
            output_cost_per_1k: 0.005,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_3_5_haiku",
        CostConfig {
            input_cost_per_1k: 0.0008,
            output_cost_per_1k: 0.004,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_3_5_sonnet",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── OpenAI ──
    (
        "gpt_5",
        CostConfig {
            input_cost_per_1k: 0.00125,
            output_cost_per_1k: 0.01,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_5_mini",
        CostConfig {
            input_cost_per_1k: 0.00025,
            output_cost_per_1k: 0.002,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_5_nano",
        CostConfig {
            input_cost_per_1k: 0.00005,
            output_cost_per_1k: 0.0004,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_4o",
        CostConfig {
            input_cost_per_1k: 0.0025,
            output_cost_per_1k: 0.01,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_4o_mini",
        CostConfig {
            input_cost_per_1k: 0.00015,
            output_cost_per_1k: 0.0006,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_4_1",
        CostConfig {
            input_cost_per_1k: 0.002,
            output_cost_per_1k: 0.008,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_4_1_mini",
        CostConfig {
            input_cost_per_1k: 0.0004,
            output_cost_per_1k: 0.0016,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "o3",
        CostConfig {
            input_cost_per_1k: 0.002,
            output_cost_per_1k: 0.008,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "o3_mini",
        CostConfig {
            input_cost_per_1k: 0.0011,
            output_cost_per_1k: 0.0044,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "o4_mini",
        CostConfig {
            input_cost_per_1k: 0.0011,
            output_cost_per_1k: 0.0044,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Google ──
    (
        "gemini_2_5_pro",
        CostConfig {
            input_cost_per_1k: 0.00125,
            output_cost_per_1k: 0.01,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_2_5_flash",
        CostConfig {
            input_cost_per_1k: 0.0003,
            output_cost_per_1k: 0.0025,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_3_pro",
        CostConfig {
            input_cost_per_1k: 0.002,
            output_cost_per_1k: 0.012,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_3_flash",
        CostConfig {
            input_cost_per_1k: 0.0005,
            output_cost_per_1k: 0.003,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_2_0_flash",
        CostConfig {
            input_cost_per_1k: 0.0001,
            output_cost_per_1k: 0.0004,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── xAI ──
    (
        "grok_4",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "grok_4_fast",
        CostConfig {
            input_cost_per_1k: 0.0002,
            output_cost_per_1k: 0.0005,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "grok_3",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "grok_3_mini",
        CostConfig {
            input_cost_per_1k: 0.0003,
            output_cost_per_1k: 0.0005,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── DeepSeek ──
    (
        "deepseek_chat",
        CostConfig {
            input_cost_per_1k: 0.00014,
            output_cost_per_1k: 0.00028,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "deepseek_reasoner",
        CostConfig {
            input_cost_per_1k: 0.00014,
            output_cost_per_1k: 0.00028,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "deepseek_v4_flash",
        CostConfig {
            input_cost_per_1k: 0.00014,
            output_cost_per_1k: 0.00028,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "deepseek_v4_pro",
        CostConfig {
            input_cost_per_1k: 0.00174,
            output_cost_per_1k: 0.00348,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Mistral ──
    (
        "mistral_large_latest",
        CostConfig {
            input_cost_per_1k: 0.0005,
            output_cost_per_1k: 0.0015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "mistral_medium_latest",
        CostConfig {
            input_cost_per_1k: 0.002,
            output_cost_per_1k: 0.0075,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "mistral_small_latest",
        CostConfig {
            input_cost_per_1k: 0.00015,
            output_cost_per_1k: 0.0006,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "codestral",
        CostConfig {
            input_cost_per_1k: 0.0003,
            output_cost_per_1k: 0.0009,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Alibaba ──
    (
        "qwen3_coder_plus",
        CostConfig {
            input_cost_per_1k: 0.001,
            output_cost_per_1k: 0.005,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "qwen_plus",
        CostConfig {
            input_cost_per_1k: 0.0004,
            output_cost_per_1k: 0.0012,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Cohere ──
    (
        "command_a",
        CostConfig {
            input_cost_per_1k: 0.0025,
            output_cost_per_1k: 0.01,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "command_r",
        CostConfig {
            input_cost_per_1k: 0.00015,
            output_cost_per_1k: 0.0006,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Groq ──
    (
        "llama_groq_3_3_70b",
        CostConfig {
            input_cost_per_1k: 0.00059,
            output_cost_per_1k: 0.00079,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Ollama (free) ──
    (
        "ollama",
        CostConfig {
            input_cost_per_1k: 0.0,
            output_cost_per_1k: 0.0,
            ..DEFAULT_COST_CONFIG
        },
    ),
    // ── Backward-compatible aliases ──
    (
        "claude_opus",
        CostConfig {
            input_cost_per_1k: 0.005,
            output_cost_per_1k: 0.025,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_sonnet",
        CostConfig {
            input_cost_per_1k: 0.003,
            output_cost_per_1k: 0.015,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "claude_haiku",
        CostConfig {
            input_cost_per_1k: 0.001,
            output_cost_per_1k: 0.005,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gpt_4_turbo",
        CostConfig {
            input_cost_per_1k: 0.01,
            output_cost_per_1k: 0.03,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_2",
        CostConfig {
            input_cost_per_1k: 0.0,
            output_cost_per_1k: 0.0,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "gemini_flash",
        CostConfig {
            input_cost_per_1k: 0.0,
            output_cost_per_1k: 0.0,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "deepseek_coder",
        CostConfig {
            input_cost_per_1k: 0.00014,
            output_cost_per_1k: 0.00028,
            ..DEFAULT_COST_CONFIG
        },
    ),
    (
        "llama_3",
        CostConfig {
            input_cost_per_1k: 0.0,
            output_cost_per_1k: 0.0,
            ..DEFAULT_COST_CONFIG
        },
    ),
];

/// `UsageRecord` — a single usage record.
#[derive(Debug, Clone, PartialEq)]
pub struct UsageRecord {
    pub timestamp: f64,
    pub model: String,
    pub input_tokens: i64,
    pub output_tokens: i64,
    pub cost: f64,
    pub session_id: Option<String>,
    pub workspace_id: Option<String>,
}

/// `BillingPlan` — a billing plan definition.
#[derive(Debug, Clone, PartialEq)]
pub struct BillingPlan {
    pub plan_type: PlanType,
    pub name: String,
    pub monthly_limit: f64,
    pub input_limit: i64,
    pub output_limit: i64,
    pub rate_limit_per_minute: i64,
    pub rate_limit_per_hour: i64,
    pub rate_limit_per_day: i64,
    pub enabled_features: Vec<String>,
    pub trial_days: i64,
    pub overage_allowed: bool,
    pub overage_multiplier: f64,
}

/// `BillingAccount` — a user's billing account.
#[derive(Debug, Clone, PartialEq)]
pub struct BillingAccount {
    pub user_id: String,
    pub plan: BillingPlan,
    pub balance: f64,
    pub used_this_month: f64,
    pub input_tokens_used: i64,
    pub output_tokens_used: i64,
    pub trial_end: Option<f64>,
    pub created_at: f64,
    pub is_active: bool,
    pub metadata: HashMap<String, Value>,
}

/// `BillingManager` — manages billing accounts, plans, and usage tracking.
pub struct BillingManager {
    accounts: HashMap<String, BillingAccount>,
    usage_history: HashMap<String, Vec<UsageRecord>>,
    default_plan: BillingPlan,
}

impl BillingManager {
    pub fn new() -> Self {
        Self {
            accounts: HashMap::new(),
            usage_history: HashMap::new(),
            default_plan: Self::plans().get(&PlanType::Free).unwrap().clone(),
        }
    }

    pub fn plans() -> HashMap<PlanType, BillingPlan> {
        let mut plans = HashMap::new();
        plans.insert(
            PlanType::Free,
            BillingPlan {
                plan_type: PlanType::Free,
                name: "Free".to_string(),
                monthly_limit: 0.0,
                input_limit: 100000,
                output_limit: 50000,
                rate_limit_per_minute: 5,
                rate_limit_per_hour: 50,
                rate_limit_per_day: 200,
                enabled_features: Vec::new(),
                trial_days: 0,
                overage_allowed: false,
                overage_multiplier: 1.5,
            },
        );
        plans.insert(
            PlanType::Pro,
            BillingPlan {
                plan_type: PlanType::Pro,
                name: "Pro".to_string(),
                monthly_limit: 20.0,
                input_limit: 10000000,
                output_limit: 5000000,
                rate_limit_per_minute: 60,
                rate_limit_per_hour: 1000,
                rate_limit_per_day: 10000,
                enabled_features: vec![
                    "advanced_tools".to_string(),
                    "priority_support".to_string(),
                    "custom_models".to_string(),
                ],
                trial_days: 7,
                overage_allowed: true,
                overage_multiplier: 1.5,
            },
        );
        plans.insert(
            PlanType::Enterprise,
            BillingPlan {
                plan_type: PlanType::Enterprise,
                name: "Enterprise".to_string(),
                monthly_limit: 100.0,
                input_limit: -1,
                output_limit: -1,
                rate_limit_per_minute: 300,
                rate_limit_per_hour: 10000,
                rate_limit_per_day: 100000,
                enabled_features: vec![
                    "advanced_tools".to_string(),
                    "priority_support".to_string(),
                    "custom_models".to_string(),
                    "sso".to_string(),
                    "audit_logs".to_string(),
                ],
                trial_days: 14,
                overage_allowed: true,
                overage_multiplier: 1.5,
            },
        );
        plans
    }

    pub fn create_account(&mut self, user_id: &str, plan_type: PlanType) -> BillingAccount {
        let plan = BillingManager::plans()
            .get(&plan_type)
            .unwrap_or(&self.default_plan)
            .clone();
        let trial_end = if plan.trial_days > 0 {
            Some(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs_f64()
                    + (plan.trial_days as f64 * 86400.0),
            )
        } else {
            None
        };
        let account = BillingAccount {
            user_id: user_id.to_string(),
            plan,
            balance: 0.0,
            used_this_month: 0.0,
            input_tokens_used: 0,
            output_tokens_used: 0,
            trial_end,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            is_active: true,
            metadata: HashMap::new(),
        };
        self.accounts.insert(user_id.to_string(), account.clone());
        self.usage_history.insert(user_id.to_string(), Vec::new());
        account
    }

    pub fn get_account(&self, user_id: &str) -> Option<&BillingAccount> {
        self.accounts.get(user_id)
    }

    pub fn calculate_cost(
        &self,
        model: &str,
        input_tokens: i64,
        output_tokens: i64,
        use_cache: bool,
        cache_tokens: i64,
    ) -> f64 {
        let input_tokens = input_tokens.max(0);
        let output_tokens = output_tokens.max(0);
        let cache_tokens = cache_tokens.max(0);
        let model_key = model.to_lowercase().replace('-', "_").replace(' ', "_");
        let cost_config = MODEL_COSTS
            .iter()
            .find(|(name, _)| *name == model_key)
            .map(|(_, c)| c)
            .unwrap_or(
                &MODEL_COSTS[MODEL_COSTS
                    .iter()
                    .position(|(n, _)| *n == "claude_sonnet")
                    .unwrap()]
                .1,
            );
        let input_cost = (input_tokens as f64 / 1000.0) * cost_config.input_cost_per_1k;
        let output_cost = (output_tokens as f64 / 1000.0) * cost_config.output_cost_per_1k;
        let cache_cost = if use_cache && cache_tokens > 0 {
            (cache_tokens as f64 / 1000.0) * cost_config.cache_read_cost_per_1m
        } else {
            0.0
        };
        ((input_cost + output_cost + cache_cost) * 1_000_000.0).round() / 1_000_000.0
    }

    pub fn check_quota(
        &mut self,
        user_id: &str,
        model: &str,
        input_tokens: i64,
        output_tokens: i64,
    ) -> (bool, String) {
        let needs_account = !self.accounts.contains_key(user_id);
        if needs_account {
            self.create_account(user_id, PlanType::Free);
        }
        let account = self.accounts.get(user_id).unwrap().clone();
        if !account.is_active {
            return (false, "Account is not active".to_string());
        }
        if let Some(trial_end) = account.trial_end {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64();
            if now > trial_end {
                return (false, "Trial period has expired".to_string());
            }
        }
        if account.plan.monthly_limit > 0.0 {
            let projected_cost = self.calculate_cost(model, input_tokens, output_tokens, false, 0);
            if account.used_this_month + projected_cost > account.plan.monthly_limit {
                if !account.plan.overage_allowed {
                    return (
                        false,
                        format!("Monthly limit of ${} exceeded", account.plan.monthly_limit),
                    );
                }
            }
        }
        if account.plan.input_limit > 0 {
            if account.input_tokens_used + input_tokens > account.plan.input_limit {
                return (
                    false,
                    format!("Input token limit exceeded ({})", account.plan.input_limit),
                );
            }
        }
        if account.plan.output_limit > 0 {
            if account.output_tokens_used + output_tokens > account.plan.output_limit {
                return (
                    false,
                    format!(
                        "Output token limit exceeded ({})",
                        account.plan.output_limit
                    ),
                );
            }
        }
        (true, "OK".to_string())
    }

    pub fn record_usage(
        &mut self,
        user_id: &str,
        model: &str,
        input_tokens: i64,
        output_tokens: i64,
        session_id: Option<&str>,
        workspace_id: Option<&str>,
    ) -> UsageRecord {
        let cost = self.calculate_cost(model, input_tokens, output_tokens, false, 0);
        let record = UsageRecord {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            model: model.to_string(),
            input_tokens,
            output_tokens,
            cost,
            session_id: session_id.map(|s| s.to_string()),
            workspace_id: workspace_id.map(|s| s.to_string()),
        };
        self.usage_history
            .entry(user_id.to_string())
            .or_default()
            .push(record.clone());
        if let Some(account) = self.accounts.get_mut(user_id) {
            account.used_this_month += cost;
            account.input_tokens_used += input_tokens;
            account.output_tokens_used += output_tokens;
        }
        record
    }

    pub fn get_usage_history(&self, user_id: &str, limit: usize) -> Vec<UsageRecord> {
        let mut history = self.usage_history.get(user_id).cloned().unwrap_or_default();
        history.sort_by(|a, b| b.timestamp.partial_cmp(&a.timestamp).unwrap());
        history.truncate(limit);
        history
    }

    pub fn get_usage_summary(&self, user_id: &str) -> serde_json::Value {
        let account = self.accounts.get(user_id);
        let history = self.usage_history.get(user_id).cloned().unwrap_or_default();
        let total_cost: f64 = history.iter().map(|r| r.cost).sum();
        let total_input: i64 = history.iter().map(|r| r.input_tokens).sum();
        let total_output: i64 = history.iter().map(|r| r.output_tokens).sum();
        serde_json::json!({
            "user_id": user_id,
            "plan": account.map(|a| a.plan.name.as_str()).unwrap_or("Unknown"),
            "balance": account.map(|a| a.balance).unwrap_or(0.0),
            "used_this_month": account.map(|a| a.used_this_month).unwrap_or(0.0),
            "input_tokens_used": account.map(|a| a.input_tokens_used).unwrap_or(0),
            "output_tokens_used": account.map(|a| a.output_tokens_used).unwrap_or(0),
            "total_cost": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_requests": history.len(),
        })
    }

    pub fn update_plan(&mut self, user_id: &str, plan_type: PlanType) -> BillingAccount {
        if !self.accounts.contains_key(user_id) {
            return self.create_account(user_id, plan_type);
        }
        let account = self.accounts.get_mut(user_id).unwrap();
        account.plan = BillingManager::plans()
            .get(&plan_type)
            .unwrap_or(&account.plan)
            .clone();
        account.trial_end = None;
        account.clone()
    }

    pub fn reset_monthly_usage(&mut self, user_id: &str) {
        if let Some(account) = self.accounts.get_mut(user_id) {
            account.used_this_month = 0.0;
            account.input_tokens_used = 0;
            account.output_tokens_used = 0;
        }
    }
}

static BILLING_MANAGER: OnceLock<Mutex<BillingManager>> = OnceLock::new();

pub fn billing_manager() -> &'static Mutex<BillingManager> {
    BILLING_MANAGER.get_or_init(|| Mutex::new(BillingManager::new()))
}
