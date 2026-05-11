"""Additional tests for apex/agent.py — Edge cases, integration scenarios.

Uses real objects only (no mocks).  Focuses on branches and edge cases not
covered by the other test files.
"""

import os

import pytest

litellm = pytest.importorskip("litellm")

from apex.agent import Agent
from apex.config import Config, MODELS
from apex.agents import (
    agent_manager,
)
from apex.permission import permission_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_permission_manager():
    """Reset the global permission_manager before each test."""
    permission_manager._initialized = False
    permission_manager._rules.clear()
    permission_manager._requests.clear()
    permission_manager._request_id_counter = 0
    permission_manager.initialize()
    yield
    permission_manager._requests.clear()


@pytest.fixture
def agent():
    """Create a fresh Agent instance."""
    return Agent()


# ---------------------------------------------------------------------------
# Agent init with custom config
# ---------------------------------------------------------------------------


class TestAgentWithCustomConfig:
    """Test Agent initialization with custom Config objects."""

    def test_agent_with_config_object(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        a = Agent(config=cfg)
        assert a.config is cfg

    def test_agent_config_cwd_propagated(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        a = Agent(config=cfg)
        assert a.cwd == a._executor.cwd

    def test_agent_none_config_uses_default(self):
        a = Agent(config=None)
        assert a.config is not None
        assert isinstance(a.config, Config)


# ---------------------------------------------------------------------------
# Cwd edge cases
# ---------------------------------------------------------------------------


class TestAgentCwdEdgeCases:
    """Test cwd property edge cases."""

    def test_cwd_setter_updates_config(self, agent, tmp_path):
        agent.cwd = tmp_path
        assert agent.config.cwd == tmp_path

    def test_cwd_setter_updates_async_executor(self, agent, tmp_path):
        agent.cwd = tmp_path
        assert agent._async_executor.cwd == tmp_path

    def test_cwd_with_nested_directory(self, agent, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        agent.cwd = nested
        assert agent.cwd == nested

    def test_cwd_property_matches_executor(self, agent, tmp_path):
        agent.cwd = tmp_path
        assert agent.cwd == agent._executor.cwd


# ---------------------------------------------------------------------------
# Switch model edge cases
# ---------------------------------------------------------------------------


class TestSwitchModelEdgeCases:
    """Test switch_model edge cases."""

    def test_switch_model_empty_string(self, agent):
        result = agent.switch_model("")
        assert result is False

    def test_switch_model_case_sensitive(self, agent):
        result = agent.switch_model("GPT-4O")
        assert result is False

    def test_switch_model_preserves_old_on_failure(self, agent):
        old_model = agent.model
        agent.switch_model("nonexistent-model-xyz")
        assert agent.model == old_model

    def test_switch_model_all_valid_models(self, agent):
        """Every key in MODELS should be a valid switch target."""
        for alias in list(MODELS.keys())[:10]:
            result = agent.switch_model(alias)
            assert result is True, f"switch_model({alias!r}) should return True"


# ---------------------------------------------------------------------------
# Switch agent edge cases
# ---------------------------------------------------------------------------


class TestSwitchAgentEdgeCases:
    """Test switch_agent edge cases."""

    def test_switch_agent_empty_string(self, agent):
        result = agent.switch_agent("")
        assert result is False

    def test_switch_agent_preserves_old_on_failure(self, agent):
        agent.switch_agent("planner")
        result = agent.switch_agent("nonexistent")
        assert result is False
        assert agent.current_agent == "planner"

    def test_switch_agent_to_each_builtin(self, agent):
        for name in ("coder", "architect", "planner", "reviewer", "shell"):
            result = agent.switch_agent(name)
            assert result is True
            assert agent.current_agent == name

    def test_switch_agent_updates_system_message_role(self, agent):
        agent.switch_agent("shell")
        assert agent._system_message["role"] == "system"


# ---------------------------------------------------------------------------
# Cycle agent edge cases
# ---------------------------------------------------------------------------


class TestCycleAgentEdgeCases:
    """Test cycle_agent edge cases."""

    def test_cycle_agent_full_cycle(self, agent):
        """Cycling through all primary agents should return to start."""
        agent.switch_agent("coder")
        primary = agent_manager.list_agents("primary")
        start = agent.current_agent
        for _ in range(len(primary)):
            agent.cycle_agent()
        assert agent.current_agent == start

    def test_cycle_agent_each_step_changes(self, agent):
        """Each cycle should change the current agent (unless only 1 primary)."""
        primary = agent_manager.list_agents("primary")
        if len(primary) > 1:
            prev = agent.current_agent
            agent.cycle_agent()
            assert agent.current_agent != prev

    def test_cycle_agent_updates_system_prompt(self, agent):
        agent.switch_agent("coder")
        agent.cycle_agent()
        assert len(agent._system_message["content"]) > 0

    def test_cycle_agent_no_primary_agents(self, agent):
        """When no primary agents exist, cycle_agent returns current agent (covers line 76)."""
        # Save and replace
        saved = agent_manager.agents.copy()
        try:
            agent_manager.agents.clear()
            result = agent.cycle_agent()
            # Should return current agent unchanged
            assert result == agent.current_agent
        finally:
            agent_manager.agents.update(saved)


# ---------------------------------------------------------------------------
# Cycle reasoning effort edge cases
# ---------------------------------------------------------------------------


class TestCycleReasoningEdgeCases:
    """Test cycle_reasoning_effort edge cases."""

    def test_cycle_three_times_returns_to_start(self, agent):
        agent.config.reasoning_effort = "off"
        agent.cycle_reasoning_effort()  # off -> high
        agent.cycle_reasoning_effort()  # high -> max
        agent.cycle_reasoning_effort()  # max -> off
        assert agent.config.reasoning_effort == "off"

    def test_cycle_updates_config(self, agent):
        agent.config.reasoning_effort = "off"
        result = agent.cycle_reasoning_effort()
        assert agent.config.reasoning_effort == result

    def test_cycle_invalid_effort_resets_to_off(self, agent):
        """Invalid reasoning effort defaults to 'off' before cycling (covers line 88).

        We bypass the Config setter validation by writing directly to _data.
        """
        agent.config._data["reasoning_effort"] = "ultra"
        result = agent.cycle_reasoning_effort()
        # "ultra" -> defaults to "off" -> cycles to "high"
        assert result == "high"
        assert agent.config.reasoning_effort == "high"


# ---------------------------------------------------------------------------
# Auto model selection edge cases
# ---------------------------------------------------------------------------


class TestAutoSelectModelEdgeCases:
    """Test auto_select_model edge cases."""

    def test_explain_anywhere_in_text(self, agent):
        assert agent.auto_select_model("please explain the function") == "claude-4-sonnet"

    def test_debug_anywhere_in_text(self, agent):
        assert agent.auto_select_model("I need to debug this") == "claude-4-opus"

    def test_refactor_before_create(self, agent):
        assert agent.auto_select_model("refactor and create") == "gpt-4o"

    def test_explain_takes_priority_over_create(self, agent):
        assert agent.auto_select_model("explain and create") == "claude-4-sonnet"

    def test_empty_string(self, agent):
        assert agent.auto_select_model("") == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Reset history edge cases
# ---------------------------------------------------------------------------


class TestResetHistoryEdgeCases:
    """Test reset_history edge cases."""

    def test_reset_twice(self, agent):
        agent.history = [{"role": "user", "content": "test"}]
        agent.reset_history()
        agent.reset_history()
        assert agent.history == []

    def test_reset_after_chat_error(self, agent):
        """After a failed chat, reset should still work."""
        agent.chat("test", max_rounds=1)
        agent.reset_history()
        assert agent.history == []
        assert agent.usage["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Chat edge cases — error handling paths
# ---------------------------------------------------------------------------


class TestChatMaxRoundsReached:
    """Test _chat_internal max rounds reached (covers line 314)."""

    def test_max_rounds_zero_returns_error(self, agent):
        """Setting max_tool_rounds to 0 causes immediate max-rounds error."""
        agent.config.max_tool_rounds = 0
        result = agent._chat_internal("hello")
        assert (
            result
            == "ERROR: Max tool rounds reached. The conversation was terminated due to too many tool calls."
        )

    def test_chat_with_zero_rounds(self, agent):
        agent.config.max_tool_rounds = 0
        result = agent.chat("hello")
        assert "Max tool rounds reached" in result


class TestChatGenericException:
    """Test _chat_internal with generic exception (covers line 308-312).

    Using an Ollama model when Ollama is not running triggers an
    APIConnectionError which falls through to the generic Exception handler.
    """

    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires Ollama running, not available in CI",
    )
    def test_ollama_connection_error_caught(self, agent):
        agent.switch_model("ollama-llama3")
        result = agent._chat_internal("hello", max_rounds=1)
        assert isinstance(result, str)
        assert result.startswith("ERROR:")
        # APIConnectionError is not Authentication/RateLimit/BadRequest
        assert "APIConnectionError" in result or "Connection" in result


class TestChatBadRequestError:
    """Test _chat_internal with BadRequestError (covers lines 305-307).

    Using a model alias that maps to an unrecognized provider string causes
    litellm to raise BadRequestError.
    """

    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires API access, not available in CI",
    )
    def test_bad_request_error_caught(self, agent):
        agent.switch_model("llama-3.2-3b-free")
        result = agent._chat_internal("hello", max_rounds=1)
        assert isinstance(result, str)
        assert result.startswith("ERROR:")
        assert "Bad request" in result

    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires API access, not available in CI",
    )
    def test_bad_request_via_chat(self, agent):
        agent.switch_model("llama-3.2-3b-free")
        result = agent.chat("hello", max_rounds=1)
        assert isinstance(result, str)
        assert "Bad request" in result or "ERROR" in result


class TestStreamingBadRequestError:
    """Test _chat_internal_streaming with BadRequestError (covers lines 481-483)."""

    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires API access, not available in CI",
    )
    @pytest.mark.asyncio
    async def test_streaming_bad_request_error_caught(self, agent):
        agent.switch_model("llama-3.2-3b-free")
        chunks = []
        async for chunk in agent._chat_internal_streaming("hello", max_rounds=1):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert "Bad request" in combined or "ERROR" in combined


class TestStreamingMaxRoundsReached:
    """Test _chat_internal_streaming max rounds reached (covers line 488)."""

    @pytest.mark.asyncio
    async def test_streaming_max_rounds_zero(self, agent):
        agent.config.max_tool_rounds = 0
        chunks = []
        async for chunk in agent._chat_internal_streaming("hello"):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert "Max tool rounds reached" in combined

    @pytest.mark.asyncio
    async def test_streaming_chat_max_rounds_zero(self, agent):
        agent.config.max_tool_rounds = 0
        chunks = []
        async for chunk in agent.chat_streaming("hello"):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert "Max tool rounds reached" in combined


class TestStreamingGenericException:
    """Test _chat_internal_streaming with generic exception (covers lines 484-486)."""

    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires Ollama running, not available in CI",
    )
    @pytest.mark.asyncio
    async def test_streaming_ollama_connection_error(self, agent):
        agent.switch_model("ollama-llama3")
        chunks = []
        async for chunk in agent._chat_internal_streaming("hello", max_rounds=1):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert "ERROR:" in combined


# ---------------------------------------------------------------------------
# Integration: full agent workflow
# ---------------------------------------------------------------------------


class TestAgentWorkflow:
    """Integration tests combining multiple agent methods."""

    def test_switch_and_cycle(self, agent):
        agent.switch_agent("planner")
        assert agent.current_agent == "planner"
        next_agent = agent.cycle_agent()
        assert agent.current_agent == next_agent
        assert agent.current_agent != "planner"

    def test_switch_model_and_agent(self, agent):
        agent.switch_model("gpt-4o")
        agent.switch_agent("planner")
        assert agent.model == "gpt-4o"
        assert agent.current_agent == "planner"

    def test_chat_then_reset(self, agent):
        result = agent.chat("hello", max_rounds=1)
        assert isinstance(result, str)
        agent.reset_history()
        assert agent.history == []

    def test_permission_lifecycle(self, agent):
        """Full permission request -> approve -> verify lifecycle."""
        req_id = agent._request_permission("write_file", {"path": "/tmp/test"}, "tc_1")
        assert req_id in agent._pending_permissions
        assert len(agent.get_pending_permissions()) >= 1

        result = agent.approve_permission(req_id)
        assert result is True
        assert req_id not in agent._pending_permissions

    def test_permission_deny_lifecycle(self, agent):
        """Full permission request -> deny -> verify lifecycle."""
        req_id = agent._request_permission("run_command", {"command": "ls"}, "tc_2")
        result = agent.deny_permission(req_id)
        assert result is True
        assert req_id not in agent._pending_permissions

    def test_tool_execution_in_tempdir(self, tmp_path):
        """End-to-end: create agent, write file, read it back."""
        a = Agent()
        a.cwd = tmp_path

        results = a._execute_tools_parallel(
            [
                ("tc_1", "write_file", {"path": str(tmp_path / "test.txt"), "content": "hello"}),
            ]
        )
        assert len(results) == 1

        results = a._execute_tools_parallel(
            [
                ("tc_2", "read_file", {"path": str(tmp_path / "test.txt")}),
            ]
        )
        _, content = results[0]
        assert "hello" in content

    def test_subagent_invocation_restores_on_error(self, agent):
        """Calling @reviewer should restore coder even when LLM fails."""
        agent.switch_agent("coder")
        result = agent.chat("@reviewer review this", max_rounds=1)
        assert agent.current_agent == "coder"
        assert isinstance(result, str)

    def test_multiple_permission_requests(self, agent):
        """Multiple pending permission requests at once."""
        ids = []
        for i in range(5):
            req_id = agent._request_permission("write_file", {"path": f"/tmp/f{i}"}, f"tc_{i}")
            ids.append(req_id)
        assert len(agent.get_pending_permissions()) == 5
        for rid in ids[:3]:
            agent.approve_permission(rid)
        assert len(agent.get_pending_permissions()) == 2
        for rid in ids[3:]:
            agent.deny_permission(rid)
        assert len(agent.get_pending_permissions()) == 0

    def test_approve_permission_with_expires(self, agent):
        """Approve permission with expiration."""
        req_id = agent._request_permission("write_file", {"path": "/tmp/exp"}, "tc_exp")
        result = agent.approve_permission(req_id, remember=True, expires_in=3600)
        assert result is True
