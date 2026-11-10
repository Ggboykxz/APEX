"""Shared data structures for the APEX agent loops.

Kept out of ``apex.agent`` so that module holds a single responsibility: the
agent itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["CompletionParams", "StreamState"]


@dataclass
class CompletionParams:
    """The parameters of one LLM call, shared by the chat loops."""

    model: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamState:
    """What a streamed completion produced: text, tool calls and usage."""

    content: str = ""
    tool_call_deltas: dict[int, dict[str, Any]] = field(default_factory=dict)
    usage: Any = None
    turn_complete: bool = False
