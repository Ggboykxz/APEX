"""Dialog component - Modal dialogs like OpenCode's dialog."""

from typing import Optional, Callable, List, Tuple
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.console import Console

from .base import BaseComponent


class Dialog(BaseComponent):
    """Dialog component - like OpenCode's Dialog."""

    def __init__(self, title: str = "", message: str = "", console: Optional[Console] = None):
        super().__init__(console)
        self.title = title
        self.message = message
        self.buttons: List[Tuple[str, str, Callable]] = []
        self.selected_index = 0

    def add_button(self, label: str, action: str, callback: Callable) -> None:
        self.buttons.append((label, action, callback))

    def render(self) -> Panel:
        content = Text.from_markup(f"{self.message}\n\n")

        for i, (label, _, _) in enumerate(self.buttons):
            prefix = "[bold][>]" if i == self.selected_index else "   "
            content += Text.from_markup(f"{prefix} {label}\n")

        border_style = "cyan" if self.visible else "dim"

        return Panel(
            content,
            title=self.title,
            border_style=border_style,
            padding=(1, 2)
        )

    def select_next(self) -> None:
        if self.buttons:
            self.selected_index = (self.selected_index + 1) % len(self.buttons)

    def select_prev(self) -> None:
        if self.buttons:
            self.selected_index = (self.selected_index - 1 + len(self.buttons)) % len(self.buttons)

    def confirm(self) -> Optional[str]:
        if self.buttons and 0 <= self.selected_index < len(self.buttons):
            _, action, callback = self.buttons[self.selected_index]
            if callback:
                callback()
            return action
        return None

    def show_dialog(self) -> None:
        self.show()

    def hide_dialog(self) -> None:
        self.hide()

    def destroy(self) -> None:
        self.buttons.clear()