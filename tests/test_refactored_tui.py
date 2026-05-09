"""Tests for refactored TUI modules."""

from apex.refactored_tui_core import (
    TUIState,
    ThemeManager,
    HistoryManager,
    SessionManager,
    CommandProcessor,
    RefactoredTUI,
    TUIEventBus,
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


class TestTUIEventBus:
    """Test TUI event bus."""

    def test_subscribe(self) -> None:
        bus = TUIEventBus()
        called = []

        def handler(msg: str) -> None:
            called.append(msg)

        bus.subscribe(str, handler)
        assert str in bus._listeners

    def test_publish(self) -> None:
        bus = TUIEventBus()
        received = []

        def handler(event: str) -> None:
            received.append(event)

        bus.subscribe(str, handler)
        bus.publish("test message")
        assert received == ["test message"]

    def test_clear(self) -> None:
        bus = TUIEventBus()

        def handler(event: str) -> None:
            pass

        bus.subscribe(str, handler)
        bus.clear()
        assert len(bus._listeners) == 0


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

    def test_max_size(self) -> None:
        manager = HistoryManager(max_size=3)
        manager.add("1")
        manager.add("2")
        manager.add("3")
        manager.add("4")
        manager.add("5")

        assert len(manager._history) == 3
        assert "3" in manager._history
        assert "5" in manager._history
        assert "1" not in manager._history

    def test_whitespace_not_added(self) -> None:
        manager = HistoryManager()
        manager.add("   ")
        assert len(manager._history) == 0

    def test_duplicate_not_added(self) -> None:
        manager = HistoryManager()
        manager.add("Hello")
        manager.add("Hello")
        manager.add("Hello")
        assert len(manager._history) == 1

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

    def test_go_down_empty(self) -> None:
        manager = HistoryManager()
        result = manager.go_down()
        assert result == ""

    def test_go_up_no_history(self) -> None:
        manager = HistoryManager()
        result = manager.go_up()
        assert result is None

    def test_go_up_at_start(self) -> None:
        manager = HistoryManager()
        manager.add("first")
        manager.go_up()
        result = manager.go_up()
        assert result is None

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

    def test_execute_with_callback(self) -> None:
        called = []

        def on_cmd(cmd: str) -> None:
            called.append(cmd)

        processor = CommandProcessor(on_command=on_cmd)
        result = processor.execute("/clear")
        assert result == "Clear conversation"
        assert called == ["/clear"]

    def test_get_commands(self) -> None:
        processor = CommandProcessor()
        commands = processor.get_commands()
        assert "/clear" in commands
        assert len(commands) > 0


class TestRefactoredTUI:
    """Test main TUI class."""

    def test_init(self) -> None:
        tui = RefactoredTUI()
        assert tui.state.model == "or-gpt4o-mini"
        assert tui.theme_manager.current() == "apex-dark"

    def test_get_help_text(self) -> None:
        tui = RefactoredTUI()
        help_text = tui._get_help_text()
        assert "Ctrl+K" in help_text
        assert "Ctrl+L" in help_text
        assert "Ctrl+T" in help_text

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

    def test_handle_cwd_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.state.cwd = "/home/user"
        tui.handle_input("/cwd")

        assert any("Current directory" in msg for msg in messages)

    def test_handle_models_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("/models")

        assert any("Models:" in msg for msg in messages)

    def test_handle_unknown_command(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(on_message=on_message)
        tui.handle_input("/unknowncmd")

        assert any("Unknown command" in msg for msg in messages)

    def test_handle_no_agent(self) -> None:
        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(agent=None, on_message=on_message)
        tui.handle_input("hello")

        assert any("No agent" in msg for msg in messages)

    def test_with_agent_error(self) -> None:
        class FailingAgent:
            def chat(self, message: str) -> str:
                raise RuntimeError("API Error")

            @property
            def usage(self) -> dict:
                return {"total_tokens": 0, "estimated_cost": 0.0}

        messages: list[str] = []

        def on_message(msg: str, model: str) -> None:
            messages.append(msg)

        tui = RefactoredTUI(agent=FailingAgent(), on_message=on_message)
        tui.handle_input("test")

        assert any("Error" in msg for msg in messages)


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


from apex.refactored_tui_theme import (
    ThemeColors,
    Theme,
    ThemeService,
    THEMES,
    get_css_variables,
    generate_css,
)


class TestThemeColors:
    """Test theme colors."""

    def test_create(self) -> None:
        colors = ThemeColors(
            bg="#000000",
            elevated="#111111",
            surface="#222222",
            accent="#00e5ff",
            success="#00ff88",
            error="#ff4444",
            warning="#ffaa00",
            text="#e6edf3",
            muted="#7d8590",
            border="#30363d",
        )
        assert colors.bg == "#000000"
        assert colors.accent == "#00e5ff"


class TestTheme:
    """Test theme dataclass."""

    def test_create(self) -> None:
        theme = Theme(
            name="test-theme",
            display_name="Test Theme",
            icon="★",
            colors=ThemeColors(
                bg="#000000",
                elevated="#111111",
                surface="#222222",
                accent="#ff0000",
                success="#00ff00",
                error="#ff0000",
                warning="#ffff00",
                text="#ffffff",
                muted="#888888",
                border="#333333",
            ),
        )
        assert theme.name == "test-theme"
        assert theme.display_name == "Test Theme"
        assert theme.icon == "★"


class TestThemeService:
    """Test theme service."""

    def test_init(self) -> None:
        service = ThemeService()
        assert service.current.name == "apex-dark"

    def test_set_valid(self) -> None:
        service = ThemeService()
        assert service.set("synthwave") is True
        assert service.current.name == "synthwave"

    def test_set_invalid(self) -> None:
        service = ThemeService()
        assert service.set("invalid") is False
        assert service.current.name == "apex-dark"

    def test_cycle(self) -> None:
        service = ThemeService()
        service.set("solarized")
        theme = service.cycle()
        assert theme.name == "apex-dark"

    def test_get_all(self) -> None:
        service = ThemeService()
        all_themes = service.get_all()
        assert len(all_themes) == 4
        names = [t.name for t in all_themes]
        assert "apex-dark" in names
        assert "gabon" in names
        assert "synthwave" in names
        assert "solarized" in names

    def test_get_names(self) -> None:
        service = ThemeService()
        names = service.get_names()
        assert "apex-dark" in names
        assert len(names) == 4


class TestGetCSSVariables:
    """Test CSS variable generation."""

    def test_generates_correct_variables(self) -> None:
        theme = THEMES["apex-dark"]
        vars = get_css_variables(theme)
        assert vars["$apex-bg"] == "#0d1117"
        assert vars["$apex-accent"] == "#00e5ff"
        assert vars["$apex-success"] == "#00ff88"

    def test_all_themes_have_variables(self) -> None:
        for name, theme in THEMES.items():
            vars = get_css_variables(theme)
            assert len(vars) == 10


class TestGenerateCSS:
    """Test CSS generation."""

    def test_generate_css(self) -> None:
        theme = THEMES["apex-dark"]
        css = generate_css(theme)
        assert "$apex-bg: #0d1117;" in css
        assert "$apex-accent: #00e5ff;" in css


from apex.refactored_tui_messages import (
    TUIEvent,
    UserInputEvent,
    CommandEvent,
    ThemeChangeEvent,
    ModelChangeEvent,
    CwdChangeEvent,
    ToolCallEvent,
    ToolResultEvent,
    TokenUpdateEvent,
    ClearEvent,
    FilePreviewEvent,
    EventHandler,
    create_event,
)


class TestTUIEvent:
    """Test base TUI event."""

    def test_create(self) -> None:
        event = TUIEvent()
        assert isinstance(event, TUIEvent)


class TestUserInputEvent:
    """Test user input events."""

    def test_create(self) -> None:
        event = UserInputEvent(text="Hello")
        assert event.text == "Hello"


class TestCommandEvent:
    """Test command events."""

    def test_create_with_args(self) -> None:
        event = CommandEvent(command="/model", arguments="gpt-4o")
        assert event.command == "/model"
        assert event.arguments == "gpt-4o"

    def test_create_no_args(self) -> None:
        event = CommandEvent(command="/help")
        assert event.command == "/help"
        assert event.arguments == ""


class TestThemeChangeEvent:
    """Test theme change events."""

    def test_create(self) -> None:
        event = ThemeChangeEvent(theme_name="synthwave")
        assert event.theme_name == "synthwave"


class TestModelChangeEvent:
    """Test model change events."""

    def test_create(self) -> None:
        event = ModelChangeEvent(model_alias="claude-sonnet")
        assert event.model_alias == "claude-sonnet"


class TestCwdChangeEvent:
    """Test cwd change events."""

    def test_create(self) -> None:
        event = CwdChangeEvent(new_cwd="/home/user")
        assert event.new_cwd == "/home/user"


class TestToolCallEvent:
    """Test tool call events."""

    def test_create(self) -> None:
        event = ToolCallEvent(tool_name="read_file", arguments={"path": "test.py"})
        assert event.tool_name == "read_file"
        assert event.arguments["path"] == "test.py"


class TestToolResultEvent:
    """Test tool result events."""

    def test_create_success(self) -> None:
        event = ToolResultEvent(tool_name="read_file", success=True, result="content", duration=0.5)
        assert event.success is True
        assert event.duration == 0.5

    def test_create_failure(self) -> None:
        event = ToolResultEvent(tool_name="read_file", success=False, result="Error", duration=0.1)
        assert event.success is False


class TestTokenUpdateEvent:
    """Test token update events."""

    def test_create(self) -> None:
        event = TokenUpdateEvent(count=1000, cost_usd=0.05)
        assert event.count == 1000
        assert event.cost_usd == 0.05


class TestClearEvent:
    """Test clear events."""

    def test_create(self) -> None:
        event = ClearEvent()
        assert isinstance(event, TUIEvent)


class TestFilePreviewEvent:
    """Test file preview events."""

    def test_create(self) -> None:
        event = FilePreviewEvent(file_path="/path/to/file.py")
        assert event.file_path == "/path/to/file.py"


class TestEventHandler:
    """Test event handler."""

    def test_on_and_emit(self) -> None:
        handler = EventHandler()
        received = []

        handler.on(UserInputEvent, lambda e: received.append(e))
        handler.emit(UserInputEvent(text="test"))

        assert len(received) == 1
        assert received[0].text == "test"

    def test_multiple_handlers(self) -> None:
        handler = EventHandler()
        count = [0]

        handler.on(UserInputEvent, lambda e: count.__setitem__(0, count[0] + 1))
        handler.on(UserInputEvent, lambda e: count.__setitem__(0, count[0] + 1))
        handler.emit(UserInputEvent(text="test"))

        assert count[0] == 2

    def test_clear(self) -> None:
        handler = EventHandler()
        received = []
        handler.on(UserInputEvent, lambda e: received.append(e))
        handler.clear()
        handler.emit(UserInputEvent(text="test"))
        assert len(received) == 0


class TestCreateEvent:
    """Test event factory."""

    def test_user_input(self) -> None:
        event = create_event("Hello")
        assert isinstance(event, UserInputEvent)
        assert event.text == "Hello"

    def test_command_with_arg(self) -> None:
        event = create_event("/model gpt-4o")
        assert isinstance(event, CommandEvent)
        assert event.command == "/model"
        assert event.arguments == "gpt-4o"

    def test_command_no_arg(self) -> None:
        event = create_event("/clear")
        assert isinstance(event, CommandEvent)
        assert event.command == "/clear"
        assert event.arguments == ""


from apex.refactored_tui_components import (
    ComponentConfig,
    HeaderBarComponent,
    ChatPaneComponent,
    SidebarComponent,
    InputBarComponent,
    StatusBarComponent,
    CommandPaletteComponent,
    create_header,
    create_chat_pane,
    create_sidebar,
    create_input_bar,
    create_status_bar,
    create_command_palette,
)


class TestComponentConfig:
    """Test component config."""

    def test_default(self) -> None:
        config = ComponentConfig()
        assert config.id == ""
        assert config.classes == ""
        assert config.visible is True

    def test_custom(self) -> None:
        config = ComponentConfig(id="test", classes="custom", width=100, height=50, visible=False)
        assert config.id == "test"
        assert config.classes == "custom"
        assert config.width == 100
        assert config.height == 50
        assert config.visible is False


class TestHeaderBarComponent:
    """Test header bar component."""

    def test_create(self) -> None:
        component = HeaderBarComponent()
        assert component.model == "or-gpt4o-mini"
        assert component.cwd == "."
        assert component.tokens == 0

    def test_update_model(self) -> None:
        component = HeaderBarComponent()
        component.update_model("claude-sonnet")
        assert component.model == "claude-sonnet"

    def test_update_cwd(self) -> None:
        component = HeaderBarComponent()
        component.update_cwd("/home/user")
        assert component.cwd == "/home/user"

    def test_update_tokens(self) -> None:
        component = HeaderBarComponent()
        component.update_tokens(1500, 0.05)
        assert component.tokens == 1500
        assert component.cost == 0.05

    def test_get_display(self) -> None:
        component = HeaderBarComponent()
        component.model = "gpt-4o"
        component.cwd = "/project"
        component.tokens = 1000
        component.cost = 0.03
        display = component.get_display()
        assert "gpt-4o" in display
        assert "/project" in display
        assert "1000k" in display


class TestChatPaneComponent:
    """Test chat pane component."""

    def test_create(self) -> None:
        component = ChatPaneComponent()
        assert len(component.messages) == 0
        assert component.thinking is False

    def test_add_user_message(self) -> None:
        component = ChatPaneComponent()
        component.add_user_message("Hello")
        assert len(component.messages) == 1
        assert component.messages[0]["role"] == "user"

    def test_add_ai_message(self) -> None:
        component = ChatPaneComponent()
        component.add_ai_message("Hi there", "gpt-4o")
        assert len(component.messages) == 1
        assert component.messages[0]["role"] == "assistant"
        assert component.messages[0]["model"] == "gpt-4o"

    def test_add_system_message(self) -> None:
        component = ChatPaneComponent()
        component.add_system_message("System info")
        assert component.messages[0]["role"] == "system"

    def test_clear(self) -> None:
        component = ChatPaneComponent()
        component.add_user_message("Hello")
        component.clear()
        assert len(component.messages) == 0

    def test_set_thinking(self) -> None:
        component = ChatPaneComponent()
        component.set_thinking(True)
        assert component.thinking is True

    def test_get_message_count(self) -> None:
        component = ChatPaneComponent()
        component.add_user_message("Hello")
        component.add_ai_message("Hi")
        assert component.get_message_count() == 2


class TestSidebarComponent:
    """Test sidebar component."""

    def test_create(self) -> None:
        component = SidebarComponent()
        assert component.width == 26
        assert component.visible is True
        assert len(component.tool_log) == 0

    def test_toggle_visibility(self) -> None:
        component = SidebarComponent()
        component.toggle_visibility()
        assert component.visible is False
        component.toggle_visibility()
        assert component.visible is True

    def test_set_width(self) -> None:
        component = SidebarComponent()
        component.set_width(40)
        assert component.width == 40

    def test_set_width_invalid(self) -> None:
        component = SidebarComponent()
        component.set_width(10)
        assert component.width == 26
        component.set_width(70)
        assert component.width == 26

    def test_add_tool_call(self) -> None:
        component = SidebarComponent()
        component.add_tool_call("read_file", {"path": "test.py"})
        assert len(component.tool_log) == 1
        assert component.tool_log[0]["status"] == "running"

    def test_add_tool_result(self) -> None:
        component = SidebarComponent()
        component.add_tool_call("read_file", {})
        component.add_tool_result("read_file", True)
        assert component.tool_log[0]["status"] == "success"

    def test_add_tool_result_failure(self) -> None:
        component = SidebarComponent()
        component.add_tool_call("read_file", {})
        component.add_tool_result("read_file", False)
        assert component.tool_log[0]["status"] == "error"

    def test_clear_tool_log(self) -> None:
        component = SidebarComponent()
        component.add_tool_call("read_file", {})
        component.clear_tool_log()
        assert len(component.tool_log) == 0


class TestInputBarComponent:
    """Test input bar component."""

    def test_create(self) -> None:
        component = InputBarComponent()
        assert component.value == ""
        assert component.disabled is False

    def test_set_value(self) -> None:
        component = InputBarComponent()
        component.set_value("Hello")
        assert component.value == "Hello"

    def test_get_value(self) -> None:
        component = InputBarComponent()
        component.set_value("World")
        assert component.get_value() == "World"

    def test_clear(self) -> None:
        component = InputBarComponent()
        component.set_value("Hello")
        component.clear()
        assert component.value == ""

    def test_set_disabled(self) -> None:
        component = InputBarComponent()
        component.set_disabled(True)
        assert component.disabled is True

    def test_navigate_history_up(self) -> None:
        component = InputBarComponent()
        component.history = ["first", "second"]
        component.history_index = 1
        result = component.navigate_history_up()
        assert result == "first"
        assert component.history_index == 0

    def test_navigate_history_up_no_history(self) -> None:
        component = InputBarComponent()
        result = component.navigate_history_up()
        assert result is None

    def test_navigate_history_down(self) -> None:
        component = InputBarComponent()
        component.history = ["first", "second"]
        component.history_index = 0
        result = component.navigate_history_down()
        assert result == "second"
        assert component.history_index == 1

    def test_navigate_history_down_at_end(self) -> None:
        component = InputBarComponent()
        component.history = ["first", "second"]
        component.history_index = 1
        result = component.navigate_history_down()
        assert result == ""
        assert component.history_index == 2

    def test_navigate_history_down_no_history(self) -> None:
        component = InputBarComponent()
        result = component.navigate_history_down()
        assert result == ""


class TestStatusBarComponent:
    """Test status bar component."""

    def test_create(self) -> None:
        component = StatusBarComponent()
        assert component.model == "or-gpt4o-mini"
        assert component.thinking is False

    def test_update_status(self) -> None:
        component = StatusBarComponent()
        component.update_status(True, "gpt-4o")
        assert component.thinking is True
        assert component.model == "gpt-4o"

    def test_get_display_thinking(self) -> None:
        component = StatusBarComponent()
        component.thinking = True
        display = component.get_display()
        assert "⠋" in display

    def test_get_display_idle(self) -> None:
        component = StatusBarComponent()
        component.thinking = False
        display = component.get_display()
        assert "●" in display


class TestCommandPaletteComponent:
    """Test command palette component."""

    def test_create(self) -> None:
        component = CommandPaletteComponent()
        assert component.visible is False
        assert component.query == ""

    def test_show(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([("/help", "Show help")])
        component.show()
        assert component.visible is True
        assert component.query == ""

    def test_hide(self) -> None:
        component = CommandPaletteComponent()
        component.show()
        component.hide()
        assert component.visible is False

    def test_filter(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([
            ("/clear", "Clear chat"),
            ("/models", "List models"),
            ("/model", "Switch model"),
        ])
        component.filter("model")
        assert len(component.filtered) == 2

    def test_filter_no_match(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([("/help", "Show help")])
        component.filter("xyz")
        assert len(component.filtered) == 0

    def test_select_next(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([("/a", "A"), ("/b", "B"), ("/c", "C")])
        component.show()
        component.select_next()
        assert component.selected_index == 1

    def test_select_prev(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([("/a", "A"), ("/b", "B"), ("/c", "C")])
        component.show()
        component.selected_index = 1
        component.select_prev()
        assert component.selected_index == 0

    def test_get_selected(self) -> None:
        component = CommandPaletteComponent()
        component.set_commands([("/help", "Show help")])
        component.show()
        result = component.get_selected()
        assert result == "/help"


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_header(self) -> None:
        header = create_header("gpt-4o", "/project")
        assert header.model == "gpt-4o"
        assert header.cwd == "/project"

    def test_create_chat_pane(self) -> None:
        chat = create_chat_pane()
        assert isinstance(chat, ChatPaneComponent)

    def test_create_sidebar(self) -> None:
        sidebar = create_sidebar("/home")
        assert isinstance(sidebar, SidebarComponent)

    def test_create_input_bar(self) -> None:
        input_bar = create_input_bar()
        assert isinstance(input_bar, InputBarComponent)

    def test_create_status_bar(self) -> None:
        status = create_status_bar("claude-sonnet")
        assert status.model == "claude-sonnet"

    def test_create_command_palette(self) -> None:
        palette = create_command_palette()
        assert isinstance(palette, CommandPaletteComponent)
        assert len(palette.commands) > 0