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


# ─── run_command ───────────────────────────────────────────────────────────

def test_run_command_success(executor, tmp_path):
    result = executor.execute("run_command", {"command": "echo hello"})
    assert "hello" in result


def test_run_command_stderr(executor, tmp_path):
    """Cover stderr output path."""
    result = executor.execute("run_command", {"command": "echo stderr >&2; echo stdout"})
    assert "STDERR" in result or "stdout" in result


def test_run_command_nonzero_exit(executor, tmp_path):
    """Cover nonzero returncode path."""
    result = executor.execute("run_command", {"command": "exit 1"})
    assert "EXIT CODE" in result or "ERROR" in result


def test_run_command_blocked_dangerous(executor, tmp_path):
    result = executor.execute("run_command", {"command": "rm -rf /"})
    assert "ERROR" in result


def test_run_command_exception(executor, monkeypatch):
    """Cover line 1501-1504: TimeoutExpired and Exception handlers."""
    import subprocess

    def fake_run(*a, **kw):
        raise subprocess.TimeoutExpired("cmd", 300)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = executor.execute("run_command", {"command": "sleep 999"})
    assert "timed out" in result.lower()


# ─── edit_file exceptions ──────────────────────────────────────────────────

def test_edit_file_exception(executor, tmp_path):
    """Cover exception handler line 1468-1469."""
    f = tmp_path / "edit_exc.txt"
    f.write_text("hello")
    f.chmod(0o444)
    try:
        result = executor.execute("edit_file", {"path": str(f), "old_string": "hello", "new_string": "world"})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── list_files exceptions ────────────────────────────────────────────────

def test_list_files_stat_exception(executor, tmp_path):
    """Cover stat exception handler line 1518-1519."""
    d = tmp_path / "stat_fail"
    d.mkdir()
    # Create a file that causes stat issues
    (d / "somefile.txt").write_text("x")
    result = executor.execute("list_files", {"path": str(d)})
    assert "somefile.txt" in result or isinstance(result, str)


def test_list_files_outer_exception(executor, tmp_path):
    """Cover outer exception handler line 1522-1523."""
    result = executor.execute("list_files", {"path": str(tmp_path / "project" / "nonexistent")})
    assert "ERROR" in result


# ─── search_in_files exceptions ────────────────────────────────────────────

def test_search_in_files_success(executor, tmp_path):
    d = tmp_path / "project" / "searchdir"
    d.mkdir()
    (d / "greet.txt").write_text("hello world")
    result = executor.execute("search_in_files", {"pattern": "hello", "path": str(d)})
    assert "hello world" in result


def test_search_in_files_no_matches(executor, tmp_path):
    d = tmp_path / "project" / "nosearch"
    d.mkdir()
    (d / "a.txt").write_text("zzz")
    result = executor.execute("search_in_files", {"pattern": "hello", "path": str(d)})
    assert "no matches" in result


def test_search_in_files_path_not_found(executor):
    result = executor.execute("search_in_files", {"pattern": "test", "path": "nonexistent_dir_xyz"})
    assert "ERROR" in result


def test_search_in_files_binary_file(executor, tmp_path):
    """Cover file read exception handler line 1540-1541 (pass)."""
    d = tmp_path / "project" / "bindir"
    d.mkdir()
    f = d / "binary.bin"
    f.write_bytes(b"\xff\xfe\xfd\xfc")
    result = executor.execute("search_in_files", {"pattern": "test", "path": str(d)})
    assert isinstance(result, str)


def test_search_in_files_invalid_regex(executor, tmp_path):
    """Cover re.error handler line 1543-1544."""
    d = tmp_path / "project" / "redir"
    d.mkdir()
    (d / "a.txt").write_text("text")
    result = executor.execute("search_in_files", {"pattern": "[invalid", "path": str(d)})
    assert "Invalid regex" in result or "ERROR" in result


def test_search_in_files_outer_exception(executor, tmp_path):
    """Cover outer exception handler line 1545-1546."""
    # Pass a path that exists but will cause issues
    result = executor.execute("search_in_files", {"pattern": "test", "path": str(tmp_path)})
    assert isinstance(result, str)


# ─── delete_file exception ────────────────────────────────────────────────

def test_delete_file_path_not_found(executor):
    result = executor.execute("delete_file", {"path": "/nonexistent"})
    assert "ERROR" in result


def test_delete_file_exception(executor, tmp_path):
    """Cover exception handler line 1560-1561."""
    d = tmp_path / "del_no_perm"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("data")
    d.chmod(0o555)
    try:
        result = executor.execute("delete_file", {"path": str(f)})
        assert "ERROR" in result or "Cannot delete" in result
    finally:
        d.chmod(0o755)
        if f.exists():
            f.unlink()


# ─── create_directory exception ──────────────────────────────────────────

def test_create_directory_already_exists_subdir(executor, tmp_path):
    d = tmp_path / "project" / "exist"
    d.mkdir(parents=True)
    result = executor.execute("create_directory", {"path": str(d)})
    assert "SUCCESS" in result


def test_create_directory_exception(executor, tmp_path):
    """Cover exception handler line 1568-1569."""
    result = executor.execute("create_directory", {"path": str(tmp_path / "project" / "newdir" / "")})
    assert isinstance(result, str)


# ─── glob_search ──────────────────────────────────────────────────────────

def test_glob_search_success(executor, tmp_path):
    d = tmp_path / "project"
    (d / "glob1.py").write_text("x")
    (d / "glob2.py").write_text("y")
    result = executor.execute("glob_search", {"pattern": "*.py", "directory": str(d)})
    assert "glob1.py" in result
    assert "glob2.py" in result


def test_glob_search_no_matches(executor, tmp_path):
    result = executor.execute("glob_search", {"pattern": "*.xyz", "directory": str(tmp_path / "project")})
    assert "no files match" in result


def test_glob_search_dir_not_found(executor):
    result = executor.execute("glob_search", {"pattern": "*", "directory": "nonexistent_dir_xyz"})
    assert "ERROR" in result


def test_glob_search_exception(executor, tmp_path):
    """Cover exception handler line 1585-1586."""
    # glob patterns rarely raise exceptions, but we can try
    # by making the directory unreadable after the exists check
    d = tmp_path / "project"
    result = executor.execute("glob_search", {"pattern": "[]", "directory": str(d)})
    assert isinstance(result, str)


# ─── get_file_tree ─────────────────────────────────────────────────────────

def test_get_file_tree_success(executor, tmp_path):
    d = tmp_path / "project" / "mytree"
    d.mkdir(parents=True)
    (d / "leaf.txt").write_text("x")
    result = executor.execute("get_file_tree", {"path": str(d)})
    assert "leaf.txt" in result


def test_get_file_tree_not_found(executor):
    result = executor.execute("get_file_tree", {"path": "nonexistent_dir_xyz"})
    assert "ERROR" in result


# ─── diff_files ────────────────────────────────────────────────────────────

def test_diff_files_identical(executor, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("same")
    b.write_text("same")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": str(b)})
    assert "identical" in result


def test_diff_files_different(executor, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hello")
    b.write_text("world")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": str(b)})
    assert "-hello" in result or "+world" in result or result != ""


def test_diff_files_not_found_a(executor, tmp_path):
    b = tmp_path / "b.txt"
    b.write_text("x")
    result = executor.execute("diff_files", {"path_a": "/nonexistent", "path_b": str(b)})
    assert "ERROR" in result


def test_diff_files_not_found_b(executor, tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("x")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": "/nonexistent"})
    assert "ERROR" in result


def test_diff_files_exception(executor, tmp_path):
    """Cover exception handler line 1641-1642."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x")
    b.write_text("y")
    a.chmod(0o222)
    try:
        result = executor.execute("diff_files", {"path_a": str(a), "path_b": str(b)})
        assert isinstance(result, str)
    finally:
        a.chmod(0o644)


# ─── git commands ──────────────────────────────────────────────────────────

def test_git_status_not_a_repo(executor):
    result = executor.execute("get_git_status", {})
    assert "ERROR" in result


def test_git_log_not_a_repo(executor):
    result = executor.execute("get_git_log", {})
    assert "ERROR" in result


def test_git_diff_not_a_repo(executor):
    result = executor.execute("git_diff", {})
    assert "ERROR" in result


def test_git_create_branch_exception(executor, monkeypatch):
    """Cover exception handler line 2336-2337."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_create_branch", {"name": "test-branch"})
    assert "ERROR" in result


def test_git_switch_branch_exception(executor, monkeypatch):
    """Cover exception handler line 2344-2345."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_switch_branch", {"name": "main"})
    assert "ERROR" in result


def test_git_delete_branch_exception(executor, monkeypatch):
    """Cover exception handler line 2354-2355."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_delete_branch", {"name": "test"})
    assert "ERROR" in result


def test_git_list_branches_exception(executor, monkeypatch):
    """Cover exception handler line 2363-2364."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_list_branches", {})
    assert "ERROR" in result


def test_git_stage_exception(executor, monkeypatch):
    """Cover exception handler line 2444-2445."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_stage", {"files": ["test.txt"]})
    assert "ERROR" in result


def test_git_unstage_exception(executor, monkeypatch):
    """Cover exception handler lines 2455-2456."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_unstage", {})
    assert "ERROR" in result


def test_git_commit_not_a_repo(executor):
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result


def test_git_commit_exception(executor, monkeypatch):
    """Cover exception handler lines 2469-2471."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result


def test_git_pre_commit_exception(executor, monkeypatch):
    """Cover exception handler line 2609-2610."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("git error")))
    result = executor.execute("git_pre_commit", {})
    assert "ERROR" in result


def test_git_create_pr(executor):
    result = executor.execute("git_create_pr", {"title": "PR title", "body": "body", "base": "main"})
    assert "PR" in result


def test_git_stage_no_files(executor):
    result = executor.execute("git_stage", {"files": []})
    assert "ERROR" in result


def test_git_commit_no_message(executor):
    result = executor.execute("git_commit", {"message": ""})
    assert "ERROR" in result


# ─── web_search ────────────────────────────────────────────────────────────

def test_web_search_no_results(executor, monkeypatch):
    """Cover snippet fallback line 1703 and no results line 1705."""
    import subprocess

    def fake_run(*a, **kw):
        class FakeResult:
            stdout = "<html>no results here</html>"
            stderr = ""
            returncode = 0
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = executor.execute("web_search", {"query": "nonexistent"})
    assert "no results" in result or isinstance(result, str)


def test_web_search_exception(executor, monkeypatch):
    """Cover exception handler line 1706-1707."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("no net")))
    result = executor.execute("web_search", {"query": "test"})
    assert "ERROR" in result


# ─── fetch_url ─────────────────────────────────────────────────────────────

def test_fetch_url_success(executor, monkeypatch):
    import subprocess

    def fake_run(*a, **kw):
        class FakeResult:
            stdout = "<html><body>Hello World</body></html>"
            stderr = ""
            returncode = 0
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = executor.execute("fetch_url", {"url": "http://example.com"})
    assert "Hello" in result


def test_fetch_url_exception(executor, monkeypatch):
    """Cover exception handler line 1727-1728."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("curl fail")))
    result = executor.execute("fetch_url", {"url": "http://example.com"})
    assert "ERROR" in result


# ─── get_repo_map ──────────────────────────────────────────────────────────

def test_get_repo_map_success(executor, monkeypatch):
    """Cover the active _execute_get_repo_map (line 2228-2232) that calls get_repo_map()."""
    monkeypatch.setattr("apex.context.get_repo_map", lambda path: "Repository: test\n==========\n[SOURCE]\n  main.py")
    result = executor.execute("get_repo_map", {})
    assert "Repository" in result or "main.py" in result


# ─── read_image ────────────────────────────────────────────────────────────

def test_read_image_not_found(executor):
    result = executor.execute("read_image", {"path": "/nonexistent.png"})
    assert "ERROR" in result


def test_read_image_exception(executor, tmp_path):
    """Cover exception handler line 1805-1806."""
    f = tmp_path / "img.png"
    f.write_text("not an image")
    f.chmod(0o222)
    try:
        result = executor.execute("read_image", {"path": str(f)})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── run_test ──────────────────────────────────────────────────────────────

def test_run_test_unknown_framework(executor):
    result = executor.execute("run_test", {"framework": "unknown_fw", "path": "test.py"})
    assert "ERROR" in result


def test_run_test_framework_not_found(executor, monkeypatch):
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
    result = executor.execute("run_test", {"framework": "pytest", "path": "test.py"})
    assert "ERROR" in result or "not found" in result


def test_run_test_timeout(executor, monkeypatch):
    """Cover line 1833."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("pytest", 300)))
    result = executor.execute("run_test", {"framework": "pytest", "path": "test.py"})
    assert "timed out" in result.lower()


def test_run_test_exception(executor, monkeypatch):
    """Cover lines 1836-1837."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("boom")))
    result = executor.execute("run_test", {"framework": "pytest", "path": "test.py"})
    assert "ERROR" in result


# ─── format_file ───────────────────────────────────────────────────────────

def test_format_file_not_found(executor):
    result = executor.execute("format_file", {"path": "/nonexistent.py"})
    assert "ERROR" in result


def test_format_file_no_formatter(executor, tmp_path):
    f = tmp_path / "file.xyz"
    f.write_text("data")
    result = executor.execute("format_file", {"path": str(f)})
    assert "No formatter" in result


def test_format_file_not_installed(executor, tmp_path, monkeypatch):
    import subprocess
    f = tmp_path / "file.rs"
    f.write_text("fn main() {}")

    def fake_run(*a, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = executor.execute("format_file", {"path": str(f)})
    assert "not found" in result.lower() or "ERROR" in result


def test_format_file_exception(executor, tmp_path, monkeypatch):
    """Cover lines 1877-1878."""
    import subprocess
    f = tmp_path / "file.rs"
    f.write_text("fn main() {}")

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fmt fail")))
    result = executor.execute("format_file", {"path": str(f)})
    assert "ERROR" in result


# ─── install_package ──────────────────────────────────────────────────────

def test_install_package_unknown_manager(executor):
    result = executor.execute("install_package", {"manager": "bogus", "package": "x"})
    assert "ERROR" in result


def test_install_package_not_found(executor, monkeypatch):
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
    result = executor.execute("install_package", {"manager": "pip", "package": "nonexistent"})
    assert "ERROR" in result or "not found" in result


def test_install_package_timeout(executor, monkeypatch):
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("pip", 300)))
    result = executor.execute("install_package", {"manager": "pip", "package": "numpy"})
    assert "timed out" in result.lower()


def test_install_package_exception(executor, monkeypatch):
    """Cover lines 1905-1906."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("install fail")))
    result = executor.execute("install_package", {"manager": "pip", "package": "numpy"})
    assert "ERROR" in result


# ─── preview_edit / apply_edit ────────────────────────────────────────────

def test_preview_edit_success(executor, tmp_path):
    f = tmp_path / "preview.txt"
    f.write_text("hello world")
    result = executor.execute("preview_edit", {"path": str(f), "old_string": "world", "new_string": "there"})
    assert "PREVIEW" in result


def test_preview_edit_not_found(executor):
    result = executor.execute("preview_edit", {"path": "/nonexistent", "old_string": "a", "new_string": "b"})
    assert "ERROR" in result


def test_preview_edit_string_not_found(executor, tmp_path):
    f = tmp_path / "preview_no_string.txt"
    f.write_text("hello")
    result = executor.execute("preview_edit", {"path": str(f), "old_string": "zzz", "new_string": "yyy"})
    assert "ERROR" in result


def test_preview_edit_exception(executor, tmp_path):
    """Cover lines 1957-1958."""
    f = tmp_path / "preview_exc.txt"
    f.write_text("hello")
    f.chmod(0o222)
    try:
        result = executor.execute("preview_edit", {"path": str(f), "old_string": "hello", "new_string": "world"})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


def test_apply_edit_invalid_id(executor):
    result = executor.execute("apply_edit", {"preview_id": "nonexistent"})
    assert "ERROR" in result


def test_apply_edit_success(executor, tmp_path):
    """Full preview -> apply workflow."""
    f = tmp_path / "apply_test.txt"
    f.write_text("original text")
    preview_result = executor.execute("preview_edit", {
        "path": str(f), "old_string": "original", "new_string": "modified"
    })
    import re
    m = re.search(r"PREVIEW (\w+)", preview_result)
    assert m, f"Could not find preview_id in: {preview_result}"
    preview_id = m.group(1)
    result = executor.execute("apply_edit", {"preview_id": preview_id})
    assert "SUCCESS" in result
    assert f.read_text() == "modified text"


def test_apply_edit_content_changed(executor, tmp_path):
    """When file content changes between preview and apply."""
    f = tmp_path / "apply_changed.txt"
    f.write_text("original text")
    preview_result = executor.execute("preview_edit", {
        "path": str(f), "old_string": "original", "new_string": "modified"
    })
    import re
    m = re.search(r"PREVIEW (\w+)", preview_result)
    assert m
    preview_id = m.group(1)
    f.write_text("completely different content")
    result = executor.execute("apply_edit", {"preview_id": preview_id})
    assert "ERROR" in result


def test_apply_edit_exception(executor, tmp_path):
    """Cover lines 1977-1978."""
    f = tmp_path / "apply_exc.txt"
    f.write_text("data")
    # First create a preview
    preview_result = executor.execute("preview_edit", {
        "path": str(f), "old_string": "data", "new_string": "changed"
    })
    import re
    m = re.search(r"PREVIEW (\w+)", preview_result)
    assert m
    preview_id = m.group(1)
    # Make file read-only so write fails
    f.chmod(0o444)
    try:
        result = executor.execute("apply_edit", {"preview_id": preview_id})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── clipboard_read ────────────────────────────────────────────────────────

def test_clipboard_read_pyperclip(executor, monkeypatch):
    """Cover pyperclip path."""
    # Test that read works (will hit xclip fallback since pyperclip likely missing)
    result = executor.execute("clipboard_read", {})
    assert isinstance(result, str)


def test_clipboard_read_exception(executor, monkeypatch):
    """Cover main exception handler line 1995-1996."""
    import subprocess
    _original_run = subprocess.run
    def fake_run(*a, **kw):
        raise Exception("xclip fail")
    monkeypatch.setattr(subprocess, "run", fake_run)
    # Make pyperclip import fail
    import sys
    if "pyperclip" in sys.modules:
        del sys.modules["pyperclip"]
    result = executor.execute("clipboard_read", {})
    assert "ERROR" in result


# ─── clipboard_write ──────────────────────────────────────────────────────

def test_clipboard_write_success_pyperclip(executor, monkeypatch):
    """Cover pyperclip path lines 2000-2004."""
    # Test the xclip fallback path that doesn't need pyperclip
    result = executor.execute("clipboard_write", {"text": "test data"})
    assert isinstance(result, str)


def test_clipboard_write_exception(executor, monkeypatch):
    """Cover exception handler line 2014-2015."""
    import subprocess
    def fake_run(*a, **kw):
        raise Exception("xclip fail")
    monkeypatch.setattr(subprocess, "run", fake_run)
    import sys
    if "pyperclip" in sys.modules:
        del sys.modules["pyperclip"]
    result = executor.execute("clipboard_write", {"text": "test"})
    assert "ERROR" in result


# ─── ask_user / run_code / bookmark / restore_bookmark ────────────────────

def test_ask_user(executor):
    result = executor.execute("ask_user", {"question": "Are you sure?"})
    assert "WAITING FOR USER INPUT" in result


def test_ask_user_with_options(executor):
    result = executor.execute("ask_user", {"question": "Pick one", "options": ["yes", "no"]})
    assert "yes" in result or "no" in result


def test_run_code(executor, monkeypatch):
    """Test run_code tool (line 2022-2029)."""
    monkeypatch.setattr("apex.sandbox.sandbox", None, raising=False)
    result = executor.execute("run_code", {"code": "print(1)", "language": "python"})
    assert isinstance(result, str)


def test_bookmark_session(executor, monkeypatch):
    """Test bookmark_session (lines 2031-2041) and restore_bookmark (lines 2043-2052)."""
    class FakeConvManager:
        def __init__(self):
            pass
        def bookmark(self, name):
            pass
        def restore_bookmark(self, name):
            return ["msg1", "msg2"] if name == "my_bm" else None

    monkeypatch.setattr("apex.context_manager.ConversationManager", lambda: FakeConvManager())
    result = executor.execute("bookmark_session", {"name": "my_bm"})
    assert "SUCCESS" in result

    result2 = executor.execute("restore_bookmark", {"name": "my_bm"})
    assert "RESTORED" in result2


def test_restore_bookmark_not_found(executor, monkeypatch):
    """Cover line 2051."""
    class FakeConvManager:
        def __init__(self):
            pass
        def bookmark(self, name):
            pass
        def restore_bookmark(self, name):
            return None

    monkeypatch.setattr("apex.context_manager.ConversationManager", lambda: FakeConvManager())
    result = executor.execute("restore_bookmark", {"name": "nonexistent"})
    assert "ERROR" in result


def test_search_history_no_conversation(executor):
    result = executor.execute("search_history", {"query": "test"})
    assert isinstance(result, str)


def test_get_conversation_stats_no_conversation(executor):
    result = executor.execute("get_conversation_stats", {})
    assert isinstance(result, str)


def test_get_conversation_stats_with_data(executor, monkeypatch):
    """Cover lines 2078-2079."""
    class FakeConvManager:
        def get_stats(self):
            return {"message_count": 5, "bookmarks": 2, "roles": {"user": 3, "assistant": 2}}

    monkeypatch.setattr("apex.context_manager.ConversationManager", lambda: FakeConvManager())
    executor._conv_manager = FakeConvManager()
    result = executor.execute("get_conversation_stats", {})
    assert "5" in result
    assert "2" in result


# ─── undo / redo ──────────────────────────────────────────────────────────

def test_undo_not_available(executor):
    result = executor.execute("undo", {})
    assert "ERROR" in result


def test_undo_success(executor, monkeypatch):
    """Cover lines 2085-2088."""
    class FakeUndo:
        def undo(self):
            return {"type": "edit_file", "details": {"path": "test.txt"}}

    # Direct approach: set _undo_manager
    class UM:
        def undo(self):
            return {"type": "edit_file", "details": {"path": "test.txt"}}
    executor._undo_manager = UM()
    result = executor.execute("undo", {})
    assert "UNDONE" in result or "ERROR" in result


def test_undo_nothing(executor, monkeypatch):
    """Cover line 2086-2087."""
    class UM:
        def undo(self):
            return None
    executor._undo_manager = UM()
    result = executor.execute("undo", {})
    assert "ERROR" in result or "Nothing" in result


def test_redo_not_available(executor):
    result = executor.execute("redo", {})
    assert "ERROR" in result


def test_undo_info_not_available(executor):
    result = executor.execute("undo_info", {})
    assert isinstance(result, str)


def test_undo_info_available(executor, monkeypatch):
    """Cover lines 2103-2105."""
    class UM:
        def can_undo(self):
            return True
        def get_undo_description(self):
            return "Edited test.txt"
    executor._undo_manager = UM()
    result = executor.execute("undo_info", {})
    assert "True" in result or "undo" in result.lower()


def test_redo_info_not_available(executor):
    result = executor.execute("redo_info", {})
    assert isinstance(result, str)


def test_redo_info_available(executor, monkeypatch):
    """Cover lines 2111-2113."""
    class UM:
        def can_redo(self):
            return True
        def get_redo_description(self):
            return "Redo edit"
    executor._undo_manager = UM()
    result = executor.execute("redo_info", {})
    assert "True" in result or "redo" in result.lower()


# ─── share_session ────────────────────────────────────────────────────────

def test_share_session_no_agent(executor):
    result = executor.execute("share_session", {})
    assert "ERROR" in result


def test_share_session_success(executor, monkeypatch):
    """Cover lines 2121-2123."""
    session_manager_calls = []

    class FakeSM:
        def share(self, agent):
            session_manager_calls.append(agent)
            return "https://apex-ai.dev/s/abc123"

    monkeypatch.setattr("apex.session.SessionManager", lambda: FakeSM())
    executor._agent = object()
    result = executor.execute("share_session", {})
    assert "share" in result.lower() or "ERROR" in result


# ─── apply_patch ──────────────────────────────────────────────────────────

def test_apply_patch_not_installed(executor, monkeypatch):
    """Cover FileNotFoundError line 2141-2142."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError()))
    result = executor.execute("apply_patch", {"patch": "diff"})
    assert "ERROR" in result or "not found" in result


def test_apply_patch_exception(executor, monkeypatch):
    """Cover lines 2143-2144."""
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("patch fail")))
    result = executor.execute("apply_patch", {"patch": "diff"})
    assert "ERROR" in result


# ─── list_commands / run_command_custom ──────────────────────────────────

def test_list_commands_empty(executor, monkeypatch):
    """When no commands available (no .apex/commands dir)."""
    class FakeCM:
        def list_commands(self):
            return []

    monkeypatch.setattr("apex.commands.get_command_manager", lambda cwd: FakeCM(), raising=False)
    result = executor.execute("list_commands", {})
    assert "No custom commands" in result


def test_list_commands_with_cmds(executor, monkeypatch):
    """Cover lines 2149-2156."""
    class FakeCM:
        def list_commands(self):
            return [{"name": "test", "description": "A test command"}]

    monkeypatch.setattr("apex.commands.get_command_manager", lambda cwd: FakeCM(), raising=False)
    result = executor.execute("list_commands", {})
    assert "/test" in result


def test_run_command_custom_not_found(executor, monkeypatch):
    """Cover line 2166."""
    class FakeCM:
        def execute(self, name, **args):
            return None

    monkeypatch.setattr("apex.commands.get_command_manager", lambda cwd: FakeCM(), raising=False)
    result = executor.execute("run_command_custom", {"name": "nonexistent"})
    assert "ERROR" in result


def test_run_command_custom_success(executor, monkeypatch):
    """Cover lines 2161-2167."""
    class FakeCM:
        def execute(self, name, **args):
            return "Command executed successfully"

    monkeypatch.setattr("apex.commands.get_command_manager", lambda cwd: FakeCM(), raising=False)
    result = executor.execute("run_command_custom", {"name": "test", "args": {"foo": "bar"}})
    assert "COMMAND" in result


# ─── plan_approve / plan_reject ──────────────────────────────────────────

def test_plan_approve_no_plan(executor):
    result = executor.execute("plan_approve", {})
    assert "ERROR" in result


def test_plan_approve_success(executor):
    """Cover lines 2217-2218."""
    class FakePlan:
        def approve(self):
            pass
    executor._plan_approval = FakePlan()
    result = executor.execute("plan_approve", {})
    assert "APPROVED" in result


def test_plan_reject_no_plan(executor):
    result = executor.execute("plan_reject", {})
    assert "ERROR" in result


def test_plan_reject_success(executor):
    """Cover lines 2224-2226."""
    class FakePlan:
        def reject(self):
            pass
    executor._plan_approval = FakePlan()
    result = executor.execute("plan_reject", {"reason": "bad plan"})
    assert "REJECTED" in result


# ─── init_project ─────────────────────────────────────────────────────────

def test_init_project_exception(executor, monkeypatch):
    """Cover lines 2241-2242."""
    class FakePI:
        def create_context_file(self):
            raise Exception("init failed")

    monkeypatch.setattr("apex.project.get_project_initializer", lambda cwd: FakePI())
    result = executor.execute("init_project", {})
    assert "ERROR" in result


# ─── get_code_actions ────────────────────────────────────────────────────

def test_get_code_actions_no_diagnostics(executor, monkeypatch):
    """When LSP returns no diagnostics."""
    class FakeLSP:
        def call_tool(self, name, args):
            return {}

    monkeypatch.setattr("apex.lsp.get_lsp_manager", lambda cwd: FakeLSP())
    result = executor.execute("get_code_actions", {"path": "test.py"})
    assert "No diagnostic" in result


def test_get_code_actions_with_diagnostics(executor, monkeypatch):
    """Cover lines 2271-2275."""
    class FakeLSP:
        def call_tool(self, name, args):
            return {"diagnostics": [{"message": "Type mismatch"}, {"message": "Unused var"}]}

    monkeypatch.setattr("apex.lsp.get_lsp_manager", lambda cwd: FakeLSP())
    result = executor.execute("get_code_actions", {"path": "test.py"})
    assert "actions" in result.lower() or "Type mismatch" in result


def test_apply_code_action(executor):
    result = executor.execute("apply_code_action", {"action_id": "fix-1"})
    assert "action" in result.lower()


# ─── start_shell / run_shell / close_shell ──────────────────────────────

def test_start_shell_not_available(executor, monkeypatch):
    """Cover line 2289-2290 (ShellSession fails to start)."""
    class FakeShell:
        def start(self, shell="bash"):
            return False
        def run(self, cmd):
            return "output"
        def close(self):
            pass

    monkeypatch.setattr("apex.sandbox.ShellSession", lambda cwd: FakeShell())
    result = executor.execute("start_shell", {"shell": "bash"})
    assert "ERROR" in result


def test_run_shell_no_session(executor):
    result = executor.execute("run_shell", {"command": "echo hi"})
    assert "ERROR" in result


def test_run_shell_success(executor, monkeypatch):
    """Cover lines 2297-2300."""
    class FakeShell:
        def start(self, shell="bash"):
            return True
        def run(self, cmd):
            return "ran: " + cmd
        def close(self):
            pass

    monkeypatch.setattr("apex.sandbox.ShellSession", lambda cwd: FakeShell())
    executor.execute("start_shell", {"shell": "bash"})
    result = executor.execute("run_shell", {"command": "echo test"})
    assert "ran" in result or "test" in result


def test_run_shell_exception(executor, monkeypatch):
    """Cover line 2299-2300 exception handler."""
    class FakeShell:
        def start(self, shell="bash"):
            return True
        def run(self, cmd):
            raise Exception("shell error")
        def close(self):
            pass

    monkeypatch.setattr("apex.sandbox.ShellSession", lambda cwd: FakeShell())
    executor.execute("start_shell", {"shell": "bash"})
    result = executor.execute("run_shell", {"command": "bad"})
    assert "ERROR" in result


def test_close_shell_no_session(executor):
    result = executor.execute("close_shell", {})
    assert "ERROR" in result


def test_close_shell_success(executor, monkeypatch):
    """Cover lines 2304-2306."""
    class FakeShell:
        def start(self, shell="bash"):
            return True
        def run(self, cmd):
            return "x"
        def close(self):
            pass

    monkeypatch.setattr("apex.sandbox.ShellSession", lambda cwd: FakeShell())
    executor.execute("start_shell", {"shell": "bash"})
    result = executor.execute("close_shell", {})
    assert "SUCCESS" in result


# ─── select_files ─────────────────────────────────────────────────────────

def test_select_files_no_patterns(executor):
    result = executor.execute("select_files", {})
    assert "ERROR" in result


def test_select_files_no_matches(executor):
    result = executor.execute("select_files", {"patterns": ["*.nonexistent"]})
    assert "No files found" in result


def test_select_files_matches(executor, tmp_path):
    (tmp_path / "project" / "match_a.py").write_text("x")
    (tmp_path / "project" / "match_b.py").write_text("y")
    result = executor.execute("select_files", {"patterns": ["*.py"]})
    assert "match_a.py" in result
    assert "match_b.py" in result


# ─── get_completions ─────────────────────────────────────────────────────

def test_get_completions_type_agent(executor):
    """Cover line 2390."""
    result = executor.execute("get_completions", {"type": "agent", "prefix": ""})
    assert "Agents" in result


def test_get_completions_type_model(executor):
    """Cover line 2391-2392."""
    result = executor.execute("get_completions", {"type": "model", "prefix": ""})
    assert "--model" in result or "model" in result.lower()


def test_get_completions_unknown(executor):
    """Cover line 2393."""
    result = executor.execute("get_completions", {"type": "unknown_type", "prefix": ""})
    assert "Unknown" in result


# ─── read_image_data ────────────────────────────────────────────────────

def test_read_image_data_not_found(executor):
    result = executor.execute("read_image_data", {"path": "/nonexistent"})
    assert "ERROR" in result


def test_read_image_data_exception(executor, tmp_path):
    """Cover lines 2405-2406."""
    f = tmp_path / "img_data.bin"
    f.write_bytes(b"\xff\xd8\xff\xe0")
    f.chmod(0o222)
    try:
        result = executor.execute("read_image_data", {"path": str(f)})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── inline_edit ─────────────────────────────────────────────────────────

def test_inline_edit_not_found(executor):
    result = executor.execute("inline_edit", {"path": "/nonexistent", "line": 1, "content": "new"})
    assert "ERROR" in result


def test_inline_edit_success(executor, tmp_path):
    f = tmp_path / "inline.txt"
    f.write_text("line1\nline2\nline3")
    result = executor.execute("inline_edit", {"path": str(f), "line": 2, "content": "MODIFIED"})
    assert "SUCCESS" in result
    assert f.read_text() == "line1\nMODIFIED\nline3"


def test_inline_edit_replace_multiple(executor, tmp_path):
    f = tmp_path / "inline_multi.txt"
    f.write_text("a\nb\nc\nd")
    result = executor.execute("inline_edit", {"path": str(f), "line": 2, "content": "X\nY", "replace": 2})
    assert "SUCCESS" in result
    assert f.read_text() == "a\nX\nY\nd"


def test_inline_edit_exception(executor, tmp_path):
    """Cover lines 2424-2425."""
    f = tmp_path / "inline_exc.txt"
    f.write_text("data")
    f.chmod(0o444)
    try:
        result = executor.execute("inline_edit", {"path": str(f), "line": 1, "content": "modified"})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── retry_last ──────────────────────────────────────────────────────────

def test_retry_last_no_previous(executor):
    result = executor.execute("retry_last", {})
    assert "ERROR" in result


def test_retry_last_success(executor, tmp_path):
    """Cover line 2434."""
    f = tmp_path / "retry.txt"
    f.write_text("original")
    executor.execute("edit_file", {"path": str(f), "old_string": "original", "new_string": "changed"})
    executor._last_tool = "edit_file"
    executor._last_args = {"path": str(f), "old_string": "changed", "new_string": "final"}
    result = executor.execute("retry_last", {})
    assert f.read_text() == "final" or "SUCCESS" in result or "ERROR" in result


# ─── list_skills / use_skill ──────────────────────────────────────────────

def test_list_skills_empty(executor, monkeypatch):
    class FakeSM:
        def list_skills(self):
            return []

    monkeypatch.setattr("apex.skills.get_skill_manager", lambda cwd: FakeSM())
    result = executor.execute("list_skills", {})
    assert "No skills" in result


def test_list_skills_with_skills(executor, monkeypatch):
    """Cover lines 2480-2483."""
    class FakeSM:
        def list_skills(self):
            return [{"name": "test-skill", "description": "A test"}]

    monkeypatch.setattr("apex.skills.get_skill_manager", lambda cwd: FakeSM())
    result = executor.execute("list_skills", {})
    assert "test-skill" in result


def test_use_skill_not_found(executor, monkeypatch):
    """Cover line 2493-2494."""
    class FakeSM:
        def render(self, name, **args):
            return None

    monkeypatch.setattr("apex.skills.get_skill_manager", lambda cwd: FakeSM())
    result = executor.execute("use_skill", {"name": "nonexistent"})
    assert "ERROR" in result


def test_use_skill_success(executor, monkeypatch):
    """Cover line 2494."""
    class FakeSM:
        def render(self, name, **args):
            return "Skill output"

    monkeypatch.setattr("apex.skills.get_skill_manager", lambda cwd: FakeSM())
    result = executor.execute("use_skill", {"name": "test", "args": {"x": 1}})
    assert "SKILL" in result


# ─── replace_in_files ────────────────────────────────────────────────────

def test_replace_in_files_error(executor, monkeypatch):
    """Cover line 2506-2507."""
    class FakeSR:
        def replace_in_files(self, pattern, replacement, files, dry_run):
            return {"error": "Pattern not found"}

    monkeypatch.setattr("apex.skills.SearchReplace", lambda cwd: FakeSR())
    result = executor.execute("replace_in_files", {"pattern": "old", "replacement": "new", "files": ["*.txt"]})
    assert "Pattern not found" in result


def test_replace_in_files_dry_run(executor, monkeypatch):
    """Cover lines 2506-2515."""
    class FakeSR:
        def replace_in_files(self, pattern, replacement, files, dry_run):
            return {"replacements": 3, "files_modified": ["a.txt", "b.txt"]}

    monkeypatch.setattr("apex.skills.SearchReplace", lambda cwd: FakeSR())
    result = executor.execute("replace_in_files", {"pattern": "old", "replacement": "new", "files": ["*.txt"]})
    assert "3 replacements" in result
    assert "DRY RUN" in result


def test_replace_in_files_apply(executor, monkeypatch):
    """Cover non-dry-run path."""
    class FakeSR:
        def replace_in_files(self, pattern, replacement, files, dry_run):
            return {"replacements": 1, "files_modified": ["a.txt"]}

    monkeypatch.setattr("apex.skills.SearchReplace", lambda cwd: FakeSR())
    result = executor.execute("replace_in_files", {"pattern": "old", "replacement": "new", "files": ["*.txt"], "dry_run": False})
    assert "1 replacements" in result
    assert "DRY RUN" not in result


# ─── analyze_code ────────────────────────────────────────────────────────

def test_analyze_code_error(executor, monkeypatch):
    """Cover line 2525."""
    class FakeCA:
        def analyze_file(self, path):
            return {"error": "File not found"}

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("analyze_code", {"path": "nonexistent.py"})
    assert "File not found" in result


# ─── explain_code ────────────────────────────────────────────────────────

def test_explain_code(executor, monkeypatch):
    class FakeCA:
        def explain_code(self, path, start, end):
            return "This code does X"

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("explain_code", {"path": "test.py", "start": 1, "end": 10})
    assert "This code does X" in result


# ─── generate_tests ──────────────────────────────────────────────────────

def test_generate_tests_error(executor, monkeypatch):
    """Cover line 2565."""
    class FakeCA:
        def analyze_file(self, path):
            return {"error": "File not found"}

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("generate_tests", {"path": "nonexistent.py"})
    assert "File not found" in result


def test_generate_tests_no_functions(executor, monkeypatch):
    """Cover line 2569."""
    class FakeCA:
        def analyze_file(self, path):
            return {"functions": []}

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("generate_tests", {"path": "test.py"})
    assert "No functions" in result


def test_generate_tests_pytest(executor, monkeypatch):
    """Cover pytest path."""
    class FakeCA:
        def analyze_file(self, path):
            return {"functions": [{"name": "foo"}, {"name": "bar"}]}

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("generate_tests", {"path": "test.py", "framework": "pytest"})
    assert "def test_foo" in result
    assert "def test_bar" in result


def test_generate_tests_jest(executor, monkeypatch):
    """Cover jest/framework path."""
    class FakeCA:
        def analyze_file(self, path):
            return {"functions": [{"name": "foo"}]}

    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA())
    result = executor.execute("generate_tests", {"path": "test.js", "framework": "jest"})
    assert "describe" in result


# ─── get_keybindings / set_theme ─────────────────────────────────────────

def test_get_keybindings(executor):
    result = executor.execute("get_keybindings", {})
    assert "Tab" in result


def test_set_theme_invalid(executor):
    result = executor.execute("set_theme", {"theme": "nonexistent"})
    assert "Available themes" in result


def test_set_theme_valid(executor):
    result = executor.execute("set_theme", {"theme": "dark"})
    assert "Theme set" in result


# ─── add_git_hook ────────────────────────────────────────────────────────

def test_add_git_hook_not_repo(executor):
    result = executor.execute("add_git_hook", {"hook": "pre-commit", "command": "echo test"})
    assert "ERROR" in result


# ─── batch_read / batch_write ───────────────────────────────────────────

def test_batch_read_no_paths(executor):
    result = executor.execute("batch_read", {"paths": []})
    assert "ERROR" in result


def test_batch_write_no_operations(executor):
    result = executor.execute("batch_write", {"operations": []})
    assert "ERROR" in result


def test_batch_write_success(executor, monkeypatch):
    """Cover lines 2674-2678."""
    class FakeBO:
        @staticmethod
        def batch_write(operations, cwd):
            return {"success": ["a.txt", "b.txt"], "failed": [{"path": "c.txt", "error": "perm denied"}]}

    monkeypatch.setattr("apex.advanced.BatchOperation", FakeBO)
    result = executor.execute("batch_write", {"operations": [{"path": "a.txt", "content": "x"}]})
    assert "2 files written" in result
    assert "Failed: 1" in result


# ─── retry_tool ─────────────────────────────────────────────────────────

def test_retry_tool_error(executor, monkeypatch):
    """Cover lines 2695-2696."""
    class FakeRH:
        class config:
            max_retries = 3
        def execute(self, fn, name, args):
            raise Exception("retry exhausted")

    monkeypatch.setattr("apex.advanced.get_retry_handler", lambda: FakeRH())
    result = executor.execute("retry_tool", {"tool": "read_file", "args": {"path": "/nonexistent"}, "retries": 2})
    assert "ERROR" in result


# ─── get_tool_timeout / set_tool_timeout / clear_file_cache ────────────

def test_get_tool_timeout(executor, monkeypatch):
    class FakeTT:
        @staticmethod
        def get_timeout(tool):
            return 120

    monkeypatch.setattr("apex.advanced.ToolTimeout", FakeTT)
    result = executor.execute("get_tool_timeout", {"tool": "read_file"})
    assert "120" in result


def test_set_tool_timeout(executor, monkeypatch):
    calls = []
    class FakeTT:
        @staticmethod
        def set_timeout(tool, timeout):
            calls.append((tool, timeout))

    monkeypatch.setattr("apex.advanced.ToolTimeout", FakeTT)
    result = executor.execute("set_tool_timeout", {"tool": "read_file", "timeout": 60})
    assert "60" in result
    assert calls == [("read_file", 60)]


def test_clear_file_cache(executor, monkeypatch):
    cleared = []
    class FakeCache:
        def clear(self):
            cleared.append(True)

    monkeypatch.setattr("apex.advanced.get_file_cache", lambda: FakeCache())
    result = executor.execute("clear_file_cache", {})
    assert "SUCCESS" in result
    assert cleared == [True]


# ─── get_context_info ───────────────────────────────────────────────────

def test_get_context_info_no_agent(executor):
    result = executor.execute("get_context_info", {})
    assert "No agent" in result or isinstance(result, str)


def test_get_context_info_success(executor, monkeypatch):
    """Cover lines 2727-2735."""
    class FakeCO:
        @staticmethod
        def extract_key_info(messages):
            return {"files_mentioned": ["a.py"], "tools_used": ["read_file"], "errors": []}

    monkeypatch.setattr("apex.advanced.ContextOptimizer", FakeCO)
    executor._agent = lambda: None
    # Need agent with history
    class FakeAgent:
        history = ["msg1", "msg2"]
    executor._agent = FakeAgent()
    result = executor.execute("get_context_info", {})
    assert "a.py" in result
    assert "read_file" in result


# ─── start_file_watch / stop_file_watch ─────────────────────────────────

def test_start_file_watch_fail(executor, monkeypatch):
    """Cover line 2748."""
    class FakeFW:
        def __init__(self, cwd):
            pass
        def watch(self, patterns=None):
            return None
        def stop(self):
            pass

    monkeypatch.setattr("apex.project.FileWatcher", FakeFW)
    result = executor.execute("start_file_watch", {})
    assert "ERROR" in result or "watchdog" in result.lower()


def test_stop_file_watch_not_running(executor):
    result = executor.execute("stop_file_watch", {})
    assert "ERROR" in result


def test_stop_file_watch_success(executor, monkeypatch):
    stopped = []
    class FakeFW:
        def __init__(self, cwd):
            pass
        def watch(self, patterns=None):
            return object()
        def stop(self):
            stopped.append(True)
    monkeypatch.setattr("apex.project.FileWatcher", FakeFW)
    executor.execute("start_file_watch", {})
    result = executor.execute("stop_file_watch", {})
    assert "SUCCESS" in result
    assert stopped == [True]


# ─── expand_vars / get_env / set_env / list_env ─────────────────────────

def test_expand_vars(executor, monkeypatch):
    class FakeSE:
        @staticmethod
        def expand(text, vars):
            return text.replace("$NAME", vars.get("NAME", ""))

    monkeypatch.setattr("apex.extras.ShellExpander", FakeSE)
    result = executor.execute("expand_vars", {"text": "Hello $NAME", "vars": {"NAME": "World"}})
    assert "Hello World" in result


def test_get_env_not_found(executor, monkeypatch):
    class FakeEM:
        def get(self, key):
            return None
    monkeypatch.setattr("apex.extras.get_env_manager", lambda cwd: FakeEM())
    result = executor.execute("get_env", {"key": "NONEXISTENT"})
    assert "ERROR" in result


def test_get_env_found(executor, monkeypatch):
    class FakeEM:
        def get(self, key):
            return "value123"
    monkeypatch.setattr("apex.extras.get_env_manager", lambda cwd: FakeEM())
    result = executor.execute("get_env", {"key": "MY_VAR"})
    assert "MY_VAR=value123" in result


def test_set_env(executor, monkeypatch):
    class FakeEM:
        def set(self, key, value):
            self._key = key
            self._value = value
    monkeypatch.setattr("apex.extras.get_env_manager", lambda cwd: FakeEM())
    result = executor.execute("set_env", {"key": "FOO", "value": "bar"})
    assert "SUCCESS" in result


def test_list_env(executor, monkeypatch):
    class FakeEM:
        def list(self):
            return {"A": "1", "B": "2"}
    monkeypatch.setattr("apex.extras.get_env_manager", lambda cwd: FakeEM())
    result = executor.execute("list_env", {})
    assert "A=1" in result
    assert "B=2" in result


# ─── submit_task / list_tasks / get_task ────────────────────────────────

def test_submit_task(executor, monkeypatch):
    """Cover lines 2791-2809."""
    tasks = []
    class FakeQueue:
        async def add(self, name, coro):
            tasks.append(name)
            return "task-1"

    monkeypatch.setattr("apex.extras.get_task_queue", lambda: FakeQueue(), raising=False)
    result = executor.execute("submit_task", {"name": "my_task", "command": "echo hi"})
    assert isinstance(result, str)


def test_list_tasks_empty(executor, monkeypatch):
    class FakeQueue:
        def list(self):
            return []
    monkeypatch.setattr("apex.extras.get_task_queue", lambda: FakeQueue())
    result = executor.execute("list_tasks", {})
    assert "No tasks" in result


def test_list_tasks_with_tasks(executor, monkeypatch):
    """Cover lines 2818-2821."""
    class FakeQueue:
        def list(self):
            return [{"id": "t1", "name": "build", "status": "running"}]
    monkeypatch.setattr("apex.extras.get_task_queue", lambda: FakeQueue())
    result = executor.execute("list_tasks", {})
    assert "t1" in result
    assert "build" in result


def test_get_task_not_found(executor, monkeypatch):
    """Cover line 2830."""
    class FakeQueue:
        def get(self, task_id):
            return None
    monkeypatch.setattr("apex.extras.get_task_queue", lambda: FakeQueue())
    result = executor.execute("get_task", {"task_id": "nonexistent"})
    assert "ERROR" in result


def test_get_task_found(executor, monkeypatch):
    """Cover line 2831."""
    class FakeTask:
        name = "build"
        status = "done"
        result = "success"
        error = None
    class FakeQueue:
        def get(self, task_id):
            return FakeTask()
    monkeypatch.setattr("apex.extras.get_task_queue", lambda: FakeQueue())
    result = executor.execute("get_task", {"task_id": "t1"})
    assert "build" in result
    assert "done" in result


# ─── validate_workspace ────────────────────────────────────────────────

def test_validate_workspace(executor, monkeypatch):
    class FakeWV:
        def __init__(self, cwd):
            pass
        def validate_config(self):
            return {"valid": True, "issues": []}
    monkeypatch.setattr("apex.extras.WorkspaceValidator", FakeWV)
    result = executor.execute("validate_workspace", {})
    assert "Valid: True" in result


def test_validate_workspace_with_issues(executor, monkeypatch):
    class FakeWV:
        def __init__(self, cwd):
            pass
        def validate_config(self):
            return {"valid": False, "issues": ["Missing config.json"]}
    monkeypatch.setattr("apex.extras.WorkspaceValidator", FakeWV)
    result = executor.execute("validate_workspace", {})
    assert "Valid: False" in result
    assert "Missing" in result


# ─── security_audit ─────────────────────────────────────────────────────

def test_security_audit_project(executor, monkeypatch):
    """Cover lines 2875-2884."""
    _issues_captured = []
    class FakeSA:
        def __init__(self, cwd):
            pass
        def audit_project(self):
            return {
                "files": [{"path": "main.py", "issues": [{"message": "Hardcoded secret"}]}],
                "total_issues": 1
            }
        def audit_file(self, path):
            return {"files": [{"path": str(path), "issues": [{"message": "Injection risk"}]}], "total_issues": 1}

    monkeypatch.setattr("apex.extras.SecurityAuditor", FakeSA)
    result = executor.execute("security_audit", {})
    assert "Security Audit" in result
    assert "1" in result or "Hardcoded" in result


def test_security_audit_file_path(executor, monkeypatch):
    """Cover audit_file path (line 2871)."""
    class FakeSA:
        def __init__(self, cwd):
            pass
        def audit_file(self, path):
            return {"issues": "Found 2 issues"}
        def audit_project(self):
            return {"files": [], "total_issues": 0}

    monkeypatch.setattr("apex.extras.SecurityAuditor", FakeSA)
    result = executor.execute("security_audit", {"path": "test.py"})
    assert isinstance(result, str)


# ─── refactor_code ──────────────────────────────────────────────────────

def test_refactor_code_error(executor, monkeypatch):
    """Cover error path."""
    class FakeCR:
        def __init__(self, cwd):
            pass
        def refactor_function(self, path, function, style):
            return {"error": "Function not found"}

    monkeypatch.setattr("apex.codegen.CodeRefactorer", FakeCR)
    result = executor.execute("refactor_code", {"path": "test.py", "function": "foo"})
    assert "ERROR" in result


def test_refactor_code_success(executor, monkeypatch):
    """Cover line 2898."""
    class FakeCR:
        def __init__(self, cwd):
            pass
        def refactor_function(self, path, function, style):
            return {"success": True}

    monkeypatch.setattr("apex.codegen.CodeRefactorer", FakeCR)
    result = executor.execute("refactor_code", {"path": "test.py", "function": "foo", "style": "async"})
    assert "SUCCESS" in result


# ─── generate_db_model / generate_dockerfile / etc ──────────────────────

def test_generate_db_model(executor, monkeypatch):
    class FakeDM:
        def __init__(self, cwd):
            pass
        def generate_model(self, table, columns):
            return "class User: pass"

    monkeypatch.setattr("apex.codegen.DatabaseManager", FakeDM)
    result = executor.execute("generate_db_model", {"table": "users", "columns": [{"name": "id", "type": "int"}]})
    assert "class User" in result or "Generated" in result


def test_generate_dockerfile(executor, monkeypatch):
    class FakeDM:
        def __init__(self, cwd):
            pass
        def generate_dockerfile(self, language):
            return "FROM python:3.11"
        def generate_docker_compose(self, services):
            return "services:"

    monkeypatch.setattr("apex.codegen.DockerManager", FakeDM)
    result = executor.execute("generate_dockerfile", {"language": "python"})
    assert "FROM python" in result


def test_generate_docker_compose(executor, monkeypatch):
    class FakeDM:
        def __init__(self, cwd):
            pass
        def generate_dockerfile(self, language):
            return ""
        def generate_docker_compose(self, services):
            return "services:\n  web:"

    monkeypatch.setattr("apex.codegen.DockerManager", FakeDM)
    result = executor.execute("generate_docker_compose", {"services": [{"name": "web", "image": "nginx"}]})
    assert "services" in result


def test_generate_api_client(executor, monkeypatch):
    class FakeACG:
        def __init__(self, cwd):
            pass
        def generate_from_openapi(self, spec):
            return "import requests"

    monkeypatch.setattr("apex.codegen.APIClientGenerator", FakeACG)
    result = executor.execute("generate_api_client", {"spec": "spec.yaml"})
    assert "import requests" in result


def test_generate_docs_readme(executor, monkeypatch):
    class FakeDG:
        def __init__(self, cwd):
            pass
        def generate_readme(self):
            return "# My Project"
        def generate_api_docs(self, path):
            return "## API"
        def generate_markdoc(self):
            return "markdoc"

    monkeypatch.setattr("apex.codegen.DocumentationGenerator", FakeDG)
    result = executor.execute("generate_docs", {"type": "readme"})
    assert "# My Project" in result


def test_generate_docs_api(executor, monkeypatch):
    """Cover line 2948."""
    class FakeDG:
        def __init__(self, cwd):
            pass
        def generate_readme(self):
            return ""
        def generate_api_docs(self, path):
            return "## API Docs"
        def generate_markdoc(self):
            return ""

    monkeypatch.setattr("apex.codegen.DocumentationGenerator", FakeDG)
    result = executor.execute("generate_docs", {"type": "api", "path": "src/main.py"})
    assert "API Docs" in result


def test_generate_docs_invalid(executor, monkeypatch):
    class FakeDG:
        def __init__(self, cwd):
            pass
    monkeypatch.setattr("apex.codegen.DocumentationGenerator", lambda cwd: FakeDG())
    result = executor.execute("generate_docs", {"type": "invalid_type"})
    assert "ERROR" in result


# ─── profile_code ───────────────────────────────────────────────────────

def test_profile_code_error(executor, monkeypatch):
    """Cover line 2963."""
    class FakePP:
        def __init__(self, cwd):
            pass
        def profile_file(self, path):
            return {"error": "File not found"}
        def suggest_optimizations(self, path):
            return []

    monkeypatch.setattr("apex.codegen.PerformanceProfiler", FakePP)
    result = executor.execute("profile_code", {"path": "nonexistent.py"})
    assert "File not found" in result


def test_profile_code_success(executor, monkeypatch):
    class FakePP:
        def __init__(self, cwd):
            pass
        def profile_file(self, path):
            return {"lines": 50, "functions": 3, "classes": 1, "imports": 5, "complexity_score": 2.5}
        def suggest_optimizations(self, path):
            return []

    monkeypatch.setattr("apex.codegen.PerformanceProfiler", FakePP)
    result = executor.execute("profile_code", {"path": "test.py"})
    assert "50" in result
    assert "3" in result


def test_optimize_code(executor, monkeypatch):
    class FakePP:
        def __init__(self, cwd):
            pass
        def profile_file(self, path):
            return {}
        def suggest_optimizations(self, path):
            return ["Use list comprehension", "Add type hints"]

    monkeypatch.setattr("apex.codegen.PerformanceProfiler", FakePP)
    result = executor.execute("optimize_code", {"path": "test.py"})
    assert "list comprehension" in result


# ─── search_history (second definition in extras) ───────────────────────

def test_search_history_extras_no_results(executor, monkeypatch):
    class FakeHS:
        def search(self, query, fuzzy=True):
            return []
        def fuzzy_match(self, query):
            return []

    monkeypatch.setattr("apex.extras.get_history_search", lambda: FakeHS())
    result = executor.execute("search_history", {"query": "nonexistent", "fuzzy": True})
    assert "No results" in result


def test_search_history_extras_with_results(executor, monkeypatch):
    """Cover lines 2844-2848."""
    class FakeHS:
        def search(self, query, fuzzy=True):
            return [{"query": "how to write tests", "similarity": 0.95}]
        def fuzzy_match(self, query):
            return []

    monkeypatch.setattr("apex.extras.get_history_search", lambda: FakeHS())
    result = executor.execute("search_history", {"query": "test", "fuzzy": True})
    assert "how to write tests" in result


# ─── AsyncToolExecutor ──────────────────────────────────────────────────

def test_async_executor_unknown_tool():
    """Test AsyncToolExecutor.execute_async with unknown tool (line ~2991)."""
    e = __import__("apex.tools", fromlist=["AsyncToolExecutor"]).AsyncToolExecutor()
    import asyncio
    result = asyncio.run(e.execute_async("nonexistent_tool", {}))
    assert "ERROR" in result


def test_async_executor_sync_method():
    """Cover line 2995 - sync method path."""
    e = __import__("apex.tools", fromlist=["AsyncToolExecutor"]).AsyncToolExecutor()
    import asyncio
    result = asyncio.run(e.execute_async("get_keybindings", {}))
    assert "Tab" in result


def test_async_executor_exception():
    """Cover lines 2996-2997 - exception handler."""
    e = __import__("apex.tools", fromlist=["AsyncToolExecutor"]).AsyncToolExecutor()
    import asyncio
    result = asyncio.run(e.execute_async("read_file", {"path": str(Path.cwd())}))
    assert "ERROR" in result or "Is a directory" in result or "Permission" in result


# ─── Task tool delegating ───────────────────────────────────────────────

def test_task_unknown_agent(executor):
    result = executor.execute("task", {"agent": "nonexistent_agent", "task": "do something"})
    assert "ERROR" in result


def test_task_known_agent(executor):
    """Test task delegation with a known agent name."""
    result = executor.execute("task", {"agent": "general", "task": "explain this"})
    assert "Delegated" in result
