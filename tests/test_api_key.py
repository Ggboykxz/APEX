"""Tests for API key management module."""

import pytest
from apex.api_key import (
    KeyManager,
    APIKeyInfo,
    Workspace,
    InvalidKeyError,
    KeyExpiredError,
    KeyDisabledError,
)


class TestKeyManager:
    """Test KeyManager class."""

    def test_init(self):
        manager = KeyManager()
        assert manager is not None

    def test_create_key(self, tmp_path):
        manager = KeyManager(str(tmp_path / "keys.db"))
        key_id, info = manager.create_key("ws-1", "Test Key", expires_in=30)
        assert key_id is not None
        assert isinstance(info, APIKeyInfo)

    def test_validate_key_invalid(self, tmp_path):
        manager = KeyManager(str(tmp_path / "keys.db"))
        with pytest.raises(InvalidKeyError):
            manager.validate_key("nonexistent-key")

    def test_list_keys(self, tmp_path):
        manager = KeyManager(str(tmp_path / "keys.db"))
        keys = manager.list_keys("ws-1")
        assert isinstance(keys, list)


class TestAPIKeyInfo:
    """Test APIKeyInfo dataclass."""

    def test_key_info_creation(self):
        info = APIKeyInfo(
            key_id="key-123",
            key_hash="hash-abc",
            workspace_id="ws-456",
            name="Test Key",
            created_at=1704067200.0,
        )
        assert info.key_id == "key-123"
        assert info.workspace_id == "ws-456"


class TestWorkspace:
    """Test Workspace dataclass."""

    def test_workspace_creation(self):
        ws = Workspace(
            workspace_id="ws-1",
            name="Test Workspace",
            owner_id="user-1",
            created_at=1704067200.0,
        )
        assert ws.workspace_id == "ws-1"


class TestExceptions:
    """Test exception classes."""

    def test_invalid_key_error(self):
        with pytest.raises(InvalidKeyError):
            raise InvalidKeyError("Invalid key")

    def test_key_expired_error(self):
        with pytest.raises(KeyExpiredError):
            raise KeyExpiredError("Key expired")

    def test_key_disabled_error(self):
        with pytest.raises(KeyDisabledError):
            raise KeyDisabledError("Key disabled")
