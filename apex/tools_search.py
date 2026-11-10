"""Discovery tools: list, search, glob, tree, batch and replace.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "SearchToolsMixin",
]

logger = logging.getLogger(__name__)


@dataclass
class _TreeContext:
    """Where the tree walker currently stands."""

    max_depth: int
    prefix: str = ""
    depth: int = 0


class SearchToolsMixin:
    def _entry_size(self, entry: Path) -> str:
        """The size column of one directory entry."""
        try:
            size = entry.stat().st_size
        except Exception:  # noqa: BLE001
            return "?          "
        return f"{size:>10}" if entry.is_file() else "<DIR>    "

    def _execute_list_files(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Directory not found: {path}"
        if not path.is_dir():
            return f"ERROR: Not a directory: {path}"
        try:
            entries = [
                f"{self._entry_size(entry)}  {entry.name}" for entry in sorted(path.iterdir())
            ]
            return "\n".join(entries) if entries else "[empty directory]"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot list directory: {e}"

    def _execute_search_in_files(self, args: dict[str, Any]) -> str:
        pattern = args["pattern"]
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            regex = re.compile(pattern)
            results = self._collect_matches(path, regex)
            return "\n".join(results) if results else "[no matches found]"
        except re.error as e:
            return f"ERROR: Invalid regex: {e}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Search failed: {e}"

    def _collect_matches(self, path: Path, regex: re.Pattern[str]) -> list[str]:
        """The matching lines of every file under a path."""
        results: list[str] = []
        for file_path in path.rglob("*"):
            if file_path.is_file():
                self._search_file(file_path, regex, results)
        return results

    def _search_file(self, file_path: Path, regex: re.Pattern[str], results: list[str]) -> None:
        """Append the matching lines of one file to the results."""
        try:
            lines = file_path.read_text().splitlines()
        except Exception:
            logger.exception("Failed to read search file %s", file_path)
            return
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                results.append(f"{file_path}:{i}: {line.rstrip()}")

    @staticmethod
    def _relative_to(match: Path, directory: Path) -> Path:
        """The path of a match relative to the searched directory."""
        try:
            return match.relative_to(directory)
        except ValueError:
            # The match is not under the directory (shouldn't happen, but handle gracefully)
            return match

    def _execute_glob_search(self, args: dict[str, Any]) -> str:
        pattern = args.get("pattern", "**/*")
        directory = self._resolve(args.get("directory", "."))
        if not directory.exists():
            return f"ERROR: Directory not found: {directory}"
        # Block path traversal patterns that could escape the workspace
        if ".." in pattern:
            return f"ERROR: Pattern contains path traversal ('..'): {pattern}"
        try:
            matches = list(directory.glob(pattern))
            if not matches:
                return f"[no files match pattern '{pattern}']"
            results = [str(self._relative_to(m, directory)) for m in matches]
            return "\n".join(sorted(results))
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Glob search failed: {e}"

    def _execute_get_file_tree(self, args: dict[str, Any]) -> str:
        path = self._resolve(args.get("path", "."))
        max_depth = args.get("max_depth", 3)
        if not path.exists():
            return f"ERROR: Path not found: {path}"

        lines = [f"{path.name}/" if path.is_dir() else path.name]
        if path.is_dir():
            lines.extend(self._walk_tree(path, _TreeContext(max_depth=max_depth)))
        return "\n".join(lines)

    def _tree_entries(self, dir_path: Path) -> list[Path] | None:
        """The sorted entries of a directory, or ``None`` when unreadable."""
        try:
            return sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return None

    def _tree_entry_lines(self, entry: Path, is_last: bool, ctx: _TreeContext) -> list[str]:
        """Render one directory entry and, for a directory, its subtree."""
        connector = "└── " if is_last else "├── "
        lines = [f"{ctx.prefix}{connector}{entry.name}"]
        if not entry.is_dir():
            return lines
        extension = "    " if is_last else "│   "
        child = _TreeContext(
            max_depth=ctx.max_depth, prefix=ctx.prefix + extension, depth=ctx.depth + 1
        )
        lines.extend(self._walk_tree(entry, child))
        return lines

    def _walk_tree(self, dir_path: Path, ctx: _TreeContext) -> list[str]:
        """Render the entries of one directory, recursively."""
        if ctx.depth > ctx.max_depth:
            return []
        entries = self._tree_entries(dir_path)
        if entries is None:
            return [f"{ctx.prefix}[permission denied]"]

        result = []
        for i, entry in enumerate(entries):
            if entry.name.startswith("."):
                continue
            result.extend(self._tree_entry_lines(entry, i == len(entries) - 1, ctx))
        return result

    def _execute_batch_read(self, args: dict[str, Any]) -> str:
        from .advanced import BatchOperation

        paths = args.get("paths", [])
        if not paths:
            return "ERROR: No paths provided"
        if len(paths) > 50:
            return "ERROR: Too many files in batch (max 50)"

        results = BatchOperation.batch_read(paths, str(self.cwd))

        output = [f"Read {len(results)} files:"]
        for path, content in results.items():
            preview = content[:200] + "..." if len(content) > 200 else content
            output.append(f"\n--- {path} ---\n{preview}")

        return "\n".join(output)

    def _execute_batch_write(self, args: dict[str, Any]) -> str:
        from .advanced import BatchOperation

        operations = args.get("operations", [])
        if not operations:
            return "ERROR: No operations provided"

        results = BatchOperation.batch_write(operations, str(self.cwd))

        output = f"SUCCESS: {len(results['success'])} files written"
        if results["failed"]:
            output += f"\nFailed: {len(results['failed'])}"
            for f in results["failed"]:
                output += f"\n  - {f['path']}: {f['error']}"

        return output

    def _execute_replace_in_files(self, args: dict[str, Any]) -> str:
        from .skills import SearchReplace

        pattern = args["pattern"]
        replacement = args["replacement"]
        files = args.get("files", [])
        dry_run = args.get("dry_run", True)
        sr = SearchReplace(str(self.cwd))
        result = sr.replace_in_files(pattern, replacement, files, dry_run)

        if "error" in result:
            return result["error"]

        output = (
            f"Found {result['replacements']} replacements in {len(result['files_modified'])} files"
        )
        if dry_run:
            output += " (DRY RUN - use dry_run: false to apply)"
        output += "\n\nFiles:\n" + "\n".join(result["files_modified"][:10])
        return output

    def _execute_clear_file_cache(self, args: dict[str, Any]) -> str:
        from .advanced import get_file_cache

        cache = get_file_cache()
        cache.clear()
        return "SUCCESS: File cache cleared"
