"""Comprehensive tests for api_key.py module — no mocks, real SQLite."""

import hashlib
import time

import pytest

from apex.api_key import (
    APIKeyInfo,
    InvalidKeyError,
    KeyDisabledError,
    KeyExpiredError,
    KeyManager,
    Workspace,
    WorkspaceNotFoundError,
    _safe_parse,
    create_key_manager,
    key_manager,
)


# ---------------------------------------------------------------------------
# _safe_parse helper
# ---------------------------------------------------------------------------


class TestSafeParse:
    """Test _safe_parse function."""

    def test_parse_list_string(self):
        result = _safe_parse("['a', 'b']", [])
        assert result == ["a", "b"]

    def test_parse_dict_string(self):
        result = _safe_parse("{'key': 'value'}", {})
        assert result == {"key": "value"}

    def test_parse_json_list(self):
        result = _safe_parse('["a", "b"]', [])
        assert result == ["a", "b"]

    def test_parse_json_dict(self):
        result = _safe_parse('{"key": "value"}', {})
        assert result == {"key": "value"}

    def test_empty_string_returns_default(self):
        assert _safe_parse("", []) == []
        assert _safe_parse("", {}) == {}

    def test_none_value_returns_default(self):
        assert _safe_parse(None, "default") == "default"

    def test_invalid_string_returns_default(self):
        assert _safe_parse("not valid {", []) == []

    def test_parse_number(self):
        result = _safe_parse("42", 0)
        assert result == 42

    def test_parse_tuple(self):
        result = _safe_parse("(1, 2, 3)", ())
        assert result == (1, 2, 3)


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class TestExceptions:
    """Test exception classes."""

    def test_invalid_key_error(self):
        with pytest.raises(InvalidKeyError):
            raise InvalidKeyError("Invalid key")

    def test_invalid_key_error_message(self):
        exc = InvalidKeyError("Bad key format")
        assert "Bad key format" in str(exc)

    def test_key_expired_error(self):
        with pytest.raises(KeyExpiredError):
            raise KeyExpiredError("Key expired")

    def test_key_disabled_error(self):
        with pytest.raises(KeyDisabledError):
            raise KeyDisabledError("Key disabled")

    def test_workspace_not_found_error(self):
        with pytest.raises(WorkspaceNotFoundError):
            raise WorkspaceNotFoundError("Workspace not found")

    def test_exceptions_are_exceptions(self):
        assert issubclass(InvalidKeyError, Exception)
        assert issubclass(KeyExpiredError, Exception)
        assert issubclass(KeyDisabledError, Exception)
        assert issubclass(WorkspaceNotFoundError, Exception)


# ---------------------------------------------------------------------------
# APIKeyInfo dataclass
# ---------------------------------------------------------------------------


class TestAPIKeyInfo:
    """Test APIKeyInfo dataclass."""

    def test_key_info_creation_minimal(self):
        info = APIKeyInfo(
            key_id="key-123",
            key_hash="hash-abc",
            workspace_id="ws-456",
            name="Test Key",
            created_at=1704067200.0,
        )
        assert info.key_id == "key-123"
        assert info.key_hash == "hash-abc"
        assert info.workspace_id == "ws-456"
        assert info.name == "Test Key"
        assert info.created_at == 1704067200.0
        assert info.expires_at is None
        assert info.last_used is None
        assert info.request_count == 0
        assert info.is_active is True
        assert info.rate_limit_per_minute == 60
        assert info.rate_limit_per_hour == 1000
        assert info.permissions == []
        assert info.metadata == {}

    def test_key_info_full(self):
        info = APIKeyInfo(
            key_id="key-123",
            key_hash="hash-abc",
            workspace_id="ws-456",
            name="Test Key",
            created_at=1704067200.0,
            expires_at=1704153600.0,
            last_used=1704100000.0,
            request_count=42,
            is_active=False,
            rate_limit_per_minute=30,
            rate_limit_per_hour=500,
            permissions=["read", "write"],
            metadata={"env": "prod"},
        )
        assert info.expires_at == 1704153600.0
        assert info.request_count == 42
        assert info.is_active is False
        assert info.rate_limit_per_minute == 30
        assert info.permissions == ["read", "write"]
        assert info.metadata == {"env": "prod"}


# ---------------------------------------------------------------------------
# Workspace dataclass
# ---------------------------------------------------------------------------


class TestWorkspace:
    """Test Workspace dataclass."""

    def test_workspace_creation_minimal(self):
        ws = Workspace(
            workspace_id="ws-1",
            name="Test Workspace",
            owner_id="user-1",
            created_at=1704067200.0,
        )
        assert ws.workspace_id == "ws-1"
        assert ws.name == "Test Workspace"
        assert ws.owner_id == "user-1"
        assert ws.is_active is True
        assert ws.settings == {}
        assert ws.metadata == {}

    def test_workspace_full(self):
        ws = Workspace(
            workspace_id="ws-1",
            name="Test Workspace",
            owner_id="user-1",
            created_at=1704067200.0,
            is_active=False,
            settings={"theme": "dark"},
            metadata={"region": "us"},
        )
        assert ws.is_active is False
        assert ws.settings == {"theme": "dark"}
        assert ws.metadata == {"region": "us"}


# ---------------------------------------------------------------------------
# KeyManager — Workspace operations
# ---------------------------------------------------------------------------


class TestKeyManagerWorkspace:
    """Test KeyManager workspace operations."""

    @pytest.fixture
    def manager(self, tmp_path):
        return KeyManager(str(tmp_path / "keys.db"))

    def test_create_workspace(self, manager):
        ws = manager.create_workspace("My Workspace", "user-1")
        assert ws.workspace_id is not None
        assert ws.name == "My Workspace"
        assert ws.owner_id == "user-1"
        assert ws.is_active is True
        assert ws.created_at > 0

    def test_create_workspace_with_settings(self, manager):
        ws = manager.create_workspace("My Workspace", "user-1", settings={"tier": "pro"})
        assert ws.settings == {"tier": "pro"}

    def test_get_workspace(self, manager):
        created = manager.create_workspace("My Workspace", "user-1")
        fetched = manager.get_workspace(created.workspace_id)
        assert fetched is not None
        assert fetched.workspace_id == created.workspace_id
        assert fetched.name == "My Workspace"
        assert fetched.owner_id == "user-1"

    def test_get_workspace_not_found(self, manager):
        result = manager.get_workspace("nonexistent")
        assert result is None

    def test_get_workspace_preserves_is_active(self, manager):
        created = manager.create_workspace("WS", "user-1")
        fetched = manager.get_workspace(created.workspace_id)
        assert fetched.is_active is True

    def test_multiple_workspaces(self, manager):
        ws1 = manager.create_workspace("WS1", "user-1")
        ws2 = manager.create_workspace("WS2", "user-2")
        assert ws1.workspace_id != ws2.workspace_id
        assert manager.get_workspace(ws1.workspace_id).name == "WS1"
        assert manager.get_workspace(ws2.workspace_id).name == "WS2"


# ---------------------------------------------------------------------------
# KeyManager — Key CRUD
# ---------------------------------------------------------------------------


class TestKeyManagerCreateKey:
    """Test KeyManager create_key method."""

    @pytest.fixture
    def manager(self, tmp_path):
        m = KeyManager(str(tmp_path / "keys.db"))
        return m

    @pytest.fixture
    def workspace_id(self, manager):
        ws = manager.create_workspace("Test WS", "user-1")
        return ws.workspace_id

    def test_create_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        assert key.startswith("apex_")
        assert info.key_id is not None
        assert info.workspace_id == workspace_id
        assert info.name == "Test Key"
        assert info.is_active is True

    def test_create_key_hash_matches(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        expected_hash = hashlib.sha256(key.encode()).hexdigest()
        assert info.key_hash == expected_hash

    def test_create_key_with_expiry(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Expiring Key", expires_in=3600)
        assert info.expires_at is not None
        assert info.expires_at > time.time()

    def test_create_key_no_expiry(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Permanent Key")
        assert info.expires_at is None

    def test_create_key_custom_rate_limits(self, manager, workspace_id):
        key, info = manager.create_key(
            workspace_id, "Custom RL", rate_limit_per_minute=30, rate_limit_per_hour=500
        )
        assert info.rate_limit_per_minute == 30
        assert info.rate_limit_per_hour == 500

    def test_create_key_with_permissions(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Perm Key", permissions=["read", "write"])
        assert info.permissions == ["read", "write"]

    def test_create_key_with_metadata(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Meta Key", metadata={"env": "test"})
        assert info.metadata == {"env": "test"}

    def test_create_multiple_keys(self, manager, workspace_id):
        key1, info1 = manager.create_key(workspace_id, "Key 1")
        key2, info2 = manager.create_key(workspace_id, "Key 2")
        assert key1 != key2
        assert info1.key_id != info2.key_id


class TestKeyManagerValidateKey:
    """Test KeyManager validate_key method."""

    @pytest.fixture
    def manager(self, tmp_path):
        m = KeyManager(str(tmp_path / "keys.db"))
        return m

    @pytest.fixture
    def workspace_id(self, manager):
        ws = manager.create_workspace("Test WS", "user-1")
        return ws.workspace_id

    def test_validate_valid_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        validated = manager.validate_key(key)
        assert validated.key_id == info.key_id
        assert validated.workspace_id == workspace_id

    def test_validate_invalid_format_no_prefix(self, manager):
        with pytest.raises(InvalidKeyError, match="Invalid API key format"):
            manager.validate_key("not_a_valid_key")

    def test_validate_invalid_format_empty(self, manager):
        with pytest.raises(InvalidKeyError, match="Invalid API key format"):
            manager.validate_key("")

    def test_validate_key_not_found(self, manager):
        with pytest.raises(InvalidKeyError, match="API key not found"):
            manager.validate_key("apex_nonexistentkey")

    def test_validate_key_updates_request_count(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        # validate_key returns key_info before the DB update, so request_count
        # on the returned object reflects the pre-increment value.
        manager.validate_key(key)
        # The update happens in DB after key_info is constructed;
        # verify by listing keys which re-reads from DB
        keys = manager.list_keys(workspace_id)
        assert keys[0].request_count >= 1

    def test_validate_disabled_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        manager.revoke_key(info.key_id)
        with pytest.raises(KeyDisabledError):
            manager.validate_key(key)

    def test_validate_expired_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Expiring Key", expires_in=1)
        # Wait for key to expire
        time.sleep(1.5)
        with pytest.raises(KeyExpiredError):
            manager.validate_key(key)


class TestKeyManagerRevokeKey:
    """Test KeyManager revoke_key method."""

    @pytest.fixture
    def manager(self, tmp_path):
        m = KeyManager(str(tmp_path / "keys.db"))
        return m

    @pytest.fixture
    def workspace_id(self, manager):
        ws = manager.create_workspace("Test WS", "user-1")
        return ws.workspace_id

    def test_revoke_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        result = manager.revoke_key(info.key_id)
        assert result is True
        keys = manager.list_keys(workspace_id)
        assert not keys[0].is_active

    def test_revoke_nonexistent_key(self, manager):
        result = manager.revoke_key("nonexistent")
        assert result is False

    def test_revoke_key_twice(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        assert manager.revoke_key(info.key_id) is True
        # Re-revoking still updates the row (sets is_active=0 again),
        # so rowcount is still > 0 in SQLite
        result = manager.revoke_key(info.key_id)
        # The key is already inactive, but UPDATE still matches the row
        assert result is True


class TestKeyManagerListKeys:
    """Test KeyManager list_keys method."""

    @pytest.fixture
    def manager(self, tmp_path):
        m = KeyManager(str(tmp_path / "keys.db"))
        return m

    @pytest.fixture
    def workspace_id(self, manager):
        ws = manager.create_workspace("Test WS", "user-1")
        return ws.workspace_id

    def test_list_keys_empty(self, manager, workspace_id):
        keys = manager.list_keys(workspace_id)
        assert keys == []

    def test_list_keys_with_keys(self, manager, workspace_id):
        manager.create_key(workspace_id, "Key 1")
        manager.create_key(workspace_id, "Key 2")
        keys = manager.list_keys(workspace_id)
        assert len(keys) == 2

    def test_list_keys_per_workspace(self, manager):
        ws1 = manager.create_workspace("WS1", "user-1")
        ws2 = manager.create_workspace("WS2", "user-2")
        manager.create_key(ws1.workspace_id, "WS1 Key")
        manager.create_key(ws2.workspace_id, "WS2 Key")
        assert len(manager.list_keys(ws1.workspace_id)) == 1
        assert len(manager.list_keys(ws2.workspace_id)) == 1

    def test_list_keys_includes_inactive(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        manager.revoke_key(info.key_id)
        keys = manager.list_keys(workspace_id)
        assert len(keys) == 1
        assert keys[0].is_active is False


class TestKeyManagerDeleteKey:
    """Test KeyManager delete_key method."""

    @pytest.fixture
    def manager(self, tmp_path):
        m = KeyManager(str(tmp_path / "keys.db"))
        return m

    @pytest.fixture
    def workspace_id(self, manager):
        ws = manager.create_workspace("Test WS", "user-1")
        return ws.workspace_id

    def test_delete_key(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        result = manager.delete_key(info.key_id)
        assert result is True
        keys = manager.list_keys(workspace_id)
        assert len(keys) == 0

    def test_delete_nonexistent_key(self, manager):
        result = manager.delete_key("nonexistent")
        assert result is False

    def test_delete_key_twice(self, manager, workspace_id):
        key, info = manager.create_key(workspace_id, "Test Key")
        assert manager.delete_key(info.key_id) is True
        assert manager.delete_key(info.key_id) is False


class TestKeyManagerInit:
    """Test KeyManager initialization."""

    def test_init_creates_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        KeyManager(db_path)
        from pathlib import Path

        assert Path(db_path).exists()

    def test_init_creates_parent_dirs(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "keys.db")
        KeyManager(db_path)
        from pathlib import Path

        assert Path(db_path).parent.exists()


# ---------------------------------------------------------------------------
# Module-level instances and factory
# ---------------------------------------------------------------------------


class TestModuleLevel:
    """Test module-level key_manager and create_key_manager."""

    def test_key_manager_exists(self):
        assert key_manager is not None
        assert isinstance(key_manager, KeyManager)

    def test_create_key_manager_default(self):
        manager = create_key_manager()
        assert isinstance(manager, KeyManager)

    def test_create_key_manager_custom_path(self, tmp_path):
        db_path = str(tmp_path / "custom.db")
        manager = create_key_manager(db_path)
        assert isinstance(manager, KeyManager)
