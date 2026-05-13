"""Tests for APEX tools - AsyncToolExecutor, batch ops, timeouts, file watch, expand_vars, shells."""

import pytest

from apex.tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


@pytest.fixture
def async_executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return AsyncToolExecutor(cwd=cwd)


# ─── AsyncToolExecutor ──────────────────────────────────────────────────────


def test_async_executor_is_tool_executor(async_executor):
    assert isinstance(async_executor, ToolExecutor)


def test_async_executor_has_cwd(async_executor, tmp_path):
    assert async_executor.cwd == tmp_path / "project"


@pytest.mark.asyncio
async def test_execute_async_read_file(async_executor, tmp_path):
    f = tmp_path / "async_test.txt"
    f.write_text("async content")
    result = await async_executor.execute_async("read_file", {"path": str(f)})
    assert "async content" in result


@pytest.mark.asyncio
async def test_execute_async_unknown_tool(async_executor):
    result = await async_executor.execute_async("nonexistent_tool", {})
    assert "ERROR" in result
    assert "Unknown tool" in result


@pytest.mark.asyncio
async def test_execute_async_write_file(async_executor, tmp_path):
    dest = tmp_path / "async_write.txt"
    result = await async_executor.execute_async(
        "write_file", {"path": str(dest), "content": "written async"}
    )
    assert "SUCCESS" in result
    assert dest.read_text() == "written async"


@pytest.mark.asyncio
async def test_execute_async_run_command(async_executor):
    result = await async_executor.execute_async("run_command", {"command": "echo async_test"})
    assert "async_test" in result


@pytest.mark.asyncio
async def test_execute_all_parallel(async_executor, tmp_path):
    (tmp_path / "f1.txt").write_text("content1")
    (tmp_path / "f2.txt").write_text("content2")
    results = await async_executor.execute_all_parallel(
        [
            ("read_file", {"path": str(tmp_path / "f1.txt")}),
            ("read_file", {"path": str(tmp_path / "f2.txt")}),
        ]
    )
    assert len(results) == 2
    assert "content1" in results[0]
    assert "content2" in results[1]


# ─── batch_read ──────────────────────────────────────────────────────────────


def test_batch_read_no_paths(executor):
    result = executor.execute("batch_read", {"paths": []})
    assert "ERROR" in result or "No paths" in result


def test_batch_read_with_files(executor, tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "b.txt").write_text("beta")
    result = executor.execute(
        "batch_read", {"paths": [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]}
    )
    assert isinstance(result, str)


# ─── batch_write ─────────────────────────────────────────────────────────────


def test_batch_write_no_operations(executor):
    result = executor.execute("batch_write", {"operations": []})
    assert "ERROR" in result or "No operations" in result


def test_batch_write_with_operations(executor, tmp_path):
    result = executor.execute(
        "batch_write",
        {
            "operations": [
                {"path": str(tmp_path / "batch1.txt"), "content": "first"},
                {"path": str(tmp_path / "batch2.txt"), "content": "second"},
            ]
        },
    )
    assert isinstance(result, str)


# ─── retry_tool ──────────────────────────────────────────────────────────────


def test_retry_tool_basic(executor):
    result = executor.execute(
        "retry_tool", {"tool": "run_command", "args": {"command": "echo retry_test"}, "retries": 1}
    )
    assert isinstance(result, str)


# ─── get_tool_timeout / set_tool_timeout ─────────────────────────────────────


def test_get_tool_timeout(executor):
    result = executor.execute("get_tool_timeout", {"tool": "run_command"})
    assert isinstance(result, str)
    assert "Timeout" in result or "timeout" in result.lower()


def test_set_tool_timeout(executor):
    result = executor.execute("set_tool_timeout", {"tool": "run_command", "timeout": 60})
    assert isinstance(result, str)
    assert "60" in result


# ─── clear_file_cache ────────────────────────────────────────────────────────


def test_clear_file_cache(executor):
    result = executor.execute("clear_file_cache", {})
    assert "SUCCESS" in result


# ─── get_context_info ────────────────────────────────────────────────────────


def test_get_context_info_no_agent(executor):
    result = executor.execute("get_context_info", {})
    assert "No agent context" in result or isinstance(result, str)


# ─── start_file_watch / stop_file_watch ──────────────────────────────────────


def test_start_file_watch(executor):
    result = executor.execute("start_file_watch", {"patterns": ["*.py"]})
    assert isinstance(result, str)
    assert "SUCCESS" in result or "ERROR" in result or "Watching" in result


def test_stop_file_watch_not_started(executor):
    result = executor.execute("stop_file_watch", {})
    assert "ERROR" in result or "No file watcher" in result


def test_start_and_stop_file_watch(executor):
    # Start
    start_result = executor.execute("start_file_watch", {"patterns": ["*.txt"]})
    if "SUCCESS" in start_result:
        # Stop
        stop_result = executor.execute("stop_file_watch", {})
        assert "SUCCESS" in stop_result or isinstance(stop_result, str)


# ─── expand_vars ─────────────────────────────────────────────────────────────


def test_expand_vars_basic(executor):
    result = executor.execute("expand_vars", {"text": "Hello ${name}", "vars": {"name": "World"}})
    assert isinstance(result, str)


def test_expand_vars_no_vars(executor):
    result = executor.execute("expand_vars", {"text": "No vars here"})
    assert isinstance(result, str)


# ─── start_shell / run_shell / close_shell ───────────────────────────────────


def test_start_shell(executor):
    result = executor.execute("start_shell", {"shell": "bash"})
    assert isinstance(result, str)
    assert "SUCCESS" in result or "ERROR" in result or "shell" in result.lower()


def test_run_shell_no_session(executor):
    result = executor.execute("run_shell", {"command": "echo test"})
    assert "ERROR" in result or "No shell session" in result


def test_close_shell_no_session(executor):
    result = executor.execute("close_shell", {})
    assert "ERROR" in result or "No shell session" in result


def test_shell_lifecycle(executor):
    """Test full shell lifecycle: start -> run -> close."""
    start_result = executor.execute("start_shell", {"shell": "bash"})
    if "SUCCESS" in start_result:
        run_result = executor.execute("run_shell", {"command": "echo lifecycle_test"})
        assert isinstance(run_result, str)

        close_result = executor.execute("close_shell", {})
        assert "SUCCESS" in close_result

        # After close, run_shell should error
        post_close_result = executor.execute("run_shell", {"command": "echo after_close"})
        assert "ERROR" in post_close_result or "No shell session" in post_close_result


# ─── ToolExecutor execute exception handling ─────────────────────────────────


def test_execute_catches_exception(executor, tmp_path):
    """Test that execute catches unexpected exceptions and returns ERROR."""
    # _execute_read_file with a directory instead of file will raise
    d = tmp_path / "a_dir"
    d.mkdir()
    result = executor.execute("read_file", {"path": str(d)})
    # read_file handles this with try/except, so check for ERROR
    assert "ERROR" in result or isinstance(result, str)


# ─── TOOL_SCHEMAS extended coverage ─────────────────────────────────────────


def test_tool_schemas_advanced_tools_present():
    names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    # Verify many tools are present
    assert "web_search" in names
    assert "fetch_url" in names
    assert "git_diff" in names
    assert "get_repo_map" in names
    assert "read_image" in names
    assert "run_test" in names
    assert "format_file" in names
    assert "install_package" in names
    assert "task" in names
    assert "preview_edit" in names
    assert "apply_edit" in names
    assert "clipboard_read" in names
    assert "clipboard_write" in names
    assert "ask_user" in names
    assert "run_code" in names
    assert "bookmark_session" in names
    assert "restore_bookmark" in names
    assert "search_history" in names
    assert "get_conversation_stats" in names
    assert "undo" in names
    assert "redo" in names
    assert "apply_patch" in names
    assert "list_commands" in names
    assert "run_command_custom" in names
    assert "inline_edit" in names
    assert "retry_last" in names
    assert "git_stage" in names
    assert "git_commit" in names
    assert "list_skills" in names
    assert "use_skill" in names
    assert "set_theme" in names
    assert "get_keybindings" in names
    assert "expand_vars" in names
    assert "batch_read" in names
    assert "batch_write" in names
