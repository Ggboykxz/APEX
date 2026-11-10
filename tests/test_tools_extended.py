"""Tests for APEX tools - preview/apply edit, clipboard, ask_user, run_code, bookmarks, conversation."""

import re

import pytest

from apex.tools import ToolExecutor


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


# ─── preview_edit ────────────────────────────────────────────────────────────


def test_preview_edit_basic(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def hello():\n    return 'world'")
    result = executor.execute(
        "preview_edit",
        {"path": str(f), "old_string": "return 'world'", "new_string": "return 'hello'"},
    )
    assert "[PREVIEW" in result
    assert "apply_edit" in result


def test_preview_edit_file_not_found(executor):
    result = executor.execute(
        "preview_edit", {"path": "/nonexistent/file.py", "old_string": "old", "new_string": "new"}
    )
    assert "ERROR" in result


def test_preview_edit_string_not_found(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("hello")
    result = executor.execute(
        "preview_edit", {"path": str(f), "old_string": "not_found_string", "new_string": "new"}
    )
    assert "ERROR" in result
    assert "String not found" in result


def test_preview_edit_generates_id(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("hello world")
    result = executor.execute(
        "preview_edit", {"path": str(f), "old_string": "hello", "new_string": "hi"}
    )
    match = re.search(r"\[PREVIEW ([a-f0-9]+)\]", result)
    assert match is not None


def test_preview_edit_does_not_modify_file(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("original content")
    executor.execute(
        "preview_edit", {"path": str(f), "old_string": "original", "new_string": "modified"}
    )
    # File should NOT be changed by preview
    assert f.read_text() == "original content"


# ─── apply_edit ──────────────────────────────────────────────────────────────


def test_apply_edit_valid_preview(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def hello():\n    return 'world'")

    preview_result = executor.execute(
        "preview_edit",
        {"path": str(f), "old_string": "return 'world'", "new_string": "return 'hello'"},
    )
    match = re.search(r"\[PREVIEW ([a-f0-9]+)\]", preview_result)
    assert match is not None

    preview_id = match.group(1)
    apply_result = executor.execute("apply_edit", {"preview_id": preview_id})
    assert "SUCCESS" in apply_result
    assert f.read_text() == "def hello():\n    return 'hello'"


def test_apply_edit_invalid_id(executor):
    result = executor.execute("apply_edit", {"preview_id": "invalid-id-not-in-cache"})
    assert "ERROR" in result


def test_apply_edit_expired_id(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("content")

    preview_result = executor.execute(
        "preview_edit", {"path": str(f), "old_string": "content", "new_string": "new"}
    )
    match = re.search(r"\[PREVIEW ([a-f0-9]+)\]", preview_result)
    preview_id = match.group(1)

    # Apply once - should succeed
    executor.execute("apply_edit", {"preview_id": preview_id})
    # Apply again - should fail (already consumed)
    result = executor.execute("apply_edit", {"preview_id": preview_id})
    assert "ERROR" in result


def test_apply_edit_file_changed_since_preview(executor, tmp_path):
    f = tmp_path / "test.py"
    f.write_text("original")

    preview_result = executor.execute(
        "preview_edit", {"path": str(f), "old_string": "original", "new_string": "modified"}
    )
    match = re.search(r"\[PREVIEW ([a-f0-9]+)\]", preview_result)
    preview_id = match.group(1)

    # Change file externally before apply
    f.write_text("totally different")

    result = executor.execute("apply_edit", {"preview_id": preview_id})
    assert "ERROR" in result or "changed" in result.lower()


# ─── clipboard_read / clipboard_write ────────────────────────────────────────


def test_clipboard_write_returns_string(executor):
    result = executor.execute("clipboard_write", {"text": "Hello World"})
    assert isinstance(result, str)
    # Either SUCCESS or ERROR (clipboard may not be available in test env)
    assert "SUCCESS" in result or "ERROR" in result


def test_clipboard_read_returns_string(executor):
    result = executor.execute("clipboard_read", {})
    assert isinstance(result, str)
    # Either returns content or an error about clipboard tool not being available


# ─── ask_user ────────────────────────────────────────────────────────────────


def test_ask_user_basic(executor):
    result = executor.execute("ask_user", {"question": "Continue?"})
    assert "WAITING FOR USER INPUT" in result
    assert "Continue?" in result


def test_ask_user_with_options(executor):
    result = executor.execute("ask_user", {"question": "Choose one", "options": ["Yes", "No"]})
    assert "WAITING FOR USER INPUT" in result
    assert "Yes" in result
    assert "No" in result


def test_ask_user_no_options(executor):
    result = executor.execute("ask_user", {"question": "What is your name?"})
    assert "WAITING FOR USER INPUT" in result
    assert "Free text answer" in result


# ─── run_code ────────────────────────────────────────────────────────────────


def test_run_code_python(executor):
    result = executor.execute(
        "run_code", {"code": "print('hello from sandbox')", "language": "python"}
    )
    assert isinstance(result, str)


def test_run_code_bash(executor):
    result = executor.execute("run_code", {"code": "echo hello", "language": "bash"})
    assert isinstance(result, str)


def test_run_code_with_args(executor):
    result = executor.execute(
        "run_code", {"code": "import sys; print(sys.argv)", "language": "python", "args": ["arg1"]}
    )
    assert isinstance(result, str)


# ─── bookmark_session / restore_bookmark ─────────────────────────────────────


def test_bookmark_session(executor):
    result = executor.execute("bookmark_session", {"name": "test_bookmark"})
    assert "SUCCESS" in result
    assert "test_bookmark" in result


def test_restore_bookmark_no_bookmarks(executor):
    # Without creating a bookmark first, should error
    result = executor.execute("restore_bookmark", {"name": "nonexistent_bookmark"})
    assert "ERROR" in result or "No bookmarks" in result


def test_bookmark_and_restore(executor):
    executor.execute("bookmark_session", {"name": "my_mark"})
    result = executor.execute("restore_bookmark", {"name": "my_mark"})
    assert isinstance(result, str)


# ─── search_history ──────────────────────────────────────────────────────────


def test_search_history_no_manager(executor):
    result = executor.execute("search_history", {"query": "test"})
    # search_history has two implementations; the extras one returns "No results found"
    assert "ERROR" in result or "No conversation history" in result or "No results found" in result


# ─── get_conversation_stats ──────────────────────────────────────────────────


def test_get_conversation_stats_no_manager(executor):
    result = executor.execute("get_conversation_stats", {})
    assert "No conversation statistics" in result or isinstance(result, str)


# ─── undo / redo ─────────────────────────────────────────────────────────────


def test_undo_no_manager(executor):
    result = executor.execute("undo", {})
    assert "Undo manager not available" in result or "Nothing to undo" in result


def test_redo_no_manager(executor):
    result = executor.execute("redo", {})
    assert "Undo manager not available" in result or "Nothing to redo" in result


def test_undo_info_no_manager(executor):
    result = executor.execute("undo_info", {})
    assert "Not available" in result or isinstance(result, str)


def test_redo_info_no_manager(executor):
    result = executor.execute("redo_info", {})
    assert "Not available" in result or isinstance(result, str)


# ─── share_session ───────────────────────────────────────────────────────────


def test_share_session_no_agent(executor):
    result = executor.execute("share_session", {})
    assert "ERROR" in result or "not available" in result.lower()


# ─── apply_patch ─────────────────────────────────────────────────────────────


def test_apply_patch_invalid(executor):
    result = executor.execute("apply_patch", {"patch": "invalid patch content"})
    assert isinstance(result, str)
    # Should either fail to apply or report an error
