"""Tests for the pure-Python multi-file apply-patch engine."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from apex.apply_patch import (
    MAX_FILE_BYTES,
    MAX_PATCH_BYTES,
    PatchError,
    apply_patch,
    parse_patch,
    preview_patch,
)
from apex.tools import TOOL_SCHEMAS, ToolExecutor


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    path.mkdir()
    return path


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_text(path: Path, data: str) -> None:
    write_bytes(path, data.encode("utf-8"))


def codex_update(path: str, body: str) -> str:
    return f"*** Begin Patch\n*** Update File: {path}\n{body}*** End Patch\n"


def unified(path: str, body: str, old: str = "a", new: str = "b") -> str:
    return f"--- {old}/{path}\n+++ {new}/{path}\n{body}"


# ---------------------------------------------------------------------------
# Codex-style format
# ---------------------------------------------------------------------------


def test_codex_add_file(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: new.py\n+hello\n+world\n*** End Patch\n"
    result = apply_patch(patch, root)

    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["files"] == [{"path": "new.py", "kind": "add", "additions": 2, "deletions": 0}]
    assert result["additions"] == 2
    assert result["deletions"] == 0
    assert (root / "new.py").read_text(encoding="utf-8") == "hello\nworld\n"


def test_codex_add_creates_parent_directories(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: nested/deep/file.txt\n+value\n*** End Patch\n"
    apply_patch(patch, root)

    assert (root / "nested" / "deep" / "file.txt").read_text(encoding="utf-8") == "value\n"


def test_codex_add_empty_file(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: empty.txt\n*** End Patch\n"
    result = apply_patch(patch, root)

    assert (root / "empty.txt").read_bytes() == b""
    assert result["files"][0]["additions"] == 0


def test_codex_update_multiple_hunks(root: Path) -> None:
    write_text(root / "a.txt", "one\ntwo\nthree\nfour\n")
    patch = codex_update(
        "a.txt",
        "@@\n one\n-two\n+TWO\n@@\n three\n-four\n+FOUR\n",
    )
    result = apply_patch(patch, root)

    assert (root / "a.txt").read_text(encoding="utf-8") == "one\nTWO\nthree\nFOUR\n"
    assert result["additions"] == 2
    assert result["deletions"] == 2


def test_codex_delete_file(root: Path) -> None:
    write_text(root / "old.txt", "one\ntwo\n")
    patch = "*** Begin Patch\n*** Delete File: old.txt\n*** End Patch\n"
    result = apply_patch(patch, root)

    assert not (root / "old.txt").exists()
    assert result["files"] == [
        {"path": "old.txt", "kind": "delete", "additions": 0, "deletions": 2}
    ]
    assert result["deletions"] == 2


def test_codex_multi_file_patch(root: Path) -> None:
    write_text(root / "update.txt", "old\n")
    write_text(root / "delete.txt", "gone\n")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: update.txt\n"
        "-old\n"
        "+new\n"
        "*** Add File: added.txt\n"
        "+fresh\n"
        "*** Delete File: delete.txt\n"
        "*** End Patch\n"
    )
    result = apply_patch(patch, root)

    assert (root / "update.txt").read_text(encoding="utf-8") == "new\n"
    assert (root / "added.txt").read_text(encoding="utf-8") == "fresh\n"
    assert not (root / "delete.txt").exists()
    assert len(result["files"]) == 3
    assert result["additions"] == 2
    assert result["deletions"] == 2


# ---------------------------------------------------------------------------
# Unified diff format
# ---------------------------------------------------------------------------


def test_unified_update(root: Path) -> None:
    write_text(root / "app.py", "line1\nold\nline3\n")
    patch = unified(
        "app.py",
        "@@ -1,3 +1,3 @@\n line1\n-old\n+new\n line3\n",
    )
    apply_patch(patch, root)

    assert (root / "app.py").read_text(encoding="utf-8") == "line1\nnew\nline3\n"


def test_unified_add_file(root: Path) -> None:
    patch = "--- /dev/null\n+++ b/generated.txt\n@@ -0,0 +1,2 @@\n+alpha\n+beta\n"
    result = apply_patch(patch, root)

    assert (root / "generated.txt").read_text(encoding="utf-8") == "alpha\nbeta\n"
    assert result["files"][0]["kind"] == "add"


def test_unified_delete_file(root: Path) -> None:
    write_text(root / "gone.txt", "x\ny\n")
    patch = "--- a/gone.txt\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-x\n-y\n"
    result = apply_patch(patch, root)

    assert not (root / "gone.txt").exists()
    assert result["files"][0]["kind"] == "delete"
    assert result["deletions"] == 2


def test_unified_multiple_files(root: Path) -> None:
    write_text(root / "a.txt", "a\n")
    write_text(root / "b.txt", "b\n")
    patch = (
        "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+A\n"
        "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-b\n+B\n"
    )
    result = apply_patch(patch, root)

    assert (root / "a.txt").read_text(encoding="utf-8") == "A\n"
    assert (root / "b.txt").read_text(encoding="utf-8") == "B\n"
    assert result["additions"] == 2
    assert result["deletions"] == 2


def test_unified_multiple_hunks(root: Path) -> None:
    write_text(root / "a.txt", "1\n2\n3\n4\n5\n6\n")
    patch = unified(
        "a.txt",
        "@@ -1,2 +1,2 @@\n 1\n-2\n+two\n@@ -5,2 +5,2 @@\n 5\n-6\n+six\n",
    )
    apply_patch(patch, root)

    assert (root / "a.txt").read_text(encoding="utf-8") == "1\ntwo\n3\n4\n5\nsix\n"


def test_unified_fuzzy_line_numbers(root: Path) -> None:
    write_text(root / "a.txt", "one\ntwo\nthree\n")
    patch = unified("a.txt", "@@ -20,1 +20,1 @@\n-two\n+TWO\n")
    result = apply_patch(patch, root)

    assert (root / "a.txt").read_text(encoding="utf-8") == "one\nTWO\nthree\n"
    assert any("offset" in warning for warning in result["warnings"])


def test_unified_add_without_final_newline(root: Path) -> None:
    patch = "--- /dev/null\n+++ b/f.txt\n@@ -0,0 +1 @@\n+tail\n\\ No newline at end of file\n"
    apply_patch(patch, root)

    assert (root / "f.txt").read_bytes() == b"tail"


# ---------------------------------------------------------------------------
# Line endings and trailing newlines
# ---------------------------------------------------------------------------


def test_crlf_is_preserved_on_update(root: Path) -> None:
    write_bytes(root / "a.txt", b"one\r\ntwo\r\n")
    patch = unified("a.txt", "@@ -1,2 +1,2 @@\n one\n-two\n+TWO\n")
    apply_patch(patch, root)

    assert (root / "a.txt").read_bytes() == b"one\r\nTWO\r\n"


def test_crlf_is_used_for_added_files_when_patch_uses_crlf(root: Path) -> None:
    patch = "*** Begin Patch\r\n*** Add File: a.txt\r\n+one\r\n+two\r\n*** End Patch\r\n"
    apply_patch(patch, root)

    assert (root / "a.txt").read_bytes() == b"one\r\ntwo\r\n"


def test_missing_final_newline_is_preserved_on_unified_update(root: Path) -> None:
    write_bytes(root / "a.txt", b"one\ntwo")
    patch = unified(
        "a.txt",
        "@@ -1,2 +1,2 @@\n one\n-two\n+TWO\n\\ No newline at end of file\n",
    )
    apply_patch(patch, root)

    assert (root / "a.txt").read_bytes() == b"one\nTWO"


def test_missing_final_newline_is_preserved_when_untouched(root: Path) -> None:
    write_bytes(root / "a.txt", b"one\ntwo")
    patch = unified("a.txt", "@@ -1 +1 @@\n-one\n+ONE\n")
    apply_patch(patch, root)

    assert (root / "a.txt").read_bytes() == b"ONE\ntwo"


def test_codex_no_newline_marker_on_add(root: Path) -> None:
    patch = (
        "*** Begin Patch\n*** Add File: a.txt\n+only\n\\ No newline at end of file\n*** End Patch\n"
    )
    apply_patch(patch, root)

    assert (root / "a.txt").read_bytes() == b"only"


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


def test_context_mismatch_rejected(root: Path) -> None:
    write_text(root / "a.txt", "actual\n")
    patch = unified("a.txt", "@@ -1 +1 @@\n-expected\n+new\n")

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "context_mismatch"
    assert excinfo.value.path == "a.txt"
    assert (root / "a.txt").read_text(encoding="utf-8") == "actual\n"


def test_overlapping_hunks_rejected(root: Path) -> None:
    write_text(root / "a.txt", "one\ntwo\n")
    patch = unified(
        "a.txt",
        "@@ -1 +1 @@\n-one\n+ONE\n@@ -1 +1 @@\n-one\n+OTHER\n",
    )

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "overlapping_hunks"
    assert (root / "a.txt").read_text(encoding="utf-8") == "one\ntwo\n"


def test_add_existing_file_rejected(root: Path) -> None:
    write_text(root / "a.txt", "keep\n")
    patch = "*** Begin Patch\n*** Add File: a.txt\n+replace\n*** End Patch\n"

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "file_exists"
    assert (root / "a.txt").read_text(encoding="utf-8") == "keep\n"


def test_delete_missing_file_rejected(root: Path) -> None:
    patch = "*** Begin Patch\n*** Delete File: missing.txt\n*** End Patch\n"

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "not_found"


def test_second_add_fails_cleanly(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n*** End Patch\n"
    apply_patch(patch, root)

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "file_exists"
    assert (root / "a.txt").read_text(encoding="utf-8") == "one\n"


def test_unknown_patch_format_rejected(root: Path) -> None:
    with pytest.raises(PatchError) as excinfo:
        apply_patch("this is not a patch", root)

    assert excinfo.value.reason == "unknown_format"


def test_mixed_formats_rejected(root: Path) -> None:
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+b\n*** Add File: c.txt\n+c\n"
    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "mixed_format"


def test_unterminated_codex_patch_rejected(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n"

    with pytest.raises(PatchError) as excinfo:
        parse_patch(patch, root)

    assert excinfo.value.reason == "unterminated_patch"


def test_unified_rename_rejected(root: Path) -> None:
    write_text(root / "a.txt", "one\n")
    patch = "--- a/a.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-one\n+ONE\n"

    with pytest.raises(PatchError) as excinfo:
        parse_patch(patch, root)

    assert excinfo.value.reason == "rename_unsupported"


# ---------------------------------------------------------------------------
# Path and content safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("/tmp/evil.txt", "absolute_path"),
        ("C:\\temp\\evil.txt", "absolute_path"),
        ("../evil.txt", "path_traversal"),
        ("nested/../../evil.txt", "path_traversal"),
    ],
)
def test_unsafe_paths_rejected(root: Path, path: str, reason: str) -> None:
    patch = f"*** Begin Patch\n*** Add File: {path}\n+x\n*** End Patch\n"

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == reason


def test_symlinked_parent_escape_rejected(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    patch = "*** Begin Patch\n*** Add File: link/evil.txt\n+x\n*** End Patch\n"
    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "outside_root"
    assert not (outside / "evil.txt").exists()


def test_nul_bytes_in_patch_rejected(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\x00two\n*** End Patch\n"

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "binary_patch"


def test_binary_source_file_rejected(root: Path) -> None:
    write_bytes(root / "a.bin", b"one\x00two\n")
    patch = unified("a.bin", "@@ -1 +1 @@\n-one\n+two\n")

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "binary_file"
    assert (root / "a.bin").read_bytes() == b"one\x00two\n"


def test_non_utf8_source_file_rejected(root: Path) -> None:
    write_bytes(root / "a.txt", b"\xff\xfe\x00")
    patch = unified("a.txt", "@@ -1 +1 @@\n-one\n+two\n")

    with pytest.raises(PatchError) as excinfo:
        parse_patch(patch, root)

    assert excinfo.value.reason == "binary_file"


def test_oversize_patch_rejected(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+" + ("x" * (MAX_PATCH_BYTES + 1))

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "patch_too_large"


def test_oversize_source_file_rejected(root: Path) -> None:
    write_bytes(root / "big.txt", b"x" * (MAX_FILE_BYTES + 1))
    patch = unified("big.txt", "@@ -1 +1 @@\n-x\n+y\n")

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "file_too_large"


def test_oversize_result_rejected(root: Path) -> None:
    write_text(root / "a.txt", "replace\n")
    additions = "\n".join("+" + ("y" * 80) for _ in range(MAX_FILE_BYTES // 80))
    patch = codex_update("a.txt", "-replace\n" + additions + "\n")

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "file_too_large"
    assert (root / "a.txt").read_text(encoding="utf-8") == "replace\n"


# ---------------------------------------------------------------------------
# Atomicity and dry runs
# ---------------------------------------------------------------------------


def test_invalid_second_file_writes_nothing(root: Path) -> None:
    write_text(root / "a.txt", "original\n")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: a.txt\n"
        "-original\n"
        "+changed\n"
        "*** Update File: missing.txt\n"
        "-anything\n"
        "+else\n"
        "*** End Patch\n"
    )

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "not_found"
    assert (root / "a.txt").read_text(encoding="utf-8") == "original\n"
    assert not (root / "missing.txt").exists()


def test_invalid_second_add_writes_nothing(root: Path) -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Add File: good.txt\n"
        "+good\n"
        "*** Add File: ../evil.txt\n"
        "+bad\n"
        "*** End Patch\n"
    )

    with pytest.raises(PatchError) as excinfo:
        apply_patch(patch, root)

    assert excinfo.value.reason == "path_traversal"
    assert not (root / "good.txt").exists()


def test_dry_run_writes_nothing(root: Path) -> None:
    write_text(root / "a.txt", "old\n")
    patch = (
        "*** Begin Patch\n"
        "*** Update File: a.txt\n"
        "-old\n"
        "+new\n"
        "*** Add File: added.txt\n"
        "+fresh\n"
        "*** End Patch\n"
    )
    result = apply_patch(patch, root, dry_run=True)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert len(result["files"]) == 2
    assert (root / "a.txt").read_text(encoding="utf-8") == "old\n"
    assert not (root / "added.txt").exists()


def test_failed_apply_leaves_no_temp_files(root: Path) -> None:
    write_text(root / "a.txt", "old\n")
    with pytest.raises(PatchError):
        apply_patch(codex_update("a.txt", "-wrong\n+new\n"), root)

    assert list(root.rglob(".apex-patch-*")) == []


def test_successful_apply_leaves_no_temp_files(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n*** End Patch\n"
    apply_patch(patch, root)

    assert list(root.rglob(".apex-patch-*")) == []


# ---------------------------------------------------------------------------
# Preview API and mode preservation
# ---------------------------------------------------------------------------


def test_preview_patch_contract(root: Path) -> None:
    write_text(root / "a.txt", "old\n")
    patch = codex_update("a.txt", "-old\n+new\n")

    preview = preview_patch(patch, root)

    assert len(preview.files) == 1
    item = preview.files[0]
    assert item.path == "a.txt"
    assert item.kind == "update"
    assert item.old_text == "old\n"
    assert item.new_text == "new\n"
    assert preview.additions == 1
    assert preview.deletions == 1
    assert preview.warnings == []
    assert preview.to_dict() == {
        "files": [{"path": "a.txt", "kind": "update", "additions": 1, "deletions": 1}],
        "additions": 1,
        "deletions": 1,
        "warnings": [],
    }


def test_parse_patch_does_not_write(root: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n*** End Patch\n"
    files = parse_patch(patch, root)

    assert files[0].new_text == "one\n"
    assert not (root / "a.txt").exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows only models the read-only mode bit")
def test_update_preserves_mode(root: Path) -> None:
    path = root / "a.sh"
    write_text(path, "old\n")
    os.chmod(path, 0o600)

    apply_patch(codex_update("a.sh", "-old\n+new\n"), root)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


# ---------------------------------------------------------------------------
# Tool wrapper
# ---------------------------------------------------------------------------


def test_apply_patch_schema_exposes_dry_run() -> None:
    schema = next(item for item in TOOL_SCHEMAS if item["function"]["name"] == "apply_patch")
    properties = schema["function"]["parameters"]["properties"]

    assert "dry_run" in properties
    assert properties["dry_run"]["type"] == "boolean"


def test_tool_wrapper_success(root: Path) -> None:
    executor = ToolExecutor(cwd=root)
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n+two\n*** End Patch\n"

    result = executor.execute("apply_patch", {"patch": patch})

    assert result == "SUCCESS: Patch applied (1 files, +2/-0)"
    assert (root / "a.txt").read_text(encoding="utf-8") == "one\ntwo\n"


def test_tool_wrapper_dry_run(root: Path) -> None:
    executor = ToolExecutor(cwd=root)
    patch = "*** Begin Patch\n*** Add File: a.txt\n+one\n*** End Patch\n"

    result = executor.execute("apply_patch", {"patch": patch, "dry_run": True})

    assert result.startswith("PREVIEW: Patch would apply (1 files, +1/-0)")
    assert not (root / "a.txt").exists()


def test_tool_wrapper_error(root: Path) -> None:
    executor = ToolExecutor(cwd=root)

    result = executor.execute("apply_patch", {"patch": "garbage"})

    assert result.startswith("ERROR: unknown_format:")
    assert "\n" not in result
