"""Public entry points of the patch engine.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .apply_patch_codex import _parse_codex
from .apply_patch_paths import _resolve_file, _validate_path, _validate_root
from .apply_patch_types import _CODEX_BEGIN, MAX_PATCH_BYTES, PatchError, PatchFile
from .apply_patch_unified import _parse_unified

__all__ = [
    "_normalise_patch",
    "_resolve_patch",
    "_result",
]


def _resolve_raw_files(
    raw_files: list[Any], resolved_root: Path, patch_eol: str
) -> tuple[list[PatchFile], list[str]]:
    """Resolve every file section of a patch."""
    files: list[PatchFile] = []
    warnings: list[str] = []
    for raw in raw_files:
        item, item_warnings = _resolve_file(raw, resolved_root, patch_eol)
        files.append(item)
        warnings.extend(item_warnings)
    return files, warnings


def _resolve_patch(patch: str, root: Path) -> tuple[list[PatchFile], list[str]]:
    """Parse a patch and resolve every file it touches."""
    if not isinstance(patch, str):
        raise PatchError("invalid_patch", "patch must be a string")

    lines, patch_eol = _normalise_patch(patch)
    resolved_root = _validate_root(root)

    raw_files = _parse_raw_files(lines)
    if not raw_files:
        raise PatchError("empty_patch", "patch does not touch any files")

    _reject_duplicate_paths(raw_files, resolved_root)
    return _resolve_raw_files(raw_files, resolved_root, patch_eol)


def _is_unified_header(line: str) -> bool:
    """Whether the line opens a unified-diff file section."""
    return line.startswith(("--- ", "diff --git "))


def _parse_raw_files(lines: list[str]) -> list[Any]:
    """Parse the patch into its raw file sections."""
    start = _first_content_line(lines)
    first = lines[start].strip()
    if first == _CODEX_BEGIN:
        return _parse_codex(lines, start)
    if _is_unified_header(lines[start]):
        return _parse_unified(lines, start)
    if first.startswith("***"):
        raise PatchError(
            "unknown_format",
            "Codex patches must start with '*** Begin Patch'",
        )
    raise PatchError(
        "unknown_format",
        "expected a '*** Begin Patch' or '--- a/path' patch header",
    )


def _skip_blank_lines(lines: list[str], index: int) -> int:
    """The index of the next line that carries content."""
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _first_content_line(lines: list[str]) -> int:
    """The index of the first line that carries content."""
    start = _skip_blank_lines(lines, 0)
    if start >= len(lines):
        raise PatchError("empty_patch", "patch is empty")
    return start


def _reject_duplicate_paths(raw_files: list[Any], resolved_root: Path) -> None:
    """Refuse a patch that touches the same file twice."""
    seen: set[str] = set()
    for raw in raw_files:
        relative, _target = _validate_path(raw.path, resolved_root)
        identity = os.path.normcase(str((resolved_root / relative).resolve()))
        if identity in seen:
            raise PatchError(
                "duplicate_path",
                f"patch touches '{relative}' more than once",
                relative,
            )
        seen.add(identity)


def _result(files: list[PatchFile], warnings: list[str], *, dry_run: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "dry_run": dry_run,
        "files": [item.summary() for item in files],
        "additions": sum(item.additions for item in files),
        "deletions": sum(item.deletions for item in files),
        "warnings": warnings,
    }


def _normalise_patch(patch: str) -> tuple[list[str], str]:
    """Split a patch into lines and detect its end-of-line convention."""
    _validate_patch_size(patch)
    patch_eol = _detect_patch_eol(patch)
    text = patch.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines, patch_eol


def _validate_patch_size(patch: str) -> None:
    """Refuse a patch that is binary or too large."""
    if "\x00" in patch:
        raise PatchError("binary_patch", "patch contains NUL bytes")
    try:
        size = len(patch.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise PatchError("invalid_patch", "patch is not valid UTF-8 text") from exc
    if size > MAX_PATCH_BYTES:
        raise PatchError(
            "patch_too_large",
            f"patch is {size} bytes; limit is {MAX_PATCH_BYTES}",
        )


def _detect_patch_eol(patch: str) -> str:
    """The end-of-line convention the patch uses."""
    crlf_count = patch.count("\r\n")
    lf_count = patch.count("\n")
    return "\r\n" if crlf_count and crlf_count * 2 >= lf_count else "\n"
