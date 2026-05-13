"""Tests for gateway configuration."""

from apex.gateway.config import GatewayConfig, TierConfig, DEFAULT_TIERS


class TestTierConfig:
    def test_free_tier_defaults(self):
        tier = DEFAULT_TIERS["free"]
        assert tier.daily_requests == 50
        assert tier.daily_tokens == 500_000
        assert tier.rate_per_minute == 10
        assert len(tier.models) == 19

    def test_pro_tier_defaults(self):
        tier = DEFAULT_TIERS["pro"]
        assert tier.daily_requests == 500
        assert tier.daily_tokens == 5_000_000
        assert tier.rate_per_minute == 60
        assert len(tier.models) == 10

    def test_unlimited_tier(self):
        tier = DEFAULT_TIERS["unlimited"]
        assert tier.daily_requests == 999999
        assert "*" in tier.models


class TestGatewayConfig:
    def test_default_values(self):
        cfg = GatewayConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 9090
        assert cfg.default_tier == "free"
        assert cfg.register_enabled is True

    def test_default_models_loaded(self):
        cfg = GatewayConfig()
        assert "free" in cfg.tiers
        assert "pro" in cfg.tiers
        assert "unlimited" in cfg.tiers

    def test_tier_allows_models(self, monkeypatch):
        cfg = GatewayConfig()
        free = cfg.tiers["free"]
        assert "free-or-qwen3-235b" in free.models
        assert "free-or-qwen3-coder" in free.models
        assert "free-or-router" in free.models
        assert "pro-glm-5" not in free.models
