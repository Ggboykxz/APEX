"""Comprehensive tests for tools.py - ToolExecutor class."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from apex.tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS


class TestToolSchemas:
    """Test TOOL_SCHEMAS constant."""

    def test_schemas_not_empty(self):
        """Test TOOL_SCHEMAS is not empty."""
        assert len(TOOL_SCHEMAS) > 0

    def test_schemas_have_required_fields(self):
        """Test each schema has required fields."""
        for schema in TOOL_SCHEMAS:
            assert "type" in schema
            assert "function" in schema
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_has_read_file(self):
        """Test read_file tool exists."""
        names = [s["function"]["name"] for s in TOOL_SCHEMAS]
        assert "read_file" in names

    def test_has_write_file(self):
        """Test write_file tool exists."""
        names = [s["function"]["name"] for s in TOOL_SCHEMAS]
        assert "write_file" in names

    def test_has_edit_file(self):
        """Test edit_file tool exists."""
        names = [s["function"]["name"] for s in TOOL_SCHEMAS]
        assert "edit_file" in names

    def test_has_run_command(self):
        """Test run_command tool exists."""
        names = [s["function"]["name"] for s in TOOL_SCHEMAS]
        assert "run_command" in names


class TestToolExecutor:
    """Test ToolExecutor class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        """Create ToolExecutor instance."""
        return ToolExecutor(cwd=temp_cwd)

    def test_init_default(self):
        """Test default initialization."""
        executor = ToolExecutor()
        assert executor.cwd == Path.cwd()

    def test_init_custom_cwd(self, temp_cwd):
        """Test custom cwd initialization."""
        executor = ToolExecutor(cwd=temp_cwd)
        assert executor.cwd == temp_cwd

    def test_resolve_absolute(self, executor, temp_cwd):
        """Test resolving absolute path."""
        result = executor._resolve("/absolute/path")
        assert result == Path("/absolute/path")

    def test_resolve_relative(self, executor, temp_cwd):
        """Test resolving relative path."""
        result = executor._resolve("relative/path")
        assert result == temp_cwd / "relative/path"

    def test_execute_unknown_tool(self, executor):
        """Test executing unknown tool."""
        result = executor.execute("nonexistent_tool", {})
        assert "ERROR" in result
        assert "Unknown tool" in result

    def test_execute_read_file_success(self, executor, temp_cwd):
        """Test read_file with existing file."""
        test_file = temp_cwd / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        result = executor.execute("read_file", {"path": "test.txt"})
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_execute_read_file_not_found(self, executor):
        """Test read_file with missing file."""
        result = executor.execute("read_file", {"path": "nonexistent.txt"})
        assert "ERROR" in result
        assert "not found" in result

    def test_execute_write_file_success(self, executor, temp_cwd):
        """Test write_file success."""
        result = executor.execute("write_file", {"path": "new_file.txt", "content": "test content"})
        assert "SUCCESS" in result
        assert (temp_cwd / "new_file.txt").exists()

    def test_execute_write_file_nested(self, executor, temp_cwd):
        """Test write_file with nested path."""
        result = executor.execute("write_file", {"path": "dir1/dir2/file.txt", "content": "nested"})
        assert "SUCCESS" in result

    def test_execute_edit_file_success(self, executor, temp_cwd):
        """Test edit_file success."""
        test_file = temp_cwd / "edit_test.txt"
        test_file.write_text("hello world")

        result = executor.execute(
            "edit_file", {"path": "edit_test.txt", "old_string": "world", "new_string": "APEX"}
        )
        assert "SUCCESS" in result
        assert "APEX" in test_file.read_text()

    def test_execute_edit_file_not_found(self, executor):
        """Test edit_file with missing file."""
        result = executor.execute(
            "edit_file", {"path": "nonexistent.txt", "old_string": "old", "new_string": "new"}
        )
        assert "ERROR" in result

    def test_execute_edit_file_string_not_found(self, executor, temp_cwd):
        """Test edit_file when string not in file."""
        test_file = temp_cwd / "test.txt"
        test_file.write_text("original text")

        result = executor.execute(
            "edit_file", {"path": "test.txt", "old_string": "not in file", "new_string": "new"}
        )
        assert "ERROR" in result

    @patch("subprocess.run")
    def test_execute_run_command_success(self, mock_run, executor):
        """Test run_command success."""
        mock_result = MagicMock()
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = executor.execute("run_command", {"command": "echo hello"})
        assert "command output" in result

    @patch("subprocess.run")
    def test_execute_run_command_error(self, mock_run, executor):
        """Test run_command with error."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = executor.execute("run_command", {"command": "false"})
        assert "EXIT CODE: 1" in result


class TestToolExecutorFileOperations:
    """Test file operation tools."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        """Create ToolExecutor."""
        return ToolExecutor(cwd=temp_cwd)

    def test_delete_file(self, executor, temp_cwd):
        """Test delete_file tool."""
        test_file = temp_cwd / "to_delete.txt"
        test_file.write_text("delete me")

        result = executor.execute("delete_file", {"path": "to_delete.txt"})
        assert "SUCCESS" in result
        assert not test_file.exists()

    def test_create_directory(self, executor, temp_cwd):
        """Test create_directory tool."""
        result = executor.execute("create_directory", {"path": "new_dir"})
        assert "SUCCESS" in result
        assert (temp_cwd / "new_dir").is_dir()

    def test_list_files(self, executor, temp_cwd):
        """Test list_files tool."""
        (temp_cwd / "file1.txt").write_text("content")
        (temp_cwd / "file2.txt").write_text("content")

        result = executor.execute("list_files", {"path": "."})
        assert "file1.txt" in result
        assert "file2.txt" in result


class TestAsyncToolExecutor:
    """Test AsyncToolExecutor class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def async_executor(self, temp_cwd):
        """Create AsyncToolExecutor."""
        return AsyncToolExecutor(cwd=temp_cwd)

    def test_inherits_from_tool_executor(self, async_executor):
        """Test AsyncToolExecutor inherits from ToolExecutor."""
        assert isinstance(async_executor, ToolExecutor)

    @pytest.mark.asyncio
    async def test_execute_read_file(self, async_executor, temp_cwd):
        """Test async read_file."""
        test_file = temp_cwd / "async_test.txt"
        test_file.write_text("async content")

        result = await async_executor.execute_async("read_file", {"path": "async_test.txt"})
        assert "async content" in result
