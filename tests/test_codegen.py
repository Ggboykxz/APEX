"""Tests for codegen module."""

import pytest
import tempfile
from pathlib import Path
from apex.codegen import CodeRefactorer


class TestCodeRefactorer:
    """Test CodeRefactorer class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def refactorer(self, temp_cwd):
        """Create CodeRefactorer instance."""
        return CodeRefactorer(temp_cwd)

    def test_init(self, temp_cwd):
        """Test initialization."""
        refactorer = CodeRefactorer(temp_cwd)
        assert refactorer.cwd == Path(temp_cwd)

    def test_refactor_function_file_not_found(self, refactorer):
        """Test refactor_function with missing file."""
        result = refactorer.refactor_function("nonexistent.py", "test_func")
        assert "error" in result

    def test_refactor_function_function_not_found(self, refactorer, temp_cwd):
        """Test refactor_function with missing function."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("def other_func():\n    pass\n")
        
        result = refactorer.refactor_function("test.py", "test_func")
        assert "error" in result

    def test_refactor_function_async_style(self, refactorer, temp_cwd):
        """Test refactor_function with async style."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("def my_func():\n    pass\n")
        
        result = refactorer.refactor_function("test.py", "my_func", style="async")
        assert result.get("success") is True

    def test_refactor_function_type_hints_style(self, refactorer, temp_cwd):
        """Test refactor_function with type_hints style."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("def my_func():\n    pass\n")
        
        result = refactorer.refactor_function("test.py", "my_func", style="type_hints")
        assert result.get("success") is True

    def test_refactor_function_modern_style(self, refactorer, temp_cwd):
        """Test refactor_function with modern style."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("def my_func():\n    pass\n")
        
        result = refactorer.refactor_function("test.py", "my_func", style="modern")
        assert result.get("success") is True

    def test_extract_method_file_not_found(self, refactorer):
        """Test extract_method with missing file."""
        result = refactorer.extract_method("nonexistent.py", "TestClass", "pass", "new_method")
        assert "error" in result

    def test_extract_method_class_not_found(self, refactorer, temp_cwd):
        """Test extract_method with missing class."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("def other_func():\n    pass\n")
        
        result = refactorer.extract_method("test.py", "TestClass", "pass", "new_method")
        assert "error" in result

    def test_extract_method_success(self, refactorer, temp_cwd):
        """Test extract_method success."""
        test_file = Path(temp_cwd) / "test.py"
        test_file.write_text("class TestClass:\n    pass\n")
        
        result = refactorer.extract_method("test.py", "TestClass", "pass", "new_method")
        assert result.get("success") is True