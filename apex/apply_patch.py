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

The engine lives in the sibling ``apex.apply_patch_*`` modules: one
responsibility per module. This module is the public facade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .apply_patch_api import _resolve_patch, _result
from .apply_patch_types import (
    MAX_FILE_BYTES,
    MAX_PATCH_BYTES,
    PatchError,
    PatchFile,
    PatchPreview,
)
from .apply_patch_writer import _write_files

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
