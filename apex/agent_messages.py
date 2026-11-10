"""Message builders for the agent tool-calling protocol.

Extracted from ``apex.agent`` so the wire-format helpers live in one place:
they are used by both the blocking and the streaming chat loops, which
previously duplicated the same message literals eight times.
"""

from __future__ import annotations

import json
import logging
from typing import Any

__all__ = [
    "assistant_tool_call_message",
    "empty_tool_call_delta",
    "merge_tool_call_delta",
    "parse_tool_args",
    "tool_result_message",
]


def empty_tool_call_delta() -> dict[str, str]:
    """Return the accumulator skeleton for one streamed tool call."""
    return {"id": "", "name": "", "arguments": ""}


def merge_tool_call_delta(tool_call_deltas: dict[int, dict[str, str]], tc_delta: Any) -> None:
    """Fold one streamed tool-call delta into the accumulator.

    Providers stream tool calls in fragments: the id and the function name
    arrive once, while the arguments arrive in several chunks that must be
    concatenated in order.
    """
    idx = tc_delta.index
    if idx not in tool_call_deltas:
        tool_call_deltas[idx] = empty_tool_call_delta()
    if tc_delta.id:
        tool_call_deltas[idx]["id"] = tc_delta.id
    if tc_delta.function:
        if tc_delta.function.name:
            tool_call_deltas[idx]["name"] = tc_delta.function.name
        if tc_delta.function.arguments:
            tool_call_deltas[idx]["arguments"] += tc_delta.function.arguments


def assistant_tool_call_message(tc_id: str, tool_name: str, raw_args: str) -> dict[str, Any]:
    """Build the assistant message that requests a tool call."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": raw_args,
                },
            }
        ],
    }


def tool_result_message(tc_id: str, content: str) -> dict[str, Any]:
    """Build the tool message that carries a tool result back to the model."""
    return {"role": "tool", "tool_call_id": tc_id, "content": content}


def parse_tool_args(raw_args: Any) -> tuple[Any, str | None]:
    """Decode streamed tool-call arguments.

    Returns ``(args, error)``. ``args`` is a dict on success; on failure
    ``error`` holds the message to send back to the model and ``args`` is
    the raw value.

    A JSON payload that decodes to a non-object (e.g. ``"123"`` or
    ``"[1, 2]"``) is rejected too: the tool-call contract requires an
    object of named arguments.
    """
    if isinstance(raw_args, dict):
        return raw_args, None

    decoded: Any = raw_args
    if isinstance(raw_args, str):
        if not raw_args.strip():
            return {}, None
        try:
            decoded = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            logging.getLogger(__name__).error(f"Invalid tool args JSON in streaming: {exc}")
            return raw_args, "ERROR: Invalid tool arguments format"

    if not isinstance(decoded, dict):
        logging.getLogger(__name__).error(f"Tool args is not a dict: {type(decoded)}")
        return raw_args, f"ERROR: Tool arguments must be a dict, got {type(decoded).__name__}"

    return decoded, None
