"""Minimal YAML frontmatter parser (stdlib only).

Handles the subset of YAML used in SKILL.md and command markdown frontmatter:

    key: value
    key: "quoted string"
    key: 'single-quoted'
    key: [item1, item2]          # inline list
    key: {a: 1, b: 2}            # inline dict
    key:                         # null / empty
    # comment

Intentionally does NOT support multi-line blocks, anchors, tags, or
complex mappings — those never appear in APEX/OpenCode skill/command
frontmatter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = ["parse_frontmatter", "split_frontmatter"]


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """Return ``(frontmatter_text, body)`` from a markdown document.

    ``frontmatter_text`` is ``None`` when no frontmatter block is present.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None, content
    return match.group(1), content[match.end() :]


def _parse_scalar(raw: str) -> Any:
    """Parse a single YAML scalar value."""
    raw = raw.strip()
    if not raw or raw.lower() in ("null", "~"):
        return None
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    if _is_quoted(raw):
        return raw[1:-1]
    if _is_inline_list(raw):
        return _parse_inline_list(raw)
    if _is_inline_dict(raw):
        return _parse_inline_dict(raw)
    return _parse_number(raw)


def _is_inline_list(raw: str) -> bool:
    """Whether the raw value is an inline list."""
    return raw.startswith("[") and raw.endswith("]")


def _is_inline_dict(raw: str) -> bool:
    """Whether the raw value is an inline dict."""
    return raw.startswith("{") and raw.endswith("}")


def _is_quoted(raw: str) -> bool:
    """Whether the raw value is a quoted string."""
    if raw.startswith('"') and raw.endswith('"'):
        return True
    return raw.startswith("'") and raw.endswith("'")


def _parse_inline_list(raw: str) -> list[Any]:
    """Parse an inline YAML list."""
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(x) for x in _split_top_level(inner, ",")]


def _parse_inline_dict(raw: str) -> dict[str, Any]:
    """Parse an inline YAML dict."""
    inner = raw[1:-1].strip()
    if not inner:
        return {}
    result: dict[str, Any] = {}
    for pair in _split_top_level(inner, ","):
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        result[_parse_scalar(key).strip()] = _parse_scalar(value)
    return result


def _parse_number(raw: str) -> Any:
    """Parse an int or float, or return the raw string."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _split_top_level(text: str, sep: str) -> list[str]:
    """Split ``text`` on ``sep`` but not inside quotes/brackets."""
    parts: list[str] = []
    current: list[str] = []
    state = _SplitState(sep=sep)
    for ch in text:
        _consume_char(ch, state, current, parts)
    if current:
        parts.append("".join(current).strip())
    return parts


@dataclass
class _SplitState:
    """The state of the top-level splitter."""

    sep: str
    depth: int = 0
    in_single: bool = False
    in_double: bool = False


def _consume_char(ch: str, state: _SplitState, current: list[str], parts: list[str]) -> None:
    """Handle one character of the input."""
    if state.in_single:
        _consume_in_single(ch, state, current)
        return
    if state.in_double:
        _consume_in_double(ch, state, current)
        return
    if _handle_special_char(ch, state, current):
        return
    if ch == state.sep and state.depth == 0:
        parts.append("".join(current).strip())
        current.clear()
        return
    current.append(ch)


def _handle_special_char(ch: str, state: _SplitState, current: list[str]) -> bool:
    """Handle a quote or bracket character. Returns True when handled."""
    if ch == "'":
        state.in_single = True
        current.append(ch)
        return True
    if ch == '"':
        state.in_double = True
        current.append(ch)
        return True
    if ch in "{[":
        state.depth += 1
        current.append(ch)
        return True
    if ch in "}]":
        state.depth -= 1
        current.append(ch)
        return True
    return False


def _consume_in_single(ch: str, state: _SplitState, current: list[str]) -> None:
    """Handle one character inside a single-quoted string."""
    current.append(ch)
    if ch == "'":
        state.in_single = False


def _consume_in_double(ch: str, state: _SplitState, current: list[str]) -> None:
    """Handle one character inside a double-quoted string."""
    current.append(ch)
    if ch == '"':
        state.in_double = False


def parse_frontmatter(frontmatter_text: str) -> dict[str, Any]:
    """Parse frontmatter text into a dict."""
    result: dict[str, Any] = {}
    for raw_line in frontmatter_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        result[key] = _parse_scalar(value)
    return result


def parse_frontmatter_document(content: str) -> tuple[dict[str, Any] | None, str]:
    """Parse a full markdown document.

    Returns ``(metadata_dict, body)`` where ``metadata_dict`` is ``None`` if
    no frontmatter block is present.
    """
    fm_text, body = split_frontmatter(content)
    if fm_text is None:
        return None, body
    return parse_frontmatter(fm_text), body
