"""Tests for refactored UI module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from apex.refactored_ui import (
    UI, AGENT_COLORS, COLOR_MAP, create_ui
)


class MockConsole:
    def __init__(self):
        self.output = []
    
    def print(self, text):
        self.output.append(text)


class TestUI:
    def test_init_default(self):
        ui = UI()
        assert ui.console is not None
        assert ui._color_map == COLOR_MAP

    def test_init_custom_console(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        assert ui.console is mock_console

    def test_init_custom_color_map(self):
        custom_map = {"primary": "blue"}
        ui = UI(color_map=custom_map)
        assert ui._color_map == custom_map

    def test_show_banner_build_agent(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.show_banner("gpt-4", "/workspace", "build")
        
        assert mock_console.print.called

    def test_show_banner_plan_agent(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.show_banner("gpt-4", "/workspace", "plan")
        
        assert mock_console.print.called

    def test_show_banner_unknown_agent(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.show_banner("gpt-4", "/workspace", "unknown")
        
        assert mock_console.print.called

    def test_show_help(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.show_help()
        
        assert mock_console.print.called

    def test_show_models(self):
        mock_console = MagicMock()
        ui = UI(
            console=mock_console,
            model_provider=lambda: {"gpt-4": "openai/gpt-4", "claude": "anthropic/claude"}
        )
        
        ui.show_models("gpt-4")
        
        assert mock_console.print.called

    def test_print_user(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_user("Hello world")
        
        mock_console.print.assert_called_once()

    def test_print_thinking(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        result = ui.print_thinking("Thinking...")
        
        assert result is not None

    def test_print_response_plain(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_response("Hello world")
        
        mock_console.print.assert_called()

    def test_print_response_with_code(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_response("```python\nprint('hello')\n```")
        
        assert mock_console.print.call_count >= 1

    def test_print_tool_call(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_tool_call("read_file", {"path": "/test.py"})
        
        mock_console.print.assert_called_once()

    def test_print_tool_result_error(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_tool_result("read_file", "ERROR: File not found")
        
        mock_console.print.assert_called_once()

    def test_print_tool_result_success(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_tool_result("read_file", "SUCCESS: File read")
        
        mock_console.print.assert_called_once()

    def test_print_tool_result_normal(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_tool_result("read_file", "file content here")
        
        mock_console.print.assert_called_once()

    def test_print_tool_result_truncate(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        long_result = "x" * 3000
        ui.print_tool_result("read_file", long_result)
        
        mock_console.print.assert_called_once()

    def test_print_error(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_error("Something went wrong")
        
        mock_console.print.assert_called_once()

    def test_print_success(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_success("Operation completed")
        
        mock_console.print.assert_called_once()

    def test_print_info(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        ui.print_info("Some information")
        
        mock_console.print.assert_called_once()

    def test_print_cost(self):
        mock_console = MagicMock()
        ui = UI(console=mock_console)
        
        usage = {"input": 1000, "output": 500}
        ui.print_cost(usage)
        
        assert mock_console.print.call_count == 2

    def test_get_color(self):
        ui = UI()
        
        assert ui.get_color("primary") == "cyan"
        assert ui.get_color("unknown") == "white"


class TestConstants:
    def test_agent_colors(self):
        assert AGENT_COLORS["build"] == "cyan"
        assert AGENT_COLORS["plan"] == "yellow"
        assert AGENT_COLORS["explore"] == "green"
        assert AGENT_COLORS["general"] == "magenta"

    def test_color_map(self):
        assert COLOR_MAP["primary"] == "cyan"
        assert COLOR_MAP["success"] == "green"
        assert COLOR_MAP["error"] == "red"


class TestFactoryFunctions:
    def test_create_ui(self):
        ui = create_ui()
        assert isinstance(ui, UI)

    def test_create_ui_with_custom_console(self):
        mock_console = MagicMock()
        ui = create_ui(console=mock_console)
        assert ui.console is mock_console