"""Parser for the unified-diff dialect.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

from typing import Any

from .apply_patch_types import (
    _HUNK_HEADER_RE,
    _NO_NEWLINE,
    _UNIFIED_HEADERS,
    _UNIFIED_SKIP_HEADERS,
    PatchError,
    PatchKind,
    _Hunk,
    _RawFile,
)

__all__ = [
    "_header_path",
    "_parse_unified",
    "_parse_unified_hunk",
    "_strip_unified_prefix",
]


def _skip_unified_line(line: str) -> bool:
    """Whether the line carries no file section and must be skipped."""
    if not line.strip():
        return True
    return line.startswith(_UNIFIED_SKIP_HEADERS)


def _parse_unified(lines: list[str], start: int) -> list[_RawFile]:
    """Parse a unified diff into its file sections."""
    files: list[_RawFile] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if _skip_unified_line(line):
            index += 1
            continue
        if line.startswith("***"):
            raise PatchError(
                "mixed_format",
                "Codex directives cannot be mixed with a unified diff",
            )
        kind, path, index = _read_unified_header(lines, index)
        hunks, index = _parse_unified_hunks(lines, index, path)
        files.append(_RawFile(path, kind, hunks, _has_no_newline(hunks)))
    return files


def _has_no_newline(hunks: list[_Hunk]) -> bool:
    """Whether the last hunk of a file section ends without a newline."""
    return bool(hunks and hunks[-1].new_no_newline)


def _has_unified_header(lines: list[str], index: int) -> bool:
    """Whether the line at *index* opens a '--- ' header pair."""
    if index >= len(lines):
        return False
    return lines[index].startswith("--- ")


def _has_new_header(lines: list[str], index: int) -> bool:
    """Whether the line at *index* opens a '+++ ' header."""
    if index + 1 >= len(lines):
        return False
    return lines[index + 1].startswith("+++ ")


def _read_unified_header(lines: list[str], index: int) -> tuple[PatchKind, str, int]:
    """Read the '--- ' and '+++ ' headers of one file section."""
    if not _has_unified_header(lines, index):
        raise PatchError(
            "malformed_patch",
            f"expected a '--- ' file header, got {lines[index]!r}",
        )
    if not _has_new_header(lines, index):
        raise PatchError(
            "malformed_header",
            "'--- ' header must be followed by a '+++ ' header",
        )
    kind, path = _unified_file_kind(lines[index][4:], lines[index + 1][4:])
    return kind, path, index + 2


def _unified_paths(old_header: str, new_header: str) -> tuple[str | None, str | None]:
    """The paths the two headers of a file section carry."""
    return (
        _strip_unified_prefix(_header_path(old_header)),
        _strip_unified_prefix(_header_path(new_header)),
    )


def _unified_file_kind(old_header: str, new_header: str) -> tuple[PatchKind, str]:
    """The kind and the path of a unified-diff file section."""
    old_path, new_path = _unified_paths(old_header, new_header)
    if old_path is None:
        return _added_file_kind(new_path)
    if new_path is None:
        return "delete", old_path
    return _updated_file_kind(old_path, new_path)


def _added_file_kind(new_path: str | None) -> tuple[PatchKind, str]:
    """The kind of a file section whose old header is /dev/null."""
    if new_path is None:
        raise PatchError(
            "malformed_header",
            "both unified diff headers cannot be /dev/null",
        )
    return "add", new_path


def _updated_file_kind(old_path: str, new_path: str) -> tuple[PatchKind, str]:
    """The kind of a file section whose two headers carry a path."""
    if old_path != new_path:
        raise PatchError(
            "rename_unsupported",
            f"renaming '{old_path}' to '{new_path}' is not supported",
            old_path,
        )
    return "update", old_path


def _parse_unified_hunk(lines: list[str], index: int, path: str) -> tuple[_Hunk, int]:
    """Parse one unified-diff hunk."""
    header = lines[index]
    match = _HUNK_HEADER_RE.match(header)
    if not match:
        raise PatchError("malformed_hunk", f"invalid hunk header: {header!r}", path)

    old_start, old_count, new_start, new_count = _hunk_counts(match)
    index += 1

    ops, index = _read_unified_hunk_body(lines, index, (old_count, new_count), path)
    no_newline, index = _read_unified_no_newline(lines, index, ops, path)

    hunk = _Hunk(old_start, old_count, new_start, new_count, ops)
    _apply_no_newline(hunk, ops, no_newline, path)
    return hunk, index


def _read_unified_hunk(lines: list[str], index: int, path: str) -> tuple[_Hunk, int]:
    """Read one hunk of a unified-diff file section."""
    hunk, index = _parse_unified_hunk(lines, index, path)
    return hunk, index


def _parse_unified_hunks(lines: list[str], index: int, path: str) -> tuple[list[_Hunk], int]:
    """Parse the hunks of one unified-diff file section."""
    hunks: list[_Hunk] = []
    while index < len(lines):
        current = lines[index]
        if current.startswith("@@"):
            hunk, index = _read_unified_hunk(lines, index, path)
            hunks.append(hunk)
            continue
        if current.startswith(_UNIFIED_HEADERS):
            break
        if current.startswith("***"):
            raise PatchError(
                "mixed_format",
                "Codex directives cannot be mixed with a unified diff",
            )
        if not current.strip():
            index += 1
            continue
        raise PatchError(
            "malformed_patch",
            f"unexpected line in unified diff: {current!r}",
            path,
        )
    return hunks, index


def _header_path(value: str) -> str:
    path = value.split("\t", 1)[0].strip()
    if not path:
        raise PatchError("malformed_header", "empty path in file header")
    return path


def _strip_unified_prefix(path: str) -> str | None:
    if path == "/dev/null":
        return None
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def _hunk_counts(match: Any) -> tuple[int, int, int, int]:
    """The old and new start and count declared by a hunk header."""
    old_start = int(match.group("old_start"))
    old_count = int(match.group("old_count")) if match.group("old_count") else 1
    new_start = int(match.group("new_start"))
    new_count = int(match.group("new_count")) if match.group("new_count") else 1
    return old_start, old_count, new_start, new_count


def _read_unified_hunk_line(lines: list[str], index: int, path: str) -> tuple[str, str, int]:
    """Read one line of a unified hunk body."""
    raw = lines[index]
    if raw.startswith("\\"):
        raise PatchError(
            "malformed_hunk",
            "'No newline' marker appeared before the hunk was complete",
            path,
        )
    prefix, text = _hunk_line_prefix(raw)
    return prefix, text, index + 1


def _read_unified_hunk_body(
    lines: list[str], index: int, counts: tuple[int, int], path: str
) -> tuple[list[tuple[str, str]], int]:
    """Read the operations of one unified hunk."""
    old_count, new_count = counts
    ops: list[tuple[str, str]] = []
    old_seen = 0
    new_seen = 0
    while old_seen < old_count or new_seen < new_count:
        if index >= len(lines):
            raise PatchError("unterminated_hunk", "hunk ends before its counts", path)
        prefix, text, index = _read_unified_hunk_line(lines, index, path)
        old_seen, new_seen = _count_hunk_line(prefix, old_seen, new_seen, path)
        if old_seen > old_count or new_seen > new_count:
            raise PatchError(
                "malformed_hunk",
                "hunk contains more lines than its header declares",
                path,
            )
        ops.append((prefix, text))
    return ops, index


def _apply_no_newline(hunk: _Hunk, ops: list[tuple[str, str]], no_newline: bool, path: str) -> None:
    """Record the trailing-newline state of a unified hunk."""
    if no_newline:
        last_prefix = ops[-1][0]
        hunk.old_no_newline = last_prefix in (" ", "-")
        hunk.new_no_newline = last_prefix in (" ", "+")
    if not ops:
        raise PatchError("empty_hunk", "hunk contains no lines", path)


def _hunk_line_prefix(raw: str) -> tuple[str, str]:
    """The prefix and the text of one hunk line."""
    if raw == "":
        # Some producers omit the single space on blank context lines.
        return " ", ""
    return raw[0], raw[1:]


def _count_hunk_line(prefix: str, old_seen: int, new_seen: int, path: str) -> tuple[int, int]:
    """Count one hunk line against the old and the new side."""
    if prefix == " ":
        return old_seen + 1, new_seen + 1
    if prefix == "-":
        return old_seen + 1, new_seen
    if prefix == "+":
        return old_seen, new_seen + 1
    raise PatchError(
        "malformed_hunk",
        f"invalid hunk line prefix {prefix!r}",
        path,
    )


def _has_no_newline_marker(lines: list[str], index: int) -> bool:
    """Whether a 'No newline' marker follows at *index*."""
    if index >= len(lines):
        return False
    return lines[index].startswith("\\")


def _read_unified_no_newline(
    lines: list[str], index: int, ops: list[tuple[str, str]], path: str
) -> tuple[bool, int]:
    """Read the optional 'No newline' marker that follows a hunk."""
    if not _has_no_newline_marker(lines, index):
        return False, index
    if not lines[index].startswith(_NO_NEWLINE):
        raise PatchError(
            "malformed_hunk",
            f"unknown backslash marker: {lines[index]!r}",
            path,
        )
    if not ops:
        raise PatchError("empty_hunk", "hunk contains no lines", path)
    return True, index + 1
