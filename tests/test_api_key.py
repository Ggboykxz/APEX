"""Tests for api_key.py module."""

import pytest
import tempfile
import os
from apex.api_key import (
    KeyManager,
    APIKeyInfo,
    Workspace,
    InvalidKeyError,
    KeyExpiredError,
    KeyDisabledError,
    create_key_manager,
)


class TestExceptions:
    """Test exception classes."""

    def test_invalid_key_error(self):
        exc = InvalidKeyError("Invalid key")
        assert str(exc) == "Invalid key"

    def test_key_expired_error(self):
        exc = KeyExpiredError("Key expired")
        assert str(exc) == "Key expired"

    def test_key_disabled_error(self):
        exc = KeyDisabledError("Key disabled")
        assert str(exc) == "Key disabled"


class TestAPIKeyInfo:
    """Test APIKeyInfo dataclass."""

    def test_creation(self):
        info = APIKeyInfo(
            key_id="key123",
            key_hash="hash123",
            workspace_id="ws123",
            name="Test Key",
            created_at=1234567890.0
        )
        assert info.key_id == "key123"
        assert info.name == "Test Key"
        assert info.is_active is True

    def test_with_expiration(self):
        info = APIKeyInfo(
            key_id="key123",
            key_hash="hash123",
            workspace_id="ws123",
            name="Test",
            created_at=1234567890.0,
            expires_at=1234567990.0
        )
        assert info.expires_at == 1234567990.0


class TestWorkspace:
    """Test Workspace dataclass."""

    def test_creation(self):
        ws = Workspace(
            workspace_id="ws123",
            name="Test Workspace",
            owner_id="user123",
            created_at=1234567890.0
        )
        assert ws.workspace_id == "ws123"
        assert ws.name == "Test Workspace"
        assert ws.is_active is True


class TestKeyManager:
    """Test KeyManager class."""

    @pytest.fixture
    def manager(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        km = KeyManager(db_path=db_path)
        yield km
        os.unlink(db_path)

    def test_init_creates_tables(self, manager):
        import sqlite3
        conn = sqlite3.connect(manager.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor]
        conn.close()
        assert "workspaces" in tables
        assert "api_keys" in tables

    def test_create_workspace(self, manager):
        ws = manager.create_workspace("My Project", "user123")
        assert ws.workspace_id is not None
        assert ws.name == "My Project"
        assert ws.owner_id == "user123"

    def test_get_workspace(self, manager):
        created = manager.create_workspace("Test", "user123")
        ws = manager.get_workspace(created.workspace_id)
        assert ws is not None
        assert ws.name == "Test"

    def test_get_workspace_not_found(self, manager):
        ws = manager.get_workspace("nonexistent")
        assert ws is None

    def test_create_key(self, manager):
        ws = manager.create_workspace("Test", "user123")
        api_key, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="production"
        )
        assert api_key.startswith("apex_")
        assert info.name == "production"
        assert info.is_active is True

    def test_create_key_with_expiration(self, manager):
        ws = manager.create_workspace("Test", "user123")
        api_key, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="temp",
            expires_in=3600
        )
        assert info.expires_at is not None

    def test_create_key_with_custom_limits(self, manager):
        ws = manager.create_workspace("Test", "user123")
        _, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="limited",
            rate_limit_per_minute=10,
            rate_limit_per_hour=100
        )
        assert info.rate_limit_per_minute == 10
        assert info.rate_limit_per_hour == 100

    def test_create_key_with_permissions(self, manager):
        ws = manager.create_workspace("Test", "user123")
        _, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="perms",
            permissions=["file:read", "shell:execute"]
        )
        assert "file:read" in info.permissions
        assert "shell:execute" in info.permissions

    def test_validate_key_success(self, manager):
        ws = manager.create_workspace("Test", "user123")
        api_key, original_info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="test"
        )
        validated_info = manager.validate_key(api_key)
        assert validated_info.key_id == original_info.key_id

    def test_validate_key_invalid_format(self, manager):
        with pytest.raises(InvalidKeyError):
            manager.validate_key("invalid_key")

    def test_validate_key_not_found(self, manager):
        with pytest.raises(InvalidKeyError):
            manager.validate_key("apex_nonexistent_key_abc123")

    def test_validate_key_disabled(self, manager):
        ws = manager.create_workspace("Test", "user123")
        api_key, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="test"
        )
        manager.revoke_key(info.key_id)
        with pytest.raises(KeyDisabledError):
            manager.validate_key(api_key)

    def test_revoke_key(self, manager):
        ws = manager.create_workspace("Test", "user123")
        _, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="test"
        )
        result = manager.revoke_key(info.key_id)
        assert result is True

    def test_revoke_key_not_found(self, manager):
        result = manager.revoke_key("nonexistent")
        assert result is False

    def test_list_keys(self, manager):
        ws = manager.create_workspace("Test", "user123")
        manager.create_key(ws.workspace_id, "key1")
        manager.create_key(ws.workspace_id, "key2")
        keys = manager.list_keys(ws.workspace_id)
        assert len(keys) == 2

    def test_delete_key(self, manager):
        ws = manager.create_workspace("Test", "user123")
        _, info = manager.create_key(
            workspace_id=ws.workspace_id,
            name="test"
        )
        result = manager.delete_key(info.key_id)
        assert result is True
        keys = manager.list_keys(ws.workspace_id)
        assert len(keys) == 0

    def test_delete_key_not_found(self, manager):
        result = manager.delete_key("nonexistent")
        assert result is False


class TestCreateKeyManager:
    """Test create_key_manager function."""

    def test_create_default(self):
        manager = create_key_manager()
        assert isinstance(manager, KeyManager)

    def test_create_with_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)
        manager = create_key_manager(db_path=db_path)
        assert isinstance(manager, KeyManager)
        os.unlink(db_path)