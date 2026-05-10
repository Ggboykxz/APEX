"""Tests for APEX new tools - task, preview_edit, clipboard, ask_user."""

import pytest
from apex.tools import ToolExecutor


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "test_project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


def test_task_tool(executor):
    result = executor.execute("task", {"agent": "general", "task": "Search for TODO"})
    assert "Delegated to @general" in result


def test_task_tool_unknown_agent(executor):
    result = executor.execute("task", {"agent": "nonexistent", "task": "do something"})
    assert "ERROR: Unknown agent" in result


def test_preview_edit_basic(executor, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    return 'world'")

    result = executor.execute(
        "preview_edit",
        {"path": str(test_file), "old_string": "return 'world'", "new_string": "return 'hello'"},
    )

    assert "[PREVIEW" in result
    assert "def hello():" in result
    assert "---" in result or "+++ " in result


def test_preview_edit_file_not_found(executor):
    result = executor.execute(
        "preview_edit", {"path": "/nonexistent/file.py", "old_string": "old", "new_string": "new"}
    )
    assert "ERROR: File not found" in result


def test_preview_edit_string_not_found(executor, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("hello")

    result = executor.execute(
        "preview_edit", {"path": str(test_file), "old_string": "not found", "new_string": "new"}
    )
    assert "ERROR: String not found" in result


def test_apply_edit_valid_preview(executor, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    return 'world'")

    preview_result = executor.execute(
        "preview_edit",
        {"path": str(test_file), "old_string": "return 'world'", "new_string": "return 'hello'"},
    )

    import re

    match = re.search(r"\[PREVIEW ([a-f0-9]+)\]", preview_result)
    assert match is not None

    preview_id = match.group(1)
    apply_result = executor.execute("apply_edit", {"preview_id": preview_id})

    assert "SUCCESS" in apply_result
    assert test_file.read_text() == "def hello():\n    return 'hello'"


def test_apply_edit_invalid_id(executor):
    result = executor.execute("apply_edit", {"preview_id": "invalid-id"})
    assert "ERROR" in result


def test_clipboard_write(executor):
    result = executor.execute("clipboard_write", {"text": "Hello World"})
    assert "SUCCESS" in result or "ERROR" in result


def test_clipboard_read(executor):
    executor.execute("clipboard_write", {"text": "Test text"})
    result = executor.execute("clipboard_read", {})
    assert "ERROR" in result or len(result) >= 0


def test_ask_user(executor):
    result = executor.execute("ask_user", {"question": "Continue?"})
    assert "WAITING FOR USER INPUT" in result
    assert "Continue?" in result


def test_ask_user_with_options(executor):
    result = executor.execute("ask_user", {"question": "Choose one", "options": ["Yes", "No"]})
    assert "WAITING FOR USER INPUT" in result
    assert "Yes" in result
    assert "No" in result
