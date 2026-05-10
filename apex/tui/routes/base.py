"""Base route class for all routes."""

from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from rich.console import Console
from .route_type import RouteType


@dataclass
class Route:
    """Route data structure."""
    type: RouteType
    name: str
    data: dict = field(default_factory=dict)


class BaseRoute:
    """Base route class - like OpenCode's route base."""

    def __init__(self, route_type: RouteType, name: str, console: Optional[Console] = None):
        self.type = route_type
        self.name = name
        self.console = console or Console()
        self._handlers: dict[str, Callable] = {}

    def render(self) -> Any:
        """Render the route content. Must be implemented by subclasses."""
        raise NotImplementedError

    def on_mount(self) -> None:
        """Called when route is mounted. Override in subclasses."""
        pass

    def on_destroy(self) -> None:
        """Called when route is destroyed. Override in subclasses."""
        pass

    def handle_action(self, action: str, data: dict = None) -> None:
        """Handle an action. Override in subclasses."""
        pass

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register an action handler."""
        self._handlers[action] = handler

    def emit(self, action: str, data: dict = None) -> None:
        """Emit an action."""
        if action in self._handlers:
            self._handlers[action](data or {})
        else:
            self.handle_action(action, data)