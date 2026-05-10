"""Tests for billing module."""

import pytest
from apex.billing import (
    BillingManager,
    BillingAccount,
    BillingPlan,
    CostConfig,
    UsageRecord,
    InsufficientBalanceError,
    TrialExpiredError,
    QuotaExceededError,
    calculate_cost,
    PlanType,
)


class TestBillingManager:
    """Test BillingManager class."""

    def test_init(self):
        manager = BillingManager()
        assert manager is not None


class TestCostConfig:
    """Test CostConfig dataclass."""

    def test_cost_config_creation(self):
        config = CostConfig(
            input_cost_per_1k=1.0,
            output_cost_per_1k=2.0,
        )
        assert config.input_cost_per_1k == 1.0
        assert config.output_cost_per_1k == 2.0

    def test_cost_config_defaults(self):
        config = CostConfig()
        assert config.input_cost_per_1k == 0.0
        assert config.output_cost_per_1k == 0.0


class TestBillingPlan:
    """Test BillingPlan dataclass."""

    def test_billing_plan_creation(self):
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


class TestBillingAccount:
    """Test BillingAccount dataclass."""

    def test_billing_account_creation(self):
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
        account = BillingAccount(
            user_id="user-1",
            plan=plan,
        )
        assert account.user_id == "user-1"


class TestUsageRecord:
    """Test UsageRecord dataclass."""

    def test_usage_record_creation(self):
        record = UsageRecord(
            timestamp=1704067200.0,
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost=0.03,
        )
        assert record.model == "gpt-4o"
        assert record.cost == 0.03


class TestBillingExceptions:
    """Test billing exceptions."""

    def test_insufficient_balance_error(self):
        with pytest.raises(InsufficientBalanceError):
            raise InsufficientBalanceError("Insufficient balance")

    def test_trial_expired_error(self):
        with pytest.raises(TrialExpiredError):
            raise TrialExpiredError("Trial expired")

    def test_quota_exceeded_error(self):
        with pytest.raises(QuotaExceededError):
            raise QuotaExceededError("Quota exceeded")


class TestCalculateCost:
    """Test cost calculation function."""

    def test_calculate_basic(self):
        cost = calculate_cost(model="gpt-4o", input_tokens=100, output_tokens=50)
        assert cost >= 0

    def test_calculate_with_cache(self):
        cost = calculate_cost(
            model="gpt-4o", input_tokens=100, output_tokens=50, use_cache=True, cache_tokens=20
        )
        assert cost >= 0

    def test_calculate_with_various_models(self):
        for model in ["gpt-4o", "claude-3-sonnet", "gemini-2.0-flash"]:
            cost = calculate_cost(model=model, input_tokens=100, output_tokens=100)
            assert cost >= 0


class TestPlanType:
    """Test PlanType enum."""

    def test_plan_type_values(self):
        assert PlanType.FREE is not None
        assert PlanType.PRO is not None
        assert PlanType.ENTERPRISE is not None
