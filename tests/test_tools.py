"""Tests for APEX tools - core file operations and ToolExecutor basics."""

import pytest
from pathlib import Path

from apex.tools import ToolExecutor, TOOL_SCHEMAS


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def executor(tmp_path):
    """Create ToolExecutor with temp working directory."""
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


# ─── TOOL_SCHEMAS ────────────────────────────────────────────────────────────


def test_tool_schemas_is_list():
    assert isinstance(TOOL_SCHEMAS, list)


def test_tool_schemas_not_empty():
    assert len(TOOL_SCHEMAS) > 0


def test_tool_schemas_have_required_fields():
    for schema in TOOL_SCHEMAS:
        assert "type" in schema
        assert "function" in schema
        func = schema["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func


def test_tool_schemas_core_tools_present():
    names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert "read_file" in names
    assert "write_file" in names
    assert "edit_file" in names
    assert "run_command" in names
    assert "list_files" in names
    assert "delete_file" in names
    assert "create_directory" in names
    assert "search_in_files" in names


# ─── ToolExecutor init ──────────────────────────────────────────────────────


def test_init_default_cwd():
    e = ToolExecutor()
    assert e.cwd == Path.cwd()


def test_init_custom_cwd(tmp_path):
    e = ToolExecutor(cwd=tmp_path)
    assert e.cwd == tmp_path


# ─── _resolve ────────────────────────────────────────────────────────────────


def test_resolve_absolute_path(executor, tmp_path):
    result = executor._resolve("/absolute/path")
    assert result == Path("/absolute/path").resolve()


def test_resolve_relative_path(executor, tmp_path):
    result = executor._resolve("relative/path")
    assert result == (tmp_path / "project" / "relative/path").resolve()


# ─── execute (unknown tool) ─────────────────────────────────────────────────


def test_execute_unknown_tool(executor):
    result = executor.execute("nonexistent_tool_xyz", {})
    assert "ERROR" in result
    assert "Unknown tool" in result


def test_execute_unknown_tool_returns_name(executor):
    result = executor.execute("bogus_tool", {})
    assert "bogus_tool" in result


# ─── read_file ───────────────────────────────────────────────────────────────


def test_read_file_success(executor, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello World\nLine 2\nLine 3")
    result = executor.execute("read_file", {"path": str(f)})
    assert "Hello World" in result
    assert "Line 2" in result
    assert "Line 3" in result


def test_read_file_has_line_numbers(executor, tmp_path):
    f = tmp_path / "numbered.txt"
    f.write_text("aaa\nbbb\nccc")
    result = executor.execute("read_file", {"path": str(f)})
    assert "1" in result
    assert "2" in result
    assert "3" in result


def test_read_file_not_found(executor):
    result = executor.execute("read_file", {"path": "/nonexistent/file.txt"})
    assert "ERROR" in result
    assert "not found" in result.lower()


def test_read_file_relative_path(executor, tmp_path):
    (tmp_path / "project" / "rel.txt").write_text("relative content")
    result = executor.execute("read_file", {"path": "rel.txt"})
    assert "relative content" in result


def test_read_file_empty(executor, tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = executor.execute("read_file", {"path": str(f)})
    assert isinstance(result, str)


# ─── write_file ──────────────────────────────────────────────────────────────


def test_write_file_success(executor, tmp_path):
    dest = tmp_path / "new_file.txt"
    result = executor.execute("write_file", {"path": str(dest), "content": "Test content"})
    assert "SUCCESS" in result
    assert dest.read_text() == "Test content"


def test_write_file_creates_parent_dirs(executor, tmp_path):
    dest = tmp_path / "sub" / "nested" / "deep" / "file.txt"
    result = executor.execute("write_file", {"path": str(dest), "content": "deep"})
    assert "SUCCESS" in result
    assert dest.read_text() == "deep"


def test_write_file_overwrites(executor, tmp_path):
    f = tmp_path / "overwrite.txt"
    f.write_text("original")
    result = executor.execute("write_file", {"path": str(f), "content": "new content"})
    assert "SUCCESS" in result
    assert f.read_text() == "new content"


def test_write_file_reports_bytes(executor, tmp_path):
    dest = tmp_path / "bytes_test.txt"
    content = "x" * 50
    result = executor.execute("write_file", {"path": str(dest), "content": content})
    assert "50" in result


# ─── edit_file ───────────────────────────────────────────────────────────────


def test_edit_file_success(executor, tmp_path):
    f = tmp_path / "edit_test.txt"
    f.write_text("Hello World")
    result = executor.execute(
        "edit_file", {"path": str(f), "old_string": "World", "new_string": "APEX"}
    )
    assert "SUCCESS" in result
    assert f.read_text() == "Hello APEX"


def test_edit_file_not_found(executor):
    result = executor.execute(
        "edit_file", {"path": "/nonexistent/file.txt", "old_string": "a", "new_string": "b"}
    )
    assert "ERROR" in result


def test_edit_file_string_not_found(executor, tmp_path):
    f = tmp_path / "no_string.txt"
    f.write_text("Hello")
    result = executor.execute(
        "edit_file", {"path": str(f), "old_string": "Goodbye", "new_string": "Hello"}
    )
    assert "ERROR" in result
    assert "String not found" in result


def test_edit_file_replaces_only_first_occurrence(executor, tmp_path):
    f = tmp_path / "multi.txt"
    f.write_text("aaa bbb aaa")
    result = executor.execute(
        "edit_file", {"path": str(f), "old_string": "aaa", "new_string": "zzz"}
    )
    assert "SUCCESS" in result
    assert f.read_text() == "zzz bbb aaa"


# ─── delete_file ─────────────────────────────────────────────────────────────


def test_delete_file_success(executor, tmp_path):
    f = tmp_path / "to_delete.txt"
    f.write_text("content")
    result = executor.execute("delete_file", {"path": str(f)})
    assert "SUCCESS" in result
    assert not f.exists()


def test_delete_empty_directory(executor, tmp_path):
    d = tmp_path / "empty_dir"
    d.mkdir()
    result = executor.execute("delete_file", {"path": str(d)})
    assert "SUCCESS" in result
    assert not d.exists()


def test_delete_non_empty_directory(executor, tmp_path):
    d = tmp_path / "nonempty_dir"
    d.mkdir()
    (d / "child.txt").write_text("data")
    result = executor.execute("delete_file", {"path": str(d)})
    assert "ERROR" in result
    assert "not empty" in result.lower()


def test_delete_nonexistent(executor):
    result = executor.execute("delete_file", {"path": "/nonexistent_path_xyz"})
    assert "ERROR" in result


# ─── create_directory ────────────────────────────────────────────────────────


def test_create_directory_success(executor, tmp_path):
    result = executor.execute("create_directory", {"path": str(tmp_path / "new_dir")})
    assert "SUCCESS" in result
    assert (tmp_path / "new_dir").is_dir()


def test_create_directory_nested(executor, tmp_path):
    result = executor.execute("create_directory", {"path": str(tmp_path / "a" / "b" / "c")})
    assert "SUCCESS" in result
    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_create_directory_already_exists(executor, tmp_path):
    d = tmp_path / "existing_dir"
    d.mkdir()
    result = executor.execute("create_directory", {"path": str(d)})
    assert "SUCCESS" in result


# ─── list_files ──────────────────────────────────────────────────────────────


def test_list_files_success(executor, tmp_path):
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.py").write_text("code")
    result = executor.execute("list_files", {"path": str(tmp_path)})
    assert "file1.txt" in result
    assert "file2.py" in result


def test_list_files_shows_dir_marker(executor, tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").write_text("data")
    result = executor.execute("list_files", {"path": str(tmp_path)})
    assert "subdir" in result
    assert "file.txt" in result


def test_list_files_empty_directory(executor, tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    result = executor.execute("list_files", {"path": str(d)})
    assert "empty" in result.lower()


def test_list_files_not_found(executor):
    result = executor.execute("list_files", {"path": "/nonexistent_dir_xyz"})
    assert "ERROR" in result


def test_list_files_path_is_file(executor, tmp_path):
    f = tmp_path / "not_a_dir.txt"
    f.write_text("text")
    result = executor.execute("list_files", {"path": str(f)})
    assert "ERROR" in result
    assert "Not a directory" in result


# ─── execute exception handling ──────────────────────────────────────────────


def test_execute_catches_method_exception(executor):
    """Test that execute() catches exceptions from _execute methods."""
    # Calling read_file on a directory triggers an exception caught by execute()
    result = executor.execute("read_file", {"path": str(executor.cwd)})
    assert "ERROR" in result


# ─── write_file error path ───────────────────────────────────────────────────


def test_write_file_readonly_path(executor, tmp_path):
    """Test write_file when target is not writable (e.g., read-only directory)."""
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)
    try:
        result = executor.execute(
            "write_file", {"path": str(readonly_dir / "sub" / "file.txt"), "content": "fail"}
        )
        assert "ERROR" in result
    finally:
        readonly_dir.chmod(0o755)


# ─── read_file unreadable ────────────────────────────────────────────────────


def test_read_file_binary_error(executor, tmp_path):
    """Test read_file on a binary file that may cause decode errors."""
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\xff\xfe\xfd\xfc")
    result = executor.execute("read_file", {"path": str(f)})
    # Either reads it (with replacement chars) or returns error
    assert isinstance(result, str)
