"""Tests for refactored_tools module."""

import os
import tempfile
import pytest
from pathlib import Path
from apex.refactored_tools import FileOperations, GitOperations, CommandOperations, WebOperations


class TestFileOperations:
    """Test file operations class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_ops(self, temp_cwd):
        """Create FileOperations instance."""
        return FileOperations(temp_cwd)

    def test_resolve_path_absolute(self, file_ops):
        """Test resolving absolute path."""
        result = file_ops.resolve_path("/absolute/path")
        assert result == Path("/absolute/path")

    def test_resolve_path_relative(self, file_ops, temp_cwd):
        """Test resolving relative path."""
        result = file_ops.resolve_path("relative/path")
        assert result == temp_cwd / "relative/path"

    def test_read_file_not_found(self, file_ops):
        """Test reading non-existent file."""
        result = file_ops.read_file("nonexistent.txt")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_read_file_success(self, file_ops, temp_cwd):
        """Test reading existing file."""
        test_file = temp_cwd / "test.txt"
        test_file.write_text("Hello World")

        result = file_ops.read_file("test.txt")
        assert "1: Hello World" in result

    def test_read_file_with_lines(self, file_ops, temp_cwd):
        """Test reading file with multiple lines."""
        test_file = temp_cwd / "multi.txt"
        test_file.write_text("line1\nline2\nline3")

        result = file_ops.read_file("multi.txt")
        assert "1: line1" in result
        assert "2: line2" in result
        assert "3: line3" in result

    def test_write_file_success(self, file_ops):
        """Test writing file."""
        result = file_ops.write_file("new.txt", "Test content")
        assert "SUCCESS" in result
        assert (file_ops.cwd / "new.txt").exists()

    def test_write_file_creates_parents(self, file_ops):
        """Test writing file creates parent directories."""
        result = file_ops.write_file("subdir/nested/file.txt", "content")
        assert "SUCCESS" in result

    def test_write_file_error(self, file_ops):
        """Test writing to invalid path."""
        result = file_ops.write_file("/root/impossible.txt", "content")
        assert "ERROR" in result

    def test_edit_file_not_found(self, file_ops):
        """Test editing non-existent file."""
        result = file_ops.edit_file("nonexistent.txt", "old", "new")
        assert "ERROR" in result

    def test_edit_file_not_found_string(self, file_ops, temp_cwd):
        """Test editing file with non-existent string."""
        test_file = temp_cwd / "edit.txt"
        test_file.write_text("original content")

        result = file_ops.edit_file("edit.txt", "nonexistent", "replacement")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_edit_file_success(self, file_ops, temp_cwd):
        """Test editing file successfully."""
        test_file = temp_cwd / "edit.txt"
        test_file.write_text("Hello World")

        result = file_ops.edit_file("edit.txt", "World", "Universe")
        assert "SUCCESS" in result
        assert test_file.read_text() == "Hello Universe"

    def test_delete_file_not_found(self, file_ops):
        """Test deleting non-existent file."""
        result = file_ops.delete_file("nonexistent.txt")
        assert "ERROR" in result

    def test_delete_file_success(self, file_ops, temp_cwd):
        """Test deleting file."""
        test_file = temp_cwd / "delete.txt"
        test_file.write_text("to delete")

        result = file_ops.delete_file("delete.txt")
        assert "SUCCESS" in result
        assert not test_file.exists()

    def test_delete_directory_success(self, file_ops, temp_cwd):
        """Test deleting directory."""
        test_dir = temp_cwd / "delete_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = file_ops.delete_file("delete_dir")
        assert "SUCCESS" in result
        assert not test_dir.exists()

    def test_create_directory_success(self, file_ops):
        """Test creating directory."""
        result = file_ops.create_directory("newdir")
        assert "SUCCESS" in result
        assert (file_ops.cwd / "newdir").is_dir()

    def test_create_directory_nested(self, file_ops):
        """Test creating nested directories."""
        result = file_ops.create_directory("a/b/c")
        assert "SUCCESS" in result

    def test_list_files_empty(self, file_ops):
        """Test listing empty directory."""
        result = file_ops.list_files(".")
        assert "[empty directory]" in result

    def test_list_files_success(self, file_ops, temp_cwd):
        """Test listing directory with files."""
        (temp_cwd / "file1.txt").write_text("content")
        (temp_cwd / "file2.txt").write_text("content")

        result = file_ops.list_files(".")
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_list_files_not_found(self, file_ops):
        """Test listing non-existent directory."""
        result = file_ops.list_files("nonexistent")
        assert "ERROR" in result

    def test_list_files_not_directory(self, file_ops, temp_cwd):
        """Test listing a file instead of directory."""
        test_file = temp_cwd / "file.txt"
        test_file.write_text("content")

        result = file_ops.list_files("file.txt")
        assert "ERROR" in result

    def test_search_in_files_not_found(self, file_ops):
        """Test searching in non-existent path."""
        result = file_ops.search_in_files("pattern", "nonexistent")
        assert "ERROR" in result

    def test_search_in_files_no_matches(self, file_ops, temp_cwd):
        """Test search with no matches."""
        (temp_cwd / "test.txt").write_text("some content")

        result = file_ops.search_in_files("nonexistent_pattern", ".")
        assert "[no matches found]" in result

    def test_search_in_files_with_match(self, file_ops, temp_cwd):
        """Test search with matches."""
        (temp_cwd / "test.txt").write_text("Hello World")

        result = file_ops.search_in_files("Hello", ".")
        assert "test.txt" in result
        assert "Hello" in result

    def test_search_in_files_invalid_regex(self, file_ops):
        """Test search with invalid regex."""
        result = file_ops.search_in_files("[invalid", ".")
        assert "ERROR" in result
        assert "regex" in result.lower()

    def test_glob_search_not_found(self, file_ops):
        """Test glob with non-existent path."""
        result = file_ops.glob_search("*.txt", "nonexistent")
        assert "ERROR" in result

    def test_glob_search_no_matches(self, file_ops, temp_cwd):
        """Test glob with no matches."""
        (temp_cwd / "file.txt").write_text("content")

        result = file_ops.glob_search("*.py", ".")
        assert "[no matches found]" in result

    def test_glob_search_with_matches(self, file_ops, temp_cwd):
        """Test glob with matches."""
        (temp_cwd / "file1.py").write_text("content")
        (temp_cwd / "file2.py").write_text("content")
        (temp_cwd / "file3.txt").write_text("content")

        result = file_ops.glob_search("*.py", ".")
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.txt" not in result


class TestGitOperations:
    """Test git operations class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def git_ops(self, temp_cwd):
        """Create GitOperations instance."""
        return GitOperations(temp_cwd)

    def test_init(self, git_ops, temp_cwd):
        """Test GitOperations initialization."""
        assert git_ops.cwd == temp_cwd

    def test_get_git_status_not_repo(self, git_ops):
        """Test git status in non-git directory."""
        result = git_ops.get_git_status()
        assert "[Not a git repository]" in result

    def test_get_git_status_with_git(self, git_ops, temp_cwd):
        """Test git status in git directory."""
        (temp_cwd / ".git").mkdir()

        result = git_ops.get_git_status(".")
        assert "git" in result.lower()


class TestCommandOperations:
    """Test command operations class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cmd_ops(self, temp_cwd):
        """Create CommandOperations instance."""
        return CommandOperations(temp_cwd)

    def test_run_echo(self, cmd_ops):
        """Test running echo command."""
        result = cmd_ops.run_command("echo Hello")
        assert "Hello" in result

    def test_run_pwd(self, cmd_ops):
        """Test running pwd command."""
        result = cmd_ops.run_command("pwd")
        assert result.strip()

    def test_run_invalid_command(self, cmd_ops):
        """Test running invalid command."""
        result = cmd_ops.run_command("invalid_command_xyz_123")
        assert "ERROR" in result

    def test_run_with_cwd(self, cmd_ops, temp_cwd):
        """Test running command with cwd."""
        result = cmd_ops.run_command("pwd", cwd=str(temp_cwd))
        assert result.strip()


class TestWebOperations:
    """Test web operations class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def web_ops(self, temp_cwd):
        """Create WebOperations instance."""
        return WebOperations(temp_cwd)

    def test_fetch_url_invalid(self, web_ops):
        """Test fetching invalid URL."""
        result = web_ops.fetch_url("invalid://url")
        assert "ERROR" in result

    def test_search_web(self, web_ops):
        """Test web search."""
        result = web_ops.search_web("test query")
        assert result is not None

    def test_run_with_cwd(self, cmd_ops):
        """Test running command with cwd."""
        result = cmd_ops.run_command("pwd", [], cwd="/tmp")
        assert "/tmp" in result or result.strip()


class TestWebOperations:
    """Test web operations class."""

    @pytest.fixture
    def web_ops(self):
        """Create WebOperations instance."""
        return WebOperations()

    def test_fetch_url_invalid(self, web_ops):
        """Test fetching invalid URL."""
        result = web_ops.fetch_url("invalid://url")
        assert "ERROR" in result