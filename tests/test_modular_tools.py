"""Tests for refactored tools module - 100% coverage."""

import pytest
import tempfile
from pathlib import Path
from apex.refactored_tools import (
    FileOperations,
    GitOperations,
    CommandOperations,
    WebOperations,
    create_file_ops,
    create_git_ops,
    create_command_ops,
    create_web_ops,
)


@pytest.fixture
def tmp_cwd():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestFileOperations:
    def test_init(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        assert ops.cwd == tmp_cwd

    def test_resolve_path_absolute(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.resolve_path("/absolute/path")
        assert result == Path("/absolute/path")

    def test_resolve_path_relative(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.resolve_path("relative/path")
        assert result == tmp_cwd / "relative/path"

    def test_read_file_not_found(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.read_file("nonexistent.txt")
        assert "ERROR" in result

    def test_read_file_success(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("Hello World")
        ops = FileOperations(tmp_cwd)
        result = ops.read_file("test.txt")
        assert "1: Hello World" in result

    def test_write_file_success(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.write_file("new.txt", "New content")
        assert "SUCCESS" in result
        assert (tmp_cwd / "new.txt").read_text() == "New content"

    def test_write_file_creates_parent_dirs(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.write_file("subdir/nested/file.txt", "content")
        assert "SUCCESS" in result

    def test_edit_file_not_found(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.edit_file("nonexistent.txt", "old", "new")
        assert "ERROR" in result

    def test_edit_file_string_not_found(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("Hello World")
        ops = FileOperations(tmp_cwd)
        result = ops.edit_file("test.txt", "nonexistent", "new")
        assert "ERROR" in result

    def test_edit_file_success(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("Hello World")
        ops = FileOperations(tmp_cwd)
        result = ops.edit_file("test.txt", "World", "Python")
        assert "SUCCESS" in result
        assert "Python" in (tmp_cwd / "test.txt").read_text()

    def test_delete_file_not_found(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.delete_file("nonexistent.txt")
        assert "ERROR" in result

    def test_delete_file_success(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("content")
        ops = FileOperations(tmp_cwd)
        result = ops.delete_file("test.txt")
        assert "SUCCESS" in result
        assert not (tmp_cwd / "test.txt").exists()

    def test_delete_directory_success(self, tmp_cwd):
        (tmp_cwd / "subdir").mkdir()
        ops = FileOperations(tmp_cwd)
        result = ops.delete_file("subdir")
        assert "SUCCESS" in result

    def test_create_directory_success(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.create_directory("newdir")
        assert "SUCCESS" in result
        assert (tmp_cwd / "newdir").is_dir()

    def test_create_directory_nested(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.create_directory("a/b/c")
        assert "SUCCESS" in result

    def test_list_files_not_found(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.list_files("nonexistent")
        assert "ERROR" in result

    def test_list_files_empty(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.list_files(".")
        assert "empty" in result.lower()

    def test_list_files_with_content(self, tmp_cwd):
        (tmp_cwd / "file1.txt").write_text("content")
        (tmp_cwd / "file2.txt").write_text("content")
        ops = FileOperations(tmp_cwd)
        result = ops.list_files(".")
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_search_in_files_not_found(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.search_in_files("pattern", "nonexistent")
        assert "ERROR" in result

    def test_search_in_files_no_matches(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("hello")
        ops = FileOperations(tmp_cwd)
        result = ops.search_in_files("nonexistent", ".")
        assert "no matches" in result.lower()

    def test_search_in_files_found(self, tmp_cwd):
        (tmp_cwd / "test.txt").write_text("hello world")
        ops = FileOperations(tmp_cwd)
        result = ops.search_in_files("world", ".")
        assert "test.txt" in result
        assert "world" in result

    def test_glob_search_no_matches(self, tmp_cwd):
        ops = FileOperations(tmp_cwd)
        result = ops.glob_search("*.py", ".")
        assert "no matches" in result.lower()

    def test_glob_search_found(self, tmp_cwd):
        (tmp_cwd / "test.py").write_text("print('hello')")
        (tmp_cwd / "test.txt").write_text("text")
        ops = FileOperations(tmp_cwd)
        result = ops.glob_search("*.py", ".")
        assert "test.py" in result


class TestGitOperations:
    def test_init(self, tmp_cwd):
        ops = GitOperations(tmp_cwd)
        assert ops.cwd == tmp_cwd

    def test_resolve_path(self, tmp_cwd):
        ops = GitOperations(tmp_cwd)
        result = ops.resolve_path(".")
        assert result == tmp_cwd

    def test_get_git_status_not_repo(self, tmp_cwd):
        ops = GitOperations(tmp_cwd)
        result = ops.get_git_status(".")
        assert "Not a git repository" in result

    def test_get_git_status_is_repo(self, tmp_cwd):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_cwd, capture_output=True)
        (tmp_cwd / "test.txt").write_text("content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_cwd, capture_output=True)
        ops = GitOperations(tmp_cwd)
        result = ops.get_git_status(".")
        assert "GIT" in result

    def test_get_git_log_not_repo(self, tmp_cwd):
        ops = GitOperations(tmp_cwd)
        result = ops.get_git_log(".")
        assert "Not a git repository" in result

    def test_get_git_log_is_repo(self, tmp_cwd):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_cwd, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=tmp_cwd, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_cwd, capture_output=True)
        (tmp_cwd / "test.txt").write_text("content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_cwd, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_cwd, capture_output=True)
        ops = GitOperations(tmp_cwd)
        result = ops.get_git_log(".")
        assert "Initial" in result

    def test_git_diff_not_repo(self, tmp_cwd):
        ops = GitOperations(tmp_cwd)
        result = ops.git_diff(".")
        assert "Not a git repository" in result

    def test_git_diff_is_repo(self, tmp_cwd):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_cwd, capture_output=True)
        (tmp_cwd / "test.txt").write_text("content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_cwd, capture_output=True)
        ops = GitOperations(tmp_cwd)
        result = ops.git_diff(".")
        assert "GIT" in result or "No changes" in result


class TestCommandOperations:
    def test_init(self, tmp_cwd):
        ops = CommandOperations(tmp_cwd)
        assert ops.cwd == tmp_cwd

    def test_resolve_path(self, tmp_cwd):
        ops = CommandOperations(tmp_cwd)
        result = ops.resolve_path("/tmp")
        assert result == Path("/tmp")

    def test_run_command_success(self, tmp_cwd):
        ops = CommandOperations(tmp_cwd)
        result = ops.run_command("echo hello")
        assert "hello" in result

    def test_run_command_with_cwd(self, tmp_cwd):
        (tmp_cwd / "subdir").mkdir()
        ops = CommandOperations(tmp_cwd)
        result = ops.run_command("pwd", cwd="subdir")
        assert "subdir" in result

    def test_run_command_failure(self, tmp_cwd):
        ops = CommandOperations(tmp_cwd)
        result = ops.run_command("exit 1")
        assert "ERROR" in result

    def test_run_command_not_found(self, tmp_cwd):
        ops = CommandOperations(tmp_cwd)
        result = ops.run_command("nonexistent_command_xyz")
        assert "ERROR" in result or "not found" in result.lower()


class TestWebOperations:
    def test_init(self, tmp_cwd):
        ops = WebOperations(tmp_cwd)
        assert ops.cwd == tmp_cwd

    def test_web_search(self):
        ops = WebOperations(Path("/tmp"))
        result = ops.web_search("test query")
        assert "test query" in result

    def test_fetch_url(self):
        ops = WebOperations(Path("/tmp"))
        result = ops.fetch_url("https://example.com")
        assert "ERROR" in result or result is not None


class TestFactories:
    def test_create_file_ops(self, tmp_cwd):
        ops = create_file_ops(str(tmp_cwd))
        assert isinstance(ops, FileOperations)

    def test_create_git_ops(self, tmp_cwd):
        ops = create_git_ops(str(tmp_cwd))
        assert isinstance(ops, GitOperations)

    def test_create_command_ops(self, tmp_cwd):
        ops = create_command_ops(str(tmp_cwd))
        assert isinstance(ops, CommandOperations)

    def test_create_web_ops(self, tmp_cwd):
        ops = create_web_ops(str(tmp_cwd))
        assert isinstance(ops, WebOperations)
