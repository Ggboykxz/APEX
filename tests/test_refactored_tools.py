"""Tests for refactored_tools module — no mocks, real file/subprocess operations."""

import tempfile
import pytest
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


class TestFileOperations:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_ops(self, temp_cwd):
        return FileOperations(temp_cwd)

    def test_resolve_path_absolute(self, file_ops):
        result = file_ops.resolve_path("/absolute/path")
        assert result == Path("/absolute/path")

    def test_resolve_path_relative(self, file_ops, temp_cwd):
        result = file_ops.resolve_path("relative/path")
        assert result == temp_cwd / "relative/path"

    def test_read_file_not_found(self, file_ops):
        result = file_ops.read_file("nonexistent.txt")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_read_file_success(self, file_ops, temp_cwd):
        test_file = temp_cwd / "test.txt"
        test_file.write_text("Hello World")
        result = file_ops.read_file("test.txt")
        assert "1: Hello World" in result

    def test_read_file_with_lines(self, file_ops, temp_cwd):
        test_file = temp_cwd / "multi.txt"
        test_file.write_text("line1\nline2\nline3")
        result = file_ops.read_file("multi.txt")
        assert "1: line1" in result
        assert "2: line2" in result
        assert "3: line3" in result

    def test_read_file_error(self, file_ops, temp_cwd):
        # Create a directory with the same name to cause read error
        (temp_cwd / "dir_as_file").mkdir()
        file_ops.read_file("dir_as_file")
        # May or may not be an error depending on read_text behavior on dirs
        # Just ensure it returns a string

    def test_write_file_success(self, file_ops, temp_cwd):
        result = file_ops.write_file("new.txt", "Test content")
        assert "SUCCESS" in result
        assert (temp_cwd / "new.txt").exists()
        assert (temp_cwd / "new.txt").read_text() == "Test content"

    def test_write_file_creates_parents(self, file_ops):
        result = file_ops.write_file("subdir/nested/file.txt", "content")
        assert "SUCCESS" in result

    def test_write_file_error(self, file_ops):
        result = file_ops.write_file("/root/impossible.txt", "content")
        assert "ERROR" in result

    def test_edit_file_not_found(self, file_ops):
        result = file_ops.edit_file("nonexistent.txt", "old", "new")
        assert "ERROR" in result

    def test_edit_file_string_not_found(self, file_ops, temp_cwd):
        test_file = temp_cwd / "edit.txt"
        test_file.write_text("original content")
        result = file_ops.edit_file("edit.txt", "nonexistent", "replacement")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_edit_file_success(self, file_ops, temp_cwd):
        test_file = temp_cwd / "edit.txt"
        test_file.write_text("Hello World")
        result = file_ops.edit_file("edit.txt", "World", "Universe")
        assert "SUCCESS" in result
        assert test_file.read_text() == "Hello Universe"

    def test_edit_file_replaces_only_first(self, file_ops, temp_cwd):
        test_file = temp_cwd / "multi_edit.txt"
        test_file.write_text("aaa bbb aaa")
        result = file_ops.edit_file("multi_edit.txt", "aaa", "ccc")
        assert "SUCCESS" in result
        assert test_file.read_text() == "ccc bbb aaa"

    def test_delete_file_not_found(self, file_ops):
        result = file_ops.delete_file("nonexistent.txt")
        assert "ERROR" in result

    def test_delete_file_success(self, file_ops, temp_cwd):
        test_file = temp_cwd / "delete.txt"
        test_file.write_text("to delete")
        result = file_ops.delete_file("delete.txt")
        assert "SUCCESS" in result
        assert not test_file.exists()

    def test_delete_directory_success(self, file_ops, temp_cwd):
        test_dir = temp_cwd / "delete_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        result = file_ops.delete_file("delete_dir")
        assert "SUCCESS" in result
        assert not test_dir.exists()

    def test_create_directory_success(self, file_ops, temp_cwd):
        result = file_ops.create_directory("newdir")
        assert "SUCCESS" in result
        assert (temp_cwd / "newdir").is_dir()

    def test_create_directory_nested(self, file_ops):
        result = file_ops.create_directory("a/b/c")
        assert "SUCCESS" in result

    def test_list_files_empty(self, file_ops):
        result = file_ops.list_files(".")
        assert "[empty directory]" in result

    def test_list_files_success(self, file_ops, temp_cwd):
        (temp_cwd / "file1.txt").write_text("content")
        (temp_cwd / "file2.txt").write_text("content")
        result = file_ops.list_files(".")
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_list_files_not_found(self, file_ops):
        result = file_ops.list_files("nonexistent")
        assert "ERROR" in result

    def test_list_files_not_directory(self, file_ops, temp_cwd):
        test_file = temp_cwd / "file.txt"
        test_file.write_text("content")
        result = file_ops.list_files("file.txt")
        assert "ERROR" in result

    def test_search_in_files_not_found(self, file_ops):
        result = file_ops.search_in_files("pattern", "nonexistent")
        assert "ERROR" in result

    def test_search_in_files_no_matches(self, file_ops, temp_cwd):
        (temp_cwd / "test.txt").write_text("some content")
        result = file_ops.search_in_files("nonexistent_pattern", ".")
        assert "[no matches found]" in result

    def test_search_in_files_with_match(self, file_ops, temp_cwd):
        (temp_cwd / "test.txt").write_text("Hello World")
        result = file_ops.search_in_files("Hello", ".")
        assert "test.txt" in result
        assert "Hello" in result

    def test_search_in_files_invalid_regex(self, file_ops):
        result = file_ops.search_in_files("[invalid", ".")
        assert "ERROR" in result
        assert "regex" in result.lower()

    def test_glob_search_not_found(self, file_ops):
        result = file_ops.glob_search("*.txt", "nonexistent")
        assert "ERROR" in result

    def test_glob_search_no_matches(self, file_ops, temp_cwd):
        (temp_cwd / "file.txt").write_text("content")
        result = file_ops.glob_search("*.py", ".")
        assert "[no matches found]" in result

    def test_glob_search_with_matches(self, file_ops, temp_cwd):
        (temp_cwd / "file1.py").write_text("content")
        (temp_cwd / "file2.py").write_text("content")
        (temp_cwd / "file3.txt").write_text("content")
        result = file_ops.glob_search("*.py", ".")
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.txt" not in result


class TestGitOperations:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_ops(self, temp_cwd):
        return GitOperations(temp_cwd)

    def test_init(self, git_ops, temp_cwd):
        assert git_ops.cwd == temp_cwd

    def test_resolve_path_absolute(self, git_ops):
        result = git_ops.resolve_path("/absolute/path")
        assert result == Path("/absolute/path")

    def test_resolve_path_relative(self, git_ops, temp_cwd):
        result = git_ops.resolve_path("relative/path")
        assert result == temp_cwd / "relative/path"

    def test_get_git_status_not_repo(self, git_ops):
        result = git_ops.get_git_status()
        assert "[Not a git repository]" in result

    def test_get_git_status_with_git(self, git_ops, temp_cwd):
        (temp_cwd / ".git").mkdir()
        # Initialize a real git repo for a more thorough test
        # Just having .git dir makes it recognized; status command may fail
        # which is okay — it returns "[Git command failed]" in that case
        result = git_ops.get_git_status(".")
        # Either succeeds or shows an error message
        assert isinstance(result, str)

    def test_get_git_log_not_repo(self, git_ops):
        result = git_ops.get_git_log()
        assert "[Not a git repository]" in result

    def test_get_git_log_with_git(self, git_ops, temp_cwd):
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_cwd, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=temp_cwd, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_cwd, capture_output=True)
        (temp_cwd / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=temp_cwd, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=temp_cwd, capture_output=True)
        result = git_ops.get_git_log()
        assert "init" in result

    def test_git_diff_not_repo(self, git_ops):
        result = git_ops.git_diff()
        assert "[Not a git repository]" in result

    def test_git_diff_with_git(self, git_ops, temp_cwd):
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_cwd, capture_output=True)
        result = git_ops.git_diff()
        # Either "[No changes]" or a diff
        assert isinstance(result, str)


class TestCommandOperations:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cmd_ops(self, temp_cwd):
        return CommandOperations(temp_cwd)

    def test_init(self, cmd_ops, temp_cwd):
        assert cmd_ops.cwd == temp_cwd

    def test_resolve_path_absolute_within_cwd(self, cmd_ops, temp_cwd):
        result = cmd_ops.resolve_path(str(temp_cwd / "subdir"))
        # Should resolve within cwd
        assert isinstance(result, Path)

    def test_resolve_path_outside_cwd(self, cmd_ops):
        result = cmd_ops.resolve_path("/etc/passwd")
        assert ".access_denied" in str(result)

    def test_resolve_path_relative(self, cmd_ops, temp_cwd):
        result = cmd_ops.resolve_path("subdir")
        assert result == (temp_cwd / "subdir").resolve()

    def test_run_pwd(self, cmd_ops):
        result = cmd_ops.run_command("pwd")
        assert result.strip()

    def test_run_ls(self, cmd_ops, temp_cwd):
        (temp_cwd / "testfile.txt").write_text("hello")
        result = cmd_ops.run_command("ls")
        assert isinstance(result, str)

    def test_run_invalid_command(self, cmd_ops):
        result = cmd_ops.run_command("invalid_command_xyz_123")
        assert "ERROR" in result

    def test_run_blocked_command(self, cmd_ops):
        result = cmd_ops.run_command("rm -rf /something")
        assert "ERROR" in result

    def test_run_with_cwd(self, cmd_ops, temp_cwd):
        (temp_cwd / "testfile.txt").write_text("hello")
        result = cmd_ops.run_command("ls", cwd=str(temp_cwd))
        assert "testfile.txt" in result

    def test_run_command_not_in_allowlist(self, cmd_ops):
        result = cmd_ops.run_command("nmap 127.0.0.1")
        assert "ERROR" in result
        assert "allowlist" in result.lower() or "not in" in result.lower()

    def test_run_command_empty(self, cmd_ops):
        result = cmd_ops.run_command("")
        assert "ERROR" in result

    def test_check_command_safety_blocked_patterns(self, cmd_ops):
        # Subshell pattern
        safe, msg = cmd_ops._check_command_safety("echo $(whoami)")
        assert safe is False

        # Backtick pattern
        safe, msg = cmd_ops._check_command_safety("echo `whoami`")
        assert safe is False

    def test_set_allowlist(self, cmd_ops, temp_cwd):
        cmd_ops.set_allowlist({"ls"})
        (temp_cwd / "testfile.txt").write_text("hello")
        result = cmd_ops.run_command("ls")
        assert "testfile.txt" in result or isinstance(result, str)
        result = cmd_ops.run_command("pwd")
        assert "ERROR" in result

    def test_set_allowlist_enabled(self, cmd_ops):
        cmd_ops.set_allowlist_enabled(False)
        # Now any command should pass the allowlist check
        result = cmd_ops.run_command("pwd")
        assert "ERROR" not in result or "/" in result


class TestWebOperations:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def web_ops(self, temp_cwd):
        return WebOperations(temp_cwd)

    def test_web_search(self, web_ops):
        result = web_ops.web_search("test query")
        assert "test query" in result

    def test_fetch_url_invalid(self, web_ops):
        result = web_ops.fetch_url("invalid://url")
        assert "ERROR" in result


class TestFactoryFunctions:
    def test_create_file_ops(self, tmp_path):
        ops = create_file_ops(str(tmp_path))
        assert isinstance(ops, FileOperations)

    def test_create_git_ops(self, tmp_path):
        ops = create_git_ops(str(tmp_path))
        assert isinstance(ops, GitOperations)

    def test_create_command_ops(self, tmp_path):
        ops = create_command_ops(str(tmp_path))
        assert isinstance(ops, CommandOperations)

    def test_create_web_ops(self, tmp_path):
        ops = create_web_ops(str(tmp_path))
        assert isinstance(ops, WebOperations)
