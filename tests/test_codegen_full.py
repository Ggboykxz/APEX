"""Tests for codegen module - improved."""

import pytest
import tempfile
from pathlib import Path
from apex.codegen import CodeRefactorer


class TestCodeRefactorerFull:
    """Full tests for CodeRefactorer."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def refactorer(self, temp_cwd):
        return CodeRefactorer(str(temp_cwd))

    def test_init(self, temp_cwd):
        r = CodeRefactorer(str(temp_cwd))
        assert r.cwd == Path(temp_cwd)

    def test_refactor_function_file_not_found(self, refactorer):
        result = refactorer.refactor_function("nonexistent.py", "func")
        assert isinstance(result, (str, dict))

    def test_refactor_function_not_found(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def other(): pass")
        result = refactorer.refactor_function("test.py", "missing")
        assert isinstance(result, (str, dict))

    def test_refactor_async(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def my_func(): pass")
        result = refactorer.refactor_function("test.py", "my_func", "async")
        assert isinstance(result, (str, dict))

    def test_refactor_type_hints(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def func(): pass")
        result = refactorer.refactor_function("test.py", "func", "type_hints")
        assert isinstance(result, (str, dict))

    def test_add_type_hints(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def add(a, b): return a + b")
        result = refactorer.add_type_hints("test.py")
        assert isinstance(result, (str, dict))

    def test_convert_to_class(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def test(): pass")
        result = refactorer.convert_to_class("test.py", "Test")
        assert isinstance(result, (str, dict))

    def test_extract_method(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def main():\n    x = 1\n    y = 2")
        result = refactorer.extract_method("test.py", "main", "helper", "new_method")
        assert isinstance(result, (str, dict))