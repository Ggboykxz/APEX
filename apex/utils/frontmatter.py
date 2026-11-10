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
    return match.group(1), content[match.end():]


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw or raw.lower() in ("null", "~"):
        return None
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    # Quoted strings
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    # Inline list: [a, b, c]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x.strip()) for x in inner.split(",") if x.strip()]
    # Inline dict: {a: 1, b: "two"}
    if raw.startswith("{") and raw.endswith("}"):
        inner = raw[1:-1].strip()
        if not inner:
            return {}
        result: dict[str, Any] = {}
        for pair in _split_top_level(inner, ","):
            if ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            result[_parse_scalar(k).strip()] = _parse_scalar(v)
        return result
    # Try int / float
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
    depth = 0
    in_single = False
    in_double = False
    for ch in text:
        if in_single:
            current.append(ch)
            if ch == "'":
                in_single = False
            continue
        if in_double:
            current.append(ch)
            if ch == '"':
                in_double = False
            continue
        if ch == "'":
            in_single = True
            current.append(ch)
            continue
        if ch == '"':
            in_double = True
            current.append(ch)
            continue
        if ch in "{[":
            depth += 1
            current.append(ch)
            continue
        if ch in "}]":
            depth -= 1
            current.append(ch)
            continue
        if ch == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


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
