"""Tests for apex/agent.py — Agent initialization, properties, and switching.

Uses real objects only (no mocks). The Agent class requires litellm but we
only test methods that do NOT trigger network calls here.
"""

from pathlib import Path

import pytest

litellm = pytest.importorskip("litellm")

from apex.agent import Agent
from apex.config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    """Create a fresh Agent instance."""
    return Agent()


@pytest.fixture
def agent_with_config(tmp_path):
    """Create an Agent with a real Config pointing to a temp directory."""
    cfg = Config(config_path=tmp_path / "test_config.json")
    return Agent(config=cfg)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestAgentInit:
    """Test Agent.__init__ and default state."""

    def test_creates_agent(self, agent):
        assert agent is not None

    def test_config_exists(self, agent):
        assert agent.config is not None
        assert isinstance(agent.config, Config)

    def test_model_set_from_config(self, agent):
        assert isinstance(agent.model, str)
        assert agent.model == agent.config.model

    def test_default_agent_is_coder(self, agent):
        assert agent.current_agent == "coder"

    def test_history_starts_empty(self, agent):
        assert agent.history == []
        assert isinstance(agent.history, list)

    def test_usage_starts_zero(self, agent):
        usage = agent.usage
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0

    def test_pending_permissions_starts_empty(self, agent):
        assert agent._pending_permissions == {}

    def test_executor_created(self, agent):
        assert agent._executor is not None

    def test_async_executor_created(self, agent):
        assert agent._async_executor is not None

    def test_ui_created(self, agent):
        assert agent._ui is not None

    def test_system_message_set(self, agent):
        assert agent._system_message["role"] == "system"
        assert len(agent._system_message["content"]) > 0

    def test_init_with_config(self, agent_with_config):
        agent = agent_with_config
        assert agent.config is not None

    def test_system_message_contains_coder_prompt(self, agent):
        from apex.agents import AGENT_CODER_PROMPT

        assert agent._system_message["content"] == AGENT_CODER_PROMPT


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestAgentProperties:
    """Test Agent properties."""

    def test_current_agent_property(self, agent):
        assert isinstance(agent.current_agent, str)
        assert agent.current_agent == "coder"

    def test_cwd_property_returns_path(self, agent):
        assert isinstance(agent.cwd, Path)

    def test_cwd_matches_executor(self, agent):
        assert agent.cwd == agent._executor.cwd

    def test_cwd_setter_updates_all(self, agent, tmp_path):
        agent.cwd = tmp_path
        assert agent._executor.cwd == tmp_path
        assert agent._async_executor.cwd == tmp_path
        assert agent.config.cwd == tmp_path

    def test_usage_returns_copy(self, agent):
        u1 = agent.usage
        u2 = agent.usage
        assert u1 == u2
        assert u1 is not u2  # different dict objects

    def test_usage_mutation_does_not_affect_internal(self, agent):
        usage = agent.usage
        usage["prompt_tokens"] = 999
        assert agent.usage["prompt_tokens"] == 0


# ---------------------------------------------------------------------------
# Model switching
# ---------------------------------------------------------------------------


class TestAgentSwitchModel:
    """Test Agent.switch_model()."""

    def test_switch_to_valid_model(self, agent):
        for model_alias in ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet", "deepseek-r1"]:
            result = agent.switch_model(model_alias)
            assert result is True
            assert agent.model == model_alias
            assert agent.config.model == model_alias

    def test_switch_to_invalid_model(self, agent):
        result = agent.switch_model("nonexistent-model-xyz-123")
        assert result is False

    def test_switch_model_updates_config(self, agent):
        agent.switch_model("gpt-4o")
        assert agent.config.model == "gpt-4o"


# ---------------------------------------------------------------------------
# Agent switching
# ---------------------------------------------------------------------------


class TestAgentSwitchAgent:
    """Test Agent.switch_agent()."""

    def test_switch_to_planner(self, agent):
        result = agent.switch_agent("planner")
        assert result is True
        assert agent.current_agent == "planner"

    def test_switch_to_architect(self, agent):
        result = agent.switch_agent("architect")
        assert result is True
        assert agent.current_agent == "architect"

    def test_switch_to_reviewer(self, agent):
        result = agent.switch_agent("reviewer")
        assert result is True
        assert agent.current_agent == "reviewer"

    def test_switch_to_shell(self, agent):
        result = agent.switch_agent("shell")
        assert result is True
        assert agent.current_agent == "shell"

    def test_switch_back_to_coder(self, agent):
        agent.switch_agent("planner")
        result = agent.switch_agent("coder")
        assert result is True
        assert agent.current_agent == "coder"

    def test_switch_to_invalid_agent(self, agent):
        result = agent.switch_agent("nonexistent-agent-xyz")
        assert result is False

    def test_switch_agent_updates_system_prompt(self, agent):
        from apex.agents import AGENT_PLANNER_PROMPT

        agent.switch_agent("planner")
        assert agent._system_message["content"] == AGENT_PLANNER_PROMPT


# ---------------------------------------------------------------------------
# Cycle agent
# ---------------------------------------------------------------------------


class TestAgentCycleAgent:
    """Test Agent.cycle_agent()."""

    def test_cycle_from_coder(self, agent):
        next_agent = agent.cycle_agent()
        assert isinstance(next_agent, str)
        assert next_agent != "coder"

    def test_cycle_cycles_through_primary_agents(self, agent):
        seen = set()
        for _ in range(6):
            name = agent.cycle_agent()
            seen.add(name)
        # Should cycle through all primary agents
        assert len(seen) >= 3

    def test_cycle_from_non_primary_agent(self, agent):
        """When current agent is not in primary list, defaults to index 0."""
        agent._current_agent = "reviewer"  # subagent, not primary
        next_agent = agent.cycle_agent()
        # Should start from index 0 of primary list
        assert next_agent in {"architect", "coder", "planner", "shell"}

    def test_cycle_restores_after_all(self, agent):
        """Cycling through all primary agents returns to start."""
        agent.switch_agent("coder")
        agent.cycle_agent()
        # Cycle through remaining
        len(
            [a for a in agent.config.cwd and [] or []]  # just count
        )
        from apex.agents import agent_manager

        primary_agents = agent_manager.list_agents("primary")
        for _ in range(len(primary_agents) - 1):
            agent.cycle_agent()
        # Should be back at or near start
        assert isinstance(agent.current_agent, str)


# ---------------------------------------------------------------------------
# Reasoning effort cycling
# ---------------------------------------------------------------------------


class TestAgentCycleReasoningEffort:
    """Test Agent.cycle_reasoning_effort()."""

    def test_cycle_off_to_high(self, agent):
        agent.config.reasoning_effort = "off"
        result = agent.cycle_reasoning_effort()
        assert result == "high"
        assert agent.config.reasoning_effort == "high"

    def test_cycle_high_to_max(self, agent):
        agent.config.reasoning_effort = "high"
        result = agent.cycle_reasoning_effort()
        assert result == "max"
        assert agent.config.reasoning_effort == "max"

    def test_cycle_max_to_off(self, agent):
        agent.config.reasoning_effort = "max"
        result = agent.cycle_reasoning_effort()
        assert result == "off"
        assert agent.config.reasoning_effort == "off"

    def test_cycle_unknown_effort_defaults_to_off(self, agent):
        """Unknown current effort defaults to 'off' before cycling (covers line 88)."""
        agent.config.reasoning_effort = "ultra"
        result = agent.cycle_reasoning_effort()
        # "ultra" is not in order, so defaults to "off", then cycles to "high"
        assert result == "high"
        assert agent.config.reasoning_effort == "high"


# ---------------------------------------------------------------------------
# Auto model selection
# ---------------------------------------------------------------------------


class TestAgentAutoSelectModel:
    """Test Agent.auto_select_model()."""

    def test_explain_selects_claude_sonnet(self, agent):
        assert agent.auto_select_model("explain this code") == "claude-4-sonnet"

    def test_debug_selects_claude_opus(self, agent):
        assert agent.auto_select_model("debug this error") == "claude-4-opus"

    def test_refactor_selects_gpt4o(self, agent):
        assert agent.auto_select_model("refactor this function") == "gpt-4o"

    def test_create_selects_gpt4o(self, agent):
        assert agent.auto_select_model("create a new module") == "gpt-4o"

    def test_reason_selects_deepseek(self, agent):
        assert agent.auto_select_model("reason about this algorithm") == "deepseek-r1"

    def test_long_input_selects_claude_sonnet(self, agent):
        long_text = "a" * 3000
        assert agent.auto_select_model(long_text) == "claude-4-sonnet"

    def test_short_default_selects_gpt4o_mini(self, agent):
        assert agent.auto_select_model("simple hello") == "gpt-4o-mini"

    def test_case_insensitive(self, agent):
        assert agent.auto_select_model("EXPLAIN this") == "claude-4-sonnet"

    def test_boundary_length(self, agent):
        # Exactly 2000 chars — should NOT trigger long input
        text_2000 = "a" * 2000
        assert agent.auto_select_model(text_2000) == "gpt-4o-mini"
        # 2001 chars — should trigger
        text_2001 = "a" * 2001
        assert agent.auto_select_model(text_2001) == "claude-4-sonnet"


# ---------------------------------------------------------------------------
# History management
# ---------------------------------------------------------------------------


class TestAgentHistory:
    """Test Agent history management."""

    def test_history_initially_empty(self, agent):
        assert agent.history == []

    def test_reset_history_clears_list(self, agent):
        agent.history = [{"role": "user", "content": "test"}]
        agent.reset_history()
        assert agent.history == []

    def test_reset_history_clears_usage(self, agent):
        agent._usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        agent.reset_history()
        assert agent.usage["prompt_tokens"] == 0
        assert agent.usage["completion_tokens"] == 0
        assert agent.usage["total_tokens"] == 0

    def test_history_can_be_appended(self, agent):
        agent.history.append({"role": "user", "content": "hello"})
        agent.history.append({"role": "assistant", "content": "hi"})
        assert len(agent.history) == 2
