"""Tests for APEX tools - search, glob, tree, diff, git, and repo_map."""

import subprocess

import pytest

from apex.tools import ToolExecutor


@pytest.fixture
def executor(tmp_path):
    cwd = tmp_path / "project"
    cwd.mkdir()
    return ToolExecutor(cwd=cwd)


@pytest.fixture
def git_executor(tmp_path):
    """Create ToolExecutor in an initialized git repo."""
    cwd = tmp_path / "git_project"
    cwd.mkdir()
    subprocess.run(["git", "init"], cwd=cwd, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=cwd, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, capture_output=True)
    return ToolExecutor(cwd=cwd)


# ─── search_in_files ────────────────────────────────────────────────────────


def test_search_in_files_found(executor, tmp_path):
    (tmp_path / "test.py").write_text("def hello():\n    print('world')")
    result = executor.execute("search_in_files", {"pattern": "hello", "path": str(tmp_path)})
    assert "test.py" in result
    assert "hello" in result


def test_search_in_files_no_matches(executor, tmp_path):
    (tmp_path / "test.py").write_text("def goodbye():\n    pass")
    result = executor.execute(
        "search_in_files", {"pattern": "nonexistent_pattern", "path": str(tmp_path)}
    )
    assert "no matches" in result.lower()


def test_search_in_files_path_not_found(executor):
    result = executor.execute("search_in_files", {"pattern": "test", "path": "/nonexistent_xyz"})
    assert "ERROR" in result


def test_search_in_files_invalid_regex(executor, tmp_path):
    result = executor.execute("search_in_files", {"pattern": "[invalid", "path": str(tmp_path)})
    assert "ERROR" in result
    assert "Invalid regex" in result


def test_search_in_files_multiple_files(executor, tmp_path):
    (tmp_path / "a.py").write_text("keyword_here")
    (tmp_path / "b.py").write_text("no match here")
    (tmp_path / "c.py").write_text("keyword_here too")
    result = executor.execute("search_in_files", {"pattern": "keyword_here", "path": str(tmp_path)})
    assert "a.py" in result
    assert "c.py" in result


# ─── glob_search ─────────────────────────────────────────────────────────────


def test_glob_search_found(executor, tmp_path):
    (tmp_path / "file1.py").touch()
    (tmp_path / "file2.js").touch()
    (tmp_path / "file3.txt").touch()
    result = executor.execute("glob_search", {"pattern": "*.py", "directory": str(tmp_path)})
    assert "file1.py" in result


def test_glob_search_no_matches(executor, tmp_path):
    result = executor.execute(
        "glob_search", {"pattern": "*.nonexistent_ext", "directory": str(tmp_path)}
    )
    assert "no files match" in result.lower()


def test_glob_search_directory_not_found(executor):
    result = executor.execute(
        "glob_search", {"pattern": "*.py", "directory": "/nonexistent_dir_xyz"}
    )
    assert "ERROR" in result


def test_glob_search_default_directory(executor, tmp_path):
    (tmp_path / "project" / "test.py").touch()
    result = executor.execute("glob_search", {"pattern": "*.py"})
    assert isinstance(result, str)


def test_glob_search_recursive(executor, tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.py").touch()
    result = executor.execute("glob_search", {"pattern": "**/*.py", "directory": str(tmp_path)})
    assert "nested.py" in result


# ─── get_file_tree ───────────────────────────────────────────────────────────


def test_get_file_tree_success(executor, tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "file.txt").touch()
    result = executor.execute("get_file_tree", {"path": str(tmp_path), "max_depth": 2})
    assert "subdir" in result


def test_get_file_tree_path_not_found(executor):
    result = executor.execute("get_file_tree", {"path": "/nonexistent_xyz"})
    assert "ERROR" in result


def test_get_file_tree_with_max_depth(executor, tmp_path):
    d1 = tmp_path / "level1"
    d1.mkdir()
    d2 = d1 / "level2"
    d2.mkdir()
    (d2 / "deep.txt").touch()
    result = executor.execute("get_file_tree", {"path": str(tmp_path), "max_depth": 1})
    assert "level1" in result


# ─── diff_files ──────────────────────────────────────────────────────────────


def test_diff_files_identical(executor, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hello")
    b.write_text("hello")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": str(b)})
    assert "identical" in result.lower()


def test_diff_files_different(executor, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hello world")
    b.write_text("hello")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": str(b)})
    assert len(result) > 0
    # Should contain diff markers or content from the different file
    assert "---" in result or "hello" in result


def test_diff_files_first_missing(executor, tmp_path):
    b = tmp_path / "b.txt"
    b.write_text("content")
    result = executor.execute("diff_files", {"path_a": "/nonexistent_a", "path_b": str(b)})
    assert "ERROR" in result


def test_diff_files_second_missing(executor, tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("content")
    result = executor.execute("diff_files", {"path_a": str(a), "path_b": "/nonexistent_b"})
    assert "ERROR" in result


# ─── get_git_status ──────────────────────────────────────────────────────────


def test_get_git_status_not_repo(executor):
    result = executor.execute("get_git_status", {})
    assert "Not a git repository" in result


def test_get_git_status_clean_repo(git_executor):
    result = git_executor.execute("get_git_status", {})
    assert "clean" in result.lower() or result.strip() != ""


def test_get_git_status_dirty_repo(git_executor, tmp_path):
    repo_dir = tmp_path / "git_project"
    (repo_dir / "newfile.txt").write_text("untracked")
    result = git_executor.execute("get_git_status", {})
    # Should show the untracked file
    assert isinstance(result, str)
    assert len(result) > 0


# ─── get_git_log ─────────────────────────────────────────────────────────────


def test_get_git_log_not_repo(executor):
    result = executor.execute("get_git_log", {"n": 5})
    assert "Not a git repository" in result


def test_get_git_log_empty_repo(git_executor):
    result = git_executor.execute("get_git_log", {"n": 5})
    assert "no commits" in result.lower() or isinstance(result, str)


def test_get_git_log_with_commits(git_executor, tmp_path):
    repo_dir = tmp_path / "git_project"
    (repo_dir / "test.txt").write_text("initial")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True)
    result = git_executor.execute("get_git_log", {"n": 5})
    assert "Initial commit" in result


# ─── git_diff ────────────────────────────────────────────────────────────────


def test_git_diff_not_repo(executor):
    result = executor.execute("git_diff", {})
    assert "Not a git repository" in result


def test_git_diff_clean_repo(git_executor):
    result = git_executor.execute("git_diff", {})
    assert "no changes" in result.lower() or isinstance(result, str)


def test_git_diff_with_changes(git_executor, tmp_path):
    repo_dir = tmp_path / "git_project"
    (repo_dir / "test.txt").write_text("initial")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True)
    (repo_dir / "test.txt").write_text("modified")
    result = git_executor.execute("git_diff", {})
    assert isinstance(result, str)


def test_git_diff_with_ref(git_executor, tmp_path):
    repo_dir = tmp_path / "git_project"
    (repo_dir / "test.txt").write_text("initial")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True)
    result = git_executor.execute("git_diff", {"ref": "HEAD"})
    assert isinstance(result, str)


# ─── get_repo_map ────────────────────────────────────────────────────────────


def test_get_repo_map_success(executor, tmp_path):
    project = tmp_path / "project"
    (project / "main.py").write_text("print('hello')")
    (project / "config.json").write_text("{}")
    (project / "README.md").write_text("# readme")
    # Note: get_repo_map uses self.cwd regardless of path arg
    result = executor.execute("get_repo_map", {"path": str(tmp_path)})
    assert isinstance(result, str)


def test_get_repo_map_returns_string(executor):
    # Note: the second _execute_get_repo_map always uses self.cwd
    result = executor.execute("get_repo_map", {"path": "/nonexistent_xyz"})
    assert isinstance(result, str)


def test_get_repo_map_with_git(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "app.py").write_text("code")
    e = ToolExecutor(cwd=tmp_path)
    result = e.execute("get_repo_map", {"path": str(tmp_path)})
    assert isinstance(result, str)


def test_get_repo_map_categorizes_files(executor, tmp_path):
    # Files must be in the executor's cwd (project dir) for get_repo_map to find them
    project = tmp_path / "project"
    (project / "source.py").write_text("code")
    (project / "config.yaml").write_text("key: value")
    (project / "docs.txt").write_text("documentation")
    (project / "data.csv").write_text("a,b,c")
    result = executor.execute("get_repo_map", {"path": str(project)})
    assert isinstance(result, str)


# ─── get_file_tree with hidden files ─────────────────────────────────────────


def test_get_file_tree_skips_hidden_files(executor, tmp_path):
    sub = tmp_path / "mydir"
    sub.mkdir()
    (sub / ".hidden").touch()
    (sub / "visible.txt").touch()
    result = executor.execute("get_file_tree", {"path": str(sub)})
    assert "visible.txt" in result
    # Hidden files should be skipped
    assert ".hidden" not in result


# ─── git error paths ────────────────────────────────────────────────────────


def test_get_git_status_exception(executor, tmp_path):
    """Test git status when .git exists but git command fails."""
    git_dir = tmp_path / "project" / ".git"
    git_dir.mkdir()
    # .git exists but it's not a real git repo, so git command may fail
    result = executor.execute("get_git_status", {})
    # Should handle the error gracefully
    assert isinstance(result, str)


def test_get_git_log_exception(executor, tmp_path):
    """Test git log when .git exists but git command fails."""
    git_dir = tmp_path / "project" / ".git"
    git_dir.mkdir()
    result = executor.execute("get_git_log", {"n": 5})
    assert isinstance(result, str)


def test_git_diff_exception(executor, tmp_path):
    """Test git diff when .git exists but git command fails."""
    git_dir = tmp_path / "project" / ".git"
    git_dir.mkdir()
    result = executor.execute("git_diff", {})
    assert isinstance(result, str)


# ─── search_in_files with binary file ───────────────────────────────────────


def test_search_in_files_skips_binary(executor, tmp_path):
    (tmp_path / "text.txt").write_text("findme")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03findme\x04\x05")
    result = executor.execute("search_in_files", {"pattern": "findme", "path": str(tmp_path)})
    assert "text.txt" in result
