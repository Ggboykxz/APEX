"""Tests for cost_local module."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from apex.cost_local import (
    ModelPricing, MODEL_PRICING, CostTracker, LocalExecutionManager,
    ZenIntegration, cost_tracker, local_manager, zen_integration
)


class TestModelPricing:
    """Test ModelPricing dataclass."""

    def test_init(self):
        """Test initialization."""
        pricing = ModelPricing(per_1k_input=0.001, per_1k_output=0.002)
        assert pricing.per_1k_input == 0.001
        assert pricing.per_1k_output == 0.002
        assert pricing.currency == "USD"


class TestMODELPRICING:
    """Test MODEL_PRICING dictionary."""

    def test_not_empty(self):
        """Test pricing dictionary is not empty."""
        assert len(MODEL_PRICING) > 0

    def test_has_gpt4o(self):
        """Test GPT-4o pricing exists."""
        assert "gpt-4o" in MODEL_PRICING
        assert MODEL_PRICING["gpt-4o"].per_1k_input > 0

    def test_has_claude(self):
        """Test Claude pricing exists."""
        assert "claude-4-sonnet" in MODEL_PRICING

    def test_has_deepseek(self):
        """Test DeepSeek pricing exists."""
        assert "deepseek-chat" in MODEL_PRICING


class TestCostTracker:
    """Test CostTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create CostTracker instance."""
        return CostTracker()

    def test_init(self, tracker):
        """Test initialization."""
        assert tracker._session_costs == []
        assert tracker._current_input_tokens == 0
        assert tracker._current_output_tokens == 0

    def test_record_usage_gpt4o(self, tracker):
        """Test recording GPT-4o usage."""
        cost = tracker.record_usage("gpt-4o", 1000, 1000)
        assert cost > 0

    def test_record_usage_unknown_model(self, tracker):
        """Test recording unknown model usage."""
        cost = tracker.record_usage("unknown-model", 1000, 1000)
        assert cost == 0

    def test_get_session_cost(self, tracker):
        """Test get_session_cost method."""
        tracker.record_usage("gpt-4o-mini", 1000, 500)
        cost_info = tracker.get_session_cost()

        assert "input_tokens" in cost_info
        assert "output_tokens" in cost_info
        assert "total_tokens" in cost_info
        assert "total_cost" in cost_info
        assert cost_info["input_tokens"] == 1000
        assert cost_info["output_tokens"] == 500
        assert cost_info["total_tokens"] == 1500

    def test_reset_session(self, tracker):
        """Test reset_session method."""
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()

        assert len(tracker._session_costs) == 1
        assert tracker._current_input_tokens == 0
        assert tracker._current_output_tokens == 0

    def test_get_history_empty(self, tracker):
        """Test get_history when empty."""
        history = tracker.get_history()
        assert history == []

    def test_get_history_with_data(self, tracker):
        """Test get_history with data."""
        tracker.record_usage("gpt-4o", 1000, 500)
        tracker.reset_session()

        history = tracker.get_history()
        assert len(history) == 1


class TestLocalExecutionManager:
    """Test LocalExecutionManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create manager with temp dir."""
        with patch.object(Path, 'home', return_value=temp_dir):
            return LocalExecutionManager()

    def test_init(self, manager):
        """Test initialization."""
        assert "enabled" in manager._config
        assert "provider" in manager._config

    def test_is_enabled_default(self, manager):
        """Test is_enabled returns False by default."""
        assert manager.is_enabled() is False

    def test_enable_local(self, manager):
        """Test enable_local method."""
        manager.enable_local(provider="ollama", model="llama3")
        assert manager.is_enabled() is True
        assert manager._config["provider"] == "ollama"
        assert manager._config["model"] == "llama3"

    def test_disable_local(self, manager):
        """Test disable_local method."""
        manager.enable_local()
        manager.disable_local()
        assert manager.is_enabled() is False

    def test_get_provider_config(self, manager):
        """Test get_provider_config method."""
        config = manager.get_provider_config()
        assert "enabled" in config
        assert "provider" in config
        assert "model" in config

    def test_local_providers(self, manager):
        """Test LOCAL_PROVIDERS has ollama."""
        providers = manager.LOCAL_PROVIDERS
        assert "ollama" in providers
        assert "lm_studio" in providers

    @patch('urllib.request.urlopen')
    def test_check_provider_available(self, mock_urlopen, manager):
        """Test check_provider_available."""
        mock_urlopen.return_value.status = 200
        result = manager.check_provider_available("ollama")
        assert result is True

    @patch('urllib.request.urlopen')
    def test_check_provider_unavailable(self, mock_urlopen, manager):
        """Test provider unavailable."""
        mock_urlopen.side_effect = Exception("Connection refused")
        result = manager.check_provider_available("ollama")
        assert result is False


class TestZenIntegration:
    """Test ZenIntegration class."""

    def test_init_no_api_key(self):
        """Test init without API key."""
        zen = ZenIntegration(api_key="")
        assert zen.is_enabled() is False

    def test_init_with_api_key(self):
        """Test init with API key."""
        zen = ZenIntegration(api_key="test_key_123")
        assert zen.is_enabled() is True

    def test_init_from_env(self):
        """Test init from environment."""
        with patch.dict(os.environ, {"ZEN_API_KEY": "env_key"}):
            zen = ZenIntegration()
            assert zen.is_enabled() is True

    def test_estimate_cost(self):
        """Test estimate_cost method."""
        zen = ZenIntegration()
        result = zen.estimate_cost("gpt-4o", 1000, 1000)
        assert "model" in result
        assert "estimated_cost" in result

    def test_create_session(self):
        """Test create_session method."""
        zen = ZenIntegration(api_key="test")
        session_id = zen.create_session(budget=10.0)
        assert session_id.startswith("zen_session_")

    def test_get_usage_report(self):
        """Test get_usage_report method."""
        zen = ZenIntegration()
        report = zen.get_usage_report()
        assert "total_spent" in report
        assert "total_tokens" in report


class TestGlobalInstances:
    """Test global instances."""

    def test_cost_tracker_global(self):
        """Test global cost_tracker."""
        assert cost_tracker is not None
        assert isinstance(cost_tracker, CostTracker)

    def test_local_manager_global(self):
        """Test global local_manager."""
        assert local_manager is not None
        assert isinstance(local_manager, LocalExecutionManager)

    def test_zen_integration_global(self):
        """Test global zen_integration."""
        assert zen_integration is not None
        assert isinstance(zen_integration, ZenIntegration)