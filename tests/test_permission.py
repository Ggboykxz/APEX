"""Tests for permission.py module."""

import pytest
import time
from apex.permission import (
    PermissionManager,
    PermissionRule,
    PermissionRequest,
    PermissionAction,
    get_tool_permission,
    PermissionRequestDenied,
)


class TestPermissionAction:
    """Test PermissionAction enum."""

    def test_allow_value(self):
        assert PermissionAction.ALLOW.value == "allow"

    def test_deny_value(self):
        assert PermissionAction.DENY.value == "deny"

    def test_ask_value(self):
        assert PermissionAction.ASK.value == "ask"


class TestPermissionRule:
    """Test PermissionRule dataclass."""

    def test_rule_creation(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW)
        assert rule.pattern == "test"
        assert rule.action == PermissionAction.ALLOW

    def test_rule_with_reason(self):
        rule = PermissionRule(
            pattern="test",
            action=PermissionAction.DENY,
            reason="Not allowed"
        )
        assert rule.reason == "Not allowed"

    def test_rule_with_expiration(self):
        expires = time.time() + 3600
        rule = PermissionRule(
            pattern="test",
            action=PermissionAction.ALLOW,
            expires_at=expires
        )
        assert rule.expires_at == expires
        assert not rule.is_expired()

    def test_rule_expired(self):
        expires = time.time() - 1
        rule = PermissionRule(
            pattern="test",
            action=PermissionAction.ALLOW,
            expires_at=expires
        )
        assert rule.is_expired()


class TestPermissionRequest:
    """Test PermissionRequest dataclass."""

    def test_request_creation(self):
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={"arg": "value"}
        )
        assert request.request_id == "req_1"
        assert request.tool_name == "test_tool"
        assert request.permission == "tool:execute"
        assert request.status == "pending"

    def test_request_with_workspace(self):
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={},
            workspace_id="ws_123"
        )
        assert request.workspace_id == "ws_123"


class TestPermissionManager:
    """Test PermissionManager class."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_initialize(self, manager):
        manager.initialize()
        assert manager._initialized is True

    def test_initialize_idempotent(self, manager):
        manager.initialize()
        manager.initialize()
        assert manager._initialized is True

    def test_default_rules(self, manager):
        manager.initialize()
        assert len(manager._rules) > 0

    def test_add_rule(self, manager):
        manager.add_rule("custom_tool", PermissionAction.ALLOW, "Custom tool")
        assert len(manager._rules) == 1
        assert manager._rules[0].pattern == "custom_tool"

    def test_add_rule_with_expiration(self, manager):
        manager.add_rule("temp_tool", PermissionAction.DENY, "Temp deny", expires_in=60)
        assert manager._rules[0].expires_at is not None

    def test_add_rule_inserts_at_front(self, manager):
        manager.add_rule("tool1", PermissionAction.ALLOW)
        manager.add_rule("tool2", PermissionAction.DENY)
        assert manager._rules[0].pattern == "tool2"

    def test_remove_rule(self, manager):
        manager.add_rule("to_remove", PermissionAction.ALLOW)
        result = manager.remove_rule("to_remove", PermissionAction.ALLOW)
        assert result is True
        assert not any(r.pattern == "to_remove" for r in manager._rules)

    def test_remove_rule_not_found(self, manager):
        result = manager.remove_rule("nonexistent", PermissionAction.ALLOW)
        assert result is False

    def test_clear_rules(self, manager):
        manager.add_rule("tool1", PermissionAction.ALLOW)
        manager.clear_rules()
        manager.initialize()
        assert len(manager._rules) > 0

    def test_can_execute_allow(self, manager):
        manager._rules = [
            PermissionRule("read_file", PermissionAction.ALLOW)
        ]
        can_exec, reason = manager.can_execute_tool("read_file")
        assert can_exec is True

    def test_can_execute_deny(self, manager):
        manager._rules = [
            PermissionRule("dangerous", PermissionAction.DENY)
        ]
        can_exec, reason = manager.can_execute_tool("dangerous")
        assert can_exec is False

    def test_can_execute_ask(self, manager):
        manager._rules = [
            PermissionRule("ask_tool", PermissionAction.ASK, "Need confirmation")
        ]
        can_exec, reason = manager.can_execute_tool("ask_tool")
        assert can_exec is False
        assert "Need confirmation" in reason or "permission" in reason.lower()

    def test_can_execute_wildcard(self, manager):
        manager._rules = [
            PermissionRule("read_*", PermissionAction.ALLOW)
        ]
        can_exec, _ = manager.can_execute_tool("read_file")
        assert can_exec is True

    def test_can_execute_no_match(self, manager):
        manager._rules = []
        can_exec, reason = manager.can_execute_tool("unknown")
        assert can_exec is False

    def test_request_permission(self, manager):
        request_id = manager.request_permission(
            tool_name="test_tool",
            args={"key": "value"},
            permission="tool:execute"
        )
        assert request_id.startswith("req_")
        assert request_id in manager._requests

    def test_approve_request(self, manager):
        request_id = manager.request_permission(
            tool_name="test_tool",
            args={},
            permission="tool:execute"
        )
        result = manager.approve_request(request_id)
        assert result is True
        assert request_id not in manager._requests

    def test_approve_request_with_remember(self, manager):
        request_id = manager.request_permission(
            tool_name="remembered_tool",
            args={},
            permission="tool:execute"
        )
        manager.approve_request(request_id, remember=True)
        can_exec, _ = manager.can_execute_tool("remembered_tool")
        assert can_exec is True

    def test_approve_request_not_found(self, manager):
        result = manager.approve_request("nonexistent")
        assert result is False

    def test_deny_request(self, manager):
        request_id = manager.request_permission(
            tool_name="denied_tool",
            args={},
            permission="tool:execute"
        )
        result = manager.deny_request(request_id)
        assert result is True
        assert request_id not in manager._requests

    def test_deny_request_with_remember(self, manager):
        request_id = manager.request_permission(
            tool_name="blocked_tool",
            args={},
            permission="tool:execute"
        )
        manager.deny_request(request_id, remember=True)
        can_exec, _ = manager.can_execute_tool("blocked_tool")
        assert can_exec is False

    def test_deny_request_not_found(self, manager):
        result = manager.deny_request("nonexistent")
        assert result is False

    def test_get_pending_requests(self, manager):
        req1 = manager.request_permission("tool1", {}, "tool:execute")
        req2 = manager.request_permission("tool2", {}, "tool:execute")
        pending = manager.get_pending_requests()
        assert len(pending) == 2

    def test_get_request(self, manager):
        request_id = manager.request_permission("tool", {}, "tool:execute")
        request = manager.get_request(request_id)
        assert request is not None
        assert request.tool_name == "tool"

    def test_get_request_not_found(self, manager):
        request = manager.get_request("nonexistent")
        assert request is None


class TestGetToolPermission:
    """Test get_tool_permission function."""

    def test_read_file(self):
        perm = get_tool_permission("read_file")
        assert perm == "file:read"

    def test_write_file(self):
        perm = get_tool_permission("write_file")
        assert perm == "file:write"

    def test_edit_file(self):
        perm = get_tool_permission("edit_file")
        assert perm == "file:edit"

    def test_delete_file(self):
        perm = get_tool_permission("delete_file")
        assert perm == "file:delete"

    def test_run_command(self):
        perm = get_tool_permission("run_command")
        assert perm == "shell:execute"

    def test_bash(self):
        perm = get_tool_permission("bash")
        assert perm == "shell:execute"

    def test_shell(self):
        perm = get_tool_permission("shell")
        assert perm == "shell:execute"

    def test_search(self):
        perm = get_tool_permission("search")
        assert perm == "web:search"

    def test_fetch_url(self):
        perm = get_tool_permission("fetch_url")
        assert perm == "web:fetch"

    def test_mcp_tool(self):
        perm = get_tool_permission("mcp_custom")
        assert perm == "mcp:execute"

    def test_unknown(self):
        perm = get_tool_permission("unknown_tool")
        assert perm == "tool:execute"


class TestPermissionRequestDenied:
    """Test PermissionRequestDenied exception."""

    def test_exception(self):
        exc = PermissionRequestDenied("tool", "permission", "req_123")
        assert exc.tool_name == "tool"
        assert exc.permission == "permission"
        assert exc.request_id == "req_123"
        assert "Permission required" in str(exc)