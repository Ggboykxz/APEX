"""Tests for UI module — no mocks, real Rich console objects."""

import io

from rich.console import Console

from apex.ui import UI, APEXTheme, create_ui, get_available_themes


# ---------------------------------------------------------------------------
# APEXTheme tests
# ---------------------------------------------------------------------------


class TestAPEXThemeGet:
    def test_get_default(self):
        theme = APEXTheme.get()
        assert isinstance(theme, dict)
        assert theme == APEXTheme.DRACULA

    def test_get_dracula(self):
        theme = APEXTheme.get("dracula")
        assert theme == APEXTheme.DRACULA
        assert "bg" in theme
        assert "fg" in theme
        assert "red" in theme
        assert "green" in theme

    def test_get_nord(self):
        theme = APEXTheme.get("nord")
        assert theme == APEXTheme.NORD
        assert theme["bg"] == "#2E3440"

    def test_get_one_dark(self):
        theme = APEXTheme.get("one_dark")
        assert theme == APEXTheme.ONE_DARK
        assert theme["bg"] == "#282C34"

    def test_get_unknown_returns_dracula(self):
        theme = APEXTheme.get("nonexistent")
        assert theme == APEXTheme.DRACULA

    def test_get_case_insensitive(self):
        # The get method does .upper() on the name
        theme = APEXTheme.get("DRACULA")
        assert theme == APEXTheme.DRACULA
        theme2 = APEXTheme.get("Nord")
        assert theme2 == APEXTheme.NORD

    def test_all_themes_have_required_keys(self):
        required_keys = [
            "bg",
            "fg",
            "red",
            "green",
            "yellow",
            "orange",
            "purple",
            "cyan",
            "pink",
            "white",
            "gray",
        ]
        for name in ["dracula", "nord", "one_dark"]:
            theme = APEXTheme.get(name)
            for key in required_keys:
                assert key in theme, f"Missing key '{key}' in theme '{name}'"


# ---------------------------------------------------------------------------
# UI initialization tests
# ---------------------------------------------------------------------------


class TestUIInit:
    def test_default_theme(self):
        ui = UI()
        assert ui.theme_name == "dracula"
        assert ui.theme == APEXTheme.DRACULA

    def test_custom_theme(self):
        ui = UI(theme="nord")
        assert ui.theme_name == "nord"
        assert ui.theme == APEXTheme.NORD

    def test_one_dark_theme(self):
        ui = UI(theme="one_dark")
        assert ui.theme_name == "one_dark"
        assert ui.theme == APEXTheme.ONE_DARK

    def test_console_is_rich_console(self):
        ui = UI()
        assert isinstance(ui.console, Console)

    def test_icons_dict(self):
        ui = UI()
        assert isinstance(ui.ICONS, dict)
        expected_keys = [
            "agent",
            "model",
            "folder",
            "file",
            "git",
            "success",
            "error",
            "warning",
            "info",
            "code",
            "thinking",
            "tool",
            "search",
            "edit",
            "delete",
            "create",
        ]
        for key in expected_keys:
            assert key in ui.ICONS


# ---------------------------------------------------------------------------
# UI color helper tests
# ---------------------------------------------------------------------------


class TestUIColorHelper:
    def test_c_plain(self):
        ui = UI()
        result = ui._c("red", "hello")
        assert "[red]hello[/red]" in result

    def test_c_bold(self):
        ui = UI()
        result = ui._c("cyan", "bold text", bold=True)
        assert "[bold cyan]bold text[/bold cyan]" in result

    def test_t_method(self):
        ui = UI()
        result = ui._t("red")
        assert result == ui.theme["red"]

    def test_t_missing_key(self):
        ui = UI()
        result = ui._t("nonexistent_key")
        assert result == "white"  # default


# ---------------------------------------------------------------------------
# UI print methods (capture console output)
# ---------------------------------------------------------------------------


class TestUIPrintMethods:
    """Test that UI print methods don't crash and produce output."""

    def _make_ui_with_capture(self):
        """Create UI with a captured console for testing output."""
        console = Console(file=io.StringIO(), width=120, force_terminal=True)
        ui = UI()
        ui.console = console
        return ui

    def test_show_banner(self):
        ui = self._make_ui_with_capture()
        ui.show_banner(model="gpt-4o", cwd="/tmp", agent="build")
        output = ui.console.file.getvalue()
        assert "APEX" in output

    def test_show_banner_different_agents(self):
        for agent in ["build", "plan", "reviewer", "shell", "planner"]:
            ui = self._make_ui_with_capture()
            ui.show_banner(model="gpt-4o", cwd="/tmp", agent=agent)
            output = ui.console.file.getvalue()
            assert len(output) > 0

    def test_show_help(self):
        ui = self._make_ui_with_capture()
        ui.show_help()
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_show_models(self):
        ui = self._make_ui_with_capture()
        ui.show_models("gpt-4o")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_show_models_different_current(self):
        ui = self._make_ui_with_capture()
        ui.show_models("claude-4-sonnet")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_user(self):
        ui = self._make_ui_with_capture()
        ui.print_user("Hello world")
        output = ui.console.file.getvalue()
        assert "Hello world" in output

    def test_print_thinking(self):
        ui = self._make_ui_with_capture()
        status = ui.print_thinking("Thinking")
        # Returns a Status context manager
        assert status is not None

    def test_print_response_plain(self):
        ui = self._make_ui_with_capture()
        ui.print_response("Hello, this is a plain response.")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_response_with_code(self):
        ui = self._make_ui_with_capture()
        ui.print_response("Here is code:\n```python\nprint('hello')\n```\nDone.")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_response_with_unknown_lang(self):
        ui = self._make_ui_with_capture()
        ui.print_response("```\nsome code\n```")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_tool_call(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_call("read_file", {"path": "test.py"})
        output = ui.console.file.getvalue()
        assert "read_file" in output

    def test_print_tool_call_many_args(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_call("edit_file", {"a": "1", "b": "2", "c": "3", "d": "4"})
        output = ui.console.file.getvalue()
        assert "edit_file" in output

    def test_print_tool_result(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_result("read_file", "file contents here")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_tool_result_error(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_result("read_file", "ERROR: file not found")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_tool_result_success(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_result("write_file", "SUCCESS: file written")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_tool_result_warning(self):
        ui = self._make_ui_with_capture()
        ui.print_tool_result("run_command", "WARNING: output truncated")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_tool_result_long(self):
        ui = self._make_ui_with_capture()
        long_result = "x" * 3000
        ui.print_tool_result("tool", long_result)
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_error(self):
        ui = self._make_ui_with_capture()
        ui.print_error("Something went wrong")
        output = ui.console.file.getvalue()
        assert "Something went wrong" in output

    def test_print_success(self):
        ui = self._make_ui_with_capture()
        ui.print_success("Operation completed")
        output = ui.console.file.getvalue()
        assert "Operation completed" in output

    def test_print_warning(self):
        ui = self._make_ui_with_capture()
        ui.print_warning("Be careful")
        output = ui.console.file.getvalue()
        assert "Be careful" in output

    def test_print_info(self):
        ui = self._make_ui_with_capture()
        ui.print_info("FYI")
        output = ui.console.file.getvalue()
        assert "FYI" in output

    def test_print_separator(self):
        ui = self._make_ui_with_capture()
        ui.print_separator()
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_git_status_with_files(self):
        ui = self._make_ui_with_capture()
        ui.print_git_status("main", "modified", ["file1.py", "file2.py"])
        output = ui.console.file.getvalue()
        assert "main" in output

    def test_print_git_status_no_files(self):
        ui = self._make_ui_with_capture()
        ui.print_git_status("main", "clean", [])
        output = ui.console.file.getvalue()
        assert "main" in output

    def test_print_git_status_many_files(self):
        ui = self._make_ui_with_capture()
        files = [f"file{i}.py" for i in range(10)]
        ui.print_git_status("dev", "modified", files)
        output = ui.console.file.getvalue()
        assert "dev" in output

    def test_print_cost(self):
        ui = self._make_ui_with_capture()
        ui.print_cost({"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500})
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_print_welcome_message(self):
        ui = self._make_ui_with_capture()
        ui.print_welcome_message()
        output = ui.console.file.getvalue()
        assert "APEX" in output

    def test_clear(self):
        ui = self._make_ui_with_capture()
        ui.clear()
        # clear() doesn't raise and doesn't produce output to capture


# ---------------------------------------------------------------------------
# Module-level function tests
# ---------------------------------------------------------------------------


class TestCreateUI:
    def test_create_ui_default(self):
        ui = create_ui()
        assert isinstance(ui, UI)
        assert ui.theme_name == "dracula"

    def test_create_ui_custom_theme(self):
        ui = create_ui("nord")
        assert isinstance(ui, UI)
        assert ui.theme_name == "nord"


class TestGetAvailableThemes:
    def test_returns_list(self):
        themes = get_available_themes()
        assert isinstance(themes, list)
        assert "dracula" in themes
        assert "nord" in themes
        assert "one_dark" in themes

    def test_all_themes_are_strings(self):
        themes = get_available_themes()
        for t in themes:
            assert isinstance(t, str)


class TestShowModelsFreeAndActive:
    """Hit lines 226 (current model active) and 228 (free model)."""

    def test_show_models_with_current_active(self, monkeypatch):
        ui = UI()
        console = Console(file=io.StringIO(), width=120, force_terminal=True)
        ui.console = console
        # Use a model in the first 25 sorted keys
        ui.show_models("claude-sonnet-4")
        output = ui.console.file.getvalue()
        assert len(output) > 0

    def test_show_models_with_free_model(self, monkeypatch):
        import apex.config as cfg

        # Add a free model early in MODELS so it appears in first 25
        original = dict(cfg.MODELS)
        cfg.MODELS["aaa-free-test"] = "test/free-model"
        try:
            ui = UI()
            console = Console(file=io.StringIO(), width=120, force_terminal=True)
            ui.console = console
            ui.show_models("other")
            output = ui.console.file.getvalue()
            assert "Free" in output or "●" in output
        finally:
            cfg.MODELS.clear()
            cfg.MODELS.update(original)
