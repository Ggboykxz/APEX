"""Tests for refactored TUI modules."""

import pytest
from apex.refactored_tui_core import (
    TUIState,
    ThemeManager,
    HistoryManager,
    SessionManager,
    CommandProcessor,
    RefactoredTUI,
)


class TestTUIState:
    """Test TUI state management."""

    def test_default_state(self) -> None:
        state = TUIState()
        assert state.model == "or-gpt4o-mini"
        assert state.cwd == "."
        assert state.token_count == 0
        assert state.is_thinking is False
        assert state.sidebar_visible is True
        assert state.current_theme == "apex-dark"

    def test_state_updates(self) -> None:
        state = TUIState()
        state.model = "claude-sonnet"
        state.token_count = 1500
        state.cost_usd = 0.05

        assert state.model == "claude-sonnet"
        assert state.token_count == 1500
        assert state.cost_usd == 0.05


class TestThemeManager:
    """Test theme manager."""

    def test_default_theme(self) -> None:
        manager = ThemeManager()
        assert manager.current() == "apex-dark"

    def test_cycle_themes(self) -> None:
        manager = ThemeManager()
        themes = []
        for _ in range(5):
            themes.append(manager.cycle())

        assert "apex-dark" in themes
        assert "gabon" in themes
        assert "synthwave" in themes
        assert "solarized" in themes
        assert len(themes) == 5

    def test_set_theme(self) -> None:
        manager = ThemeManager()
        manager.set("synthwave")
        assert manager.current() == "synthwave"

    def test_invalid_theme(self) -> None:
        manager = ThemeManager()
        manager.set("invalid-theme")
        assert manager.current() == "apex-dark"

    def test_reset(self) -> None:
        manager = ThemeManager()
        manager.cycle()
        manager.cycle()
        manager.reset()
        assert manager.current() == "apex-dark"


class TestHistoryManager:
    """Test history management."""

    def test_add_message(self) -> None:
        manager = HistoryManager()
        manager.add("Hello")
        manager.add("World")

        assert manager.go_up() == "World"
        assert manager.go_up() == "Hello"

    def test_no_duplicate(self) -> None:
        manager = HistoryManager()
        manager.add("Hello")
        manager.add("Hello")

        assert manager.go_up() == "Hello"
        assert manager.go_up() is None

    def test_go_down(self) -> None:
        manager = HistoryManager()
        manager.add("First")
        manager.add("Second")

        manager.go_up()
        manager.go_up()
        assert manager.go_down() == "Second"
        assert manager.go_down() == ""

    def test_empty_history(self) -> None:
        manager = HistoryManager()
        assert manager.go_up() is None
        assert manager.go_down() == ""

    def test_clear(self) -> None:
        manager = HistoryManager()
        manager.add("Hello")
        manager.reset()
        assert manager.go_up() is None


class TestSessionManager:
    """Test session management."""

    def test_default_session(self) -> None:
        manager = SessionManager()
        assert manager.session_name == "main"
        assert manager.message_count == 0

    def test_message_increment(self) -> None:
        manager = SessionManager()
        assert manager.increment_messages() == 1
        assert manager.increment_messages() == 2

    def test_new_session(self) -> None:
        manager = SessionManager()
        manager.increment_messages()
        manager.increment_messages()
        manager.new_session()

        assert manager.message_count == 0
        assert "session-" in manager.session_name


class TestCommandProcessor:
    """Test command processor."""

    def test_is_command(self) -> None:
        processor = CommandProcessor()
        assert processor.is_command("/help") is True
        assert processor.is_command("/clear") is True
        assert processor.is_command("hello") is False

    def test_parse(self) -> None:
        processor = CommandProcessor()
        cmd, arg = processor.parse("/model gpt-4o")
        assert cmd == "/model"
        assert arg == "gpt-4o"

    def test_parse_no_arg(self) -> None:
        processor = CommandProcessor()
        cmd, arg = processor.parse("/help")
        assert cmd == "/help"
        assert arg == ""

    def test_execute(self) -> None:
        processor = CommandProcessor()
        result = processor.execute("/clear")
        assert result == "Clear conversation"

    def test_execute_unknown(self) -> None:
        processor = CommandProcessor()
        result = processor.execute("/unknown")
        assert result is None


class TestRefactoredTUI:
    """Test main TUI class."""

    def test_init(self) -> None:
        tui = RefactoredTUI()
        assert tui.state.model == "or-gpt4o-mini"
        assert tui.theme_manager.current() == "apex-dark"

    def test_handle_empty_input(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("   ")

        assert len(messages) == 0

    def test_handle_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("/help")

        assert len(messages) == 1
        assert "SHORTCUTS" in messages[0]

    def test_handle_theme_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("/theme")

        assert len(messages) == 1
        assert "Theme:" in messages[0]
        assert tui.state.current_theme == "gabon"

    def test_handle_clear_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("Hello")
        tui.handle_input("/clear")

        assert tui.state.message_count == 0
        assert len(messages) >= 1

    def test_get_status(self) -> None:
        tui = RefactoredTUI()
        status = tui.get_status()

        assert status["model"] == "or-gpt4o-mini"
        assert status["theme"] == "apex-dark"
        assert status["thinking"] is False
        assert status["messages"] == 0


class TestMockAgent:
    """Test TUI with mock agent."""

    def test_with_mock_agent(self) -> None:
        class MockAgent:
            def chat(self, message: str) -> str:
                return f"Echo: {message}"

            @property
            def usage(self) -> dict:
                return {"total_tokens": 100, "estimated_cost": 0.01}

        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(agent=MockAgent(), on_message=on_message)
        tui.handle_input("test message")

        assert len(messages) >= 1
        assert "Echo: test message" in "".join(messages)