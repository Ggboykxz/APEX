"""Tests for ui module."""

from apex.ui import UI, APEXTheme


class TestAPEXTheme:
    """Test APEXTheme class."""

    def test_get_default(self):
        """Test get default theme."""
        theme = APEXTheme.get()
        assert isinstance(theme, dict)
        assert "bg" in theme
        assert "fg" in theme
        assert "red" in theme

    def test_get_dracula(self):
        """Test get dracula theme."""
        theme = APEXTheme.get("dracula")
        assert theme == APEXTheme.DRACULA

    def test_get_nord(self):
        """Test get nord theme."""
        theme = APEXTheme.get("nord")
        assert theme == APEXTheme.NORD

    def test_get_one_dark(self):
        """Test get one_dark theme."""
        theme = APEXTheme.get("one_dark")
        assert theme == APEXTheme.ONE_DARK

    def test_get_unknown_returns_default(self):
        """Test get unknown theme returns default."""
        theme = APEXTheme.get("unknown_theme")
        assert theme == APEXTheme.DRACULA


class TestUI:
    """Test UI class."""

    def test_ui_init_default(self):
        """Test UI initialization with default theme."""
        ui = UI()
        assert ui.theme_name == "dracula"
        assert ui.console is not None
        assert isinstance(ui.ICONS, dict)

    def test_ui_init_custom_theme(self):
        """Test UI initialization with custom theme."""
        ui = UI(theme="nord")
        assert ui.theme_name == "nord"

    def test_ui_c_method(self):
        """Test _c color method."""
        ui = UI()
        result = ui._c("red", "test")
        assert isinstance(result, str)

    def test_ui_print_success(self):
        """Test print_success method."""
        ui = UI()
        ui.print_success("Test message")

    def test_ui_print_error(self):
        """Test print_error method."""
        ui = UI()
        ui.print_error("Test error")

    def test_ui_print_info(self):
        """Test print_info method."""
        ui = UI()
        ui.print_info("Test info")

    def test_ui_print_warning(self):
        """Test print_warning method."""
        ui = UI()
        ui.print_warning("Test warning")

    def test_ui_print_user(self):
        """Test print_user method."""
        ui = UI()
        ui.print_user("User message")

    def test_ui_print_response(self):
        """Test print_response method."""
        ui = UI()
        ui.print_response("Response message")

    def test_ui_print_tool_call(self):
        """Test print_tool_call method."""
        ui = UI()
        ui.print_tool_call("tool_name", {"arg": "value"})

    def test_ui_print_tool_result(self):
        """Test print_tool_result method."""
        ui = UI()
        ui.print_tool_result("tool_name", "result content")

    def test_ui_show_models(self):
        """Test show_models method."""
        ui = UI()
        ui.show_models("gpt-4o")

    def test_ui_show_help(self):
        """Test show_help method."""
        ui = UI()
        ui.show_help()

    def test_ui_icons(self):
        """Test icons are available."""
        ui = UI()
        assert "success" in ui.ICONS
        assert "error" in ui.ICONS
        assert "agent" in ui.ICONS
        assert "model" in ui.ICONS