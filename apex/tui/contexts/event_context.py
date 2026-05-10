"""Event context - Like OpenCode's Event system."""

from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    # TUI Events
    TUI_READY = "tui:ready"
    TUI_EXIT = "tui:exit"
    
    # Route Events
    ROUTE_CHANGE = "route:change"
    ROUTE_MOUNT = "route:mount"
    ROUTE_UNMOUNT = "route:unmount"
    
    # Theme Events
    THEME_CHANGE = "theme:change"
    
    # Model/Agent Events
    MODEL_CHANGE = "model:change"
    AGENT_CHANGE = "agent:change"
    
    # Session Events
    SESSION_CREATED = "session:created"
    SESSION_UPDATED = "session:updated"
    SESSION_DELETED = "session:deleted"
    SESSION_SAVE = "session:save"
    SESSION_LOAD = "session:load"
    SESSION_SHARE = "session:share"
    
    # Message Events
    MESSAGE_ADDED = "message:added"
    MESSAGE_UPDATED = "message:updated"
    MESSAGE_DELETED = "message:deleted"
    
    # File Events
    FILE_CHANGED = "file:changed"
    FILE_CREATED = "file:created"
    FILE_DELETED = "file:deleted"
    FILE_SAVED = "file:saved"
    
    # Tool Events
    TOOL_CALLED = "tool:called"
    TOOL_EXECUTED = "tool:executed"
    TOOL_ERROR = "tool:error"
    TOOL_RESULT = "tool:result"
    
    # Permission Events
    PERMISSION_REQUESTED = "permission:requested"
    PERMISSION_GRANTED = "permission:granted"
    PERMISSION_DENIED = "permission:denied"
    
    # UI Events
    TOAST_SHOW = "toast:show"
    TOAST_HIDE = "toast:hide"
    DIALOG_OPEN = "dialog:open"
    DIALOG_CLOSE = "dialog:close"
    
    # Input Events
    KEY_PRESS = "key:press"
    MOUSE_CLICK = "mouse:click"
    INPUT_SUBMIT = "input:submit"
    
    # Undo/Redo Events
    SNAPSHOT_CREATED = "snapshot:created"
    SNAPSHOT_RESTORED = "snapshot:restored"
    UNDO_PERFORMED = "undo:performed"
    REDO_PERFORMED = "redo:performed"
    
    # LSP Events
    LSP_DIAGNOSTICS = "lsp:diagnostics"
    LSP_ERROR = "lsp:error"


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