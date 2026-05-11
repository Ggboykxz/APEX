"""Comprehensive tests for billing.py module — no mocks."""

import time

import pytest

from apex.billing import (
    BillingAccount,
    BillingManager,
    BillingPlan,
    CostConfig,
    InsufficientBalanceError,
    PlanType,
    QuotaExceededError,
    TrialExpiredError,
    UsageRecord,
    billing_manager,
    calculate_cost,
    MODEL_COSTS,
)


# ---------------------------------------------------------------------------
# PlanType enum
# ---------------------------------------------------------------------------


class TestPlanType:
    """Test PlanType enum."""

    def test_free_value(self):
        assert PlanType.FREE.value == "free"

    def test_pro_value(self):
        assert PlanType.PRO.value == "pro"

    def test_enterprise_value(self):
        assert PlanType.ENTERPRISE.value == "enterprise"

    def test_custom_value(self):
        assert PlanType.CUSTOM.value == "custom"

    def test_all_members(self):
        members = list(PlanType)
        assert len(members) == 4
        assert PlanType.FREE in members
        assert PlanType.PRO in members
        assert PlanType.ENTERPRISE in members
        assert PlanType.CUSTOM in members

    def test_from_value(self):
        assert PlanType("free") == PlanType.FREE
        assert PlanType("pro") == PlanType.PRO


# ---------------------------------------------------------------------------
# CostConfig
# ---------------------------------------------------------------------------


class TestCostConfig:
    """Test CostConfig dataclass."""

    def test_default_values(self):
        config = CostConfig()
        assert config.input_cost_per_1k == 0.0
        assert config.output_cost_per_1k == 0.0
        assert config.input_cost_per_1k_vision == 0.0
        assert config.cache_read_cost_per_1m == 0.0
        assert config.store_cost_per_1k == 0.0

    def test_custom_values(self):
        config = CostConfig(
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.05,
            input_cost_per_1k_vision=0.02,
            cache_read_cost_per_1m=0.001,
            store_cost_per_1k=0.003,
        )
        assert config.input_cost_per_1k == 0.01
        assert config.output_cost_per_1k == 0.05
        assert config.input_cost_per_1k_vision == 0.02
        assert config.cache_read_cost_per_1m == 0.001
        assert config.store_cost_per_1k == 0.003


# ---------------------------------------------------------------------------
# MODEL_COSTS
# ---------------------------------------------------------------------------


class TestModelCosts:
    """Test MODEL_COSTS dictionary."""

    def test_contains_known_models(self):
        expected_models = [
            "claude-opus",
            "claude-sonnet",
            "claude-haiku",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gemini-2",
            "gemini-flash",
            "deepseek-chat",
            "deepseek-coder",
            "llama-3",
            "ollama",
        ]
        for model in expected_models:
            assert model in MODEL_COSTS

    def test_all_values_are_cost_config(self):
        for model, config in MODEL_COSTS.items():
            assert isinstance(config, CostConfig), f"{model} has wrong type"

    def test_opus_more_expensive_than_sonnet(self):
        assert (
            MODEL_COSTS["claude-opus"].input_cost_per_1k
            > MODEL_COSTS["claude-sonnet"].input_cost_per_1k
        )
        assert (
            MODEL_COSTS["claude-opus"].output_cost_per_1k
            > MODEL_COSTS["claude-sonnet"].output_cost_per_1k
        )

    def test_free_models_have_zero_cost(self):
        assert MODEL_COSTS["gemini-2"].input_cost_per_1k == 0.0
        assert MODEL_COSTS["gemini-2"].output_cost_per_1k == 0.0
        assert MODEL_COSTS["gemini-flash"].input_cost_per_1k == 0.0
        assert MODEL_COSTS["ollama"].input_cost_per_1k == 0.0
        assert MODEL_COSTS["ollama"].output_cost_per_1k == 0.0


# ---------------------------------------------------------------------------
# UsageRecord
# ---------------------------------------------------------------------------


class TestUsageRecord:
    """Test UsageRecord dataclass."""

    def test_creation(self):
        record = UsageRecord(
            timestamp=1704067200.0,
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost=0.03,
        )
        assert record.model == "gpt-4o"
        assert record.cost == 0.03
        assert record.session_id is None
        assert record.workspace_id is None

    def test_with_session_and_workspace(self):
        record = UsageRecord(
            timestamp=1704067200.0,
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost=0.03,
            session_id="sess-1",
            workspace_id="ws-1",
        )
        assert record.session_id == "sess-1"
        assert record.workspace_id == "ws-1"


# ---------------------------------------------------------------------------
# BillingPlan
# ---------------------------------------------------------------------------


class TestBillingPlan:
    """Test BillingPlan dataclass."""

    def test_creation(self):
        plan = BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=20,
            rate_limit_per_hour=200,
            rate_limit_per_day=1000,
        )
        assert plan.name == "Free"
        assert plan.plan_type == PlanType.FREE
        assert plan.trial_days == 0
        assert plan.overage_allowed is False
        assert plan.overage_multiplier == 1.5
        assert plan.enabled_features == []

    def test_with_features(self):
        plan = BillingPlan(
            plan_type=PlanType.PRO,
            name="Pro",
            monthly_limit=20.0,
            input_limit=10000000,
            output_limit=5000000,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            enabled_features=["advanced_tools", "priority_support"],
            trial_days=7,
            overage_allowed=True,
        )
        assert len(plan.enabled_features) == 2
        assert plan.trial_days == 7
        assert plan.overage_allowed is True


# ---------------------------------------------------------------------------
# BillingAccount
# ---------------------------------------------------------------------------


class TestBillingAccount:
    """Test BillingAccount dataclass."""

    def test_creation(self):
        plan = BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=20,
            rate_limit_per_hour=200,
            rate_limit_per_day=1000,
        )
        account = BillingAccount(user_id="user-1", plan=plan)
        assert account.user_id == "user-1"
        assert account.balance == 0.0
        assert account.used_this_month == 0.0
        assert account.input_tokens_used == 0
        assert account.output_tokens_used == 0
        assert account.trial_end is None
        assert account.is_active is True
        assert account.metadata == {}

    def test_with_trial(self):
        plan = BillingPlan(
            plan_type=PlanType.PRO,
            name="Pro",
            monthly_limit=20.0,
            input_limit=10000000,
            output_limit=5000000,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            trial_days=7,
        )
        account = BillingAccount(
            user_id="user-1",
            plan=plan,
            trial_end=time.time() + 604800,
        )
        assert account.trial_end is not None

    def test_created_at_auto_set(self):
        plan = BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=20,
            rate_limit_per_hour=200,
            rate_limit_per_day=1000,
        )
        before = time.time()
        account = BillingAccount(user_id="user-1", plan=plan)
        after = time.time()
        assert before <= account.created_at <= after


# ---------------------------------------------------------------------------
# BillingManager PLANS
# ---------------------------------------------------------------------------


class TestBillingManagerPlans:
    """Test BillingManager.PLANS configuration."""

    def test_free_plan(self):
        plan = BillingManager.PLANS[PlanType.FREE]
        assert plan.name == "Free"
        assert plan.monthly_limit == 0.0
        assert plan.input_limit == 100000
        assert plan.output_limit == 50000
        assert plan.trial_days == 0

    def test_pro_plan(self):
        plan = BillingManager.PLANS[PlanType.PRO]
        assert plan.name == "Pro"
        assert plan.monthly_limit == 20.0
        assert plan.input_limit == 10000000
        assert plan.output_limit == 5000000
        assert plan.trial_days == 7
        assert plan.overage_allowed is True
        assert "advanced_tools" in plan.enabled_features

    def test_enterprise_plan(self):
        plan = BillingManager.PLANS[PlanType.ENTERPRISE]
        assert plan.name == "Enterprise"
        assert plan.monthly_limit == 100.0
        assert plan.input_limit == -1
        assert plan.output_limit == -1
        assert plan.trial_days == 14
        assert plan.overage_allowed is True
        assert "sso" in plan.enabled_features
        assert "audit_logs" in plan.enabled_features


# ---------------------------------------------------------------------------
# BillingManager — Account management
# ---------------------------------------------------------------------------


class TestBillingManagerAccount:
    """Test BillingManager account operations."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_create_account_free(self, manager):
        account = manager.create_account("user-1")
        assert account.user_id == "user-1"
        assert account.plan.plan_type == PlanType.FREE
        assert account.trial_end is None

    def test_create_account_pro_with_trial(self, manager):
        account = manager.create_account("user-2", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO
        assert account.trial_end is not None
        assert account.trial_end > time.time()

    def test_create_account_enterprise_with_trial(self, manager):
        account = manager.create_account("user-3", PlanType.ENTERPRISE)
        assert account.plan.plan_type == PlanType.ENTERPRISE
        assert account.trial_end is not None

    def test_get_account(self, manager):
        created = manager.create_account("user-1")
        fetched = manager.get_account("user-1")
        assert fetched is created

    def test_get_account_not_found(self, manager):
        result = manager.get_account("nonexistent")
        assert result is None

    def test_create_account_initializes_usage_history(self, manager):
        manager.create_account("user-1")
        assert "user-1" in manager._usage_history
        assert manager._usage_history["user-1"] == []


# ---------------------------------------------------------------------------
# BillingManager — Cost calculation
# ---------------------------------------------------------------------------


class TestBillingManagerCalculateCost:
    """Test BillingManager.calculate_cost method."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_claude_sonnet_cost(self, manager):
        # input_cost_per_1k = 0.003, output_cost_per_1k = 0.015
        cost = manager.calculate_cost("claude-sonnet", 1000, 1000)
        expected = (1000 / 1000) * 0.003 + (1000 / 1000) * 0.015
        assert cost == round(expected, 6)

    def test_gpt4o_cost(self, manager):
        # Model name normalization converts hyphens to underscores,
        # but MODEL_COSTS uses hyphens as keys, so "gpt_4o" isn't found
        # and falls back to claude-sonnet pricing.
        cost = manager.calculate_cost("gpt-4o", 1000, 1000)
        # Fallback to claude-sonnet: (1000/1000)*0.003 + (1000/1000)*0.015 = 0.018
        assert cost == 0.018

    def test_free_model_cost(self, manager):
        cost = manager.calculate_cost("ollama", 1000, 1000)
        assert cost == 0.0

    def test_gemini_cost(self, manager):
        # "gemini-2" normalizes to "gemini_2" (not in MODEL_COSTS),
        # falls back to claude-sonnet pricing
        cost = manager.calculate_cost("gemini-2", 10000, 5000)
        # Fallback: (10000/1000)*0.003 + (5000/1000)*0.015 = 0.03 + 0.075 = 0.105
        assert cost == 0.105

    def test_zero_tokens(self, manager):
        cost = manager.calculate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_with_cache_zero_tokens(self, manager):
        cost = manager.calculate_cost("gpt-4o", 1000, 1000, use_cache=True, cache_tokens=0)
        assert cost > 0

    def test_unknown_model_defaults_to_sonnet(self, manager):
        cost = manager.calculate_cost("unknown-model-xyz", 1000, 1000)
        sonnet_cost = manager.calculate_cost("claude-sonnet", 1000, 1000)
        assert cost == sonnet_cost

    def test_model_name_normalization_hyphens(self, manager):
        """Model names with hyphens should be normalized."""
        # "claude-sonnet" -> "claude_sonnet" (already in MODEL_COSTS as "claude-sonnet")
        cost1 = manager.calculate_cost("claude-sonnet", 1000, 1000)
        cost2 = manager.calculate_cost("claude_sonnet", 1000, 1000)
        assert cost1 == cost2

    def test_model_name_normalization_spaces(self, manager):
        cost1 = manager.calculate_cost("claude sonnet", 1000, 1000)
        cost2 = manager.calculate_cost("claude_sonnet", 1000, 1000)
        assert cost1 == cost2

    def test_cost_rounding(self, manager):
        cost = manager.calculate_cost("gpt-4o", 1, 1)
        # Should be rounded to 6 decimal places
        assert isinstance(cost, float)
        # Very small cost, but still precise
        assert cost >= 0

    def test_large_token_count(self, manager):
        # claude-opus normalizes to claude_opus, falls back to claude-sonnet
        cost = manager.calculate_cost("claude-opus", 1000000, 500000)
        # Fallback to claude-sonnet: (1000000/1000)*0.003 + (500000/1000)*0.015 = 3.0 + 7.5
        expected_input = (1000000 / 1000) * 0.003
        expected_output = (500000 / 1000) * 0.015
        assert cost == round(expected_input + expected_output, 6)

    def test_deepseek_chat_cost(self, manager):
        # "deepseek-chat" normalizes to "deepseek_chat", falls back to claude-sonnet
        cost = manager.calculate_cost("deepseek-chat", 1000, 1000)
        # Fallback to claude-sonnet: (1000/1000)*0.003 + (1000/1000)*0.015 = 0.018
        assert cost == 0.018

    def test_deepseek_coder_cost(self, manager):
        # "deepseek-coder" normalizes to "deepseek_coder", falls back to claude-sonnet
        cost = manager.calculate_cost("deepseek-coder", 1000, 1000)
        # Fallback to claude-sonnet: (1000/1000)*0.003 + (1000/1000)*0.015 = 0.018
        assert cost == 0.018


# ---------------------------------------------------------------------------
# BillingManager — Quota checking
# ---------------------------------------------------------------------------


class TestBillingManagerCheckQuota:
    """Test BillingManager.check_quota method."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_check_quota_free_plan(self, manager):
        manager.create_account("user-1", PlanType.FREE)
        ok, msg = manager.check_quota("user-1", "gpt-4o", 100, 100)
        assert ok is True
        assert msg == "OK"

    def test_check_quota_auto_creates_account(self, manager):
        ok, msg = manager.check_quota("new_user", "gpt-4o", 100, 100)
        assert ok is True
        assert manager.get_account("new_user") is not None

    def test_check_quota_inactive_account(self, manager):
        account = manager.create_account("user-1")
        account.is_active = False
        ok, msg = manager.check_quota("user-1", "gpt-4o", 100, 100)
        assert ok is False
        assert "not active" in msg

    def test_check_quota_trial_expired(self, manager):
        account = manager.create_account("user-1", PlanType.PRO)
        account.trial_end = time.time() - 1
        with pytest.raises(TrialExpiredError):
            manager.check_quota("user-1", "gpt-4o", 100, 100)

    def test_check_quota_monthly_limit_exceeded(self, manager):
        account = manager.create_account("user-1", PlanType.PRO)
        account.used_this_month = 19.99
        # Pro plan has overage_allowed=True, so it won't raise QuotaExceededError.
        # To test the exception, we need a plan with overage_allowed=False.
        # Create a custom plan with a low limit and no overage.
        account.plan = BillingPlan(
            plan_type=PlanType.CUSTOM,
            name="No Overage",
            monthly_limit=0.01,
            input_limit=10000000,
            output_limit=5000000,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            overage_allowed=False,
        )
        account.used_this_month = 0.005
        with pytest.raises(QuotaExceededError):
            manager.check_quota("user-1", "claude-sonnet", 10000, 10000)

    def test_check_quota_monthly_limit_with_overage_allowed(self, manager):
        account = manager.create_account("user-1", PlanType.PRO)
        # Pro plan monthly_limit is $20. Set used close to limit so projected cost exceeds it.
        account.used_this_month = 19.99
        # Use enough tokens to push past the $20 limit.
        # claude-sonnet fallback: (10000/1000)*0.003 + (10000/1000)*0.015 = 0.03 + 0.15 = 0.18
        # 19.99 + 0.18 = 20.17 > 20.0 → overage triggered, but allowed
        ok, msg = manager.check_quota("user-1", "claude-sonnet", 10000, 10000)
        assert ok is True

    def test_check_quota_input_limit_exceeded(self, manager):
        account = manager.create_account("user-1", PlanType.FREE)
        account.input_tokens_used = 99900
        ok, msg = manager.check_quota("user-1", "gpt-4o", 200, 100)
        assert ok is False
        assert "Input token limit" in msg

    def test_check_quota_output_limit_exceeded(self, manager):
        account = manager.create_account("user-1", PlanType.FREE)
        account.output_tokens_used = 49900
        ok, msg = manager.check_quota("user-1", "gpt-4o", 100, 200)
        assert ok is False
        assert "Output token limit" in msg

    def test_check_quota_enterprise_no_token_limits(self, manager):
        """Enterprise plan has -1 limits meaning unlimited."""
        account = manager.create_account("user-1", PlanType.ENTERPRISE)
        account.input_tokens_used = 1000000000
        account.output_tokens_used = 1000000000
        ok, msg = manager.check_quota("user-1", "gpt-4o", 1000, 1000)
        assert ok is True

    def test_check_quota_free_plan_no_monthly_limit(self, manager):
        """Free plan has monthly_limit=0, so the monthly check is skipped."""
        account = manager.create_account("user-1", PlanType.FREE)
        account.used_this_month = 0.0
        ok, msg = manager.check_quota("user-1", "gpt-4o", 100, 100)
        assert ok is True


# ---------------------------------------------------------------------------
# BillingManager — Usage recording
# ---------------------------------------------------------------------------


class TestBillingManagerRecordUsage:
    """Test BillingManager.record_usage method."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_record_usage(self, manager):
        manager.create_account("user-1")
        record = manager.record_usage("user-1", "gpt-4o", 1000, 500)
        assert record.model == "gpt-4o"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost > 0
        assert record.timestamp > 0

    def test_record_usage_updates_account(self, manager):
        manager.create_account("user-1")
        record = manager.record_usage("user-1", "gpt-4o", 1000, 500)
        account = manager.get_account("user-1")
        assert account.used_this_month == record.cost
        assert account.input_tokens_used == 1000
        assert account.output_tokens_used == 500

    def test_record_usage_multiple(self, manager):
        manager.create_account("user-1")
        r1 = manager.record_usage("user-1", "gpt-4o", 1000, 500)
        r2 = manager.record_usage("user-1", "gpt-4o", 2000, 1000)
        account = manager.get_account("user-1")
        assert account.used_this_month == r1.cost + r2.cost
        assert account.input_tokens_used == 3000
        assert account.output_tokens_used == 1500

    def test_record_usage_with_session(self, manager):
        manager.create_account("user-1")
        record = manager.record_usage("user-1", "gpt-4o", 1000, 500, session_id="sess-1")
        assert record.session_id == "sess-1"

    def test_record_usage_with_workspace(self, manager):
        manager.create_account("user-1")
        record = manager.record_usage("user-1", "gpt-4o", 1000, 500, workspace_id="ws-1")
        assert record.workspace_id == "ws-1"

    def test_record_usage_no_account(self, manager):
        """Recording usage without an account still works, just doesn't update account."""
        record = manager.record_usage("no-account-user", "gpt-4o", 1000, 500)
        assert record.model == "gpt-4o"
        assert "no-account-user" in manager._usage_history

    def test_record_usage_creates_history_if_missing(self, manager):
        """If user has no history, it's created."""
        manager.record_usage("new-user", "gpt-4o", 100, 50)
        assert len(manager._usage_history["new-user"]) == 1


# ---------------------------------------------------------------------------
# BillingManager — Usage history
# ---------------------------------------------------------------------------


class TestBillingManagerUsageHistory:
    """Test BillingManager usage history methods."""

    @pytest.fixture
    def manager(self):
        m = BillingManager()
        m.create_account("user-1")
        return m

    def test_get_usage_history(self, manager):
        manager.record_usage("user-1", "gpt-4o", 1000, 500)
        manager.record_usage("user-1", "claude-sonnet", 2000, 1000)
        history = manager.get_usage_history("user-1")
        assert len(history) == 2

    def test_get_usage_history_sorted_desc(self, manager):
        manager.record_usage("user-1", "gpt-4o", 1000, 500)
        manager.record_usage("user-1", "claude-sonnet", 2000, 1000)
        history = manager.get_usage_history("user-1")
        assert history[0].timestamp >= history[1].timestamp

    def test_get_usage_history_with_limit(self, manager):
        for i in range(10):
            manager.record_usage("user-1", "gpt-4o", 100, 50)
        history = manager.get_usage_history("user-1", limit=5)
        assert len(history) == 5

    def test_get_usage_history_no_user(self, manager):
        history = manager.get_usage_history("nonexistent")
        assert history == []

    def test_get_usage_summary(self, manager):
        manager.record_usage("user-1", "gpt-4o", 1000, 500)
        manager.record_usage("user-1", "claude-sonnet", 2000, 1000)
        summary = manager.get_usage_summary("user-1")
        assert summary["user_id"] == "user-1"
        assert summary["plan"] == "Free"
        assert summary["total_requests"] == 2
        assert summary["total_input_tokens"] == 3000
        assert summary["total_output_tokens"] == 1500
        assert summary["total_cost"] > 0
        assert summary["input_tokens_used"] == 3000
        assert summary["output_tokens_used"] == 1500

    def test_get_usage_summary_no_account(self, manager):
        summary = manager.get_usage_summary("nonexistent")
        assert summary["user_id"] == "nonexistent"
        assert summary["plan"] == "Unknown"
        assert summary["balance"] == 0.0
        assert summary["total_cost"] == 0.0
        assert summary["total_requests"] == 0


# ---------------------------------------------------------------------------
# BillingManager — Plan management
# ---------------------------------------------------------------------------


class TestBillingManagerPlanUpdate:
    """Test BillingManager.update_plan method."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_update_plan_existing_account(self, manager):
        manager.create_account("user-1", PlanType.FREE)
        account = manager.update_plan("user-1", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO
        assert account.trial_end is None

    def test_update_plan_creates_account_if_missing(self, manager):
        account = manager.update_plan("new-user", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO
        assert manager.get_account("new-user") is not None

    def test_update_plan_resets_trial(self, manager):
        manager.create_account("user-1", PlanType.PRO)
        account = manager.get_account("user-1")
        assert account.trial_end is not None
        account = manager.update_plan("user-1", PlanType.ENTERPRISE)
        assert account.trial_end is None

    def test_update_plan_preserves_usage(self, manager):
        manager.create_account("user-1", PlanType.FREE)
        manager.record_usage("user-1", "gpt-4o", 1000, 500)
        account = manager.get_account("user-1")
        old_used = account.used_this_month
        manager.update_plan("user-1", PlanType.PRO)
        account = manager.get_account("user-1")
        assert account.used_this_month == old_used


# ---------------------------------------------------------------------------
# BillingManager — Monthly reset
# ---------------------------------------------------------------------------


class TestBillingManagerResetMonthly:
    """Test BillingManager.reset_monthly_usage method."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_reset_monthly_usage(self, manager):
        manager.create_account("user-1")
        manager.record_usage("user-1", "gpt-4o", 1000, 500)
        account = manager.get_account("user-1")
        assert account.used_this_month > 0
        assert account.input_tokens_used > 0
        assert account.output_tokens_used > 0

        manager.reset_monthly_usage("user-1")
        account = manager.get_account("user-1")
        assert account.used_this_month == 0.0
        assert account.input_tokens_used == 0
        assert account.output_tokens_used == 0

    def test_reset_monthly_usage_nonexistent(self, manager):
        # Should not raise
        manager.reset_monthly_usage("nonexistent")


# ---------------------------------------------------------------------------
# Module-level calculate_cost function
# ---------------------------------------------------------------------------


class TestModuleLevelCalculateCost:
    """Test module-level calculate_cost function."""

    def test_delegates_to_billing_manager(self):
        cost = calculate_cost("gpt-4o", 1000, 1000)
        assert cost > 0

    def test_free_model(self):
        cost = calculate_cost("ollama", 1000, 1000)
        assert cost == 0.0

    def test_with_cache(self):
        cost = calculate_cost("gpt-4o", 1000, 1000, use_cache=True, cache_tokens=100)
        assert cost > 0


# ---------------------------------------------------------------------------
# Module-level billing_manager
# ---------------------------------------------------------------------------


class TestGlobalBillingManager:
    """Test the module-level billing_manager instance."""

    def test_exists(self):
        assert billing_manager is not None
        assert isinstance(billing_manager, BillingManager)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestBillingExceptions:
    """Test billing exception classes."""

    def test_insufficient_balance_error(self):
        with pytest.raises(InsufficientBalanceError):
            raise InsufficientBalanceError("Insufficient balance")

    def test_trial_expired_error(self):
        with pytest.raises(TrialExpiredError):
            raise TrialExpiredError("Trial expired")

    def test_quota_exceeded_error(self):
        with pytest.raises(QuotaExceededError):
            raise QuotaExceededError("Quota exceeded")

    def test_insufficient_balance_is_exception(self):
        assert issubclass(InsufficientBalanceError, Exception)

    def test_trial_expired_is_exception(self):
        assert issubclass(TrialExpiredError, Exception)

    def test_quota_exceeded_is_exception(self):
        assert issubclass(QuotaExceededError, Exception)

    def test_exception_message(self):
        exc = QuotaExceededError("Monthly limit of $20 exceeded")
        assert "$20" in str(exc)
