"""Additional tests for tools.py - more tool functions."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from apex.tools import ToolExecutor


class TestToolExecutorGit:
    """Test git-related tool functions."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_get_git_status(self, executor, temp_cwd):
        """Test get_git_status tool."""
        result = executor.execute("get_git_status", {"path": str(temp_cwd)})
        assert isinstance(result, str)

    def test_execute_get_git_log(self, executor, temp_cwd):
        """Test get_git_log tool."""
        result = executor.execute("get_git_log", {"path": str(temp_cwd), "max_count": 5})
        assert isinstance(result, str)

    def test_execute_git_diff(self, executor, temp_cwd):
        """Test git_diff tool."""
        result = executor.execute("git_diff", {"path": str(temp_cwd)})
        assert isinstance(result, str)


class TestToolExecutorWeb:
    """Test web-related tool functions."""

    @pytest.fixture
    def executor(self, temp_cwd=None):
        if temp_cwd:
            return ToolExecutor(cwd=temp_cwd)
        return ToolExecutor(cwd=temp_path())

    def test_execute_web_search(self, executor):
        """Test web_search tool."""
        result = executor.execute("web_search", {"query": "python test"})
        assert isinstance(result, str)

    def test_execute_fetch_url(self, executor):
        """Test fetch_url tool."""
        result = executor.execute("fetch_url", {"url": "https://example.com"})
        assert isinstance(result, str)


class TestToolExecutorSearch:
    """Test search-related tool functions."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_search_in_files(self, executor, temp_cwd):
        """Test search_in_files tool."""
        (temp_cwd / "test.txt").write_text("hello world test")
        result = executor.execute("search_in_files", {
            "path": str(temp_cwd),
            "pattern": "hello"
        })
        assert isinstance(result, str)

    def test_execute_glob_search(self, executor, temp_cwd):
        """Test glob_search tool."""
        (temp_cwd / "test.py").write_text("# test")
        result = executor.execute("glob_search", {
            "path": str(temp_cwd),
            "pattern": "*.py"
        })
        assert isinstance(result, str)

    def test_execute_get_file_tree(self, executor, temp_cwd):
        """Test get_file_tree tool."""
        result = executor.execute("get_file_tree", {"path": str(temp_cwd)})
        assert isinstance(result, str)


class TestToolExecutorFileOps:
    """Test more file operations."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def executor(self, temp_cwd):
        return ToolExecutor(cwd=temp_cwd)

    def test_execute_diff_files(self, executor, temp_cwd):
        """Test diff_files tool."""
        f1 = temp_cwd / "f1.txt"
        f2 = temp_cwd / "f2.txt"
        f1.write_text("line1\nline2")
        f2.write_text("line1\nmodified")
        
        result = executor.execute("diff_files", {
            "file1": str(f1),
            "file2": str(f2)
        })
        assert isinstance(result, str)

    def test_execute_get_repo_map(self, executor, temp_cwd):
        """Test get_repo_map tool."""
        result = executor.execute("get_repo_map", {"path": str(temp_cwd)})
        assert isinstance(result, str)


class TestToolExecutorSystem:
    """Test system-related tools."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor(cwd=temp_path())

    @patch('subprocess.run')
    def test_execute_install_package(self, mock_run, executor):
        """Test install_package tool."""
        mock_run.return_value = MagicMock(returncode=0, stdout="installed", stderr="")
        result = executor.execute("install_package", {"package": "pytest"})
        assert isinstance(result, str)

    @patch('subprocess.run')
    def test_execute_run_test(self, mock_run, executor):
        """Test run_test tool."""
        mock_run.return_value = MagicMock(returncode=0, stdout="passed", stderr="")
        result = executor.execute("run_test", {"path": "tests/"})
        assert isinstance(result, str)


def temp_path():
    """Create temp path for tests."""
    import tempfile
    return Path(tempfile.gettempdir())