"""Tests for cost_local module — no mocks, real objects and file system."""

import json
from pathlib import Path

import pytest

from apex.cost_local import (
    ModelPricing,
    MODEL_PRICING,
    CostTracker,
    LocalExecutionManager,
    ZenIntegration,
    cost_tracker,
    local_manager,
    zen_integration,
)


# ---------------------------------------------------------------------------
# ModelPricing dataclass
# ---------------------------------------------------------------------------


class TestModelPricing:
    def test_init_default_currency(self):
        pricing = ModelPricing(per_1k_input=0.001, per_1k_output=0.002)
        assert pricing.per_1k_input == 0.001
        assert pricing.per_1k_output == 0.002
        assert pricing.currency == "USD"

    def test_init_custom_currency(self):
        pricing = ModelPricing(per_1k_input=0.001, per_1k_output=0.002, currency="EUR")
        assert pricing.currency == "EUR"


# ---------------------------------------------------------------------------
# MODEL_PRICING dictionary
# ---------------------------------------------------------------------------


class TestModelPricingDict:
    def test_not_empty(self):
        assert len(MODEL_PRICING) > 0

    def test_has_gpt4o(self):
        assert "gpt-4o" in MODEL_PRICING
        assert MODEL_PRICING["gpt-4o"].per_1k_input > 0

    def test_has_gpt4o_mini(self):
        assert "gpt-4o-mini" in MODEL_PRICING

    def test_has_claude(self):
        assert "claude-4-sonnet" in MODEL_PRICING
        assert "claude-4-opus" in MODEL_PRICING

    def test_has_gemini(self):
        assert "gemini-1.5-flash" in MODEL_PRICING
        assert "gemini-1.5-pro" in MODEL_PRICING

    def test_has_deepseek(self):
        assert "deepseek-chat" in MODEL_PRICING
        assert "deepseek-r1" in MODEL_PRICING

    def test_all_pricing_positive(self):
        for name, pricing in MODEL_PRICING.items():
            assert pricing.per_1k_input >= 0, f"{name} has negative input price"
            assert pricing.per_1k_output >= 0, f"{name} has negative output price"


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class TestCostTracker:
    @pytest.fixture
    def tracker(self):
        return CostTracker()

    def test_init(self, tracker):
        assert tracker._session_costs == []
        assert tracker._current_input_tokens == 0
        assert tracker._current_output_tokens == 0

    def test_record_usage_gpt4o(self, tracker):
        cost = tracker.record_usage("gpt-4o", 1000, 1000)
        assert cost > 0
        # gpt-4o: 0.005/1k input, 0.015/1k output
        expected = (1000 / 1000) * 0.005 + (1000 / 1000) * 0.015
        assert abs(cost - expected) < 0.0001

    def test_record_usage_gpt4o_mini(self, tracker):
        cost = tracker.record_usage("gpt-4o-mini", 1000, 500)
        assert cost > 0

    def test_record_usage_unknown_model(self, tracker):
        cost = tracker.record_usage("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_record_usage_updates_tokens(self, tracker):
        tracker.record_usage("gpt-4o", 1000, 500)
        assert tracker._current_input_tokens == 1000
        assert tracker._current_output_tokens == 500

    def test_record_usage_accumulates_tokens(self, tracker):
        tracker.record_usage("gpt-4o", 100, 50)
        tracker.record_usage("gpt-4o", 200, 100)
        assert tracker._current_input_tokens == 300
        assert tracker._current_output_tokens == 150

    def test_get_session_cost(self, tracker):
        tracker.record_usage("gpt-4o-mini", 1000, 500)
        cost_info = tracker.get_session_cost()
        assert "input_tokens" in cost_info
        assert "output_tokens" in cost_info
        assert "total_tokens" in cost_info
        assert "total_cost" in cost_info
        assert "input_cost" in cost_info
        assert "output_cost" in cost_info
        assert "currency" in cost_info
        assert "session_duration" in cost_info
        assert cost_info["input_tokens"] == 1000
        assert cost_info["output_tokens"] == 500
        assert cost_info["total_tokens"] == 1500
        assert cost_info["currency"] == "USD"

    def test_get_session_cost_no_usage(self, tracker):
        cost_info = tracker.get_session_cost()
        assert cost_info["input_tokens"] == 0
        assert cost_info["total_cost"] == 0.0

    def test_reset_session(self, tracker):
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()
        assert len(tracker._session_costs) == 1
        assert tracker._current_input_tokens == 0
        assert tracker._current_output_tokens == 0

    def test_reset_session_preserves_history(self, tracker):
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()
        assert tracker._session_costs[0]["input_tokens"] == 1000

    def test_get_history_empty(self, tracker):
        history = tracker.get_history()
        assert history == []

    def test_get_history_with_data(self, tracker):
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()
        history = tracker.get_history()
        assert len(history) == 1
        assert "timestamp" in history[0]

    def test_get_history_returns_copy(self, tracker):
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()
        history = tracker.get_history()
        history.append({"extra": True})
        assert len(tracker._session_costs) == 1


# ---------------------------------------------------------------------------
# LocalExecutionManager
# ---------------------------------------------------------------------------


class TestLocalExecutionManager:
    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        """Create manager using temp directory as home."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        return LocalExecutionManager()

    def test_init(self, manager):
        assert "enabled" in manager._config
        assert "provider" in manager._config

    def test_is_enabled_default(self, manager):
        assert manager.is_enabled() is False

    def test_enable_local(self, manager):
        manager.enable_local(provider="ollama", model="llama3")
        assert manager.is_enabled() is True
        assert manager._config["provider"] == "ollama"
        assert manager._config["model"] == "llama3"

    def test_disable_local(self, manager):
        manager.enable_local()
        manager.disable_local()
        assert manager.is_enabled() is False

    def test_get_provider_config(self, manager):
        config = manager.get_provider_config()
        assert "enabled" in config
        assert "provider" in config
        assert "model" in config

    def test_get_provider_config_returns_copy(self, manager):
        config = manager.get_provider_config()
        config["extra"] = True
        assert "extra" not in manager._config

    def test_local_providers(self, manager):
        providers = manager.LOCAL_PROVIDERS
        assert "ollama" in providers
        assert "lm_studio" in providers
        assert "llamafile" in providers

    def test_check_provider_available_unknown(self, manager):
        """Unknown provider returns False."""
        result = manager.check_provider_available("nonexistent_provider")
        assert result is False

    def test_check_provider_available_no_url(self, manager):
        """Provider with no URL returns False."""
        manager.LOCAL_PROVIDERS["test_no_url"] = {"url": "", "models": [], "enabled": False}
        result = manager.check_provider_available("test_no_url")
        assert result is False

    def test_check_provider_available_real(self, manager):
        """Check with real urllib — localhost typically not running."""
        result = manager.check_provider_available("ollama")
        # This will return False unless ollama is actually running
        assert isinstance(result, bool)

    def test_get_available_providers(self, manager):
        """Returns dict of available providers (likely empty)."""
        result = manager.get_available_providers()
        assert isinstance(result, dict)

    def test_enable_local_saves_config(self, manager, tmp_path, monkeypatch):
        """enable_local persists to disk."""
        manager.enable_local(provider="lm_studio", model="codellama")
        # Config file should exist
        config_file = tmp_path / ".apex" / "local_config.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["enabled"] is True
        assert data["provider"] == "lm_studio"

    def test_disable_local_saves_config(self, manager, tmp_path, monkeypatch):
        """disable_local persists to disk."""
        manager.enable_local()
        manager.disable_local()
        config_file = tmp_path / ".apex" / "local_config.json"
        data = json.loads(config_file.read_text())
        assert data["enabled"] is False

    def test_load_config_corrupt_json(self, tmp_path, monkeypatch):
        """Load config with corrupt JSON falls back to defaults."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        config_dir = tmp_path / ".apex"
        config_dir.mkdir()
        config_file = config_dir / "local_config.json"
        config_file.write_text("{invalid json")
        mgr = LocalExecutionManager()
        assert mgr._config["enabled"] is False

    def test_load_config_no_file(self, tmp_path, monkeypatch):
        """Load config with no file falls back to defaults."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        mgr = LocalExecutionManager()
        assert mgr._config["enabled"] is False
        assert mgr._config["provider"] == "ollama"
        assert mgr._config["fallback_to_api"] is True


# ---------------------------------------------------------------------------
# ZenIntegration
# ---------------------------------------------------------------------------


class TestZenIntegration:
    def test_init_no_api_key(self):
        zen = ZenIntegration(api_key="")
        assert zen.is_enabled() is False

    def test_init_with_api_key(self):
        zen = ZenIntegration(api_key="test_key_123")
        assert zen.is_enabled() is True

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("ZEN_API_KEY", "env_key")
        zen = ZenIntegration()
        assert zen.is_enabled() is True

    def test_init_no_env(self, monkeypatch):
        monkeypatch.delenv("ZEN_API_KEY", raising=False)
        zen = ZenIntegration()
        assert zen.is_enabled() is False

    def test_estimate_cost_known_model(self):
        zen = ZenIntegration()
        result = zen.estimate_cost("gpt-4o", 1000, 1000)
        assert "model" in result
        assert "estimated_cost" in result
        assert result["model"] == "gpt-4o"
        assert result["estimated_cost"] > 0
        assert result["currency"] == "USD"
        assert result["provider"] == "zen"

    def test_estimate_cost_unknown_model(self):
        zen = ZenIntegration()
        result = zen.estimate_cost("unknown-model", 1000, 1000)
        assert result["estimated_cost"] == 0.0

    def test_estimate_cost_zero_tokens(self):
        zen = ZenIntegration()
        result = zen.estimate_cost("gpt-4o", 0, 0)
        assert result["estimated_cost"] == 0.0

    def test_create_session_disabled(self):
        zen = ZenIntegration(api_key="")
        session_id = zen.create_session(budget=10.0)
        assert session_id == ""

    def test_create_session_enabled(self):
        zen = ZenIntegration(api_key="test")
        session_id = zen.create_session(budget=10.0)
        assert session_id.startswith("zen_session_")

    def test_get_usage_report(self):
        zen = ZenIntegration()
        report = zen.get_usage_report()
        assert "total_spent" in report
        assert "total_tokens" in report
        assert "sessions" in report


# ---------------------------------------------------------------------------
# Global instances
# ---------------------------------------------------------------------------


class TestGlobalInstances:
    def test_cost_tracker_global(self):
        assert cost_tracker is not None
        assert isinstance(cost_tracker, CostTracker)

    def test_local_manager_global(self):
        assert local_manager is not None
        assert isinstance(local_manager, LocalExecutionManager)

    def test_zen_integration_global(self):
        assert zen_integration is not None
        assert isinstance(zen_integration, ZenIntegration)
