"""Comprehensive tests for tools.py - file operations."""

import pytest
import tempfile
from pathlib import Path
from apex.tools import ToolExecutor


class TestFileOperations:
    """Test file operations in ToolExecutor."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_read_file(self, executor, temp_cwd):
        """Test read_file tool."""
        test_file = temp_cwd / "test.txt"
        test_file.write_text("line1\nline2\nline3")
        result = executor.execute("read_file", {"path": str(test_file)})
        assert "line1" in result

    def test_execute_read_file_not_found(self, executor, temp_cwd):
        """Test read_file with missing file."""
        result = executor.execute("read_file", {"path": str(temp_cwd / "nonexistent.txt")})
        assert "ERROR" in result

    def test_execute_write_file(self, executor, temp_cwd):
        """Test write_file tool."""
        result = executor.execute("write_file", {
            "path": str(temp_cwd / "new.txt"),
            "content": "test content"
        })
        assert "SUCCESS" in result

    def test_execute_write_file_nested(self, executor, temp_cwd):
        """Test write_file creates nested directories."""
        result = executor.execute("write_file", {
            "path": str(temp_cwd / "a" / "b" / "c.txt"),
            "content": "nested"
        })
        assert "SUCCESS" in result

    def test_execute_edit_file(self, executor, temp_cwd):
        """Test edit_file tool."""
        test_file = temp_cwd / "edit_test.txt"
        test_file.write_text("hello world")
        result = executor.execute("edit_file", {
            "path": str(test_file),
            "old_string": "world",
            "new_string": "APEX"
        })
        assert "SUCCESS" in result

    def test_execute_edit_file_not_found(self, executor, temp_cwd):
        """Test edit_file with missing string."""
        test_file = temp_cwd / "test.txt"
        test_file.write_text("hello")
        result = executor.execute("edit_file", {
            "path": str(test_file),
            "old_string": "nonexistent",
            "new_string": "new"
        })
        assert "ERROR" in result


class TestCommandExecution:
    """Test command execution in ToolExecutor."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_run_command(self, executor, temp_cwd):
        """Test run_command tool."""
        result = executor.execute("run_command", {"command": "echo hello"})
        assert "hello" in result

    def test_execute_run_command_cd(self, executor, temp_cwd):
        """Test run_command with cd."""
        result = executor.execute("run_command", {"command": "pwd"})
        assert str(temp_cwd) in result or "tmp" in result


class TestSearchOperations:
    """Test search operations in ToolExecutor."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_search_in_files(self, executor, temp_cwd):
        """Test search_in_files tool."""
        (temp_cwd / "test.txt").write_text("hello world search test")
        result = executor.execute("search_in_files", {
            "path": str(temp_cwd),
            "pattern": "hello"
        })
        assert "test.txt" in result

    def test_execute_glob_search(self, executor, temp_cwd):
        """Test glob_search tool."""
        (temp_cwd / "test.py").write_text("# python")
        (temp_cwd / "test.txt").write_text("text")
        result = executor.execute("glob_search", {
            "path": str(temp_cwd),
            "pattern": "*.py"
        })
        assert "test.py" in result

    def test_execute_get_file_tree(self, executor, temp_cwd):
        """Test get_file_tree tool."""
        (temp_cwd / "sub" / "file.txt").parent.mkdir()
        (temp_cwd / "sub" / "file.txt").write_text("test")
        result = executor.execute("get_file_tree", {"path": str(temp_cwd)})
        assert isinstance(result, str)


class TestUnknownTool:
    """Test unknown tool handling."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_execute_unknown_tool(self, executor):
        """Test unknown tool returns error."""
        result = executor.execute("nonexistent_tool", {})
        assert "ERROR" in result
        assert "Unknown tool" in result


class TestToolExecutorPathResolution:
    """Test path resolution in ToolExecutor."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_resolve_absolute_path(self, executor, temp_cwd):
        """Test resolving absolute path."""
        test_file = temp_cwd / "absolute.txt"
        test_file.write_text("test")
        result = executor.execute("read_file", {"path": str(test_file)})
        assert "test" in result