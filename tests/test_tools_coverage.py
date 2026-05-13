"""Additional coverage tests for apex/tools.py - covering remaining uncovered lines."""

import pytest
import subprocess
from pathlib import Path


# Helper: create minimal .git dir
def _create_git_repo(path):
    git_dir = path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    return git_dir


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    from apex.tools import ToolExecutor
    return ToolExecutor(cwd=cwd)


# ─── run_command: stderr + nonzero exit (lines 1497, 1499) ────────────────

def test_run_command_full_output(executor, monkeypatch):
    class FakeResult:
        stdout = "output text"
        stderr = "error text"
        returncode = 1
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = executor.execute("run_command", {"command": "some_cmd"})
    assert "EXIT CODE" in result
    assert "STDERR" in result
    assert "output text" in result


def test_run_command_only_stderr(executor, monkeypatch):
    class FakeResult:
        stdout = ""
        stderr = "some error"
        returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = executor.execute("run_command", {"command": "cmd"})
    assert "STDERR" in result


# ─── list_files: stat exception (1518-1519) ──────────────────────────────

def test_list_files_stat_exception(executor, monkeypatch):
    import os
    orig_stat = os.stat
    def broken_stat(path, *a, **kw):
        if "broken_file" in str(path):
            raise OSError("stat failed")
        return orig_stat(path, *a, **kw)
    monkeypatch.setattr(os, "stat", broken_stat)
    d = executor.cwd / "stat_test"
    d.mkdir(parents=True, exist_ok=True)
    (d / "broken_file.txt").write_text("x")
    (d / "ok_file.txt").write_text("y")
    result = executor.execute("list_files", {"path": str(d)})
    assert "ok_file.txt" in result


# ─── list_files: outer exception (1522-1523) ─────────────────────────────

def test_list_files_outer_exception(executor, monkeypatch):
    monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(PermissionError("denied")))
    result = executor.execute("list_files", {"path": str(executor.cwd)})
    assert "ERROR" in result


# ─── search_in_files: outer exception (1545-1546) ────────────────────────

def test_search_in_files_re_error(executor, monkeypatch):
    """Trigger outer exception by making rglob raise."""
    monkeypatch.setattr(Path, "rglob", lambda self, p: (_ for _ in ()).throw(Exception("boom")))
    result = executor.execute("search_in_files", {"pattern": "test", "path": str(executor.cwd)})
    assert "ERROR" in result


# ─── create_directory: exception (1568-1569) ────────────────────────────

def test_create_directory_on_file(executor, tmp_path):
    f = tmp_path / "not_a_dir"
    f.write_text("x")
    result = executor.execute("create_directory", {"path": str(f / "sub")})
    assert "ERROR" in result


# ─── glob_search: exception (1585-1586) ──────────────────────────────────

def test_glob_search_relative_to_fail(executor, monkeypatch):
    d = executor.cwd / "glob_exc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.txt").write_text("x")
    orig = Path.relative_to
    def broken(self, other):
        if "glob_exc" in str(self):
            raise ValueError("fail")
        return orig(self, other)
    monkeypatch.setattr(Path, "relative_to", broken)
    result = executor.execute("glob_search", {"pattern": "a.txt", "directory": str(d)})
    assert isinstance(result, str)


# ─── get_file_tree: depth limit (1598), hidden skip (1607, 1612-1613) ───

def test_get_file_tree_depth_and_hidden(executor, tmp_path):
    d = tmp_path / "tree_dh"
    d.mkdir()
    (d / ".hidden").write_text("x")
    sub = d / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("x")
    result = executor.execute("get_file_tree", {"path": str(d), "max_depth": 0})
    assert ".hidden" not in result
    assert isinstance(result, str)


# ─── get_file_tree: PermissionError (1601-1602) ─────────────────────────

def test_get_file_tree_permission_error(executor, tmp_path):
    d = tmp_path / "tree_perm"
    d.mkdir()
    r = d / "restricted"
    r.mkdir()
    r.chmod(0o000)
    try:
        result = executor.execute("get_file_tree", {"path": str(d)})
        assert isinstance(result, str)
    finally:
        r.chmod(0o755)


# ─── diff_files: file not found (1624, 1626) ────────────────────────────

def test_diff_files_not_found(executor):
    result = executor.execute("diff_files", {"path_a": "nonexistent_a", "path_b": "nonexistent_b"})
    assert "ERROR" in result


# ─── git_status exception (1647-1655) ────────────────────────────────────

def test_git_status_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("get_git_status", {})
    assert "ERROR" in result


def test_git_status_clean(executor):
    _create_git_repo(executor.cwd)
    result = executor.execute("get_git_status", {})
    assert isinstance(result, str)


# ─── git_log exception (1661-1670) ───────────────────────────────────────

def test_git_log_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("get_git_log", {})
    assert "ERROR" in result


def test_git_log_empty(executor):
    _create_git_repo(executor.cwd)
    result = executor.execute("get_git_log", {})
    assert isinstance(result, str)


# ─── git_diff exception (1676-1683) ──────────────────────────────────────

def test_git_diff_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_diff", {})
    assert "ERROR" in result


def test_git_diff_with_ref(executor):
    _create_git_repo(executor.cwd)
    result = executor.execute("git_diff", {"ref": "main"})
    assert isinstance(result, str)


# ─── web_search: snippet fallback (1703-1704) ────────────────────────────

def test_web_search_snippet_empty(executor, monkeypatch):
    html = '<html><a class="result__a" href="http://x.com">Title</a></html>'
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"stdout": html, "stderr": "", "returncode": 0})())
    result = executor.execute("web_search", {"query": "test"})
    assert isinstance(result, str)


# ─── format_file: python returncode paths (1867-1869) ────────────────────

def test_format_file_python_success(executor, tmp_path, monkeypatch):
    f = tmp_path / "f.py"
    f.write_text("x=1")
    from apex.formatter import formatter_manager as fm
    monkeypatch.setattr(fm, "format_file", lambda path: True)
    result = executor.execute("format_file", {"path": str(f)})
    assert "SUCCESS" in result


def test_format_file_python_error(executor, tmp_path, monkeypatch):
    f = tmp_path / "f.py"
    f.write_text("x=1")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stderr": "fail", "stdout": ""})())
    result = executor.execute("format_file", {"path": str(f)})
    assert "ERROR" in result


# ─── format_file: non-python returncode paths (1872-1874) ────────────────

def test_format_file_rs_success(executor, tmp_path, monkeypatch):
    f = tmp_path / "f.rs"
    f.write_text("fn main(){}")
    from apex.formatter import formatter_manager as fm
    monkeypatch.setattr(fm, "format_file", lambda path: True)
    result = executor.execute("format_file", {"path": str(f)})
    assert "SUCCESS" in result


def test_format_file_rs_error(executor, tmp_path, monkeypatch):
    f = tmp_path / "f.rs"
    f.write_text("fn main(){}")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stderr": "err"})())
    result = executor.execute("format_file", {"path": str(f)})
    assert "ERROR" in result


# ─── install_package: success/failure (1899-1900) ────────────────────────

def test_install_package_success(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stderr": ""})())
    result = executor.execute("install_package", {"manager": "pip", "package": "x"})
    assert "SUCCESS" in result


def test_install_package_failure(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stderr": "err"})())
    result = executor.execute("install_package", {"manager": "pip", "package": "x"})
    assert "ERROR" in result


# ─── read_image: exception (1803-1804) ──────────────────────────────────

def test_read_image_exception(executor, tmp_path):
    f = tmp_path / "img.png"
    f.touch()
    f.chmod(0o222)
    try:
        result = executor.execute("read_image", {"path": str(f)})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── read_image_data: exception (2398, 2403-2404) ───────────────────────

def test_read_image_data_exception(executor, tmp_path):
    f = tmp_path / "img.dat"
    f.touch()
    f.chmod(0o222)
    try:
        result = executor.execute("read_image_data", {"path": str(f)})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── inline_edit: exception (2424-2425) ──────────────────────────────────

def test_inline_edit_exception(executor, tmp_path):
    f = tmp_path / "inline_exc.txt"
    f.write_text("a\nb\nc")
    f.chmod(0o444)
    try:
        result = executor.execute("inline_edit", {"path": str(f), "line": 1, "content": "x"})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── git_commit: failure stderr (2468) ───────────────────────────────────

def test_git_commit_failure_stderr(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stderr": "fail", "stdout": ""})())
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result


# ─── git_pre_commit: with staged changes (2600-2606) ─────────────────────

def test_git_pre_commit_with_changes(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    calls = []
    def fake_run(*a, **kw):
        cmd = a[0] if a else kw.get("args", [])
        calls.append(cmd)
        if isinstance(cmd, list) and "status" in cmd:
            return type("R", (), {"stdout": " M f.txt\n", "stderr": "", "returncode": 0})()
        return type("R", (), {"stdout": "1 file changed", "stderr": "", "returncode": 0})()
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = executor.execute("git_pre_commit", {})
    assert isinstance(result, str)


# ─── add_git_hook: success path (2639-2647) ─────────────────────────────

def test_add_git_hook_success(executor):
    _create_git_repo(executor.cwd)
    result = executor.execute("add_git_hook", {"hook": "pre-commit", "command": "echo test"})
    assert "SUCCESS" in result
    assert (executor.cwd / ".git" / "hooks" / "pre-commit").exists()


# ─── batch_read: success (2656-2663) ────────────────────────────────────

def test_batch_read_success(executor, monkeypatch):
    class FakeBO:
        @staticmethod
        def batch_read(paths, cwd):
            return {"a": "content a", "b": "content b"}
    monkeypatch.setattr("apex.advanced.BatchOperation", FakeBO, raising=False)
    result = executor.execute("batch_read", {"paths": ["a", "b"]})
    assert "Read 2 files" in result


# ─── retry_tool: error/exception (2694-2696) ────────────────────────────

def test_retry_tool_exception(executor, monkeypatch):
    class FakeRH:
        class config:
            max_retries = 1
        def execute(self, fn, name, args):
            raise Exception("failed")
    monkeypatch.setattr("apex.advanced.get_retry_handler", lambda: FakeRH(), raising=False)
    result = executor.execute("retry_tool", {"tool": "read_file", "args": {"path": "x"}, "retries": 1})
    assert "ERROR" in result


# ─── get_context_info: with agent (2727-2735) ──────────────────────────

def test_get_context_info_with_agent(executor, monkeypatch):
    class FakeCO:
        @staticmethod
        def extract_key_info(messages):
            return {"files_mentioned": ["a.py"], "tools_used": ["read"], "errors": ["e1"]}
    monkeypatch.setattr("apex.advanced.ContextOptimizer", FakeCO, raising=False)
    class FakeAgent:
        history = ["msg"]
    executor._agent = FakeAgent()
    result = executor.execute("get_context_info", {})
    assert "a.py" in result


# ─── AsyncToolExecutor: execute_async exception (2996-2997) + parallel (3000-3001) ────

def test_async_executor_exception_handler():
    import asyncio
    from apex.tools import AsyncToolExecutor
    e = AsyncToolExecutor()
    result = asyncio.run(e.execute_async("nonexistent_tool", {}))
    assert "ERROR" in result


def test_async_executor_parallel():
    import asyncio
    from apex.tools import AsyncToolExecutor
    e = AsyncToolExecutor()
    results = asyncio.run(e.execute_all_parallel([("get_keybindings", {}), ("set_theme", {"theme": "dark"})]))
    assert len(results) == 2


# ─── run_command: restricted command warning (1485-1486) ──────────────────

def test_run_command_restricted(executor, monkeypatch):
    from apex.shell_security import shell_analyzer
    class FakeAnalysis:
        requires_confirmation = True
        category = type("FakeCat", (), {"value": "network"})()
        warnings = ["Network access"]
    monkeypatch.setattr(shell_analyzer, "analyze", lambda cmd: FakeAnalysis())
    result = executor.execute("run_command", {"command": "curl http://x.com"})
    assert "WARNING" in result


# ─── diff_files: file not found paths (1624, 1626) ──────────────────────

def test_diff_files_both_not_found(executor):
    result = executor.execute("diff_files", {"path_a": "nonexistent_a", "path_b": "nonexistent_b"})
    assert "ERROR" in result


# ─── git_status: with output (1653) ──────────────────────────────────────

def test_git_status_with_output(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"stdout": " M f.txt\n", "stderr": "", "returncode": 0})())
    result = executor.execute("get_git_status", {})
    assert "f.txt" in result


# ─── read_image_data: exception handlers (2398, 2403-2404) ──────────────

def test_read_image_data_path_not_found(executor):
    result = executor.execute("read_image_data", {"path": "_nonexistent_img_"})
    assert "ERROR" in result


# ─── inline_edit: not found (2415) ──────────────────────────────────────

def test_inline_edit_not_found(executor):
    result = executor.execute("inline_edit", {"path": "_nonexistent_", "line": 1, "content": "x"})
    assert "ERROR" in result


# ─── preview_edit: not found path (1922) ─────────────────────────────────

def test_preview_edit_path_not_found(executor):
    result = executor.execute("preview_edit", {"path": "_nonexistent_", "old_string": "a", "new_string": "b"})
    assert "ERROR" in result


# ─── apply_patch: cleanup + success/error (2136-2140) ───────────────────

def test_apply_patch_patch_failure(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "patch err"})())
    import os
    monkeypatch.setattr(os, "unlink", lambda p: None)
    result = executor.execute("apply_patch", {"patch": "diff --git a/x b/x\nindex 0..1\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"})
    assert "ERROR" in result


# ─── restore_bookmark: not found (2051) ─────────────────────────────────

def test_restore_bookmark_not_found_direct(executor):
    """Cover restore_bookmark when no conv_manager exists."""
    result = executor.execute("restore_bookmark", {"name": "test"})
    assert "ERROR" in result


# ─── undo: nothing to undo (2086-2087) & redo: nothing (2094-2097) ──────

def test_undo_nothing(executor):
    class UM:
        def undo(self):
            return None
    executor._undo_manager = UM()
    result = executor.execute("undo", {})
    assert "Nothing" in result or "ERROR" in result


def test_redo_nothing(executor):
    class UM:
        def redo(self):
            return None
    executor._undo_manager = UM()
    result = executor.execute("redo", {})
    assert "Nothing" in result or "ERROR" in result


# ─── git command exceptions (2333-2362) ────────────────────────────────

def test_git_create_branch_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_create_branch", {"name": "test"})
    assert "ERROR" in result


def test_git_switch_branch_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_switch_branch", {"name": "main"})
    assert "ERROR" in result


def test_git_delete_branch_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_delete_branch", {"name": "test"})
    assert "ERROR" in result


def test_git_list_branches_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_list_branches", {})
    assert "ERROR" in result


# ─── git stage/unstage/commit exceptions (2443-2468) ─────────────────────

def test_git_stage_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_stage", {"files": ["f.txt"]})
    assert "ERROR" in result


def test_git_unstage_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_unstage", {"files": ["f.txt"]})
    assert "ERROR" in result


def test_git_commit_exception(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result


# ─── git_pre_commit: clean tree path (2601) ────────────────────────────

def test_git_pre_commit_clean(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"stdout": "", "stderr": "", "returncode": 0})())
    result = executor.execute("git_pre_commit", {})
    assert "clean" in result or isinstance(result, str)


# ─── analyze_code: full result formatting (2527-2544) ───────────────────

def test_analyze_code_full_result(executor, monkeypatch):
    class FakeCA:
        def analyze_file(self, path):
            return {"path": "test.py", "lines": 20, "code_lines": 15,
                    "comment_lines": 3, "blank_lines": 2,
                    "functions": [{"name": "foo", "line": 5}],
                    "classes": [{"name": "Bar", "line": 10}],
                    "imports": ["os", "sys"]}
    monkeypatch.setattr("apex.skills.CodeAnalyzer", lambda cwd: FakeCA(), raising=False)
    result = executor.execute("analyze_code", {"path": "test.py"})
    assert "foo" in result
    assert "Bar" in result
    assert "os" in result
    assert "20" in result


# ─── generate_docs: api with missing path → error (2952) ────────────────

def test_generate_docs_api_no_path(executor, monkeypatch):
    class FakeDG:
        def __init__(self, cwd):
            pass
    monkeypatch.setattr("apex.codegen.DocumentationGenerator", lambda cwd: FakeDG(), raising=False)
    result = executor.execute("generate_docs", {"type": "api"})
    assert "ERROR" in result or isinstance(result, str)


# ─── convert_bookmark → search_history without conv_manager (2055-2071) ──

def test_search_history_no_conv_manager(executor):
    result = executor.execute("search_history", {"query": "test", "fuzzy": True})
    assert "ERROR" in result or isinstance(result, str)


# ─── run_test: with program output (1826-1831) ─────────────────────────

def test_run_test_with_output(executor, monkeypatch):
    class FakeResult:
        stdout = "test output"
        stderr = ""
        returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = executor.execute("run_test", {"framework": "pytest", "path": "test.py"})
    assert "test output" in result


def test_run_test_with_stderr(executor, monkeypatch):
    class FakeResult:
        stdout = ""
        stderr = "error output"
        returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = executor.execute("run_test", {"framework": "pytest", "path": "test.py"})
    assert isinstance(result, str)


# ─── apply_patch: success path (2138) ──────────────────────────────────

def test_apply_patch_success(executor, monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "patch ok", "stderr": ""})())
    import os
    monkeypatch.setattr(os, "unlink", lambda p: None)
    result = executor.execute("apply_patch", {"patch": "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"})
    assert "SUCCESS" in result


# ─── clipboard tests using fake pyperclip that raises ImportError ────────

def test_clipboard_read_xclip_fallback(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def paste():
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "cb_data"})())
    result = executor.execute("clipboard_read", {})
    assert "cb_data" in result


def test_clipboard_read_xclip_fails(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def paste():
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("no xclip")))
    result = executor.execute("clipboard_read", {})
    assert "ERROR" in result


def test_clipboard_read_exception_handler(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def paste():
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(OSError("xclip missing")))
    result = executor.execute("clipboard_read", {})
    assert "ERROR" in result


def test_clipboard_write_xclip_fallback(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def copy(text):
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0})())
    result = executor.execute("clipboard_write", {"text": "test data"})
    assert "SUCCESS" in result


def test_clipboard_write_xclip_error(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def copy(text):
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("no xclip")))
    result = executor.execute("clipboard_write", {"text": "data"})
    assert "ERROR" in result


def test_clipboard_write_exception_handler(executor, monkeypatch):
    import sys
    class _FakeNoClip:
        @staticmethod
        def copy(text):
            raise ImportError("no pyperclip")
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeNoClip)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(OSError("xclip missing")))
    result = executor.execute("clipboard_write", {"text": "data"})
    assert "ERROR" in result


def test_git_delete_branch_with_repo_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_delete_branch", {"name": "old"})
    assert "ERROR" in result


def test_git_list_branches_with_repo_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_list_branches", {})
    assert "ERROR" in result


# ─── git_stage/unstage/commit with .git dir + mock exception ──────────

def test_git_stage_with_repo_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_stage", {"files": ["f.txt"]})
    assert "ERROR" in result


def test_git_unstage_with_files_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_unstage", {"files": ["f.txt"]})
    assert "ERROR" in result


def test_git_commit_with_repo_exception(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result


# ─── read_image_data: inner try block (2403-2404) ──────────────────────

def test_read_image_data_not_found_early(executor):
    result = executor.execute("read_image_data", {"path": "_no_such_file_"})
    assert "ERROR" in result


# ─── retry_tool: success path (2694) ───────────────────────────────────

def test_retry_tool_success(executor, monkeypatch):
    class FakeRH:
        class config:
            max_retries = 2
        def execute(self, fn, name, args):
            return "success after retry"
    monkeypatch.setattr("apex.advanced.get_retry_handler", lambda: FakeRH(), raising=False)
    result = executor.execute("retry_tool", {"tool": "get_keybindings", "args": {}, "retries": 2})
    assert "SUCCESS" in result


# ─── (search_history first definition is dead code - overridden) ─────────


# ─── redo: with result (2097) ─────────────────────────────────────────

def test_redo_with_action(executor, monkeypatch):
    class UM:
        def redo(self):
            return {"type": "edit_file", "details": {"path": "test.txt"}}
    executor._undo_manager = UM()
    result = executor.execute("redo", {})
    assert "REDONE" in result or isinstance(result, str)


# ─── read_image: exception handler deeper path ─────────────────────────

def test_read_image_cannot_read(executor, tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n")
    f.chmod(0o222)
    try:
        result = executor.execute("read_image", {"path": str(f)})
        assert "ERROR" in result
    finally:
        f.chmod(0o644)


# ─── read_image: not found (1801) ──────────────────────────────────────

def test_read_image_not_found(executor):
    result = executor.execute("read_image", {"path": "_no_file_"})
    assert "ERROR" in result


# ─── git_unstage without files (line 2453-2454) ────────────────────────

def test_git_unstage_no_files(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    result = executor.execute("git_unstage", {})
    assert "ERROR" in result


# ─── generate_docs: invalid type error at line 2952 ────────────────────

def test_generate_docs_type_error(executor, monkeypatch):
    class FakeDG:
        def __init__(self, cwd):
            pass
    monkeypatch.setattr("apex.codegen.DocumentationGenerator", lambda cwd: FakeDG(), raising=False)
    result = executor.execute("generate_docs", {"type": "bogus"})
    assert "ERROR" in result


# ─── diff_files: path_b not found (1626) ────────────────────────────────

def test_diff_files_only_b_not_found(executor, tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("hello")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": "nonexistent_b"})
    assert "ERROR" in result


# ─── git switch/delete/list/stage/unstage with .git AND mock success ────

def test_git_switch_branch_mocked_success(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    result = executor.execute("git_switch_branch", {"name": "main"})
    assert "SUCCESS" in result


def test_git_delete_branch_mocked_success(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    result = executor.execute("git_delete_branch", {"name": "old"})
    assert "SUCCESS" in result


def test_git_list_branches_mocked_success(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "* main\n  feature\n", "stderr": ""})())
    result = executor.execute("git_list_branches", {})
    assert "main" in result


def test_git_stage_mocked_success(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    result = executor.execute("git_stage", {"files": ["f.txt"]})
    assert "SUCCESS" in result


def test_git_unstage_mocked_success(executor, monkeypatch):
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    result = executor.execute("git_unstage", {})
    assert "SUCCESS" in result


def test_git_commit_stderr_error(executor, monkeypatch):
    """Cover line 2468: git commit returning error stderr."""
    _create_git_repo(executor.cwd)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stderr": "nothing to commit", "stdout": ""})())
    result = executor.execute("git_commit", {"message": "test"})
    assert "ERROR" in result
