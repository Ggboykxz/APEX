"""Base component class."""

from typing import Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class BaseComponent:
    """Base component - like OpenCode's BaseComponent."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.visible = True
        self.position = {"x": 0, "y": 0}
        self.size = {"width": 80, "height": 24}

    def render(self) -> Any:
        """Render the component. Must be implemented by subclasses."""
        raise NotImplementedError

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def toggle(self) -> None:
        self.visible = not self.visible

    def set_position(self, x: int, y: int) -> None:
        self.position = {"x": x, "y": y}

    def set_size(self, width: int, height: int) -> None:
        self.size = {"width": width, "height": height}

    def destroy(self) -> None:
        pass