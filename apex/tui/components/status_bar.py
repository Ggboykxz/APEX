"""StatusBar component - Bottom status bar like OpenCode's StatusBar."""

from typing import Optional, List
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from datetime import datetime


class StatusBar(BaseComponent):
    """StatusBar component - like OpenCode's StatusBar."""

    def __init__(self, console=None):
        super().__init__(console)
        self.left_items: List[str] = []
        self.center_items: List[str] = []
        self.right_items: List[str] = []
        self.mode = "normal"
        self._last_update = datetime.now()

    def set_left(self, items: List[str]) -> None:
        self.left_items = items

    def set_center(self, items: List[str]) -> None:
        self.center_items = items

    def set_right(self, items: List[str]) -> None:
        self.right_items = items

    def add_left(self, item: str) -> None:
        self.left_items.append(item)

    def add_center(self, item: str) -> None:
        self.center_items.append(item)

    def add_right(self, item: str) -> None:
        self.right_items.append(item)

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def render(self) -> str:
        left = "  ".join(self.left_items) if self.left_items else ""
        center = "  ".join(self.center_items) if self.center_items else ""
        right = "  ".join(self.right_items) if self.right_items else ""

        left_text = Text.from_markup(f"[cyan]{left}[/]" if left else "")
        center_text = Text.from_markup(f"[bold]{center}[/]" if center else "")
        right_text = Text.from_markup(f"[dim]{right}[/]" if right else "")

        return f"{left_text}  │  {center_text}  │  {right_text}"

    def update(self) -> None:
        self._last_update = datetime.now()

    def get_time_since_update(self) -> float:
        return (datetime.now() - self._last_update).total_seconds()

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False