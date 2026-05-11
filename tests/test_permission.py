"""Comprehensive tests for permission.py module — no mocks."""

import time

import pytest

from apex.permission import (
    PermissionAction,
    PermissionManager,
    PermissionRequest,
    PermissionRequestDenied,
    PermissionRule,
    get_tool_permission,
    permission_manager,
)


# ---------------------------------------------------------------------------
# PermissionAction enum
# ---------------------------------------------------------------------------


class TestPermissionAction:
    """Test PermissionAction enum."""

    def test_allow_value(self):
        assert PermissionAction.ALLOW.value == "allow"

    def test_deny_value(self):
        assert PermissionAction.DENY.value == "deny"

    def test_ask_value(self):
        assert PermissionAction.ASK.value == "ask"

    def test_enum_from_value(self):
        assert PermissionAction("allow") == PermissionAction.ALLOW
        assert PermissionAction("deny") == PermissionAction.DENY
        assert PermissionAction("ask") == PermissionAction.ASK

    def test_all_members(self):
        members = list(PermissionAction)
        assert len(members) == 3
        assert PermissionAction.ALLOW in members
        assert PermissionAction.DENY in members
        assert PermissionAction.ASK in members


# ---------------------------------------------------------------------------
# PermissionRule dataclass
# ---------------------------------------------------------------------------


class TestPermissionRule:
    """Test PermissionRule dataclass."""

    def test_rule_creation_minimal(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW)
        assert rule.pattern == "test"
        assert rule.action == PermissionAction.ALLOW
        assert rule.reason is None
        assert rule.expires_at is None
        assert rule.remember is False

    def test_rule_with_reason(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.DENY, reason="Not allowed")
        assert rule.reason == "Not allowed"

    def test_rule_with_expiration_not_expired(self):
        expires = time.time() + 3600
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW, expires_at=expires)
        assert rule.expires_at == expires
        assert rule.is_expired() is False

    def test_rule_expired(self):
        expires = time.time() - 1
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW, expires_at=expires)
        assert rule.is_expired() is True

    def test_rule_no_expiration(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW)
        assert rule.expires_at is None
        assert rule.is_expired() is False

    def test_rule_remember_flag(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.ALLOW, remember=True)
        assert rule.remember is True

    def test_rule_deny_action(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.DENY)
        assert rule.action == PermissionAction.DENY

    def test_rule_ask_action(self):
        rule = PermissionRule(pattern="test", action=PermissionAction.ASK)
        assert rule.action == PermissionAction.ASK


# ---------------------------------------------------------------------------
# PermissionRequest dataclass
# ---------------------------------------------------------------------------


class TestPermissionRequest:
    """Test PermissionRequest dataclass."""

    def test_request_creation_minimal(self):
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={"arg": "value"},
        )
        assert request.request_id == "req_1"
        assert request.tool_name == "test_tool"
        assert request.permission == "tool:execute"
        assert request.args == {"arg": "value"}
        assert request.status == "pending"
        assert request.workspace_id is None
        assert request.user_id is None

    def test_request_with_workspace(self):
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={},
            workspace_id="ws_123",
        )
        assert request.workspace_id == "ws_123"

    def test_request_with_user_id(self):
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={},
            user_id="user_456",
        )
        assert request.user_id == "user_456"

    def test_request_has_timestamp(self):
        before = time.time()
        request = PermissionRequest(
            request_id="req_1",
            tool_name="test_tool",
            permission="tool:execute",
            args={},
        )
        after = time.time()
        assert before <= request.timestamp <= after


# ---------------------------------------------------------------------------
# PermissionManager
# ---------------------------------------------------------------------------


class TestPermissionManagerInit:
    """Test PermissionManager initialization."""

    def test_init(self):
        manager = PermissionManager()
        assert manager is not None
        assert manager._initialized is False
        assert manager._rules == []
        assert manager._requests == {}
        assert manager._default_action == PermissionAction.ASK

    def test_initialize(self):
        manager = PermissionManager()
        manager.initialize()
        assert manager._initialized is True

    def test_initialize_idempotent(self):
        manager = PermissionManager()
        manager.initialize()
        rules_before = list(manager._rules)
        manager.initialize()
        assert manager._rules == rules_before

    def test_default_rules_after_init(self):
        manager = PermissionManager()
        manager.initialize()
        assert len(manager._rules) == 5
        patterns = [r.pattern for r in manager._rules]
        assert "read_file" in patterns
        assert "glob" in patterns
        assert "grep" in patterns
        assert "lsp_*" in patterns
        assert "*" in patterns

    def test_default_rules_actions(self):
        manager = PermissionManager()
        manager.initialize()
        allow_rules = [r for r in manager._rules if r.action == PermissionAction.ALLOW]
        ask_rules = [r for r in manager._rules if r.action == PermissionAction.ASK]
        assert len(allow_rules) == 4  # read_file, glob, grep, lsp_*
        assert len(ask_rules) == 1  # wildcard *

    def test_default_rules_reasons(self):
        manager = PermissionManager()
        manager.initialize()
        for rule in manager._rules:
            assert rule.reason is not None


class TestPermissionManagerAddRule:
    """Test add_rule method."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_add_rule(self, manager):
        manager.add_rule("custom_tool", PermissionAction.ALLOW, "Custom tool")
        assert len(manager._rules) == 1
        assert manager._rules[0].pattern == "custom_tool"
        assert manager._rules[0].action == PermissionAction.ALLOW
        assert manager._rules[0].reason == "Custom tool"

    def test_add_rule_inserts_at_front(self, manager):
        manager.add_rule("tool1", PermissionAction.ALLOW)
        manager.add_rule("tool2", PermissionAction.DENY)
        assert manager._rules[0].pattern == "tool2"
        assert manager._rules[1].pattern == "tool1"

    def test_add_rule_with_expiration(self, manager):
        before = time.time()
        manager.add_rule("temp_tool", PermissionAction.DENY, "Temp deny", expires_in=60)
        assert manager._rules[0].expires_at is not None
        assert manager._rules[0].expires_at >= before + 59
        assert manager._rules[0].expires_at <= before + 61

    def test_add_rule_with_remember_no_expiry(self, manager):
        manager.add_rule("remembered", PermissionAction.ALLOW, remember=True)
        assert manager._rules[0].remember is True
        # When remember=True and no expires_in, expires_at should be None
        assert manager._rules[0].expires_at is None

    def test_add_rule_with_remember_and_expiry(self, manager):
        manager.add_rule("remembered", PermissionAction.ALLOW, expires_in=3600, remember=True)
        assert manager._rules[0].remember is True
        assert manager._rules[0].expires_at is not None

    def test_add_rule_without_reason(self, manager):
        manager.add_rule("tool", PermissionAction.ALLOW)
        assert manager._rules[0].reason is None


class TestPermissionManagerRemoveRule:
    """Test remove_rule method."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_remove_rule(self, manager):
        manager.add_rule("to_remove", PermissionAction.ALLOW)
        result = manager.remove_rule("to_remove", PermissionAction.ALLOW)
        assert result is True
        assert not any(r.pattern == "to_remove" for r in manager._rules)

    def test_remove_rule_not_found(self, manager):
        result = manager.remove_rule("nonexistent", PermissionAction.ALLOW)
        assert result is False

    def test_remove_rule_wrong_action(self, manager):
        manager.add_rule("tool", PermissionAction.ALLOW)
        result = manager.remove_rule("tool", PermissionAction.DENY)
        assert result is False
        assert len(manager._rules) == 1

    def test_remove_rule_preserves_others(self, manager):
        manager.add_rule("tool1", PermissionAction.ALLOW)
        manager.add_rule("tool2", PermissionAction.DENY)
        manager.remove_rule("tool1", PermissionAction.ALLOW)
        assert len(manager._rules) == 1
        assert manager._rules[0].pattern == "tool2"


class TestPermissionManagerClearRules:
    """Test clear_rules method."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_clear_rules_resets_to_defaults(self, manager):
        manager.add_rule("tool1", PermissionAction.ALLOW)
        manager.clear_rules()
        # After clear, _setup_default_rules is called
        assert len(manager._rules) == 5  # default rules

    def test_clear_rules_after_init(self, manager):
        manager.initialize()
        manager.add_rule("extra", PermissionAction.DENY)
        assert len(manager._rules) == 6
        manager.clear_rules()
        assert len(manager._rules) == 5


class TestPermissionManagerCanExecute:
    """Test can_execute_tool method."""

    @pytest.fixture
    def manager(self):
        m = PermissionManager()
        m.initialize()
        return m

    def test_allow_read_file(self, manager):
        can_exec, reason = manager.can_execute_tool("read_file")
        assert can_exec is True
        assert "Allowed" in reason or "safe" in reason.lower()

    def test_allow_glob(self, manager):
        can_exec, _ = manager.can_execute_tool("glob")
        assert can_exec is True

    def test_allow_grep(self, manager):
        can_exec, _ = manager.can_execute_tool("grep")
        assert can_exec is True

    def test_allow_lsp_wildcard(self, manager):
        can_exec, _ = manager.can_execute_tool("lsp_hover")
        assert can_exec is True

    def test_ask_for_unknown(self, manager):
        can_exec, reason = manager.can_execute_tool("unknown_tool")
        assert can_exec is False
        assert "permission" in reason.lower() or "ask" in reason.lower()

    def test_deny_rule(self, manager):
        manager.add_rule("dangerous", PermissionAction.DENY, "Dangerous tool")
        can_exec, reason = manager.can_execute_tool("dangerous")
        assert can_exec is False
        assert "Denied" in reason or "Dangerous" in reason

    def test_deny_rule_reason(self, manager):
        manager.add_rule("tool", PermissionAction.DENY, "Custom deny reason")
        _, reason = manager.can_execute_tool("tool")
        assert reason == "Custom deny reason"

    def test_ask_rule(self, manager):
        manager.add_rule("ask_tool", PermissionAction.ASK, "Need confirmation")
        can_exec, reason = manager.can_execute_tool("ask_tool")
        assert can_exec is False
        assert "permission" in reason.lower() or "confirmation" in reason.lower()

    def test_wildcard_pattern_match(self, manager):
        manager.add_rule("read_*", PermissionAction.ALLOW, "Read access")
        can_exec, _ = manager.can_execute_tool("read_config")
        assert can_exec is True

    def test_no_match_returns_ask(self, manager):
        # Clear all rules and add nothing
        manager._rules = []
        can_exec, reason = manager.can_execute_tool("anything")
        assert can_exec is False
        assert "No rule matched" in reason

    def test_expired_rule_is_skipped(self, manager):
        # Add an expired allow rule
        expired_rule = PermissionRule(
            "expired_tool", PermissionAction.ALLOW, "Expired allow", expires_at=time.time() - 10
        )
        manager._rules.insert(0, expired_rule)
        can_exec, reason = manager.can_execute_tool("expired_tool")
        # Expired rule is skipped, falls through to next rules
        # Eventually hits the wildcard * ASK rule
        assert can_exec is False

    def test_priority_first_match(self, manager):
        # Add a DENY rule before the default ALLOW for read_file
        manager.add_rule("read_file", PermissionAction.DENY, "Override deny")
        can_exec, reason = manager.can_execute_tool("read_file")
        assert can_exec is False

    def test_can_execute_auto_initializes(self):
        manager = PermissionManager()
        assert manager._initialized is False
        manager.can_execute_tool("read_file")
        assert manager._initialized is True

    def test_can_execute_with_workspace(self, manager):
        can_exec, _ = manager.can_execute_tool("read_file", workspace_id="ws_1")
        assert can_exec is True

    def test_can_execute_with_user(self, manager):
        can_exec, _ = manager.can_execute_tool("read_file", user_id="user_1")
        assert can_exec is True


class TestPermissionManagerRequestPermission:
    """Test request_permission method."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_request_permission(self, manager):
        request_id = manager.request_permission(
            tool_name="test_tool", args={"key": "value"}, permission="tool:execute"
        )
        assert request_id.startswith("req_")
        assert request_id in manager._requests

    def test_request_id_unique(self, manager):
        id1 = manager.request_permission("tool1", {}, "tool:execute")
        id2 = manager.request_permission("tool2", {}, "tool:execute")
        assert id1 != id2

    def test_request_stored_correctly(self, manager):
        request_id = manager.request_permission(
            tool_name="my_tool",
            args={"arg1": "val1"},
            permission="shell:execute",
            workspace_id="ws_1",
            user_id="u_1",
        )
        request = manager._requests[request_id]
        assert request.tool_name == "my_tool"
        assert request.permission == "shell:execute"
        assert request.args == {"arg1": "val1"}
        assert request.workspace_id == "ws_1"
        assert request.user_id == "u_1"
        assert request.status == "pending"

    def test_request_counter_increments(self, manager):
        manager.request_permission("tool1", {}, "tool:execute")
        manager.request_permission("tool2", {}, "tool:execute")
        assert manager._request_id_counter == 2


class TestPermissionManagerApproveRequest:
    """Test approve_request method."""

    @pytest.fixture
    def manager(self):
        m = PermissionManager()
        m.initialize()
        return m

    def test_approve_request(self, manager):
        request_id = manager.request_permission(
            tool_name="test_tool", args={}, permission="tool:execute"
        )
        result = manager.approve_request(request_id)
        assert result is True
        assert request_id not in manager._requests

    def test_approve_request_not_found(self, manager):
        result = manager.approve_request("nonexistent")
        assert result is False

    def test_approve_request_with_remember(self, manager):
        request_id = manager.request_permission(
            tool_name="remembered_tool", args={}, permission="tool:execute"
        )
        manager.approve_request(request_id, remember=True)
        # The rule was added before can_execute_tool initializes
        # But since manager is already initialized, the rule persists
        can_exec, _ = manager.can_execute_tool("remembered_tool")
        assert can_exec is True

    def test_approve_request_with_remember_and_expiry(self, manager):
        request_id = manager.request_permission(
            tool_name="temp_tool", args={}, permission="tool:execute"
        )
        manager.approve_request(request_id, remember=True, expires_in=3600)
        can_exec, _ = manager.can_execute_tool("temp_tool")
        assert can_exec is True

    def test_approve_request_status_updated(self, manager):
        request_id = manager.request_permission(
            tool_name="test_tool", args={}, permission="tool:execute"
        )
        request = manager._requests[request_id]
        assert request.status == "pending"
        manager.approve_request(request_id)
        # Request is deleted after approval
        assert request_id not in manager._requests


class TestPermissionManagerDenyRequest:
    """Test deny_request method."""

    @pytest.fixture
    def manager(self):
        m = PermissionManager()
        m.initialize()
        return m

    def test_deny_request(self, manager):
        request_id = manager.request_permission(
            tool_name="denied_tool", args={}, permission="tool:execute"
        )
        result = manager.deny_request(request_id)
        assert result is True
        assert request_id not in manager._requests

    def test_deny_request_not_found(self, manager):
        result = manager.deny_request("nonexistent")
        assert result is False

    def test_deny_request_with_remember(self, manager):
        request_id = manager.request_permission(
            tool_name="blocked_tool", args={}, permission="tool:execute"
        )
        manager.deny_request(request_id, remember=True)
        can_exec, _ = manager.can_execute_tool("blocked_tool")
        assert can_exec is False

    def test_deny_then_cannot_execute(self, manager):
        request_id = manager.request_permission(
            tool_name="some_tool", args={}, permission="tool:execute"
        )
        manager.deny_request(request_id)
        # The tool won't have a specific deny rule (no remember),
        # so it falls through to default ASK behavior
        can_exec, _ = manager.can_execute_tool("some_tool")
        assert can_exec is False


class TestPermissionManagerGetRequests:
    """Test get_pending_requests and get_request."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_get_pending_requests_empty(self, manager):
        pending = manager.get_pending_requests()
        assert pending == []

    def test_get_pending_requests(self, manager):
        manager.request_permission("tool1", {}, "tool:execute")
        manager.request_permission("tool2", {}, "tool:execute")
        pending = manager.get_pending_requests()
        assert len(pending) == 2

    def test_get_pending_requests_after_approval(self, manager):
        rid1 = manager.request_permission("tool1", {}, "tool:execute")
        manager.request_permission("tool2", {}, "tool:execute")
        manager.approve_request(rid1)
        pending = manager.get_pending_requests()
        assert len(pending) == 1

    def test_get_request(self, manager):
        request_id = manager.request_permission("tool", {}, "tool:execute")
        request = manager.get_request(request_id)
        assert request is not None
        assert request.tool_name == "tool"

    def test_get_request_not_found(self, manager):
        request = manager.get_request("nonexistent")
        assert request is None

    def test_get_pending_returns_copy(self, manager):
        manager.request_permission("tool1", {}, "tool:execute")
        pending1 = manager.get_pending_requests()
        pending2 = manager.get_pending_requests()
        assert pending1 is not pending2


class TestPermissionManagerMatchPattern:
    """Test _match_pattern method."""

    @pytest.fixture
    def manager(self):
        return PermissionManager()

    def test_exact_match(self, manager):
        assert manager._match_pattern("read_file", "read_file") is True

    def test_no_match(self, manager):
        assert manager._match_pattern("read_file", "write_file") is False

    def test_wildcard_match(self, manager):
        assert manager._match_pattern("read_file", "read_*") is True

    def test_wildcard_no_match(self, manager):
        assert manager._match_pattern("write_file", "read_*") is False

    def test_full_wildcard(self, manager):
        assert manager._match_pattern("anything", "*") is True


# ---------------------------------------------------------------------------
# get_tool_permission
# ---------------------------------------------------------------------------


class TestGetToolPermission:
    """Test get_tool_permission function."""

    def test_read_file(self):
        assert get_tool_permission("read_file") == "file:read"

    def test_write_file(self):
        assert get_tool_permission("write_file") == "file:write"

    def test_edit_file(self):
        assert get_tool_permission("edit_file") == "file:edit"

    def test_delete_file(self):
        assert get_tool_permission("delete_file") == "file:delete"

    def test_run_command(self):
        assert get_tool_permission("run_command") == "shell:execute"

    def test_bash(self):
        assert get_tool_permission("bash") == "shell:execute"

    def test_shell(self):
        assert get_tool_permission("shell") == "shell:execute"

    def test_search(self):
        assert get_tool_permission("search") == "web:search"

    def test_fetch_url(self):
        assert get_tool_permission("fetch_url") == "web:fetch"

    def test_mcp_tool(self):
        assert get_tool_permission("mcp_custom") == "mcp:execute"

    def test_mcp_another(self):
        assert get_tool_permission("mcp_server_tool") == "mcp:execute"

    def test_unknown_defaults_to_tool_execute(self):
        assert get_tool_permission("unknown_tool") == "tool:execute"

    def test_non_matching_mcp(self):
        """A tool that starts with 'mcp' but doesn't match 'mcp_*' pattern."""
        # Actually fnmatch matches mcp_anything to mcp_*
        # So this is covered by mcp_tool test
        assert get_tool_permission("mcp_test") == "mcp:execute"


# ---------------------------------------------------------------------------
# PermissionRequestDenied exception
# ---------------------------------------------------------------------------


class TestPermissionRequestDenied:
    """Test PermissionRequestDenied exception."""

    def test_exception_attributes(self):
        exc = PermissionRequestDenied("tool", "permission", "req_123")
        assert exc.tool_name == "tool"
        assert exc.permission == "permission"
        assert exc.request_id == "req_123"

    def test_exception_message(self):
        exc = PermissionRequestDenied("my_tool", "shell:execute", "req_456")
        assert "my_tool" in str(exc)
        assert "shell:execute" in str(exc)

    def test_exception_is_exception(self):
        exc = PermissionRequestDenied("t", "p", "r")
        assert isinstance(exc, Exception)

    def test_exception_can_be_raised(self):
        with pytest.raises(PermissionRequestDenied) as exc_info:
            raise PermissionRequestDenied("tool", "perm", "req_1")
        assert exc_info.value.tool_name == "tool"


# ---------------------------------------------------------------------------
# Module-level permission_manager
# ---------------------------------------------------------------------------


class TestGlobalPermissionManager:
    """Test the module-level permission_manager instance."""

    def test_exists(self):
        assert permission_manager is not None
        assert isinstance(permission_manager, PermissionManager)
