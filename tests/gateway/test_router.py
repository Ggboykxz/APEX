"""Tests for gateway router — rate limiting, model validation."""

import tempfile
from pathlib import Path

import pytest

from apex.gateway.auth import AuthManager
from apex.gateway.config import GatewayConfig, DEFAULT_TIERS
from apex.gateway.router import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter()
        key = "test:free"
        for _ in range(5):
            assert rl.check(key, 10) is True

    def test_blocks_over_limit(self):
        rl = RateLimiter()
        key = "test:pro"
        for _ in range(3):
            rl.check(key, 3)
        assert rl.check(key, 3) is False

    def test_expires_after_window(self):
        rl = RateLimiter()
        key = "test:expire"
        rl._buckets[key] = [0]  # old timestamp
        assert rl.check(key, 10) is True  # expired entry cleaned

    def test_separate_keys(self):
        rl = RateLimiter()
        for _ in range(5):
            rl.check("key1", 5)
        assert rl.check("key2", 5) is True  # different key, not limited


class TestModelValidation:
    def test_free_tier_allows_free_models(self):
        tier = DEFAULT_TIERS["free"]
        assert "free-or-qwen3-coder" in tier.models
        assert "*" not in tier.models

    def test_free_tier_blocks_pro_models(self):
        tier = DEFAULT_TIERS["free"]
        assert "pro-glm-5" not in tier.models

    def test_unlimited_allows_all(self):
        tier = DEFAULT_TIERS["unlimited"]
        assert "*" in tier.models

    def test_pro_tier_allows_pro_models(self):
        tier = DEFAULT_TIERS["pro"]
        assert "pro-glm-5" in tier.models
        assert "pro-deepseek-v4-pro" in tier.models

    def test_model_allowed_helper(self):
        cfg = GatewayConfig()
        free_tier = cfg.tiers["free"]
        pro_tier = cfg.tiers["pro"]

        from apex.gateway.router import RequestRouter
        from apex.gateway.auth import AuthManager
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            auth = AuthManager(db_path)
            router = RequestRouter(cfg, auth)

            assert router._model_allowed("free-or-qwen3-coder", free_tier) is True
            assert router._model_allowed("pro-glm-5", free_tier) is False
            assert router._model_allowed("pro-glm-5", pro_tier) is True


class TestAuthzIntegration:
    def test_api_key_generation_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            auth = AuthManager(db_path)

            key = auth.generate_key("pro", "integration-test")
            info = auth.validate_key(key)
            assert info is not None
            assert info["tier"] == "pro"

            cfg = GatewayConfig()
            from apex.gateway.router import RequestRouter
            router = RequestRouter(cfg, auth)
            tier = router._get_tier("pro")
            assert tier.daily_requests == 500

    def test_free_key_cannot_access_pro_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            auth = AuthManager(db_path)
            cfg = GatewayConfig()

            from apex.gateway.router import RequestRouter
            router = RequestRouter(cfg, auth)

            key = auth.generate_key("free")
            info = auth.validate_key(key)
            tier = router._get_tier(info["tier"])

            assert router._model_allowed("free-or-qwen3-coder", tier) is True
            assert router._model_allowed("pro-glm-5", tier) is False
