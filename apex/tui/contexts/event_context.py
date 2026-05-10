"""Event context - Like OpenCode's Event system."""

from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    TUI_READY = "tui:ready"
    TUI_EXIT = "tui:exit"
    ROUTE_CHANGE = "route:change"
    THEME_CHANGE = "theme:change"
    MODEL_CHANGE = "model:change"
    AGENT_CHANGE = "agent:change"
    SESSION_SAVE = "session:save"
    SESSION_LOAD = "session:load"
    TOAST_SHOW = "toast:show"
    TOAST_HIDE = "toast:hide"
    DIALOG_OPEN = "dialog:open"
    DIALOG_CLOSE = "dialog:close"
    KEY_PRESS = "key:press"
    MOUSE_CLICK = "mouse:click"


@dataclass
class Event:
    type: EventType
    data: Any = None
    source: Optional[str] = None


class EventBus:
    """Event bus - like OpenCode's Event system."""

    def __init__(self):
        self._handlers: dict[EventType, list[Callable]] = {}
        self._once_handlers: dict[EventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []

    def on(self, event: EventType, handler: Callable) -> Callable:
        """Register event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        return handler

    def once(self, event: EventType, handler: Callable) -> Callable:
        """Register one-time event handler."""
        if event not in self._once_handlers:
            self._once_handlers[event] = []
        self._once_handlers[event].append(handler)
        return handler

    def off(self, event: EventType, handler: Callable) -> None:
        """Unregister event handler."""
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def emit(self, event: EventType, data: Any = None, source: Optional[str] = None) -> None:
        """Emit an event."""
        evt = Event(type=event, data=data, source=source)

        for handler in self._handlers.get(event, []):
            try:
                handler(evt)
            except Exception as e:
                print(f"Event handler error: {e}")

        for handler in self._once_handlers.pop(event, []):
            try:
                handler(evt)
            except Exception as e:
                print(f"Event handler error: {e}")

        for handler in self._global_handlers:
            try:
                handler(evt)
            except Exception as e:
                print(f"Global event handler error: {e}")

    def on_any(self, handler: Callable) -> None:
        """Register global event handler."""
        self._global_handlers.append(handler)

    def clear(self) -> None:
        """Clear all handlers."""
        self._handlers.clear()
        self._once_handlers.clear()
        self._global_handlers.clear()


class EventProvider:
    """Event context provider - like OpenCode's Event system."""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._bus = event_bus or EventBus()

    @property
    def bus(self) -> EventBus:
        return self._bus

    def on(self, event: EventType, handler: Callable) -> Callable:
        return self._bus.on(event, handler)

    def once(self, event: EventType, handler: Callable) -> Callable:
        return self._bus.once(event, handler)

    def off(self, event: EventType, handler: Callable) -> None:
        self._bus.off(event, handler)

    def emit(self, event: EventType, data: Any = None, source: Optional[str] = None) -> None:
        self._bus.emit(event, data, source)

    def on_any(self, handler: Callable) -> None:
        self._bus.on_any(handler)


def create_event(event_type: EventType, data: Any = None, source: Optional[str] = None) -> Event:
    """Create an event."""
    return Event(type=event_type, data=data, source=source)