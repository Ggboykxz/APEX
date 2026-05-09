"""Comprehensive tests for main module - all command handlers."""

import pytest
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestParseArgsExtended:
    """Extended tests for parse_args."""

    def test_parse_args_tui_flag(self):
        """Test parsing with --tui flag."""
        with patch('sys.argv', ['apex', '-t', 'prompt']):
            from apex.main import parse_args
            args = parse_args()
            assert args.tui is True


class TestHandleCommandBasic:
    """Test handle_command with basic functionality."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        agent = MagicMock()
        agent.switch_model.return_value = True
        agent.model = "gpt-4o"
        agent.cwd = Path.cwd()
        agent.history = []
        agent.reset_history = MagicMock()
        agent.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        agent.cycle_reasoning_effort.return_value = "high"
        agent.switch_agent.return_value = True
        agent.current_agent = "build"
        return agent

    @pytest.fixture
    def mock_ui(self):
        """Create mock UI."""
        ui = MagicMock()
        ui.console = MagicMock()
        ui.show_models = MagicMock()
        ui.print_error = MagicMock()
        ui.print_success = MagicMock()
        ui.print_info = MagicMock()
        return ui

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.auto_model = False
        config.reasoning_effort = "off"
        config.agent_mode = "agent"
        return config

    def test_reasoning_command(self, mock_agent, mock_ui, mock_config):
        """Test /reasoning command."""
        from apex.main import handle_command
        result = handle_command("/reasoning", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_cwd_current(self, mock_agent, mock_ui, mock_config):
        """Test /cwd without path."""
        from apex.main import handle_command
        result = handle_command("/cwd", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_cwd_with_valid_path(self, mock_agent, mock_ui, mock_config):
        """Test /cwd with valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from apex.main import handle_command
            result = handle_command(f"/cwd {tmpdir}", mock_agent, mock_ui, mock_config)
            assert result is True

    def test_clear_command(self, mock_agent, mock_ui, mock_config):
        """Test /clear command."""
        from apex.main import handle_command
        result = handle_command("/clear", mock_agent, mock_ui, mock_config)
        assert result is True
        mock_agent.reset_history.assert_called_once()

    def test_history_empty(self, mock_agent, mock_ui, mock_config):
        """Test /history with empty history."""
        from apex.main import handle_command
        result = handle_command("/history", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_history_with_data(self, mock_agent, mock_ui, mock_config):
        """Test /history with non-empty history."""
        mock_agent.history = [{"role": "user", "content": "test"}]
        from apex.main import handle_command
        result = handle_command("/history", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_model_auto(self, mock_agent, mock_ui, mock_config):
        """Test /model auto command."""
        from apex.main import handle_command
        result = handle_command("/model auto", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_models_list(self, mock_agent, mock_ui, mock_config):
        """Test /models command."""
        from apex.main import handle_command
        result = handle_command("/models", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_plan_switch(self, mock_agent, mock_ui, mock_config):
        """Test /plan command."""
        from apex.main import handle_command
        result = handle_command("/plan", mock_agent, mock_ui, mock_config)
        assert result is True
        mock_agent.switch_agent.assert_called_with("plan")

    def test_build_switch(self, mock_agent, mock_ui, mock_config):
        """Test /build command."""
        from apex.main import handle_command
        result = handle_command("/build", mock_agent, mock_ui, mock_config)
        assert result is True
        mock_agent.switch_agent.assert_called_with("build")

    def test_unknown_command(self, mock_agent, mock_ui, mock_config):
        """Test unknown command."""
        from apex.main import handle_command
        result = handle_command("/unknowncmd", mock_agent, mock_ui, mock_config)
        assert result is True

    def test_non_slash_input(self, mock_agent, mock_ui, mock_config):
        """Test non-slash input returns False."""
        from apex.main import handle_command
        result = handle_command("hello world", mock_agent, mock_ui, mock_config)
        assert result is False


class TestListModels:
    """Test list_models function."""

    @pytest.fixture
    def mock_ui(self):
        """Create mock UI."""
        return MagicMock()

    def test_list_models_creates_config(self, mock_ui):
        """Test list_models creates Config."""
        with patch('apex.main.Config') as MockConfig:
            MockConfig.return_value.model = "gpt-4o"
            from apex.main import list_models
            list_models(mock_ui)
            MockConfig.assert_called_once()


class TestMemoryGlobal:
    """Test global memory instance."""

    def test_memory_exists(self):
        """Test memory global exists."""
        from apex.main import memory
        assert memory is not None