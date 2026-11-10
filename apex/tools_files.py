"""File I/O tools: read, write, edit, patch and delete files.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from .tools_security import is_blocked_secret

__all__ = [
    "FileToolsMixin",
]


class FileToolsMixin:
    def _execute_read_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        if self._is_blocked_secret(path):
            name = path.name.lower()
            return f"ERROR: Reading {name} is blocked by default (contains secrets)."
        try:
            lines = path.read_text().splitlines()
            max_line_num = len(str(len(lines)))
            result = []
            for i, line in enumerate(lines, 1):
                result.append(f"{i:>{max_line_num}}  {line}")
            return "\n".join(result)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot read file: {e}"

    def _is_blocked_secret(self, path: Path) -> bool:
        """Whether reading this file is blocked because it usually holds secrets."""
        return is_blocked_secret(path)

    def _execute_write_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"])
            return f"SUCCESS: Written {len(args['content'])} bytes to {path}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot write file: {e}"

    def _execute_edit_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        try:
            content = path.read_text()
            old_string = args["old_string"]
            new_string = args["new_string"]
            if old_string not in content:
                return "ERROR: String not found in file. Use read_file to see content."
            new_content = content.replace(old_string, new_string, 1)
            path.write_text(new_content)
            return f"SUCCESS: Edited {path}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot edit file: {e}"

    def _execute_delete_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Path not found: {path}"
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                if any(path.iterdir()):
                    return f"ERROR: Directory not empty: {path}"
                path.rmdir()
            return f"SUCCESS: Deleted {path}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot delete: {e}"

    def _execute_create_directory(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"SUCCESS: Created directory {path}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot create directory: {e}"

    def _execute_diff_files(self, args: dict[str, Any]) -> str:
        path_a = self._resolve(args["path_a"])
        path_b = self._resolve(args["path_b"])
        if not path_a.exists():
            return f"ERROR: File not found: {path_a}"
        if not path_b.exists():
            return f"ERROR: File not found: {path_b}"
        try:
            with open(path_a) as f:
                lines_a = f.read().splitlines()
            with open(path_b) as f:
                lines_b = f.read().splitlines()

            import difflib

            diff = list(
                difflib.unified_diff(
                    lines_a, lines_b, fromfile=str(path_a), tofile=str(path_b), lineterm=""
                )
            )
            return "\n".join(diff) if diff else "[files are identical]"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot diff files: {e}"

    def _execute_preview_edit(self, args: dict[str, Any]) -> str:
        import uuid

        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"

        try:
            content = path.read_text()
            old_string = args["old_string"]
            new_string = args["new_string"]

            if old_string not in content:
                return "ERROR: String not found in file"

            import difflib

            old_lines = content.splitlines(keepends=True)
            new_lines = content.replace(old_string, new_string, 1).splitlines(keepends=True)

            diff = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=str(path),
                    tofile=f"{path} (modified)",
                    lineterm="",
                )
            )
            diff_text = "".join(diff)

            preview_id = str(uuid.uuid4())[:8]
            self._preview_cache = getattr(self, "_preview_cache", {})
            self._preview_cache[preview_id] = {
                "path": str(path),
                "old_string": old_string,
                "new_string": new_string,
            }

            return f"[PREVIEW {preview_id}]\n{diff_text}\n\nUse apply_edit with preview_id={preview_id} to confirm, or the edit will be discarded."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Preview failed: {e}"

    def _execute_apply_edit(self, args: dict[str, Any]) -> str:
        preview_id = args["preview_id"]
        cache = getattr(self, "_preview_cache", {})

        if preview_id not in cache:
            return f"ERROR: Invalid or expired preview ID: {preview_id}"

        preview = cache.pop(preview_id)
        path = Path(preview["path"])

        try:
            content = path.read_text()
            if preview["old_string"] not in content:
                return "ERROR: File content changed since preview"
            new_content = content.replace(preview["old_string"], preview["new_string"], 1)
            path.write_text(new_content)
            return f"SUCCESS: Applied edit to {path}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Apply failed: {e}"

    def _execute_apply_patch(self, args: dict[str, Any]) -> str:
        from .apply_patch import PatchError
        from .apply_patch import apply_patch as apply_patch_text

        patch = args.get("patch", "")
        dry_run = bool(args.get("dry_run", False))
        try:
            result = apply_patch_text(patch, Path(self.cwd), dry_run=dry_run)
        except PatchError as exc:
            detail = f"{exc.reason}: {exc.message}"
            if exc.path and exc.path not in exc.message:
                detail += f" ({exc.path})"
            return f"ERROR: {detail}"
        except Exception as exc:  # pragma: no cover - defensive boundary  # noqa: BLE001
            return f"ERROR: patch_failed: {exc}"

        count = len(result["files"])
        header = "PREVIEW" if dry_run else "SUCCESS"
        action = "Patch would apply" if dry_run else "Patch applied"
        lines = [
            f"{header}: {action} ({count} files, +{result['additions']}/-{result['deletions']})"
        ]
        lines.extend(f"warning: {warning}" for warning in result["warnings"])
        return "\n".join(lines)

    def _execute_read_image(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: Image not found: {path}"
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
        if path.suffix.lower() not in image_extensions:
            return f"ERROR: Not a supported image format: {path.suffix}. Supported: {', '.join(sorted(image_extensions))}"
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/{path.suffix[1:]};base64,{data}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Cannot read image: {e}"

    def _execute_read_image_data(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        if not path.exists():
            return f"ERROR: File not found: {path}"
        try:
            import base64

            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"[IMAGE DATA] {path.name} ({len(data)} bytes base64)"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"

    def _execute_inline_edit(self, args: dict[str, Any]) -> str:
        path = self._resolve(args["path"])
        line = args.get("line", 1)
        content = args.get("content", "")
        replace = args.get("replace", 1)

        if not path.exists():
            return f"ERROR: File not found: {path}"

        try:
            lines = path.read_text().splitlines()
            start = max(0, line - 1)
            end = min(len(lines), start + replace)
            new_lines = lines[:start] + [content] + lines[end:]
            path.write_text("\n".join(new_lines))
            return f"SUCCESS: Edited {path} at line {line}"
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {e}"
