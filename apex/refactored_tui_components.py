"""
Refactored TUI Components - Factory functions for testable UI.

These components can be instantiated with mock dependencies
for easy unit testing.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ComponentConfig:
    """Configuration for UI components."""

    id: str = ""
    classes: str = ""
    width: int = 0
    height: int = 0
    visible: bool = True


class HeaderBarComponent:
    """Header bar component - data only, no Textual."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.model = "or-gpt4o-mini"
        self.cwd = "."
        self.tokens = 0
        self.cost = 0.0
        self.theme = "apex-dark"

    def update_model(self, model: str) -> None:
        self.model = model

    def update_cwd(self, cwd: str) -> None:
        self.cwd = cwd

    def update_tokens(self, count: int, cost: float) -> None:
        self.tokens = count
        self.cost = cost

    def get_display(self) -> str:
        return f"◆ APEX | {self.model} | 📁 {self.cwd} | ●{self.tokens}k | ${self.cost:.4f}"


class ChatPaneComponent:
    """Chat pane component - data only."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.messages: list[dict[str, str]] = []
        self.thinking = False

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_ai_message(self, text: str, model: str = "") -> None:
        self.messages.append({"role": "assistant", "content": text, "model": model})

    def add_system_message(self, text: str) -> None:
        self.messages.append({"role": "system", "content": text})

    def clear(self) -> None:
        self.messages = []

    def set_thinking(self, thinking: bool) -> None:
        self.thinking = thinking

    def get_message_count(self) -> int:
        return len(self.messages)


class SidebarComponent:
    """Sidebar component - data only."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.width = 26
        self.visible = True
        self.file_tree: list[dict[str, Any]] = []
        self.tool_log: list[dict[str, str]] = []

    def toggle_visibility(self) -> None:
        self.visible = not self.visible

    def set_width(self, width: int) -> None:
        if 20 <= width <= 60:
            self.width = width

    def add_tool_call(self, name: str, args: dict) -> None:
        self.tool_log.append({"name": name, "args": str(args), "status": "running"})

    def add_tool_result(self, name: str, success: bool) -> None:
        for entry in self.tool_log:
            if entry["name"] == name and entry["status"] == "running":
                entry["status"] = "success" if success else "error"
                break

    def clear_tool_log(self) -> None:
        self.tool_log = []


class InputBarComponent:
    """Input bar component - data only."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.value = ""
        self.placeholder = "Message APEX..."
        self.disabled = False
        self.history: list[str] = []
        self.history_index = -1

    def set_value(self, value: str) -> None:
        self.value = value

    def get_value(self) -> str:
        return self.value

    def clear(self) -> None:
        self.value = ""

    def set_disabled(self, disabled: bool) -> None:
        self.disabled = disabled

    def navigate_history_up(self) -> str | None:
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.value = self.history[self.history_index]
            return self.value
        return None

    def navigate_history_down(self) -> str | None:
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
            return self.value
        elif self.history_index >= len(self.history) - 1:
            self.history_index = len(self.history)
            self.value = ""
            return self.value
        return None


class StatusBarComponent:
    """Status bar component - data only."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.model = "or-gpt4o-mini"
        self.thinking = False
        self.shortcuts: list[str] = []

    def update_status(self, thinking: bool, model: str) -> None:
        self.thinking = thinking
        self.model = model

    def get_display(self) -> str:
        icon = "⠋" if self.thinking else "●"
        return f"{icon} {self.model}"


class CommandPaletteComponent:
    """Command palette component - data only."""

    def __init__(self, config: ComponentConfig | None = None) -> None:
        self.config = config or ComponentConfig()
        self.visible = False
        self.query = ""
        self.commands: list[tuple[str, str]] = []
        self.filtered: list[tuple[str, str]] = []
        self.selected_index = 0

    def show(self) -> None:
        self.visible = True
        self.query = ""
        self.filtered = self.commands.copy()

    def hide(self) -> None:
        self.visible = False

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        self.commands = commands
        self.filtered = commands.copy()

    def filter(self, query: str) -> None:
        self.query = query
        if query:
            self.filtered = [
                (cmd, desc) for cmd, desc in self.commands
                if query.lower() in cmd.lower() or query.lower() in desc.lower()
            ]
        else:
            self.filtered = self.commands.copy()
        self.selected_index = 0

    def select_next(self) -> None:
        if self.filtered:
            self.selected_index = (self.selected_index + 1) % len(self.filtered)

    def select_prev(self) -> None:
        if self.filtered:
            self.selected_index = (self.selected_index - 1) % len(self.filtered)

    def get_selected(self) -> str | None:
        if self.filtered:
            return self.filtered[self.selected_index][0]
        return None


def create_header(model: str = "or-gpt4o-mini", cwd: str = ".") -> HeaderBarComponent:
    """Factory function for header bar."""
    component = HeaderBarComponent()
    component.model = model
    component.cwd = cwd
    return component


def create_chat_pane() -> ChatPaneComponent:
    """Factory function for chat pane."""
    return ChatPaneComponent()


def create_sidebar(cwd: str = ".") -> SidebarComponent:
    """Factory function for sidebar."""
    component = SidebarComponent()
    return component


def create_input_bar() -> InputBarComponent:
    """Factory function for input bar."""
    return InputBarComponent()


def create_status_bar(model: str = "or-gpt4o-mini") -> StatusBarComponent:
    """Factory function for status bar."""
    component = StatusBarComponent()
    component.model = model
    return component


def create_command_palette() -> CommandPaletteComponent:
    """Factory function for command palette."""
    component = CommandPaletteComponent()
    component.set_commands([
        ("/clear", "Clear conversation"),
        ("/models", "List models"),
        ("/model", "Switch model"),
        ("/cwd", "Change directory"),
        ("/theme", "Toggle theme"),
        ("/help", "Show help"),
    ])
    return component