"""Tests for gateway authentication and API key management."""

import json
import tempfile
from pathlib import Path

import pytest

from apex.gateway.auth import AuthManager


@pytest.fixture
def auth():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        yield AuthManager(db_path)


class TestAuthManager:
    def test_generate_key(self, auth):
        key = auth.generate_key("free", "test")
        assert key.startswith("apex_")
        assert len(key) > 32

    def test_generate_key_default_tier(self, auth):
        key = auth.generate_key()
        info = auth.validate_key(key)
        assert info is not None
        assert info["tier"] == "free"

    def test_validate_key_valid(self, auth):
        key = auth.generate_key("pro", "alice")
        info = auth.validate_key(key)
        assert info is not None
        assert info["tier"] == "pro"

    def test_validate_key_invalid(self, auth):
        info = auth.validate_key("invalid_key")
        assert info is None

    def test_validate_key_revoked(self, auth):
        key = auth.generate_key("free")
        auth.revoke_key(key)
        info = auth.validate_key(key)
        assert info is None

    def test_list_keys(self, auth):
        auth.generate_key("free", "k1")
        auth.generate_key("pro", "k2")
        keys = auth.list_keys()
        assert len(keys) == 2

    def test_revoke_key(self, auth):
        key = auth.generate_key("free")
        assert auth.revoke_key(key) is True
        assert auth.revoke_key("nonexistent") is False

    def test_usage_tracking(self, auth):
        key = auth.generate_key("free")
        info = auth.validate_key(key)
        key_id = info["key_id"]

        req, tok = auth.get_or_create_day_usage(key_id, "2026-01-01")
        assert req == 0
        assert tok == 0

        auth.record_usage(key_id, "2026-01-01", requests=3, tokens=150)
        req, tok = auth.get_or_create_day_usage(key_id, "2026-01-01")
        assert req == 3
        assert tok == 150

        auth.record_usage(key_id, "2026-01-01", requests=1, tokens=50)
        req, tok = auth.get_or_create_day_usage(key_id, "2026-01-01")
        assert req == 4
        assert tok == 200

    def test_usage_separate_dates(self, auth):
        key = auth.generate_key("free")
        info = auth.validate_key(key)
        key_id = info["key_id"]

        auth.record_usage(key_id, "2026-01-01", requests=5)
        auth.record_usage(key_id, "2026-01-02", requests=3)

        req1, _ = auth.get_or_create_day_usage(key_id, "2026-01-01")
        req2, _ = auth.get_or_create_day_usage(key_id, "2026-01-02")
        assert req1 == 5
        assert req2 == 3
