"""Tests for agent module."""

import tempfile
from pathlib import Path
from apex.agent import Agent


class TestAgent:
    """Test Agent class - real instantiation."""

    def test_agent_init(self):
        """Test agent initialization."""
        agent = Agent()
        assert agent is not None
        assert hasattr(agent, 'config')
        assert hasattr(agent, 'model')
        assert hasattr(agent, 'history')

    def test_agent_current_agent_property(self):
        """Test current_agent property."""
        agent = Agent()
        assert agent.current_agent == "build"

    def test_agent_cwd_property(self):
        """Test cwd property."""
        agent = Agent()
        cwd = agent.cwd
        assert cwd is not None
        assert isinstance(cwd, Path)

    def test_agent_cwd_setter(self):
        """Test cwd setter."""
        agent = Agent()
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir)
            agent.cwd = new_path
            assert agent.cwd == new_path

    def test_agent_usage_property(self):
        """Test usage property."""
        agent = Agent()
        usage = agent.usage
        assert isinstance(usage, dict)
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_agent_history_attribute(self):
        """Test history attribute."""
        agent = Agent()
        assert isinstance(agent.history, list)
        assert len(agent.history) == 0  # Empty initially

    def test_agent_model_property(self):
        """Test model property."""
        agent = Agent()
        assert isinstance(agent.model, str)

    def test_agent_switch_model(self):
        """Test switch_model method."""
        agent = Agent()
        result = agent.switch_model("gpt-4o")
        assert result is True
        assert agent.model == "gpt-4o"

    def test_agent_switch_model_invalid(self):
        """Test switch_model with invalid model."""
        agent = Agent()
        result = agent.switch_model("nonexistent-model-xyz")
        assert result is False

    def test_agent_switch_agent(self):
        """Test switch_agent method."""
        agent = Agent()
        result = agent.switch_agent("plan")
        assert result is True
        assert agent.current_agent == "plan"

    def test_agent_switch_agent_invalid(self):
        """Test switch_agent with invalid agent."""
        agent = Agent()
        result = agent.switch_agent("nonexistent-agent-xyz")
        assert result is False

    def test_agent_cycle_agent(self):
        """Test cycle_agent method."""
        agent = Agent()
        agent.current_agent  # just access to ensure it's set
        next_agent = agent.cycle_agent()
        assert isinstance(next_agent, str)

    def test_agent_reset_history(self):
        """Test reset_history method."""
        agent = Agent()
        agent.history = [{"role": "user", "content": "test"}]
        agent.reset_history()
        assert len(agent.history) == 0
        assert agent.usage["total_tokens"] == 0

    def test_agent_chat_method_exists(self):
        """Test chat method exists."""
        agent = Agent()
        assert callable(agent.chat)

    def test_agent_has_executor(self):
        """Test agent has executor attributes."""
        agent = Agent()
        assert hasattr(agent, '_executor')
        assert hasattr(agent, '_async_executor')