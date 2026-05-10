"""Route context - Like OpenCode's RouteProvider."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any


class RouteType(Enum):
    HOME = "home"
    SESSION = "session"
    PLUGIN = "plugin"


@dataclass
class Route:
    """Route data structure - like OpenCode's Route."""
    type: RouteType
    name: str
    data: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.data.get("title", self.name)

    @property
    def id(self) -> str:
        return self.name


class RouteContext:
    """Route context - manages navigation between routes."""

    def __init__(self):
        self._current_route: Optional[Route] = None
        self._history: list[Route] = []
        self._route_handlers: dict[RouteType, list[Callable]] = {}
        self._listeners: list[Callable] = []

    @property
    def current_route(self) -> Optional[Route]:
        return self._current_route

    @property
    def previous_route(self) -> Optional[Route]:
        if len(self._history) > 1:
            return self._history[-2]
        return None

    def navigate(self, route: Route) -> None:
        """Navigate to a route."""
        if self._current_route:
            self._history.append(self._current_route)
        self._current_route = route
        self._notify(route)

    def navigate_home(self) -> None:
        """Navigate to home route."""
        self.navigate(Route(RouteType.HOME, "home"))

    def navigate_session(self, session_id: str, title: str = "", data: Optional[dict] = None) -> None:
        """Navigate to session route."""
        route_data = {"title": title or session_id, **(data or {})}
        self.navigate(Route(RouteType.SESSION, session_id, route_data))

    def navigate_plugin(self, plugin_id: str, data: Optional[dict] = None) -> None:
        """Navigate to plugin route."""
        route_data = {"id": plugin_id, **(data or {})}
        self.navigate(Route(RouteType.PLUGIN, plugin_id, route_data))

    def go_back(self) -> bool:
        """Go back to previous route."""
        if self._history:
            self._current_route = self._history.pop()
            self._notify(self._current_route)
            return True
        return False

    def register_route_handler(self, route_type: RouteType, handler: Callable) -> None:
        """Register handler for a route type."""
        if route_type not in self._route_handlers:
            self._route_handlers[route_type] = []
        self._route_handlers[route_type].append(handler)

    def on_change(self, listener: Callable) -> None:
        """Subscribe to route changes."""
        self._listeners.append(listener)

    def _notify(self, route: Route) -> None:
        handlers = self._route_handlers.get(route.type, [])
        for handler in handlers:
            handler(route)
        for listener in self._listeners:
            listener(route)


class RouteProvider:
    """Route context provider - like OpenCode's RouteProvider."""

    def __init__(self, route_context: Optional[RouteContext] = None):
        self._context = route_context or RouteContext()

    @property
    def current_route(self) -> Optional[Route]:
        return self._context.current_route

    @property
    def route_type(self) -> Optional[RouteType]:
        if self._context.current_route:
            return self._context.current_route.type
        return None

    def is_home(self) -> bool:
        return self.route_type == RouteType.HOME

    def is_session(self) -> bool:
        return self.route_type == RouteType.SESSION

    def is_plugin(self) -> bool:
        return self.route_type == RouteType.PLUGIN

    def navigate_home(self) -> None:
        self._context.navigate_home()

    def navigate_session(self, session_id: str, **kwargs) -> None:
        self._context.navigate_session(session_id, **kwargs)

    def go_back(self) -> bool:
        return self._context.go_back()

    def on_change(self, listener: Callable) -> None:
        self._context.on_change(listener)


def create_home_route() -> Route:
    """Create default home route."""
    return Route(RouteType.HOME, "home")


def create_session_route(session_id: str, title: str = "") -> Route:
    """Create session route."""
    return Route(RouteType.SESSION, session_id, {"title": title or session_id})


def create_plugin_route(plugin_id: str, **data) -> Route:
    """Create plugin route."""
    return Route(RouteType.PLUGIN, plugin_id, {"id": plugin_id, **data})