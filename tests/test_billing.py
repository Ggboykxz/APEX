"""Tests for billing.py module."""

import pytest
import time
from apex.billing import (
    BillingManager,
    BillingAccount,
    BillingPlan,
    UsageRecord,
    CostConfig,
    PlanType,
    InsufficientBalanceError,
    TrialExpiredError,
    QuotaExceededError,
    billing_manager,
    calculate_cost,
)


class TestExceptions:
    """Test exception classes."""

    def test_insufficient_balance(self):
        exc = InsufficientBalanceError("Not enough balance")
        assert "Not enough balance" in str(exc)

    def test_trial_expired(self):
        exc = TrialExpiredError("Trial expired")
        assert "Trial expired" in str(exc)

    def test_quota_exceeded(self):
        exc = QuotaExceededError("Quota exceeded")
        assert "Quota exceeded" in str(exc)


class TestPlanType:
    """Test PlanType enum."""

    def test_values(self):
        assert PlanType.FREE.value == "free"
        assert PlanType.PRO.value == "pro"
        assert PlanType.ENTERPRISE.value == "enterprise"
        assert PlanType.CUSTOM.value == "custom"


class TestCostConfig:
    """Test CostConfig dataclass."""

    def test_default_values(self):
        config = CostConfig()
        assert config.input_cost_per_1k == 0.0
        assert config.output_cost_per_1k == 0.0

    def test_with_costs(self):
        config = CostConfig(
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002
        )
        assert config.input_cost_per_1k == 0.001


class TestBillingPlan:
    """Test BillingPlan dataclass."""

    def test_free_plan(self):
        plan = BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=5,
            rate_limit_per_hour=50,
            rate_limit_per_day=200
        )
        assert plan.plan_type == PlanType.FREE
        assert plan.trial_days == 0

    def test_pro_plan(self):
        plan = BillingPlan(
            plan_type=PlanType.PRO,
            name="Pro",
            monthly_limit=20.0,
            input_limit=10000000,
            output_limit=5000000,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            enabled_features=["advanced_tools"],
            trial_days=7,
            overage_allowed=True
        )
        assert plan.overage_allowed is True
        assert len(plan.enabled_features) > 0


class TestUsageRecord:
    """Test UsageRecord dataclass."""

    def test_creation(self):
        record = UsageRecord(
            timestamp=time.time(),
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost=0.0125
        )
        assert record.model == "gpt-4o"
        assert record.cost == 0.0125

    def test_with_session(self):
        record = UsageRecord(
            timestamp=time.time(),
            model="claude-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost=0.005,
            session_id="session_123",
            workspace_id="ws_123"
        )
        assert record.session_id == "session_123"


class TestBillingAccount:
    """Test BillingAccount dataclass."""

    def test_creation(self):
        plan = BillingPlan(
            plan_type=PlanType.FREE,
            name="Free",
            monthly_limit=0.0,
            input_limit=100000,
            output_limit=50000,
            rate_limit_per_minute=5,
            rate_limit_per_hour=50,
            rate_limit_per_day=200
        )
        account = BillingAccount(
            user_id="user_123",
            plan=plan
        )
        assert account.user_id == "user_123"
        assert account.balance == 0.0
        assert account.is_active is True


class TestBillingManager:
    """Test BillingManager class."""

    @pytest.fixture
    def manager(self):
        return BillingManager()

    def test_create_account_free(self, manager):
        account = manager.create_account("user_123", PlanType.FREE)
        assert account.user_id == "user_123"
        assert account.plan.plan_type == PlanType.FREE

    def test_create_account_pro(self, manager):
        account = manager.create_account("user_123", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO
        assert account.trial_end is not None

    def test_create_account_enterprise(self, manager):
        account = manager.create_account("user_123", PlanType.ENTERPRISE)
        assert account.plan.plan_type == PlanType.ENTERPRISE
        assert account.trial_end is not None

    def test_get_account(self, manager):
        manager.create_account("user_123")
        account = manager.get_account("user_123")
        assert account is not None
        assert account.user_id == "user_123"

    def test_get_account_not_found(self, manager):
        account = manager.get_account("nonexistent")
        assert account is None

    def test_calculate_cost_gpt4o(self, manager):
        cost = manager.calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_calculate_cost_claude(self, manager):
        cost = manager.calculate_cost("claude-sonnet", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_calculate_cost_free_model(self, manager):
        cost = manager.calculate_cost("ollama", input_tokens=1000, output_tokens=500)
        assert cost == 0.0

    def test_calculate_cost_with_cache(self, manager):
        cost = manager.calculate_cost(
            "gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            use_cache=True,
            cache_tokens=500
        )
        assert cost > 0

    def test_check_quota_allowed(self, manager):
        manager.create_account("user_123", PlanType.PRO)
        can_proceed, msg = manager.check_quota(
            "user_123",
            "gpt-4o",
            input_tokens=1000,
            output_tokens=500
        )
        assert can_proceed is True

    def test_check_quota_creates_account(self, manager):
        can_proceed, msg = manager.check_quota(
            "new_user",
            "gpt-4o",
            input_tokens=100,
            output_tokens=50
        )
        assert can_proceed is True
        assert manager.get_account("new_user") is not None

    def test_check_quota_inactive_account(self, manager):
        account = manager.create_account("user_123")
        account.is_active = False
        can_proceed, msg = manager.check_quota("user_123", "gpt-4o", 100, 50)
        assert can_proceed is False

    def test_check_quota_trial_expired(self, manager):
        account = manager.create_account("user_123", PlanType.PRO)
        account.trial_end = time.time() - 1
        with pytest.raises(TrialExpiredError):
            manager.check_quota("user_123", "gpt-4o", 100, 50)

    def test_record_usage(self, manager):
        manager.create_account("user_123")
        record = manager.record_usage(
            user_id="user_123",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500
        )
        assert record.cost > 0
        account = manager.get_account("user_123")
        assert account.used_this_month > 0

    def test_record_usage_with_session(self, manager):
        manager.create_account("user_123")
        record = manager.record_usage(
            user_id="user_123",
            model="claude-sonnet",
            input_tokens=1000,
            output_tokens=500,
            session_id="session_123",
            workspace_id="ws_123"
        )
        assert record.session_id == "session_123"

    def test_get_usage_history(self, manager):
        manager.create_account("user_123")
        manager.record_usage("user_123", "gpt-4o", 100, 50)
        manager.record_usage("user_123", "claude-sonnet", 200, 100)
        history = manager.get_usage_history("user_123")
        assert len(history) == 2

    def test_get_usage_history_limit(self, manager):
        manager.create_account("user_123")
        for _ in range(10):
            manager.record_usage("user_123", "gpt-4o", 100, 50)
        history = manager.get_usage_history("user_123", limit=5)
        assert len(history) == 5

    def test_get_usage_summary(self, manager):
        manager.create_account("user_123", PlanType.PRO)
        manager.record_usage("user_123", "gpt-4o", 1000, 500)
        summary = manager.get_usage_summary("user_123")
        assert summary["user_id"] == "user_123"
        assert summary["plan"] == "Pro"
        assert summary["total_requests"] == 1

    def test_update_plan(self, manager):
        manager.create_account("user_123", PlanType.FREE)
        account = manager.update_plan("user_123", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO

    def test_update_plan_creates_if_not_exists(self, manager):
        account = manager.update_plan("new_user", PlanType.PRO)
        assert account.plan.plan_type == PlanType.PRO

    def test_reset_monthly_usage(self, manager):
        manager.create_account("user_123")
        manager.record_usage("user_123", "gpt-4o", 1000, 500)
        manager.reset_monthly_usage("user_123")
        account = manager.get_account("user_123")
        assert account.used_this_month == 0.0
        assert account.input_tokens_used == 0


class TestCalculateCost:
    """Test calculate_cost function."""

    def test_basic_cost(self):
        cost = calculate_cost("gpt-4o", 1000, 500)
        assert cost > 0

    def test_zero_tokens(self):
        cost = calculate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_with_cache(self):
        cost = calculate_cost("gpt-4o", 1000, 500, use_cache=True, cache_tokens=100)
        assert cost > 0


class TestGlobalBillingManager:
    """Test global billing_manager instance."""

    def test_exists(self):
        assert billing_manager is not None
        assert isinstance(billing_manager, BillingManager)