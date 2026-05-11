"""Tests for refactored UI module — no mocks, real rich Console."""

from io import StringIO

from rich.console import Console

from apex.refactored_ui import UI, AGENT_COLORS, COLOR_MAP, create_ui, CommandHelp


class TestCommandHelp:
    def test_init(self):
        help_item = CommandHelp(command="/test", description="Test command")
        assert help_item.command == "/test"
        assert help_item.description == "Test command"


class TestUI:
    def test_init_default(self):
        ui = UI()
        assert ui.console is not None
        assert ui._color_map == COLOR_MAP

    def test_init_custom_console(self):
        console = Console()
        ui = UI(console=console)
        assert ui.console is console

    def test_init_custom_color_map(self):
        custom_map = {"primary": "blue"}
        ui = UI(color_map=custom_map)
        assert ui._color_map == custom_map

    def test_init_custom_model_provider(self):
        def provider():
            return {"test": "test/model"}

        ui = UI(model_provider=provider)
        assert ui._model_provider is provider

    def test_show_banner_build_agent(self, capsys):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.show_banner("gpt-4", "/workspace", "build")
        output = console.file.getvalue()
        assert "APEX" in output or "build" in output

    def test_show_banner_plan_agent(self, capsys):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.show_banner("gpt-4", "/workspace", "plan")
        output = console.file.getvalue()
        assert "APEX" in output or "plan" in output

    def test_show_banner_unknown_agent(self, capsys):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.show_banner("gpt-4", "/workspace", "unknown")
        output = console.file.getvalue()
        assert "APEX" in output

    def test_show_help(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.show_help()
        output = console.file.getvalue()
        assert "APEX Commands" in output or "/help" in output

    def test_show_models(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(
            console=console,
            model_provider=lambda: {"gpt-4": "openai/gpt-4", "claude": "anthropic/claude"},
        )
        ui.show_models("gpt-4")
        output = console.file.getvalue()
        assert "gpt-4" in output

    def test_print_user(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_user("Hello world")
        output = console.file.getvalue()
        assert "Hello world" in output

    def test_print_thinking(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        result = ui.print_thinking("Thinking...")
        assert result is not None

    def test_print_response_plain(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_response("Hello world")
        output = console.file.getvalue()
        assert "Hello world" in output

    def test_print_response_with_code(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_response("```python\nprint('hello')\n```")
        output = console.file.getvalue()
        assert "print" in output

    def test_print_response_with_code_no_lang(self):
        console = Console(file=StringIO(), force_terminal=True, width=120, legacy_windows=False)
        ui = UI(console=console)
        ui.print_response("```\ncode here\n```")
        output = console.file.getvalue()
        # Strip ANSI escape codes for robust text matching in CI
        import re
        clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
        assert "code" in clean

    def test_print_tool_call(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_tool_call("read_file", {"path": "/test.py"})
        output = console.file.getvalue()
        assert "read_file" in output

    def test_print_tool_result_error(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_tool_result("read_file", "ERROR: File not found")
        output = console.file.getvalue()
        assert "File not found" in output

    def test_print_tool_result_success(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_tool_result("read_file", "SUCCESS: File read")
        output = console.file.getvalue()
        assert "File read" in output

    def test_print_tool_result_normal(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_tool_result("read_file", "file content here")
        output = console.file.getvalue()
        assert "file content here" in output

    def test_print_tool_result_truncate(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        long_result = "x" * 3000
        ui.print_tool_result("read_file", long_result)
        output = console.file.getvalue()
        # Rich renders [truncated] as a style tag, so we check for "..." indicator
        assert "..." in output

    def test_print_error(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_error("Something went wrong")
        output = console.file.getvalue()
        assert "Something went wrong" in output

    def test_print_success(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_success("Operation completed")
        output = console.file.getvalue()
        assert "Operation completed" in output

    def test_print_info(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        ui.print_info("Some information")
        output = console.file.getvalue()
        assert "Some information" in output

    def test_print_cost(self):
        console = Console(file=StringIO(), force_terminal=True)
        ui = UI(console=console)
        usage = {"input": 1000, "output": 500}
        ui.print_cost(usage)
        output = console.file.getvalue()
        assert "1,000" in output or "1000" in output

    def test_get_color(self):
        ui = UI()
        assert ui.get_color("primary") == "cyan"
        assert ui.get_color("text") == "white"
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
        console = Console()
        ui = create_ui(console=console)
        assert ui.console is console

    def test_create_ui_with_custom_color_map(self):
        custom_map = {"primary": "blue"}
        ui = create_ui(color_map=custom_map)
        assert ui._color_map == custom_map
