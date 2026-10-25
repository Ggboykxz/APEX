"""Pure-Python, dependency-free multi-file patch engine.

The engine understands two patch dialects:

* Codex-style patches delimited by ``*** Begin Patch`` / ``*** End Patch`` and
  ``*** Add File:``, ``*** Update File:``, ``*** Delete File:`` directives.
* Unified diffs with ``--- a/path`` / ``+++ b/path`` headers and ``@@`` hunks.

Every patch is validated in memory before anything is written.  The on-disk
apply phase writes files through a temporary file in the destination directory
and :func:`os.replace`, then removes deleted files only once all writes have
succeeded.  A failure rolls previously written files back on a best-effort
basis.
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_PATCH_BYTES",
    "PatchError",
    "PatchFile",
    "PatchPreview",
    "apply_patch",
    "parse_patch",
    "preview_patch",
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


def parse_patch(patch: str, root: Path) -> list[PatchFile]:
    """Parse and validate *patch* against *root*, returning resolved files.

    No filesystem writes occur.  The returned :class:`PatchFile` objects carry
    the current and future contents plus addition/deletion counts.  Validation
    failures raise :class:`PatchError`.
    """
    files, _warnings = _resolve_patch(patch, root)
    return files


def preview_patch(patch: str, root: Path) -> PatchPreview:
    """Validate *patch* and return the resolved multi-file preview."""
    files, warnings = _resolve_patch(patch, root)
    return PatchPreview(
        files=files,
        additions=sum(item.additions for item in files),
        deletions=sum(item.deletions for item in files),
        warnings=warnings,
    )


def apply_patch(patch: str, root: Path, dry_run: bool = False) -> dict[str, Any]:
    """Validate and atomically apply *patch* under *root*.

    With ``dry_run=True`` every check runs but no file, directory, or temporary
    file is created.  On success a result dictionary is returned; validation
    and write failures raise :class:`PatchError`.
    """
    files, warnings = _resolve_patch(patch, root)
    if dry_run:
        return _result(files, warnings, dry_run=True)

    _write_files(files, root)
    return _result(files, warnings, dry_run=False)


def _resolve_patch(patch: str, root: Path) -> tuple[list[PatchFile], list[str]]:
    if not isinstance(patch, str):
        raise PatchError("invalid_patch", "patch must be a string")

    lines, patch_eol = _normalise_patch(patch)
    resolved_root = _validate_root(root)

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines):
        raise PatchError("empty_patch", "patch is empty")

    first = lines[start].strip()
    if first == _CODEX_BEGIN:
        raw_files = _parse_codex(lines, start)
    elif lines[start].startswith("--- ") or lines[start].startswith("diff --git "):
        raw_files = _parse_unified(lines, start)
    elif first.startswith("***"):
        raise PatchError(
            "unknown_format",
            "Codex patches must start with '*** Begin Patch'",
        )
    else:
        raise PatchError(
            "unknown_format",
            "expected a '*** Begin Patch' or '--- a/path' patch header",
        )

    if not raw_files:
        raise PatchError("empty_patch", "patch does not touch any files")

    files: list[PatchFile] = []
    warnings: list[str] = []
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

    for raw in raw_files:
        item, item_warnings = _resolve_file(raw, resolved_root, patch_eol)
        files.append(item)
        warnings.extend(item_warnings)
    return files, warnings


def _result(files: list[PatchFile], warnings: list[str], *, dry_run: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "dry_run": dry_run,
        "files": [item.summary() for item in files],
        "additions": sum(item.additions for item in files),
        "deletions": sum(item.deletions for item in files),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Patch text and format parsing
# ---------------------------------------------------------------------------


def _normalise_patch(patch: str) -> tuple[list[str], str]:
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

    crlf_count = patch.count("\r\n")
    lf_count = patch.count("\n")
    patch_eol = "\r\n" if crlf_count and crlf_count * 2 >= lf_count else "\n"
    text = patch.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines, patch_eol


def _validate_root(root: Path) -> Path:
    try:
        resolved = Path(root).resolve()
    except OSError as exc:
        raise PatchError("invalid_root", f"cannot resolve root: {root}") from exc
    if not resolved.is_dir():
        raise PatchError("invalid_root", f"root is not a directory: {root}")
    return resolved


def _parse_codex(lines: list[str], start: int) -> list[_RawFile]:
    if lines[start].strip() != _CODEX_BEGIN:
        raise PatchError("unknown_format", "missing '*** Begin Patch'")

    files: list[_RawFile] = []
    index = start + 1
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
        if stripped.startswith(_CODEX_ADD):
            path, index = _codex_path(lines[index], _CODEX_ADD, index)
            ops: list[tuple[str, str]] = []
            no_newline = False
            marker_seen = False
            while index < len(lines) and not _is_codex_directive(lines[index]):
                raw = lines[index]
                if raw.startswith(_NO_NEWLINE):
                    if marker_seen or not ops:
                        raise PatchError(
                            "malformed_patch",
                            "unexpected 'No newline' marker in added file",
                            path,
                        )
                    no_newline = True
                    marker_seen = True
                elif marker_seen and raw.strip():
                    raise PatchError(
                        "malformed_patch",
                        "'No newline' marker must terminate the file body",
                        path,
                    )
                elif raw.startswith("+"):
                    ops.append(("+", raw[1:]))
                else:
                    raise PatchError(
                        "malformed_patch",
                        "added file lines must start with '+'",
                        path,
                    )
                index += 1
            if any(prefix != "+" for prefix, _ in ops):
                raise PatchError("malformed_patch", "invalid added file body", path)
            hunks = [_Hunk(None, None, None, None, ops)] if ops else []
            files.append(_RawFile(path, "add", hunks, no_newline))
            continue
        if stripped.startswith(_CODEX_UPDATE):
            path, index = _codex_path(lines[index], _CODEX_UPDATE, index)
            hunks, index = _parse_codex_update(lines, index, path)
            files.append(_RawFile(path, "update", hunks))
            continue
        if stripped.startswith(_CODEX_DELETE):
            path, index = _codex_path(lines[index], _CODEX_DELETE, index)
            while index < len(lines) and not _is_codex_directive(lines[index]):
                if lines[index].strip():
                    raise PatchError(
                        "malformed_patch",
                        "a deleted file cannot carry content",
                        path,
                    )
                index += 1
            files.append(_RawFile(path, "delete", []))
            continue
        if stripped.startswith("***"):
            raise PatchError(
                "unsupported_directive",
                f"unsupported Codex directive: {stripped}",
            )
        raise PatchError(
            "malformed_patch",
            f"unexpected content outside a Codex file section: {stripped!r}",
        )

    if not ended:
        raise PatchError("unterminated_patch", "missing '*** End Patch'")
    while index < len(lines):
        if lines[index].strip():
            raise PatchError(
                "trailing_content",
                "unexpected content after '*** End Patch'",
            )
        index += 1
    return files


def _codex_path(line: str, directive: str, index: int) -> tuple[str, int]:
    raw = line.strip()[len(directive) :].strip()
    if not raw:
        raise PatchError(
            "malformed_patch",
            f"{directive.rstrip(':')} requires a path (line {index + 1})",
        )
    return raw, index + 1


def _is_codex_directive(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped == _CODEX_END
        or stripped.startswith(_CODEX_ADD)
        or stripped.startswith(_CODEX_UPDATE)
        or stripped.startswith(_CODEX_DELETE)
        or stripped.startswith("***")
    )


def _parse_codex_update(lines: list[str], index: int, path: str) -> tuple[list[_Hunk], int]:
    hunks: list[_Hunk] = []
    current = _Hunk(None, None, None, None)
    current_started = False
    marker_seen = False

    def finish_current() -> None:
        nonlocal current, current_started, marker_seen
        if current.ops:
            hunks.append(current)
        elif current_started:
            raise PatchError("empty_hunk", "update hunk contains no lines", path)
        current = _Hunk(None, None, None, None)
        current_started = False
        marker_seen = False

    while index < len(lines) and not _is_codex_directive(lines[index]):
        raw = lines[index]
        if raw.startswith("@@"):
            finish_current()
            current_started = True
            index += 1
            continue
        if raw.startswith(_NO_NEWLINE):
            if marker_seen or not current.ops:
                raise PatchError(
                    "malformed_patch",
                    "unexpected 'No newline' marker",
                    path,
                )
            last_prefix = current.ops[-1][0]
            current.old_no_newline = last_prefix in (" ", "-")
            current.new_no_newline = last_prefix in (" ", "+")
            marker_seen = True
            index += 1
            continue
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
        current_started = True
        index += 1

    finish_current()
    if not hunks:
        raise PatchError("empty_hunk", "update has no hunks", path)
    return hunks, index


def _parse_unified(lines: list[str], start: int) -> list[_RawFile]:
    files: list[_RawFile] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("diff --git "):
            index += 1
            continue
        if line.startswith(_UNIFIED_METADATA):
            index += 1
            continue
        if line.startswith("***"):
            raise PatchError(
                "mixed_format",
                "Codex directives cannot be mixed with a unified diff",
            )
        if not line.startswith("--- "):
            raise PatchError(
                "malformed_patch",
                f"expected a '--- ' file header, got {line!r}",
            )
        if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise PatchError(
                "malformed_header",
                "'--- ' header must be followed by a '+++ ' header",
            )
        old_header = _header_path(lines[index][4:])
        new_header = _header_path(lines[index + 1][4:])
        index += 2

        old_path = _strip_unified_prefix(old_header)
        new_path = _strip_unified_prefix(new_header)
        if old_path is None:
            if new_path is None:
                raise PatchError(
                    "malformed_header",
                    "both unified diff headers cannot be /dev/null",
                )
            kind: PatchKind = "add"
            path = new_path
        elif new_path is None:
            kind = "delete"
            path = old_path
        else:
            if old_path != new_path:
                raise PatchError(
                    "rename_unsupported",
                    f"renaming '{old_path}' to '{new_path}' is not supported",
                    old_path,
                )
            kind = "update"
            path = old_path

        hunks: list[_Hunk] = []
        while index < len(lines):
            current = lines[index]
            if current.startswith("@@"):
                hunk, index = _parse_unified_hunk(lines, index, path)
                hunks.append(hunk)
                continue
            if (
                current.startswith("--- ")
                or current.startswith("diff --git ")
                or current.startswith(_UNIFIED_METADATA)
            ):
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

        no_newline = bool(hunks and hunks[-1].new_no_newline)
        files.append(_RawFile(path, kind, hunks, no_newline))
    return files


def _header_path(value: str) -> str:
    path = value.split("\t", 1)[0].strip()
    if not path:
        raise PatchError("malformed_header", "empty path in file header")
    return path


def _strip_unified_prefix(path: str) -> str | None:
    if path == "/dev/null":
        return None
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _parse_unified_hunk(lines: list[str], index: int, path: str) -> tuple[_Hunk, int]:
    header = lines[index]
    match = _HUNK_HEADER_RE.match(header)
    if not match:
        raise PatchError("malformed_hunk", f"invalid hunk header: {header!r}", path)

    old_start = int(match.group("old_start"))
    old_count = int(match.group("old_count")) if match.group("old_count") else 1
    new_start = int(match.group("new_start"))
    new_count = int(match.group("new_count")) if match.group("new_count") else 1
    index += 1

    ops: list[tuple[str, str]] = []
    old_seen = 0
    new_seen = 0
    while old_seen < old_count or new_seen < new_count:
        if index >= len(lines):
            raise PatchError("unterminated_hunk", "hunk ends before its counts", path)
        raw = lines[index]
        if raw.startswith("\\"):
            raise PatchError(
                "malformed_hunk",
                "'No newline' marker appeared before the hunk was complete",
                path,
            )
        if raw == "":
            # Some producers omit the single space on blank context lines.
            prefix = " "
            text = ""
        else:
            prefix = raw[0]
            text = raw[1:]
        if prefix == " ":
            old_seen += 1
            new_seen += 1
        elif prefix == "-":
            old_seen += 1
        elif prefix == "+":
            new_seen += 1
        else:
            raise PatchError(
                "malformed_hunk",
                f"invalid hunk line prefix {prefix!r}",
                path,
            )
        if old_seen > old_count or new_seen > new_count:
            raise PatchError(
                "malformed_hunk",
                "hunk contains more lines than its header declares",
                path,
            )
        ops.append((prefix, text))
        index += 1

    no_newline = False
    if index < len(lines) and lines[index].startswith("\\"):
        if not lines[index].startswith(_NO_NEWLINE):
            raise PatchError(
                "malformed_hunk",
                f"unknown backslash marker: {lines[index]!r}",
                path,
            )
        if not ops:
            raise PatchError("empty_hunk", "hunk contains no lines", path)
        no_newline = True
        index += 1

    hunk = _Hunk(old_start, old_count, new_start, new_count, ops)
    if no_newline:
        last_prefix = ops[-1][0]
        hunk.old_no_newline = last_prefix in (" ", "-")
        hunk.new_no_newline = last_prefix in (" ", "+")
    if not ops:
        raise PatchError("empty_hunk", "hunk contains no lines", path)
    return hunk, index


# ---------------------------------------------------------------------------
# Path, content, and hunk resolution
# ---------------------------------------------------------------------------


def _validate_path(raw: str, root: Path) -> tuple[str, Path]:
    """Validate *raw*, returning the display path and the write target."""
    value = raw.strip()
    if not value:
        raise PatchError("invalid_path", "empty file path")
    if "\x00" in value:
        raise PatchError("invalid_path", "path contains NUL bytes")

    normalised = value.replace("\\", "/")
    if normalised.startswith(("/", "~")) or _DRIVE_RE.match(normalised):
        raise PatchError("absolute_path", f"absolute paths are not allowed: {value}")

    pure = PurePosixPath(normalised)
    if ".." in pure.parts:
        raise PatchError("path_traversal", f"'..' is not allowed in paths: {value}")
    if not pure.parts or pure.as_posix() in ("", "."):
        raise PatchError("invalid_path", f"invalid file path: {value}")
    relative = pure.as_posix()

    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise PatchError("invalid_path", f"cannot resolve path: {value}") from exc

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
    return relative, candidate


def _read_source(path: Path, relative: str) -> tuple[str, int]:
    try:
        metadata = path.stat()
    except FileNotFoundError as exc:
        raise PatchError("not_found", "file does not exist", relative) from exc
    except OSError as exc:
        raise PatchError("read_failed", f"cannot stat file: {exc}", relative) from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise PatchError("not_a_file", "path is not a regular file", relative)
    if metadata.st_size > MAX_FILE_BYTES:
        raise PatchError(
            "file_too_large",
            f"file is {metadata.st_size} bytes; limit is {MAX_FILE_BYTES}",
            relative,
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PatchError("read_failed", f"cannot read file: {exc}", relative) from exc
    if b"\x00" in data:
        raise PatchError("binary_file", "file contains NUL bytes", relative)
    try:
        return data.decode("utf-8"), len(data)
    except UnicodeDecodeError as exc:
        raise PatchError("binary_file", "file is not valid UTF-8 text", relative) from exc


def _resolve_file(raw: _RawFile, root: Path, patch_eol: str) -> tuple[PatchFile, list[str]]:
    relative, target = _validate_path(raw.path, root)

    if raw.kind == "add":
        if os.path.lexists(target):
            raise PatchError("file_exists", "file already exists", relative)
        _validate_add_parent(target, relative)
        lines, no_newline = _collect_added_lines(raw, relative)
        text = _join_lines(lines, patch_eol, not no_newline)
        _check_result_size(text, relative)
        return PatchFile(relative, "add", "", text, len(lines), 0), []

    if raw.kind == "delete":
        if not os.path.lexists(target):
            raise PatchError("not_found", "file does not exist", relative)
        try:
            metadata = target.stat()
        except OSError as exc:
            raise PatchError("read_failed", f"cannot stat file: {exc}", relative) from exc
        if not stat.S_ISREG(metadata.st_mode):
            raise PatchError("not_a_file", "path is not a regular file", relative)
        if metadata.st_size > MAX_FILE_BYTES:
            raise PatchError(
                "file_too_large",
                f"file is {metadata.st_size} bytes; limit is {MAX_FILE_BYTES}",
                relative,
            )
        for hunk in raw.hunks:
            if any(prefix != "-" for prefix, _ in hunk.ops):
                raise PatchError(
                    "malformed_patch",
                    "a deleted file may only contain removed lines",
                    relative,
                )
        if raw.hunks:
            old_text, _ = _read_source(target, relative)
            _match_all_hunks(old_text, raw.hunks, relative, codex=False)
        deletions = _count_file_lines(target) if metadata.st_size else 0
        return PatchFile(relative, "delete", "", "", 0, deletions), []

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


def _validate_add_parent(target: Path, relative: str) -> None:
    parent = target.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    if not parent.is_dir():
        raise PatchError(
            "invalid_parent",
            f"parent path is not a directory: {parent}",
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


def _check_result_size(text: str, relative: str) -> None:
    size = len(text.encode("utf-8"))
    if size > MAX_FILE_BYTES:
        raise PatchError(
            "file_too_large",
            f"resulting file is {size} bytes; limit is {MAX_FILE_BYTES}",
            relative,
        )


def _split_lines(text: str) -> list[str]:
    if not text:
        return []
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalised.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _detect_eol(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _join_lines(lines: list[str], eol: str, final_newline: bool) -> str:
    if not lines:
        return ""
    text = eol.join(lines)
    return text + eol if final_newline else text


def _old_block(hunk: _Hunk) -> list[str]:
    return [text for prefix, text in hunk.ops if prefix in (" ", "-")]


def _new_block(hunk: _Hunk) -> list[str]:
    return [text for prefix, text in hunk.ops if prefix in (" ", "+")]


def _find_match(
    lines: list[str],
    block: list[str],
    expected: int,
    *,
    prefer_forward: bool,
) -> int | None:
    total = len(lines)
    width = len(block)
    if width == 0:
        return min(max(expected, 0), total)
    if width > total:
        return None

    start = min(max(expected, 0), total - width)
    if prefer_forward:
        candidates = list(range(start, total - width + 1))
        candidates.extend(range(start - 1, -1, -1))
    else:
        candidates = []
        max_distance = max(start, total - width - start)
        for distance in range(max_distance + 1):
            after = start + distance
            before = start - distance
            if after <= total - width:
                candidates.append(after)
            if distance and before >= 0:
                candidates.append(before)

    for position in candidates:
        if lines[position : position + width] == block:
            return position
    return None


def _match_all_hunks(
    old_text: str, hunks: list[_Hunk], relative: str, *, codex: bool
) -> list[tuple[int, int, list[str], _Hunk, int]]:
    lines = _split_lines(old_text)
    matched: list[tuple[int, int, list[str], _Hunk, int]] = []
    cursor = 0
    for number, hunk in enumerate(hunks, start=1):
        block = _old_block(hunk)
        if hunk.old_start is not None:
            expected = hunk.old_start if hunk.old_count == 0 else hunk.old_start - 1
        else:
            expected = cursor
        found = _find_match(lines, block, expected, prefer_forward=codex)
        if found is None:
            raise PatchError(
                "context_mismatch",
                f"hunk {number} does not match the current file content",
                relative,
            )
        matched.append((found, found + len(block), _new_block(hunk), hunk, number))
        cursor = found + len(block)

    ordered = sorted(matched, key=lambda item: (item[0], item[1]))
    previous_start = -1
    previous_end = -1
    for start, end, _, _, _ in ordered:
        if start < previous_end:
            raise PatchError(
                "overlapping_hunks",
                "two hunks modify overlapping regions",
                relative,
            )
        if start == previous_start == end == previous_end and start == end:
            raise PatchError(
                "overlapping_hunks",
                "two insertion hunks target the same position",
                relative,
            )
        previous_start, previous_end = start, end
    return matched


def _apply_hunks(old_text: str, hunks: list[_Hunk], relative: str) -> tuple[str, list[str]]:
    lines = _split_lines(old_text)
    codex = all(hunk.old_start is None for hunk in hunks)
    matched = _match_all_hunks(old_text, hunks, relative, codex=codex)
    warnings: list[str] = []

    # Explicit line numbers only exist in unified diffs.  Report fuzz visibly.
    for start, _end, _replacement, hunk, number in matched:
        if hunk.old_start is None:
            continue
        expected = hunk.old_start if hunk.old_count == 0 else hunk.old_start - 1
        if start != expected:
            warnings.append(
                f"{relative}: hunk {number} applied at line {start + 1} "
                f"(offset {start - expected:+d})"
            )

    ordered = sorted(matched, key=lambda item: (item[0], item[1]))
    output: list[str] = []
    position = 0
    for start, end, replacement, _hunk, _number in ordered:
        output.extend(lines[position:start])
        output.extend(replacement)
        position = end
    output.extend(lines[position:])

    old_final_newline = old_text.endswith(("\n", "\r"))
    final_newline = old_final_newline
    if not output:
        final_newline = False
    else:
        end_hunks = [item for item in ordered if item[1] == len(lines)]
        if end_hunks:
            _start, _end, _replacement, hunk, _number = end_hunks[-1]
            last_output = next(
                (prefix for prefix, _ in reversed(hunk.ops) if prefix != "-"),
                None,
            )
            last_source = hunk.ops[-1][0] if hunk.ops else None
            if hunk.new_no_newline:
                final_newline = False
            elif last_output == "+":
                final_newline = True
            elif last_output == " ":
                # A context line that is still the final source line keeps the
                # source's trailing-newline state.  If it was followed by
                # removed lines, the context line necessarily had a newline.
                final_newline = old_final_newline if last_source == " " else True
            else:
                # The hunk removed the trailing lines; the remaining line came
                # from earlier in the file and therefore had a newline.
                final_newline = True

    eol = _detect_eol(old_text)
    return _join_lines(output, eol, final_newline), warnings


# ---------------------------------------------------------------------------
# Atomic write phase
# ---------------------------------------------------------------------------


def _write_files(files: list[PatchFile], root: Path) -> None:
    resolved_root = _validate_root(root)
    writes: list[PatchFile] = [item for item in files if item.kind in ("add", "update")]
    deletes: list[PatchFile] = [item for item in files if item.kind == "delete"]

    # Capture every original before touching the disk.
    originals: dict[str, bytes] = {}
    modes: dict[str, int] = {}
    for item in writes:
        target = resolved_root / item.path
        if item.kind == "update":
            try:
                originals[item.path] = target.read_bytes()
                modes[item.path] = stat.S_IMODE(target.stat().st_mode)
            except OSError as exc:
                raise PatchError(
                    "read_failed",
                    f"cannot capture original file: {exc}",
                    item.path,
                ) from exc
    for item in deletes:
        target = resolved_root / item.path
        try:
            originals[item.path] = target.read_bytes()
            modes[item.path] = stat.S_IMODE(target.stat().st_mode)
        except OSError as exc:
            raise PatchError(
                "read_failed",
                f"cannot capture original file: {exc}",
                item.path,
            ) from exc

    written: list[PatchFile] = []
    removed: list[PatchFile] = []
    created_dirs: list[Path] = []
    default_mode = _default_file_mode()
    try:
        for item in writes:
            target = resolved_root / item.path
            created_dirs.extend(_ensure_parent(target.parent))
            mode = modes.get(item.path, default_mode if item.kind == "add" else None)
            _atomic_write(target, item.new_text.encode("utf-8"), mode)
            written.append(item)
        for item in deletes:
            target = resolved_root / item.path
            target.unlink()
            removed.append(item)
    except OSError as exc:
        rollback_errors = _rollback(
            resolved_root,
            written,
            removed,
            originals,
            modes,
            created_dirs,
        )
        failed = written[-1] if written else (removed[-1] if removed else None)
        detail = f"write failed: {exc}"
        if rollback_errors:
            detail += "; rollback incomplete: " + "; ".join(rollback_errors)
        else:
            detail += "; partial changes were rolled back"
        raise PatchError(
            "write_failed",
            detail,
            failed.path if failed else None,
        ) from exc


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
        except OSError:
            pass
        raise


def _rollback(
    root: Path,
    written: list[PatchFile],
    removed: list[PatchFile],
    originals: dict[str, bytes],
    modes: dict[str, int],
    created_dirs: list[Path],
) -> list[str]:
    errors: list[str] = []
    for item in reversed(written):
        target = root / item.path
        try:
            original = originals.get(item.path)
            if original is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, original, modes.get(item.path))
        except OSError as exc:
            errors.append(f"{item.path}: {exc}")

    for item in reversed(removed):
        target = root / item.path
        try:
            _atomic_write(target, originals[item.path], modes.get(item.path))
        except (KeyError, OSError) as exc:
            errors.append(f"{item.path}: {exc}")

    for directory in reversed(created_dirs):
        try:
            directory.rmdir()
        except OSError:
            # Non-empty or already gone: leave it in place.
            pass
    return errors
