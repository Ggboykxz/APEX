"""Repository map: symbol extraction, caching and rendering.

Split out of ``apex.repomap`` so that each module keeps one
responsibility.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "FileSymbols",
    "Symbol",
    "_SourceFile",
]


@dataclass(frozen=True, slots=True)
class Symbol:
    """A declaration found in a source file.

    Attributes:
        kind: Declaration kind (``class``, ``method``, ``function``,
            ``interface``, ``type``, ``struct``, ``enum``, ``trait`` or
            ``impl``).
        name: Simple declared name (no parent qualification).
        line: 1-based line number of the declaration.
        signature: Single-line declaration signature without a body.
        decorators: Python decorator expressions, without the leading ``@``.
        parent: Enclosing class/type name when known, otherwise ``""``.
    """

    kind: str
    name: str
    line: int
    signature: str
    decorators: tuple[str, ...] = ()
    parent: str = ""


@dataclass(frozen=True, slots=True)
class FileSymbols:
    """Symbols and module summary for one scanned source file.

    ``path`` is relative to the scanned root and always uses POSIX separators,
    which keeps maps and cache keys stable across operating systems.
    """

    path: str
    module_doc: str = ""
    symbols: tuple[Symbol, ...] = ()


@dataclass(frozen=True, slots=True)
class _SourceFile:
    path: str
    text: str
    mtime_ns: int
    size: int


def _summarize_doc(doc: str | None) -> str:
    if not doc:
        return ""
    for line in doc.splitlines():
        compact = _collapse(line)
        if compact:
            return _truncate(compact, _MODULE_DOC_CHARS)
    return ""


def _collapse(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


_WHITESPACE_RE = re.compile(r"\s+")


_MODULE_DOC_CHARS = 120


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
