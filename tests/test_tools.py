"""Tests for APEX tools."""

import pytest
from pathlib import Path

from apex.tools import ToolExecutor, TOOL_SCHEMAS


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "test_project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


def test_read_file(executor, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World\nLine 2")
    result = executor.execute("read_file", {"path": str(test_file)})
    assert "Hello World" in result
    assert "1  " in result


def test_read_file_not_found(executor):
    result = executor.execute("read_file", {"path": "/nonexistent/file.txt"})
    assert result.startswith("ERROR:")


def test_write_file(executor, tmp_path):
    result = executor.execute("write_file", {
        "path": str(tmp_path / "new_file.txt"),
        "content": "Test content"
    })
    assert result.startswith("SUCCESS:")
    assert (tmp_path / "new_file.txt").read_text() == "Test content"


def test_write_creates_parent_dirs(executor, tmp_path):
    result = executor.execute("write_file", {
        "path": str(tmp_path / "sub" / "nested" / "file.txt"),
        "content": "deep"
    })
    assert result.startswith("SUCCESS:")


def test_edit_file(executor, tmp_path):
    test_file = tmp_path / "edit_test.txt"
    test_file.write_text("Hello World")
    result = executor.execute("edit_file", {
        "path": str(test_file),
        "old_string": "World",
        "new_string": "APEX"
    })
    assert result.startswith("SUCCESS:")
    assert test_file.read_text() == "Hello APEX"


def test_edit_file_not_found(executor):
    result = executor.execute("edit_file", {
        "path": "/nonexistent/file.txt",
        "old_string": "text",
        "new_string": "text"
    })
    assert result.startswith("ERROR:")


def test_edit_file_string_not_found(executor, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello")
    result = executor.execute("edit_file", {
        "path": str(test_file),
        "old_string": "Goodbye",
        "new_string": "Hello"
    })
    assert result.startswith("ERROR:")


def test_run_command(executor):
    result = executor.execute("run_command", {"command": "echo 'test output'"})
    assert "test output" in result


def test_run_command_error(executor):
    result = executor.execute("run_command", {"command": "exit 1"})
    assert "EXIT CODE: 1" in result


def test_list_files(executor, tmp_path):
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").write_text("content")
    result = executor.execute("list_files", {"path": str(tmp_path)})
    assert "file1.txt" in result
    assert "file2.txt" in result


def test_list_files_not_found(executor):
    result = executor.execute("list_files", {"path": "/nonexistent"})
    assert result.startswith("ERROR:")


def test_search_in_files(executor, tmp_path):
    (tmp_path / "test.py").write_text("def hello():\n    print('world')")
    result = executor.execute("search_in_files", {
        "pattern": "hello",
        "path": str(tmp_path)
    })
    assert "test.py" in result


def test_delete_file(executor, tmp_path):
    test_file = tmp_path / "to_delete.txt"
    test_file.write_text("content")
    result = executor.execute("delete_file", {"path": str(test_file)})
    assert result.startswith("SUCCESS:")
    assert not test_file.exists()


def test_delete_directory(executor, tmp_path):
    test_dir = tmp_path / "empty_dir"
    test_dir.mkdir()
    result = executor.execute("delete_file", {"path": str(test_dir)})
    assert result.startswith("SUCCESS:")


def test_delete_nonexistent(executor):
    result = executor.execute("delete_file", {"path": "/nonexistent"})
    assert result.startswith("ERROR:")


def test_create_directory(executor, tmp_path):
    result = executor.execute("create_directory", {
        "path": str(tmp_path / "new" / "nested" / "dir")
    })
    assert result.startswith("SUCCESS:")
    assert (tmp_path / "new" / "nested" / "dir").exists()


def test_unknown_tool(executor):
    result = executor.execute("unknown_tool", {})
    assert "ERROR: Unknown tool" in result


def test_tool_schemas_exist():
    assert len(TOOL_SCHEMAS) >= 18
    names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert "read_file" in names
    assert "write_file" in names
    assert "run_command" in names
    assert "git_diff" in names
    assert "web_search" in names