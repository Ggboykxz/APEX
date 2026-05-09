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
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = MagicMock()
            agent.switch_model.return_value = True
            agent.model = "gpt-4o"
            agent.cwd = Path(tmpdir)
            agent.history = []
            agent.reset_history = MagicMock()
            agent.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            agent.cycle_reasoning_effort.return_value = "high"
            agent.switch_agent.return_value = True
            agent.current_agent = "build"
            yield agent

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
        mock_agent.cycle_reasoning_effort.assert_called_once()

    def test_models_command(self, mock_agent, mock_ui):
        """Test /models command."""
        from apex.main import handle_command
        result = handle_command("/models", mock_agent, mock_ui)
        assert result is True

    def test_cwd_command(self, mock_agent, mock_ui):
        """Test /cwd command."""
        from apex.main import handle_command
        with patch('pathlib.Path.mkdir', return_value=None):
            result = handle_command("/cwd /test", mock_agent, mock_ui)
            assert result is True