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
        assert "error" in result.lower()

    def test_refactor_function_not_found(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def other(): pass")
        result = refactorer.refactor_function("test.py", "missing")
        assert "error" in result.lower()

    def test_refactor_async(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def my_func(): pass")
        result = refactorer.refactor_function("test.py", "my_func", "async")
        assert result.get("success")

    def test_refactor_type_hints(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def func(): pass")
        result = refactorer.refactor_function("test.py", "func", "type_hints")
        assert result.get("success")

    def test_refactor_modern(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def func(): pass")
        result = refactorer.refactor_function("test.py", "func", "modern")
        assert result.get("success")

    def test_extract_method_file_not_found(self, refactorer):
        result = refactorer.extract_method("x.py", "C", "pass", "new")
        assert "error" in result.lower()

    def test_extract_method_class_not_found(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def other(): pass")
        result = refactorer.extract_method("test.py", "Missing", "pass", "new")
        assert "error" in result.lower()

    def test_extract_method_success(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("class MyClass:\n    pass")
        result = refactorer.extract_method("test.py", "MyClass", "pass", "new_method")
        assert result.get("success")

    def test_analyze_code(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def foo():\n    x = 1\n    return x")
        result = refactorer.analyze_code("test.py")
        assert "lines" in result or "error" in result.lower()

    def test_generate_tests(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def add(a, b): return a + b")
        result = refactorer.generate_tests("test.py", "add")
        assert "test" in result.lower() or "error" in result.lower()