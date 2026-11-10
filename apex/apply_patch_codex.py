"""Parser for the Codex patch dialect.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .apply_patch_types import (
    _CODEX_ADD,
    _CODEX_BEGIN,
    _CODEX_DELETE,
    _CODEX_END,
    _CODEX_UPDATE,
    _NO_NEWLINE,
    PatchError,
    _Hunk,
    _RawFile,
)

__all__ = [
    "_UpdateState",
    "_codex_path",
    "_is_codex_directive",
    "_parse_codex",
    "_parse_codex_update",
]


def _read_codex_sections(lines: list[str], index: int) -> tuple[list[_RawFile], int, bool]:
    """Read the file sections of a Codex patch."""
    files: list[_RawFile] = []
    ended = False
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped == _CODEX_END:
            ended = True
            index += 1
            break
        raw_file, index = _parse_codex_section(lines, index, stripped)
        files.append(raw_file)
    return files, index, ended


def _parse_codex(lines: list[str], start: int) -> list[_RawFile]:
    """Parse a Codex patch into its file sections."""
    if lines[start].strip() != _CODEX_BEGIN:
        raise PatchError("unknown_format", "missing '*** Begin Patch'")

    files, index, ended = _read_codex_sections(lines, start + 1)
    if not ended:
        raise PatchError("unterminated_patch", "missing '*** End Patch'")
    _reject_trailing_content(lines, index)
    return files


def _parse_codex_section(lines: list[str], index: int, stripped: str) -> tuple[_RawFile, int]:
    """Parse one file section of a Codex patch."""
    parser = _codex_section_parser(stripped)
    if parser is None:
        raise PatchError(
            "malformed_patch",
            f"unexpected content outside a Codex file section: {stripped!r}",
        )
    return parser(lines, index)


def _codex_section_parser(stripped: str) -> Any:
    """The parser of the file section the directive opens."""
    if stripped.startswith(_CODEX_ADD):
        return _parse_codex_add
    if stripped.startswith(_CODEX_UPDATE):
        return _parse_codex_update_section
    if stripped.startswith(_CODEX_DELETE):
        return _parse_codex_delete
    if stripped.startswith("***"):
        raise PatchError(
            "unsupported_directive",
            f"unsupported Codex directive: {stripped}",
        )
    return None


def _read_no_newline_marker(marker_seen: bool, ops: list[tuple[str, str]], path: str) -> bool:
    """Validate a 'No newline' marker in an added file."""
    if marker_seen:
        raise PatchError(
            "malformed_patch",
            "unexpected 'No newline' marker in added file",
            path,
        )
    if not ops:
        raise PatchError(
            "malformed_patch",
            "unexpected 'No newline' marker in added file",
            path,
        )
    return True


def _read_codex_added_line(
    raw: str, marker_seen: bool, ops: list[tuple[str, str]], path: str
) -> None:
    """Consume one line of an added file body."""
    if _marker_ends_body(marker_seen, raw):
        raise PatchError(
            "malformed_patch",
            "'No newline' marker must terminate the file body",
            path,
        )
    _append_codex_added_line(raw, ops, path)


def _marker_ends_body(marker_seen: bool, raw: str) -> bool:
    """Whether a 'No newline' marker is followed by more content."""
    if not marker_seen:
        return False
    return bool(raw.strip())


def _append_codex_added_line(raw: str, ops: list[tuple[str, str]], path: str) -> None:
    """Append one added line, refusing anything that is not an addition."""
    if not raw.startswith("+"):
        raise PatchError(
            "malformed_patch",
            "added file lines must start with '+'",
            path,
        )
    ops.append(("+", raw[1:]))


def _read_codex_added_body(
    lines: list[str], index: int, path: str
) -> tuple[list[tuple[str, str]], bool, int]:
    """Read the body of an added file."""
    ops: list[tuple[str, str]] = []
    no_newline = False
    marker_seen = False
    while not _at_codex_directive(lines, index):
        raw = lines[index]
        if raw.startswith(_NO_NEWLINE):
            marker_seen = _read_no_newline_marker(marker_seen, ops, path)
            no_newline = True
        else:
            _read_codex_added_line(raw, marker_seen, ops, path)
        index += 1
    return ops, no_newline, index


def _parse_codex_add(lines: list[str], index: int) -> tuple[_RawFile, int]:
    """Parse an '*** Add File' section."""
    path, index = _codex_path(lines[index], _CODEX_ADD, index)
    ops, no_newline, index = _read_codex_added_body(lines, index, path)
    if any(prefix != "+" for prefix, _ in ops):
        raise PatchError("malformed_patch", "invalid added file body", path)
    hunks = [_Hunk(None, None, None, None, ops)] if ops else []
    return _RawFile(path, "add", hunks, no_newline), index


def _parse_codex_update_section(lines: list[str], index: int) -> tuple[_RawFile, int]:
    """Parse an '*** Update File' section."""
    path, index = _codex_path(lines[index], _CODEX_UPDATE, index)
    hunks, index = _parse_codex_update(lines, index, path)
    return _RawFile(path, "update", hunks), index


def _parse_codex_delete(lines: list[str], index: int) -> tuple[_RawFile, int]:
    """Parse a '*** Delete File' section."""
    path, index = _codex_path(lines[index], _CODEX_DELETE, index)
    while not _at_codex_directive(lines, index):
        if lines[index].strip():
            raise PatchError(
                "malformed_patch",
                "a deleted file cannot carry content",
                path,
            )
        index += 1
    return _RawFile(path, "delete", []), index


def _reject_trailing_content(lines: list[str], index: int) -> None:
    """Reject any content after the end of the patch."""
    while index < len(lines):
        if lines[index].strip():
            raise PatchError(
                "trailing_content",
                "unexpected content after '*** End Patch'",
            )
        index += 1


def _codex_path(line: str, directive: str, index: int) -> tuple[str, int]:
    raw = line.strip()[len(directive) :].strip()
    if not raw:
        raise PatchError(
            "malformed_patch",
            f"{directive.rstrip(':')} requires a path (line {index + 1})",
        )
    return raw, index + 1


def _at_codex_directive(lines: list[str], index: int) -> bool:
    """Whether the line at *index* opens a new Codex section."""
    return index >= len(lines) or _is_codex_directive(lines[index])


def _is_codex_directive(line: str) -> bool:
    stripped = line.strip()
    return stripped == _CODEX_END or stripped.startswith(
        (_CODEX_ADD, _CODEX_UPDATE, _CODEX_DELETE, "***")
    )


def _read_codex_no_newline(state: _UpdateState, path: str) -> None:
    """Consume the 'No newline' marker that closes a Codex hunk."""
    if state.marker_seen or not state.current.ops:
        raise PatchError(
            "malformed_patch",
            "unexpected 'No newline' marker",
            path,
        )
    last_prefix = state.current.ops[-1][0]
    state.current.old_no_newline = last_prefix in (" ", "-")
    state.current.new_no_newline = last_prefix in (" ", "+")
    state.marker_seen = True


def _read_codex_update_line(
    raw: str,
    current: _Hunk,
    marker_seen: bool,
    path: str,
) -> tuple[_Hunk, bool, bool]:
    """Consume one line of a Codex update hunk.

    Returns the hunk, whether a 'No newline' marker was seen and whether
    the line carried a hunk operation.
    """
    if raw.startswith(_NO_NEWLINE):
        return _read_codex_no_newline(current, marker_seen, path)
    if marker_seen:
        raise PatchError(
            "malformed_patch",
            "'No newline' marker must terminate the hunk",
            path,
        )
    if raw == "":
        raise PatchError(
            "malformed_patch",
            "empty hunk lines must carry a ' ', '-' or '+' prefix",
            path,
        )
    prefix = raw[0]
    if prefix not in (" ", "-", "+"):
        raise PatchError(
            "malformed_patch",
            f"invalid hunk line prefix {prefix!r}",
            path,
        )
    current.ops.append((prefix, raw[1:]))
    return current, False, True


def _finish_codex_hunk(state: _UpdateState, path: str) -> None:
    """Close the hunk being parsed."""
    if state.current.ops:
        state.hunks.append(state.current)
    elif state.started:
        raise PatchError("empty_hunk", "update hunk contains no lines", path)
    state.current = _Hunk(None, None, None, None)
    state.started = False
    state.marker_seen = False


@dataclass
class _UpdateState:
    """The state of the Codex update section being parsed."""

    hunks: list[_Hunk] = field(default_factory=list)
    current: _Hunk = field(default_factory=lambda: _Hunk(None, None, None, None))
    started: bool = False
    marker_seen: bool = False


def _codex_hunk_prefix(raw: str, path: str) -> str:
    """The prefix of a hunk line, refusing an unknown one."""
    if raw == "":
        raise PatchError(
            "malformed_patch",
            "empty hunk lines must carry a ' ', '-' or '+' prefix",
            path,
        )
    prefix = raw[0]
    if prefix not in (" ", "-", "+"):
        raise PatchError(
            "malformed_patch",
            f"invalid hunk line prefix {prefix!r}",
            path,
        )
    return prefix


def _read_codex_update_hunk(state: _UpdateState, raw: str, path: str) -> None:
    """Consume one line of a Codex update hunk."""
    if raw.startswith(_NO_NEWLINE):
        _read_codex_no_newline(state, path)
        return
    if state.marker_seen:
        raise PatchError(
            "malformed_patch",
            "'No newline' marker must terminate the hunk",
            path,
        )
    prefix = _codex_hunk_prefix(raw, path)
    state.current.ops.append((prefix, raw[1:]))
    state.started = True


def _read_codex_update_body(lines: list[str], index: int, path: str) -> tuple[list[_Hunk], int]:
    """Read the hunks of a Codex update section."""
    state = _UpdateState()
    while not _at_codex_directive(lines, index):
        raw = lines[index]
        if raw.startswith("@@"):
            _finish_codex_hunk(state, path)
            state.started = True
            index += 1
            continue
        _read_codex_update_hunk(state, raw, path)
        index += 1

    _finish_codex_hunk(state, path)
    if not state.hunks:
        raise PatchError("empty_hunk", "update has no hunks", path)
    return state.hunks, index


def _parse_codex_update(lines: list[str], index: int, path: str) -> tuple[list[_Hunk], int]:
    """Parse the hunks of a Codex '*** Update File' section."""
    return _read_codex_update_body(lines, index, path)
