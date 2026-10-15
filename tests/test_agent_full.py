"""Comprehensive tests for apex/agent.py — Chat, subagent, permissions, tool execution.

Uses real objects only (no mocks).  Chat methods will trigger litellm calls that
fail due to missing API keys — we verify that error handling works correctly.
"""

import pytest

litellm = pytest.importorskip("litellm")

from apex.agent import Agent
from apex.permission import permission_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_permission_manager():
    """Reset the global permission_manager before each test to avoid state leaks."""
    permission_manager._initialized = False
    permission_manager._rules.clear()
    permission_manager._requests.clear()
    permission_manager._request_id_counter = 0
    permission_manager.initialize()
    yield
    # Cleanup after test too
    permission_manager._requests.clear()


@pytest.fixture
def agent():
    """Create a fresh Agent instance."""
    return Agent()


@pytest.fixture
def agent_in_tmpdir(tmp_path):
    """Agent with cwd set to a temp directory."""
    a = Agent()
    a.cwd = tmp_path
    return a


# ---------------------------------------------------------------------------
# Subagent parsing
# ---------------------------------------------------------------------------


class TestSubagentParsing:
    """Test Agent._parse_subagent_invocation()."""

    def test_valid_subagent_reviewer(self, agent):
        sub, task = agent._parse_subagent_invocation("@reviewer fix this bug")
        assert sub == "reviewer"
        assert task == "fix this bug"

    def test_valid_subagent_with_leading_spaces(self, agent):
        sub, task = agent._parse_subagent_invocation("  @reviewer review code  ")
        assert sub == "reviewer"
        assert task == "review code"

    def test_no_at_sign_returns_none(self, agent):
        sub, task = agent._parse_subagent_invocation("just a message")
        assert sub is None
        assert task == "just a message"

    def test_nonexistent_subagent_returns_none(self, agent):
        sub, task = agent._parse_subagent_invocation("@nonexistent do stuff")
        assert sub is None
        # Original input is returned as task
        assert "nonexistent" in task

    def test_primary_agent_not_treated_as_subagent(self, agent):
        """Primary agents (coder, architect) are NOT subagents."""
        sub, task = agent._parse_subagent_invocation("@coder write code")
        assert sub is None  # coder is primary, not subagent

    def test_at_sign_without_name(self, agent):
        sub, task = agent._parse_subagent_invocation("@ do stuff")
        assert sub is None

    def test_at_sign_without_task(self, agent):
        sub, task = agent._parse_subagent_invocation("@reviewer")
        # No task after @reviewer — doesn't match pattern
        assert sub is None

    def test_at_sign_at_end(self, agent):
        sub, task = agent._parse_subagent_invocation("@reviewer ")
        # Trailing space — the regex requires ".+" after the name
        assert sub is None


# ---------------------------------------------------------------------------
# Permission request/approve/deny
# ---------------------------------------------------------------------------


class TestPermissionRequests:
    """Test Agent permission request lifecycle."""

    def test_request_permission(self, agent):
        req_id = agent._request_permission("write_file", {"path": "/tmp/test"}, "tc_1")
        assert isinstance(req_id, str)
        assert req_id.startswith("req_")
        assert req_id in agent._pending_permissions

    def test_request_permission_stores_args(self, agent):
        req_id = agent._request_permission("run_command", {"command": "ls"}, "tc_2")
        pending = agent._pending_permissions[req_id]
        assert pending["tool_name"] == "run_command"
        assert pending["tool_args"] == {"command": "ls"}
        assert pending["tc_id"] == "tc_2"

    def test_approve_permission(self, agent):
        req_id = agent._request_permission("write_file", {"path": "/tmp/test"}, "tc_3")
        result = agent.approve_permission(req_id)
        assert result is True
        assert req_id not in agent._pending_permissions

    def test_approve_permission_with_remember(self, agent):
        req_id = agent._request_permission("write_file", {"path": "/tmp/test"}, "tc_4")
        result = agent.approve_permission(req_id, remember=True)
        assert result is True

    def test_approve_nonexistent_permission(self, agent):
        result = agent.approve_permission("nonexistent_req_id")
        assert result is False

    def test_deny_permission(self, agent):
        req_id = agent._request_permission("run_command", {"command": "rm"}, "tc_5")
        result = agent.deny_permission(req_id)
        assert result is True
        assert req_id not in agent._pending_permissions

    def test_deny_nonexistent_permission(self, agent):
        result = agent.deny_permission("nonexistent_req_id")
        assert result is False

    def test_get_pending_permissions(self, agent):
        agent._request_permission("write_file", {"path": "/tmp/a"}, "tc_6")
        agent._request_permission("run_command", {"command": "ls"}, "tc_7")
        pending = agent.get_pending_permissions()
        assert len(pending) == 2
        tool_names = {p["tool_name"] for p in pending}
        assert "write_file" in tool_names
        assert "run_command" in tool_names

    def test_get_pending_permissions_empty(self, agent):
        pending = agent.get_pending_permissions()
        assert pending == []

    def test_pending_permissions_have_required_fields(self, agent):
        agent._request_permission("write_file", {"path": "/tmp/test"}, "tc_8")
        pending = agent.get_pending_permissions()
        assert len(pending) == 1
        p = pending[0]
        assert "request_id" in p
        assert "tool_name" in p
        assert "permission" in p
        assert "args" in p
        assert "timestamp" in p


# ---------------------------------------------------------------------------
# Tool permission checking
# ---------------------------------------------------------------------------


class TestToolPermissionChecking:
    """Test Agent._check_tool_permission()."""

    def test_read_file_allowed(self, agent):
        allowed, msg = agent._check_tool_permission("read_file")
        assert allowed is True

    def test_glob_allowed(self, agent):
        allowed, msg = agent._check_tool_permission("glob")
        assert allowed is True

    def test_write_file_requires_permission(self, agent):
        """write_file is not in default ALLOW rules — should require permission."""
        allowed, msg = agent._check_tool_permission("write_file")
        assert allowed is False
        assert "permission" in msg.lower() or "Requires" in msg


# ---------------------------------------------------------------------------
# _execute_tools_parallel
# ---------------------------------------------------------------------------


class TestExecuteToolsParallel:
    """Test Agent._execute_tools_parallel() with real tool execution."""

    def test_execute_read_file(self, agent_in_tmpdir, tmp_path):
        test_file = tmp_path / "hello.txt"
        test_file.write_text("hello world")
        results = agent_in_tmpdir._execute_tools_parallel(
            [("tc_1", "read_file", {"path": str(test_file)})]
        )
        assert len(results) == 1
        tc_id, content = results[0]
        assert tc_id == "tc_1"
        assert "hello world" in content

    def test_execute_write_file(self, agent_in_tmpdir, tmp_path):
        out_file = tmp_path / "output.txt"
        results = agent_in_tmpdir._execute_tools_parallel(
            [("tc_1", "write_file", {"path": str(out_file), "content": "test content"})]
        )
        assert len(results) == 1
        assert out_file.exists()
        assert out_file.read_text() == "test content"

    def test_execute_list_files(self, agent_in_tmpdir, tmp_path):
        (tmp_path / "a.py").write_text("print('a')")
        (tmp_path / "b.py").write_text("print('b')")
        results = agent_in_tmpdir._execute_tools_parallel(
            [("tc_1", "list_files", {"path": str(tmp_path)})]
        )
        assert len(results) == 1
        _, content = results[0]
        assert "a.py" in content

    def test_execute_multiple_tools(self, agent_in_tmpdir, tmp_path):
        (tmp_path / "data.txt").write_text("some data")
        results = agent_in_tmpdir._execute_tools_parallel(
            [
                ("tc_1", "read_file", {"path": str(tmp_path / "data.txt")}),
                ("tc_2", "list_files", {"path": str(tmp_path)}),
            ]
        )
        assert len(results) == 2
        assert results[0][0] == "tc_1"
        assert results[1][0] == "tc_2"

    def test_execute_invalid_tool(self, agent_in_tmpdir):
        results = agent_in_tmpdir._execute_tools_parallel([("tc_1", "nonexistent_tool_xyz", {})])
        assert len(results) == 1
        _, content = results[0]
        assert "ERROR" in content or "error" in content.lower()


# ---------------------------------------------------------------------------
# _execute_tools_parallel_async
# ---------------------------------------------------------------------------


class TestExecuteToolsParallelAsync:
    """Test Agent._execute_tools_parallel_async() with real tool execution."""

    @pytest.mark.asyncio
    async def test_async_execute_read_file(self, agent_in_tmpdir, tmp_path):
        test_file = tmp_path / "async_test.txt"
        test_file.write_text("async content")
        results = await agent_in_tmpdir._execute_tools_parallel_async(
            [("tc_1", "read_file", {"path": str(test_file)})]
        )
        assert len(results) == 1
        tc_id, content = results[0]
        assert tc_id == "tc_1"
        assert "async content" in content

    @pytest.mark.asyncio
    async def test_async_execute_write_file(self, agent_in_tmpdir, tmp_path):
        out_file = tmp_path / "async_output.txt"
        results = await agent_in_tmpdir._execute_tools_parallel_async(
            [("tc_1", "write_file", {"path": str(out_file), "content": "async write"})]
        )
        assert len(results) == 1
        assert out_file.exists()
        assert out_file.read_text() == "async write"


# ---------------------------------------------------------------------------
# _update_usage
# ---------------------------------------------------------------------------


class TestUpdateUsage:
    """Test Agent._update_usage()."""

    def test_update_with_usage_object(self, agent):
        class Usage:
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150

        agent._update_usage(Usage())
        assert agent.usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def test_update_accumulates(self, agent):
        class Usage1:
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150

        class Usage2:
            prompt_tokens = 200
            completion_tokens = 100
            total_tokens = 300

        agent._update_usage(Usage1())
        agent._update_usage(Usage2())
        assert agent.usage["prompt_tokens"] == 300
        assert agent.usage["completion_tokens"] == 150
        assert agent.usage["total_tokens"] == 450

    def test_update_with_none_skips(self, agent):
        agent._update_usage(None)
        assert agent.usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_update_with_none_attributes(self, agent):
        class PartialUsage:
            prompt_tokens = None
            completion_tokens = 50
            total_tokens = None

        agent._update_usage(PartialUsage())
        assert agent.usage["prompt_tokens"] == 0
        assert agent.usage["completion_tokens"] == 50
        assert agent.usage["total_tokens"] == 0

    def test_update_with_missing_attributes(self, agent):
        """Object without usage attributes should default to 0."""

        class EmptyUsage:
            pass

        agent._update_usage(EmptyUsage())
        assert agent.usage["prompt_tokens"] == 0
        assert agent.usage["completion_tokens"] == 0
        assert agent.usage["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Chat (error handling — no API key)
# ---------------------------------------------------------------------------


class TestChatErrorHandling:
    """Test Agent.chat() error handling when litellm fails (no API key).

    These tests verify that the error-handling paths in _chat_internal work
    correctly.  Without a valid API key, litellm raises an exception that is
    caught and returned as a user-facing error string.
    """

    def test_chat_returns_error_string_without_api_key(self, agent):
        """chat() should return an error string, not raise an exception."""
        result = agent.chat("hello", max_rounds=1)
        assert isinstance(result, str)
        assert result.startswith("ERROR:")

    def test_chat_internal_returns_error_string(self, agent):
        """_chat_internal() should return an error string without a valid key."""
        result = agent._chat_internal("test input", max_rounds=1)
        assert isinstance(result, str)
        assert result.startswith("ERROR:")

    def test_chat_does_not_raise_exception(self, agent):
        """chat() must never raise — all errors should be caught."""
        try:
            result = agent.chat("any input", max_rounds=1)
            assert isinstance(result, str)
        except Exception:
            pytest.fail("chat() raised an exception instead of returning an error string")

    def test_chat_preserves_agent_state(self, agent):
        """After a failed chat, agent state should still be consistent."""
        original_agent = agent.current_agent
        agent.chat("hello", max_rounds=1)
        assert agent.current_agent == original_agent

    def test_chat_with_subagent_invocation(self, agent):
        """chat() with @reviewer should invoke _chat_as_subagent and return error.

        Even though the LLM call fails, the subagent parsing and agent switching
        logic should be exercised.
        """
        result = agent.chat("@reviewer check this code", max_rounds=1)
        assert isinstance(result, str)
        # Should contain subagent prefix or error
        assert len(result) > 0

    def test_chat_as_subagent_restores_agent(self, agent):
        """_chat_as_subagent must restore the original agent even on error."""
        agent.switch_agent("build")
        agent._chat_as_subagent("reviewer", "check this", max_rounds=1)
        # Original agent should be restored
        assert agent.current_agent == "build"

    def test_chat_as_subagent_returns_prefixed_result(self, agent):
        """_chat_as_subagent should prefix result with [@agentname]."""
        result = agent._chat_as_subagent("reviewer", "check this", max_rounds=1)
        assert result.startswith("[@reviewer]:")


# ---------------------------------------------------------------------------
# Chat streaming (error handling — no API key)
# ---------------------------------------------------------------------------


class TestChatStreamingErrorHandling:
    """Test Agent.chat_streaming() error handling when litellm fails."""

    @pytest.mark.asyncio
    async def test_streaming_returns_error_string(self, agent):
        """chat_streaming() should yield error strings without raising."""
        chunks = []
        async for chunk in agent.chat_streaming("hello", max_rounds=1):
            chunks.append(chunk)
        assert len(chunks) > 0
        combined = "".join(chunks)
        assert "ERROR:" in combined

    @pytest.mark.asyncio
    async def test_streaming_with_subagent(self, agent):
        """chat_streaming() with @reviewer should prefix output."""
        chunks = []
        async for chunk in agent.chat_streaming("@reviewer check code", max_rounds=1):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert len(combined) > 0
        # Should contain the subagent prefix or an error
        assert "[@reviewer]:" in combined or "ERROR:" in combined

    @pytest.mark.asyncio
    async def test_streaming_restores_agent(self, agent):
        """chat_streaming() should restore original agent after subagent."""
        agent.switch_agent("build")
        chunks = []
        async for chunk in agent.chat_streaming("@reviewer check", max_rounds=1):
            chunks.append(chunk)
        # Agent should be restored
        assert agent.current_agent == "build"


# ---------------------------------------------------------------------------
# _set_agent_prompt (alias for _set_agent_system_prompt)
# ---------------------------------------------------------------------------


class TestSetAgentPrompt:
    """Test _set_agent_prompt() — the alias used in streaming."""

    def test_set_agent_prompt_matches_set_system_prompt(self, agent):
        agent._set_agent_prompt()
        assert agent._system_message["role"] == "system"

    def test_set_agent_prompt_for_planner(self, agent):
        agent._current_agent = "planner"
        agent._set_agent_prompt()
        from apex.agents import AGENT_PLANNER_PROMPT

        assert agent._system_message["content"] == AGENT_PLANNER_PROMPT

    def test_set_agent_prompt_for_nonexistent(self, agent):
        """If agent doesn't exist, system message content should be empty."""
        agent._current_agent = "nonexistent_agent"
        agent._set_agent_prompt()
        assert agent._system_message["content"] == ""
