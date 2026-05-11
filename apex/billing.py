"""Billing and trial system for APEX."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    pass


class TrialExpiredError(Exception):
    pass


class QuotaExceededError(Exception):
    pass


class PlanType(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class CostConfig:
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    input_cost_per_1k_vision: float = 0.0
    cache_read_cost_per_1m: float = 0.0
    store_cost_per_1k: float = 0.0


MODEL_COSTS = {
    # ── Anthropic ──
    "claude_opus_4_7": CostConfig(0.005, 0.025),
    "claude_sonnet_4_6": CostConfig(0.003, 0.015),
    "claude_opus_4_5": CostConfig(0.005, 0.025),
    "claude_sonnet_4_5": CostConfig(0.003, 0.015),
    "claude_haiku_4_5": CostConfig(0.001, 0.005),
    "claude_3_5_haiku": CostConfig(0.0008, 0.004),
    "claude_3_5_sonnet": CostConfig(0.003, 0.015),
    # ── OpenAI ──
    "gpt_5": CostConfig(0.00125, 0.01),
    "gpt_5_mini": CostConfig(0.00025, 0.002),
    "gpt_5_nano": CostConfig(0.00005, 0.0004),
    "gpt_4o": CostConfig(0.0025, 0.01),
    "gpt_4o_mini": CostConfig(0.00015, 0.0006),
    "gpt_4_1": CostConfig(0.002, 0.008),
    "gpt_4_1_mini": CostConfig(0.0004, 0.0016),
    "o3": CostConfig(0.002, 0.008),
    "o3_mini": CostConfig(0.0011, 0.0044),
    "o4_mini": CostConfig(0.0011, 0.0044),
    # ── Google ──
    "gemini_2_5_pro": CostConfig(0.00125, 0.01),
    "gemini_2_5_flash": CostConfig(0.0003, 0.0025),
    "gemini_3_pro": CostConfig(0.002, 0.012),
    "gemini_3_flash": CostConfig(0.0005, 0.003),
    "gemini_2_0_flash": CostConfig(0.0001, 0.0004),
    # ── xAI ──
    "grok_4": CostConfig(0.003, 0.015),
    "grok_4_fast": CostConfig(0.0002, 0.0005),
    "grok_3": CostConfig(0.003, 0.015),
    "grok_3_mini": CostConfig(0.0003, 0.0005),
    # ── DeepSeek ──
    "deepseek_chat": CostConfig(0.00014, 0.00028),
    "deepseek_reasoner": CostConfig(0.00014, 0.00028),
    "deepseek_v4_flash": CostConfig(0.00014, 0.00028),
    "deepseek_v4_pro": CostConfig(0.00174, 0.00348),
    # ── Mistral ──
    "mistral_large_latest": CostConfig(0.0005, 0.0015),
    "mistral_medium_latest": CostConfig(0.002, 0.0075),
    "mistral_small_latest": CostConfig(0.00015, 0.0006),
    "codestral": CostConfig(0.0003, 0.0009),
    # ── Alibaba ──
    "qwen3_coder_plus": CostConfig(0.001, 0.005),
    "qwen_plus": CostConfig(0.0004, 0.0012),
    # ── Cohere ──
    "command_a": CostConfig(0.0025, 0.01),
    "command_r": CostConfig(0.00015, 0.0006),
    # ── Groq ──
    "llama_groq_3_3_70b": CostConfig(0.00059, 0.00079),
    # ── Ollama (free) ──
    "ollama": CostConfig(0.0, 0.0),
    # ── Backward-compatible aliases ──
    "claude_opus": CostConfig(0.005, 0.025),  # alias → claude_opus_4_5
    "claude_sonnet": CostConfig(0.003, 0.015),  # alias → claude_sonnet_4_5
    "claude_haiku": CostConfig(0.001, 0.005),  # alias → claude_haiku_4_5
    "gpt_4_turbo": CostConfig(0.01, 0.03),  # legacy
    "gemini_2": CostConfig(0.0, 0.0),  # legacy free tier
    "gemini_flash": CostConfig(0.0, 0.0),  # legacy free tier
    "deepseek_coder": CostConfig(0.00014, 0.00028),  # alias → deepseek_chat
    "llama_3": CostConfig(0.0, 0.0),  # legacy free
}


@dataclass
class UsageRecord:
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None


@dataclass
class BillingPlan:
    plan_type: PlanType
    name: str
    monthly_limit: float
    input_limit: int
    output_limit: int
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    enabled_features: list[str] = field(default_factory=list)
    trial_days: int = 0
    overage_allowed: bool = False
    overage_multiplier: float = 1.5


@dataclass
class BillingAccount:
    user_id: str
    plan: BillingPlan
    balance: float = 0.0
    used_this_month: float = 0.0
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    trial_end: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    is_active: bool = True
    metadata: dict = field(default_factory=dict)


class BillingManager:
    PLANS = {
        PlanType.FREE: BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=5,
            rate_limit_per_hour=50,
            rate_limit_per_day=200,
            trial_days=0,
        ),
        PlanType.PRO: BillingPlan(
            plan_type=PlanType.PRO,
            name="Pro",
            monthly_limit=20.0,
            input_limit=10000000,
            output_limit=5000000,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            enabled_features=["advanced_tools", "priority_support", "custom_models"],
            trial_days=7,
            overage_allowed=True,
        ),
        PlanType.ENTERPRISE: BillingPlan(
            plan_type=PlanType.ENTERPRISE,
            name="Enterprise",
            monthly_limit=100.0,
            input_limit=-1,
            output_limit=-1,
            rate_limit_per_minute=300,
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000,
            enabled_features=[
                "advanced_tools",
                "priority_support",
                "custom_models",
                "sso",
                "audit_logs",
            ],
            trial_days=14,
            overage_allowed=True,
        ),
    }

    def __init__(self):
        self._accounts: dict[str, BillingAccount] = {}
        self._usage_history: dict[str, list[UsageRecord]] = {}
        self._default_plan = self.PLANS[PlanType.FREE]

    def create_account(self, user_id: str, plan_type: PlanType = PlanType.FREE) -> BillingAccount:
        plan = self.PLANS.get(plan_type, self._default_plan)
        trial_end = None
        if plan.trial_days > 0:
            trial_end = time.time() + (plan.trial_days * 86400)
        account = BillingAccount(
            user_id=user_id,
            plan=plan,
            trial_end=trial_end,
        )
        self._accounts[user_id] = account
        self._usage_history[user_id] = []
        logger.info(f"Created billing account for user {user_id} with plan {plan.name}")
        return account

    def get_account(self, user_id: str) -> Optional[BillingAccount]:
        return self._accounts.get(user_id)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        use_cache: bool = False,
        cache_tokens: int = 0,
    ) -> float:
        model_key = model.lower().replace("-", "_").replace(" ", "_")
        cost_config = MODEL_COSTS.get(model_key, MODEL_COSTS.get("claude_sonnet"))
        input_cost = (input_tokens / 1000) * cost_config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * cost_config.output_cost_per_1k
        if use_cache and cache_tokens > 0:
            input_cost += (cache_tokens / 1000) * cost_config.cache_read_cost_per_1m
        return round(input_cost + output_cost, 6)

    def check_quota(
        self, user_id: str, model: str, input_tokens: int, output_tokens: int
    ) -> tuple[bool, str]:
        account = self._accounts.get(user_id)
        if not account:
            account = self.create_account(user_id)
        if not account.is_active:
            return False, "Account is not active"
        if account.trial_end and time.time() > account.trial_end:
            raise TrialExpiredError("Trial period has expired")
        if account.plan.monthly_limit > 0:
            projected_cost = self.calculate_cost(model, input_tokens, output_tokens)
            if account.used_this_month + projected_cost > account.plan.monthly_limit:
                if account.plan.overage_allowed:
                    logger.warning(f"User {user_id} exceeding monthly limit, applying overage")
                else:
                    raise QuotaExceededError(
                        f"Monthly limit of ${account.plan.monthly_limit} exceeded"
                    )
        if account.plan.input_limit > 0:
            if account.input_tokens_used + input_tokens > account.plan.input_limit:
                return False, f"Input token limit exceeded ({account.plan.input_limit})"
        if account.plan.output_limit > 0:
            if account.output_tokens_used + output_tokens > account.plan.output_limit:
                return False, f"Output token limit exceeded ({account.plan.output_limit})"
        return True, "OK"

    def record_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> UsageRecord:
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        record = UsageRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            session_id=session_id,
            workspace_id=workspace_id,
        )
        if user_id not in self._usage_history:
            self._usage_history[user_id] = []
        self._usage_history[user_id].append(record)
        account = self._accounts.get(user_id)
        if account:
            account.used_this_month += cost
            account.input_tokens_used += input_tokens
            account.output_tokens_used += output_tokens
        return record

    def get_usage_history(self, user_id: str, limit: int = 100) -> list[UsageRecord]:
        history = self._usage_history.get(user_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_usage_summary(self, user_id: str) -> dict:
        account = self._accounts.get(user_id)
        history = self._usage_history.get(user_id, [])
        total_cost = sum(r.cost for r in history)
        total_input = sum(r.input_tokens for r in history)
        total_output = sum(r.output_tokens for r in history)
        return {
            "user_id": user_id,
            "plan": account.plan.name if account else "Unknown",
            "balance": account.balance if account else 0.0,
            "used_this_month": account.used_this_month if account else 0.0,
            "input_tokens_used": account.input_tokens_used if account else 0,
            "output_tokens_used": account.output_tokens_used if account else 0,
            "total_cost": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_requests": len(history),
        }

    def update_plan(self, user_id: str, plan_type: PlanType) -> BillingAccount:
        if user_id not in self._accounts:
            return self.create_account(user_id, plan_type)
        account = self._accounts[user_id]
        old_plan = account.plan
        account.plan = self.PLANS[plan_type]
        account.trial_end = None
        logger.info(f"Updated user {user_id} from {old_plan.name} to {account.plan.name}")
        return account

    def reset_monthly_usage(self, user_id: str) -> None:
        if user_id in self._accounts:
            self._accounts[user_id].used_this_month = 0.0
            self._accounts[user_id].input_tokens_used = 0
            self._accounts[user_id].output_tokens_used = 0
            logger.info(f"Reset monthly usage for user {user_id}")


billing_manager = BillingManager()


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    use_cache: bool = False,
    cache_tokens: int = 0,
) -> float:
    return billing_manager.calculate_cost(
        model, input_tokens, output_tokens, use_cache, cache_tokens
    )
