"""Path validation and resolution.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath

from .apply_patch_hunks import _apply_hunks, _join_lines, _match_all_hunks
from .apply_patch_types import _DRIVE_RE, MAX_FILE_BYTES, PatchError, PatchFile, _RawFile
from .apply_patch_writer import (
    _check_result_size,
    _collect_added_lines,
    _count_file_lines,
    _read_source,
    _validate_root,
)

__all__ = [
    "_resolve_file",
    "_validate_add_parent",
    "_validate_path",
    "_validate_root",
]


def _is_empty_relative(pure: PurePosixPath, relative: str) -> bool:
    """Whether the relative path designates nothing."""
    return not pure.parts or relative in ("", ".")


def _validate_relative_parts(pure: PurePosixPath, value: str) -> str:
    """The relative path, refusing anything that escapes the root."""
    if ".." in pure.parts:
        raise PatchError("path_traversal", f"'..' is not allowed in paths: {value}")
    relative = pure.as_posix()
    if _is_empty_relative(pure, relative):
        raise PatchError("invalid_path", f"invalid file path: {value}")
    return relative


def _resolve_candidate(candidate: Path, value: str) -> Path:
    """Resolve the target path, refusing a path the system cannot resolve."""
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise PatchError("invalid_path", f"cannot resolve path: {value}") from exc


def _validate_path_value(value: str) -> None:
    """Refuse an empty path or one that carries NUL bytes."""
    if not value:
        raise PatchError("invalid_path", "empty file path")
    if "\x00" in value:
        raise PatchError("invalid_path", "path contains NUL bytes")


def _is_absolute_path(normalised: str) -> bool:
    """Whether the path points outside the project."""
    return normalised.startswith(("/", "~")) or bool(_DRIVE_RE.match(normalised))


def _validate_path(raw: str, root: Path) -> tuple[str, Path]:
    """Validate *raw*, returning the display path and the write target."""
    value = raw.strip()
    _validate_path_value(value)

    normalised = value.replace("\\", "/")
    if _is_absolute_path(normalised):
        raise PatchError("absolute_path", f"absolute paths are not allowed: {value}")

    pure = PurePosixPath(normalised)
    relative = _validate_relative_parts(pure, value)

    candidate = root.joinpath(*pure.parts)
    resolved = _resolve_candidate(candidate, value)
    _validate_inside_root(resolved, root, value, relative)
    return relative, candidate


def _validate_inside_root(resolved: Path, root: Path, value: str, relative: str) -> None:
    """Refuse a path that escapes the project root."""
    try:
        common = Path(os.path.commonpath([str(resolved), str(root)]))
    except ValueError as exc:
        raise PatchError(
            "outside_root",
            f"path escapes the project root: {value}",
            relative,
        ) from exc
    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise PatchError(
            "outside_root",
            f"path escapes the project root: {value}",
            relative,
        )


def _resolve_file(raw: _RawFile, root: Path, patch_eol: str) -> tuple[PatchFile, list[str]]:
    """Turn one parsed file section into the file to write."""
    relative, target = _validate_path(raw.path, root)
    if raw.kind == "add":
        return _resolve_added(raw, target, relative, patch_eol), []
    if raw.kind == "delete":
        return _resolve_deleted(raw, target, relative), []
    return _resolve_updated(raw, target, relative)


def _resolve_added(raw: _RawFile, target: Path, relative: str, patch_eol: str) -> PatchFile:
    """Build the file that an 'add' section writes."""
    if os.path.lexists(target):
        raise PatchError("file_exists", "file already exists", relative)
    _validate_add_parent(target, relative)
    lines, no_newline = _collect_added_lines(raw, relative)
    text = _join_lines(lines, patch_eol, not no_newline)
    _check_result_size(text, relative)
    return PatchFile(relative, "add", "", text, len(lines), 0)


def _resolve_deleted(raw: _RawFile, target: Path, relative: str) -> PatchFile:
    """Build the file that a 'delete' section removes."""
    if not os.path.lexists(target):
        raise PatchError("not_found", "file does not exist", relative)
    metadata = _stat_target(target, relative)
    _validate_deletable(metadata, relative)
    _validate_deleted_hunks(raw, relative)
    if raw.hunks:
        old_text, _ = _read_source(target, relative)
        _match_all_hunks(old_text, raw.hunks, relative, codex=False)
    deletions = _count_file_lines(target) if metadata.st_size else 0
    return PatchFile(relative, "delete", "", "", 0, deletions)


def _stat_target(target: Path, relative: str) -> os.stat_result:
    """Stat a file the patch is about to delete."""
    try:
        return target.stat()
    except OSError as exc:
        raise PatchError("read_failed", f"cannot stat file: {exc}", relative) from exc


def _validate_deletable(metadata: os.stat_result, relative: str) -> None:
    """Refuse to delete anything but a small regular file."""
    if not stat.S_ISREG(metadata.st_mode):
        raise PatchError("not_a_file", "path is not a regular file", relative)
    if metadata.st_size > MAX_FILE_BYTES:
        raise PatchError(
            "file_too_large",
            f"file is {metadata.st_size} bytes; limit is {MAX_FILE_BYTES}",
            relative,
        )


def _validate_deleted_hunks(raw: _RawFile, relative: str) -> None:
    """A deleted file may only carry removed lines."""
    for hunk in raw.hunks:
        if any(prefix != "-" for prefix, _ in hunk.ops):
            raise PatchError(
                "malformed_patch",
                "a deleted file may only contain removed lines",
                relative,
            )


def _resolve_updated(raw: _RawFile, target: Path, relative: str) -> tuple[PatchFile, list[str]]:
    """Build the file that an 'update' section writes."""
    if not raw.hunks:
        raise PatchError("empty_hunk", "update has no hunks", relative)
    old_text, _ = _read_source(target, relative)
    new_text, warnings = _apply_hunks(old_text, raw.hunks, relative)
    _check_result_size(new_text, relative)
    additions = sum(1 for hunk in raw.hunks for prefix, _ in hunk.ops if prefix == "+")
    deletions = sum(1 for hunk in raw.hunks for prefix, _ in hunk.ops if prefix == "-")
    return (
        PatchFile(relative, "update", old_text, new_text, additions, deletions),
        warnings,
    )


def _nearest_existing_parent(parent: Path) -> Path:
    """The closest ancestor of *parent* that exists."""
    current = parent
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def _validate_add_parent(target: Path, relative: str) -> None:
    """Refuse to create a file under a parent that is not a directory."""
    parent = _nearest_existing_parent(target.parent)
    if not parent.is_dir():
        raise PatchError(
            "invalid_parent",
            f"parent path is not a directory: {parent}",
            relative,
        )
