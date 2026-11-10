"""Shared types, constants and errors.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_PATCH_BYTES",
    "_CODEX_ADD",
    "_CODEX_BEGIN",
    "_CODEX_DELETE",
    "_CODEX_END",
    "_CODEX_UPDATE",
    "_DRIVE_RE",
    "_HUNK_HEADER_RE",
    "_NO_NEWLINE",
    "_UNIFIED_HEADERS",
    "_UNIFIED_METADATA",
    "_UNIFIED_SKIP_HEADERS",
    "PatchError",
    "PatchFile",
    "PatchKind",
    "PatchPreview",
    "_Hunk",
    "_RawFile",
]

MAX_PATCH_BYTES = 1024 * 1024
MAX_FILE_BYTES = 512 * 1024
PatchKind = Literal["add", "update", "delete"]
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?:.*)$"
)
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_CODEX_BEGIN = "*** Begin Patch"
_CODEX_END = "*** End Patch"
_CODEX_ADD = "*** Add File:"
_CODEX_UPDATE = "*** Update File:"
_CODEX_DELETE = "*** Delete File:"
_NO_NEWLINE = "\\ No newline at end of file"
_UNIFIED_METADATA = (
    "index ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
)

# The headers that open a new file section in a unified diff.
_UNIFIED_HEADERS = ("--- ", "diff --git ") + _UNIFIED_METADATA
# The headers that carry no file section and are simply skipped.
_UNIFIED_SKIP_HEADERS = ("diff --git ",) + _UNIFIED_METADATA


class PatchError(Exception):
    """A patch could not be parsed, validated, or applied.

    ``reason`` is a short machine-readable token such as ``context_mismatch``
    or ``path_traversal``.  ``path`` is the offending repository-relative path
    when one is known.
    """

    def __init__(self, reason: str, message: str, path: str | None = None) -> None:
        self.reason = reason
        self.message = message
        self.path = path
        super().__init__(f"{reason}: {message}")


@dataclass
class PatchFile:
    """One file touched by a patch, with its fully resolved contents.

    ``old_text`` and ``new_text`` contain the current and resulting file
    contents for ``add`` and ``update`` operations.  Both are empty for
    ``delete`` operations, as required by the preview contract.
    """

    path: str
    kind: PatchKind
    old_text: str
    new_text: str
    additions: int
    deletions: int

    def summary(self) -> dict[str, Any]:
        """Return the compact representation used by apply results."""
        return {
            "path": self.path,
            "kind": self.kind,
            "additions": self.additions,
            "deletions": self.deletions,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the resolved file without embedding the text contents."""
        return self.summary()


@dataclass
class PatchPreview:
    """The resolved result of a patch without touching the filesystem."""

    files: list[PatchFile] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the preview to JSON-compatible primitives."""
        return {
            "files": [item.to_dict() for item in self.files],
            "additions": self.additions,
            "deletions": self.deletions,
            "warnings": list(self.warnings),
        }


@dataclass
class _Hunk:
    old_start: int | None
    old_count: int | None
    new_start: int | None
    new_count: int | None
    ops: list[tuple[str, str]] = field(default_factory=list)
    old_no_newline: bool = False
    new_no_newline: bool = False


@dataclass
class _RawFile:
    path: str
    kind: PatchKind
    hunks: list[_Hunk]
    no_newline: bool = False
