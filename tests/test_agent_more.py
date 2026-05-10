"""More tests for agent module."""

import pytest
from apex.agent import Agent
from apex.config import Config


class TestAgentInit:
    """Test agent initialization."""

    def test_agent_default_init(self):
        """Test default initialization."""
        agent = Agent()
        assert agent.model is not None
        assert agent.config is not None

    def test_agent_with_config(self):
        """Test initialization with config."""
        config = Config()
        agent = Agent(config=config)
        assert agent.config == config


class TestAgentProperties:
    """Test agent properties."""

    @pytest.fixture
    def agent(self):
        return Agent()

    def test_current_agent_property(self, agent):
        """Test current_agent property."""
        assert hasattr(agent, 'current_agent')
        assert isinstance(agent.current_agent, str)

    def test_cwd_property(self, agent):
        """Test cwd property."""
        assert hasattr(agent, 'cwd')
        assert agent.cwd is not None

    def test_usage_property(self, agent):
        """Test usage property."""
        assert hasattr(agent, 'usage')
        assert isinstance(agent.usage, dict)


class TestAgentModel:
    """Test agent model switching."""

    @pytest.fixture
    def agent(self):
        return Agent()

    def test_switch_model_valid(self, agent):
        """Test switching to valid model."""
        result = agent.switch_model("claude-3.5-sonnet")
        assert result is True

    def test_switch_model_invalid(self, agent):
        """Test switching to invalid model."""
        result = agent.switch_model("nonexistent-model")
        assert result is False


class TestAgentCwd:
    """Test agent cwd handling."""

    @pytest.fixture
    def agent(self):
        return Agent()

    def test_cwd_setter(self, agent):
        """Test cwd setter."""
        from pathlib import Path
        new_path = Path("/tmp")
        agent.cwd = new_path
        assert agent.cwd == new_path


class TestAgentUsage:
    """Test usage tracking."""

    @pytest.fixture
    def agent(self):
        return Agent()

    def test_usage_keys(self, agent):
        """Test usage has expected keys."""
        usage = agent.usage
        assert 'prompt_tokens' in usage
        assert 'completion_tokens' in usage
        assert 'total_tokens' in usage


class TestAgentHistory:
    """Test agent history."""

    @pytest.fixture
    def agent(self):
        return Agent()

    def test_history_attribute(self, agent):
        """Test history attribute exists."""
        assert hasattr(agent, 'history')
        assert isinstance(agent.history, list)