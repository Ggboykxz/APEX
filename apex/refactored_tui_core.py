"""
Refactored TUI Core - Testable application logic.

Extracts business logic from Textual App for unit testing.
"""

from dataclasses import dataclass, field
from typing import Callable, Protocol, Any


class AgentProtocol(Protocol):
    """Protocol for agent interface - makes testing easy."""

    def chat(self, message: str) -> str: ...
    @property
    def usage(self) -> dict[str, Any]: ...


@dataclass
class TUIState:
    """Application state - easily testable."""

    model: str = "or-gpt4o-mini"
    cwd: str = "."
    token_count: int = 0
    cost_usd: float = 0.0
    is_thinking: bool = False
    sidebar_visible: bool = True
    current_theme: str = "apex-dark"
    sidebar_width: int = 26
    message_history: list[str] = field(default_factory=list)
    history_index: int = -1
    session_name: str = "main"
    message_count: int = 0


class ThemeManager:
    """Manages theme switching - testable without UI."""

    THEMES = ["apex-dark", "gabon", "synthwave", "solarized"]

    def __init__(self) -> None:
        self._current_index = 0

    def cycle(self) -> str:
        self._current_index = (self._current_index + 1) % len(self.THEMES)
        return self.THEMES[self._current_index]

    def current(self) -> str:
        return self.THEMES[self._current_index]

    def set(self, theme: str) -> None:
        if theme in self.THEMES:
            self._current_index = self.THEMES.index(theme)

    def reset(self) -> None:
        self._current_index = 0


class HistoryManager:
    """Manages message history - testable."""

    def __init__(self, max_size: int = 100) -> None:
        self._history: list[str] = []
        self._index: int = -1
        self._max_size = max_size

    def add(self, message: str) -> None:
        if message.strip() and message not in self._history:
            self._history.append(message)
            if len(self._history) > self._max_size:
                self._history.pop(0)
        self._index = len(self._history)

    def go_up(self) -> str | None:
        if self._history and self._index > 0:
            self._index -= 1
            return self._history[self._index]
        return None

    def go_down(self) -> str | None:
        if self._history and self._index < len(self._history) - 1:
            self._index += 1
            return self._history[self._index]
        elif self._index >= len(self._history) - 1:
            self._index = len(self._history)
            return ""
        return None

    def reset(self) -> None:
        self._history = []
        self._index = -1

    @property
    def has_history(self) -> bool:
        return bool(self._history)


class SessionManager:
    """Manages session state - testable."""

    def __init__(self) -> None:
        self._session_name = "main"
        self._message_count = 0

    def new_session(self) -> None:
        self._session_name = f"session-{self._message_count}"
        self._message_count = 0

    def increment_messages(self) -> int:
        self._message_count += 1
        return self._message_count

    @property
    def session_name(self) -> str:
        return self._session_name

    @property
    def message_count(self) -> int:
        return self._message_count


class CommandProcessor:
    """Processes commands - testable without UI."""

    COMMANDS = {
        "/clear": "Clear conversation",
        "/models": "List available models",
        "/model": "Switch to a specific model",
        "/cwd": "Show/change directory",
        "/theme": "Toggle theme",
        "/help": "Show help",
        "/save": "Save session",
    }

    def __init__(self, on_command: Callable[[str], None] | None = None) -> None:
        self._on_command = on_command

    def execute(self, command: str) -> str | None:
        if command in self.COMMANDS:
            if self._on_command:
                self._on_command(command)
            return self.COMMANDS[command]
        return None

    def get_commands(self) -> dict[str, str]:
        return self.COMMANDS.copy()

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def parse(self, text: str) -> tuple[str, str]:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        return cmd, arg


class TUIEventBus:
    """Event bus for TUI - decouples components."""

    def __init__(self) -> None:
        self._listeners: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, callback: Callable) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event: Any) -> None:
        event_type = type(event)
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(event)

    def clear(self) -> None:
        self._listeners.clear()


class RefactoredTUI:
    """Main TUI logic - fully testable without Textual."""

    def __init__(
        self,
        agent: AgentProtocol | None = None,
        on_message: Callable[[str, str], None] | None = None,
    ) -> None:
        self.state = TUIState()
        self.agent = agent
        self.on_message = on_message
        self.theme_manager = ThemeManager()
        self.history_manager = HistoryManager()
        self.session_manager = SessionManager()
        self.command_processor = CommandProcessor()
        self.event_bus = TUIEventBus()

    def handle_input(self, text: str) -> None:
        """Process user input - main entry point."""
        if not text.strip():
            return

        self.state.is_thinking = True
        self.state.message_count = self.session_manager.increment_messages()

        if self.command_processor.is_command(text):
            cmd, arg = self.command_processor.parse(text)
            self._handle_command(cmd, arg)
        else:
            self.history_manager.add(text)
            self._process_message(text)

    def _handle_command(self, command: str, arg: str) -> None:
        if command == "/clear":
            self.state.message_count = 0
            self.history_manager.reset()
            self._notify("Session cleared")
        elif command == "/theme":
            new_theme = self.theme_manager.cycle()
            self.state.current_theme = new_theme
            self._notify(f"Theme: {new_theme}")
        elif command == "/models":
            from .config import MODELS
            self._notify(f"Models: {', '.join(MODELS.keys())}")
        elif command == "/cwd":
            self._notify(f"Current directory: {self.state.cwd}")
        elif command == "/help":
            self._notify(self._get_help_text())
        else:
            self._notify(f"Unknown command: {command}")

        self.state.is_thinking = False

    def _process_message(self, message: str) -> None:
        if not self.agent:
            self._notify("No agent configured")
            self.state.is_thinking = False
            return

        try:
            response = self.agent.chat(message)
            usage = self.agent.usage
            self.state.token_count = usage.get("total_tokens", 0)
            self.state.cost_usd = usage.get("estimated_cost", 0.0)
            self._notify(f"APEX: {response}")
        except Exception as e:
            self._notify(f"Error: {e}")
        finally:
            self.state.is_thinking = False

    def _notify(self, message: str) -> None:
        if self.on_message:
            self.on_message(message, self.state.model)

    def _get_help_text(self) -> str:
        return """APEX TUI SHORTCUTS:
• Ctrl+K - Command Palette
• Ctrl+L - Clear Chat
• Ctrl+N - New Session
• Ctrl+T - Toggle Theme
• ↑/↓ - Message History
• F1 - Help"""

    def get_status(self) -> dict[str, Any]:
        return {
            "model": self.state.model,
            "cwd": self.state.cwd,
            "tokens": self.state.token_count,
            "cost": self.state.cost_usd,
            "theme": self.state.current_theme,
            "thinking": self.state.is_thinking,
            "messages": self.state.message_count,
        }


def create_tui(agent: AgentProtocol | None = None) -> RefactoredTUI:
    """Factory function for creating TUI instances."""
    return RefactoredTUI(agent=agent)