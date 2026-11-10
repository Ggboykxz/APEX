"""Reading and writing the patched files.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

import logging
import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

from .apply_patch_types import MAX_FILE_BYTES, PatchError, PatchFile, _RawFile

__all__ = [
    "_WriteState",
    "_atomic_write",
    "_check_result_size",
    "_collect_added_lines",
    "_count_file_lines",
    "_default_file_mode",
    "_ensure_parent",
    "_read_source",
    "_rollback",
    "_validate_root",
    "_write_files",
]


@dataclass
class _WriteState:
    """What the write phase must restore when it fails."""

    root: Path
    written: list[PatchFile] = field(default_factory=list)
    removed: list[PatchFile] = field(default_factory=list)
    originals: dict[str, bytes] = field(default_factory=dict)
    modes: dict[str, int] = field(default_factory=dict)
    created_dirs: list[Path] = field(default_factory=list)


def _read_source(path: Path, relative: str) -> tuple[str, int]:
    """Read a source file as UTF-8 text, refusing binaries and huge files."""
    metadata = _stat_source(path, relative)
    _validate_source(metadata, relative)
    data = _read_bytes(path, relative)
    if b"\x00" in data:
        raise PatchError("binary_file", "file contains NUL bytes", relative)
    try:
        return data.decode("utf-8"), len(data)
    except UnicodeDecodeError as exc:
        raise PatchError("binary_file", "file is not valid UTF-8 text", relative) from exc


def _stat_source(path: Path, relative: str) -> os.stat_result:
    """Stat a source file the patch is about to read."""
    try:
        return path.stat()
    except FileNotFoundError as exc:
        raise PatchError("not_found", "file does not exist", relative) from exc
    except OSError as exc:
        raise PatchError("read_failed", f"cannot stat file: {exc}", relative) from exc


def _validate_source(metadata: os.stat_result, relative: str) -> None:
    """Refuse to read anything but a small regular file."""
    if not stat.S_ISREG(metadata.st_mode):
        raise PatchError("not_a_file", "path is not a regular file", relative)
    if metadata.st_size > MAX_FILE_BYTES:
        raise PatchError(
            "file_too_large",
            f"file is {metadata.st_size} bytes; limit is {MAX_FILE_BYTES}",
            relative,
        )


def _read_bytes(path: Path, relative: str) -> bytes:
    """Read the bytes of a source file."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise PatchError("read_failed", f"cannot read file: {exc}", relative) from exc


def _validate_root(root: Path) -> Path:
    try:
        resolved = Path(root).resolve()
    except OSError as exc:
        raise PatchError("invalid_root", f"cannot resolve root: {root}") from exc
    if not resolved.is_dir():
        raise PatchError("invalid_root", f"root is not a directory: {root}")
    return resolved


def _capture_one(state: _WriteState, item: PatchFile) -> None:
    """Capture the content and the mode of one file the patch touches."""
    target = state.root / item.path
    try:
        state.originals[item.path] = target.read_bytes()
        state.modes[item.path] = stat.S_IMODE(target.stat().st_mode)
    except OSError as exc:
        raise PatchError(
            "read_failed",
            f"cannot capture original file: {exc}",
            item.path,
        ) from exc


def _capture_originals(
    state: _WriteState, writes: list[PatchFile], deletes: list[PatchFile]
) -> None:
    """Capture every original before touching the disk."""
    for item in writes:
        if item.kind == "update":
            _capture_one(state, item)
    for item in deletes:
        _capture_one(state, item)


def _write_files(files: list[PatchFile], root: Path) -> None:
    resolved_root = _validate_root(root)
    writes: list[PatchFile] = [item for item in files if item.kind in ("add", "update")]
    deletes: list[PatchFile] = [item for item in files if item.kind == "delete"]

    state = _WriteState(root=resolved_root)
    _capture_originals(state, writes, deletes)

    default_mode = _default_file_mode()
    try:
        for item in writes:
            target = resolved_root / item.path
            state.created_dirs.extend(_ensure_parent(target.parent))
            mode = state.modes.get(item.path, default_mode if item.kind == "add" else None)
            _atomic_write(target, item.new_text.encode("utf-8"), mode)
            state.written.append(item)
        for item in deletes:
            target = resolved_root / item.path
            target.unlink()
            state.removed.append(item)
    except OSError as exc:
        raise _write_failure(state, exc) from exc


def _write_failure(state: _WriteState, exc: OSError) -> PatchError:
    """Roll the partial write back and describe the failure."""
    rollback_errors = _rollback(state)
    failed = state.written[-1] if state.written else (state.removed[-1] if state.removed else None)
    detail = f"write failed: {exc}"
    if rollback_errors:
        detail += "; rollback incomplete: " + "; ".join(rollback_errors)
    else:
        detail += "; partial changes were rolled back"
    return PatchError(
        "write_failed",
        detail,
        failed.path if failed else None,
    )


def _atomic_write(target: Path, data: bytes, mode: int | None) -> None:
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".apex-patch-", dir=str(parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError as exc:
            logger.debug("failed to remove temporary file %s: %s", temporary, exc)
        raise


def _rollback(state: _WriteState) -> list[str]:
    """Restore the files the write phase touched; returns the errors."""
    errors: list[str] = []
    errors.extend(_restore_written(state))
    errors.extend(_restore_removed(state))
    _remove_created_dirs(state)
    return errors


def _restore_written(state: _WriteState) -> list[str]:
    """Restore the files the write phase created or overwrote."""
    errors: list[str] = []
    for item in reversed(state.written):
        target = state.root / item.path
        try:
            original = state.originals.get(item.path)
            if original is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, original, state.modes.get(item.path))
        except OSError as exc:
            errors.append(f"{item.path}: {exc}")
    return errors


def _restore_removed(state: _WriteState) -> list[str]:
    """Restore the files the write phase deleted."""
    errors: list[str] = []
    for item in reversed(state.removed):
        target = state.root / item.path
        try:
            _atomic_write(target, state.originals[item.path], state.modes.get(item.path))
        except (KeyError, OSError) as exc:
            errors.append(f"{item.path}: {exc}")
    return errors


def _remove_created_dirs(state: _WriteState) -> None:
    """Remove the directories the write phase had to create."""
    for directory in reversed(state.created_dirs):
        try:
            directory.rmdir()
        except OSError:
            # Non-empty or already gone: leave it in place.
            pass


def _ensure_parent(parent: Path) -> list[Path]:
    missing: list[Path] = []
    current = parent
    while not current.exists() and current != current.parent:
        missing.append(current)
        current = current.parent
    parent.mkdir(parents=True, exist_ok=True)
    return list(reversed(missing))


def _default_file_mode() -> int:
    """Return the mode a normally created file would receive."""
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def _check_result_size(text: str, relative: str) -> None:
    size = len(text.encode("utf-8"))
    if size > MAX_FILE_BYTES:
        raise PatchError(
            "file_too_large",
            f"resulting file is {size} bytes; limit is {MAX_FILE_BYTES}",
            relative,
        )


def _collect_added_lines(raw: _RawFile, relative: str) -> tuple[list[str], bool]:
    lines: list[str] = []
    no_newline = raw.no_newline
    for hunk in raw.hunks:
        for prefix, text in hunk.ops:
            if prefix != "+":
                raise PatchError(
                    "malformed_patch",
                    "an added file may only contain added lines",
                    relative,
                )
            lines.append(text)
    return lines, no_newline and bool(lines)


def _count_file_lines(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    if not data:
        return 0
    normalised = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    count = normalised.count(b"\n")
    if not normalised.endswith(b"\n"):
        count += 1
    return count
