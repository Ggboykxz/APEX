"""
Refactored TUI Messages - Protocol-based messages for testability.

Instead of Textual Message classes, we use simple dataclasses
that can be easily tested without UI dependencies.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class TUIEvent:
    """Base class for all TUI events."""

    pass


@dataclass
class UserInputEvent(TUIEvent):
    """User submitted a message."""

    text: str


@dataclass
class CommandEvent(TUIEvent):
    """User executed a command."""

    command: str
    arguments: str = ""


@dataclass
class ThemeChangeEvent(TUIEvent):
    """Theme was changed."""

    theme_name: str


@dataclass
class ModelChangeEvent(TUIEvent):
    """Model was changed."""

    model_alias: str


@dataclass
class CwdChangeEvent(TUIEvent):
    """Working directory changed."""

    new_cwd: str


@dataclass
class ToolCallEvent(TUIEvent):
    """Agent called a tool."""

    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ToolResultEvent(TUIEvent):
    """Tool execution completed."""

    tool_name: str
    success: bool
    result: str
    duration: float


@dataclass
class TokenUpdateEvent(TUIEvent):
    """Token usage updated."""

    count: int
    cost_usd: float


@dataclass
class ClearEvent(TUIEvent):
    """Clear the chat."""

    pass


@dataclass
class FilePreviewEvent(TUIEvent):
    """Request to preview a file."""

    file_path: str


class EventHandler:
    """Simple event handler for testing."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[callable]] = {}

    def on(self, event_type: type, handler: callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: TUIEvent) -> None:
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)

    def clear(self) -> None:
        self._handlers.clear()


def create_event(text: str) -> UserInputEvent:
    """Factory for user input events."""
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        return CommandEvent(command=cmd, arguments=arg)
    return UserInputEvent(text=text)