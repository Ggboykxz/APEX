"""Comprehensive tests for agent.py."""

import pytest
from apex.agent import Agent


class TestAgentCore:
    """Test core Agent functionality."""

    @pytest.fixture
    def agent(self):
        """Create Agent instance."""
        return Agent()

    def test_init_creates_executor(self, agent):
        """Test init creates executor."""
        assert agent._executor is not None

    def test_init_creates_ui(self, agent):
        """Test init creates UI."""
        assert agent._ui is not None

    def test_init_sets_current_agent(self, agent):
        """Test init sets default agent."""
        assert agent.current_agent == "coder"

    def test_init_creates_system_message(self, agent):
        """Test init creates system message."""
        assert hasattr(agent, "_system_message")
        assert agent._system_message["role"] == "system"

    def test_cwd_setter(self, agent, tmp_path):
        """Test cwd setter updates executors."""
        agent.cwd = tmp_path
        assert agent._executor.cwd == tmp_path
        assert agent._async_executor.cwd == tmp_path

    def test_switch_model_valid(self, agent):
        """Test switch_model with valid model."""
        result = agent.switch_model("claude-3.5-sonnet")
        assert result is True
        assert agent.model == "claude-3.5-sonnet"

    def test_switch_model_invalid(self, agent):
        """Test switch_model with invalid model."""
        result = agent.switch_model("nonexistent-model-xyz")
        assert result is False

    def test_switch_agent_valid(self, agent):
        """Test switch_agent with valid agent."""
        result = agent.switch_agent("planner")
        assert result is True
        assert agent.current_agent == "planner"

    def test_switch_agent_invalid(self, agent):
        """Test switch_agent with invalid agent."""
        result = agent.switch_agent("nonexistent-agent-xyz")
        assert result is False


class TestAgentAutoModel:
    """Test auto model selection."""

    @pytest.fixture
    def agent(self):
        """Create Agent instance."""
        return Agent()

    def test_auto_select_explain(self, agent):
        """Test auto select for explain."""
        model = agent.auto_select_model("explain this code")
        assert model == "claude-4-sonnet"

    def test_auto_select_debug(self, agent):
        """Test auto select for debug."""
        model = agent.auto_select_model("debug this error")
        assert model == "claude-4-opus"

    def test_auto_select_refactor(self, agent):
        """Test auto select for refactor."""
        model = agent.auto_select_model("refactor this function")
        assert model == "gpt-4o"

    def test_auto_select_create(self, agent):
        """Test auto select for create."""
        model = agent.auto_select_model("create a new file")
        assert model == "gpt-4o"

    def test_auto_select_reason(self, agent):
        """Test auto select for reasoning."""
        model = agent.auto_select_model("reason about this algorithm")
        assert model == "deepseek-r1"

    def test_auto_select_long_input(self, agent):
        """Test auto select for long input."""
        long_text = "a" * 3000
        model = agent.auto_select_model(long_text)
        assert model == "claude-4-sonnet"

    def test_auto_select_default(self, agent):
        """Test auto select default."""
        model = agent.auto_select_model("simple hello")
        assert model == "gpt-4o-mini"


class TestAgentReasoning:
    """Test reasoning effort cycling."""

    @pytest.fixture
    def agent(self):
        """Create Agent instance."""
        return Agent()

    def test_cycle_reasoning_off_to_high(self, agent):
        """Test cycling from off to high."""
        agent.config.reasoning_effort = "off"
        result = agent.cycle_reasoning_effort()
        assert result == "high"

    def test_cycle_reasoning_high_to_max(self, agent):
        """Test cycling from high to max."""
        agent.config.reasoning_effort = "high"
        result = agent.cycle_reasoning_effort()
        assert result == "max"

    def test_cycle_reasoning_max_to_off(self, agent):
        """Test cycling from max to off."""
        agent.config.reasoning_effort = "max"
        result = agent.cycle_reasoning_effort()
        assert result == "off"


class TestAgentHistory:
    """Test history management."""

    @pytest.fixture
    def agent(self):
        """Create Agent instance."""
        return Agent()

    def test_history_initially_empty(self, agent):
        """Test history is initially empty."""
        assert agent.history == []

    def test_reset_history(self, agent):
        """Test reset_history method."""
        agent.history = [{"role": "user", "content": "test"}]
        agent._usage = {"prompt_tokens": 100, "completion_tokens": 50}
        agent.reset_history()
        assert agent.history == []
        assert agent.usage["total_tokens"] == 0


class TestAgentParsing:
    """Test agent parsing methods."""

    @pytest.fixture
    def agent(self):
        """Create Agent instance."""
        return Agent()

    def test_parse_subagent_invocation_valid(self, agent):
        """Test parsing valid subagent invocation."""
        subagent, task = agent._parse_subagent_invocation("@reviewer fix this")
        assert subagent == "reviewer"
        assert task == "fix this"

    def test_parse_subagent_invocation_invalid(self, agent):
        """Test parsing without subagent invocation."""
        subagent, task = agent._parse_subagent_invocation("just a regular message")
        assert subagent is None
        assert task == "just a regular message"

    def test_check_tool_permission_allowed(self, agent):
        """Test tool permission check."""
        allowed, message = agent._check_tool_permission("read_file")
        assert allowed is True

    def test_check_tool_permission_denied(self, agent):
        """Test tool permission denied for planner agent."""
        agent.switch_agent("planner")
        allowed, message = agent._check_tool_permission("write_file")
        assert allowed is False
