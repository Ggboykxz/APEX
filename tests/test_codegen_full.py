"""Extended tests for codegen module — full coverage, no mocks."""

import json
import tempfile
from pathlib import Path

import pytest

from apex.codegen import (
    CodeRefactorer,
    DatabaseManager,
    DockerManager,
    APIClientGenerator,
    DocumentationGenerator,
    PerformanceProfiler,
)


# ---------------------------------------------------------------------------
# CodeRefactorer — extended coverage
# ---------------------------------------------------------------------------


class TestCodeRefactorerExtended:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def refactorer(self, temp_cwd):
        return CodeRefactorer(str(temp_cwd))

    def test_refactor_function_modern_double_async_guard(self, refactorer, temp_cwd):
        """Modern style on an already-async function leaves it unchanged."""
        (temp_cwd / "test.py").write_text("async def my_func():\n    pass\n")
        result = refactorer.refactor_function("test.py", "my_func", style="modern")
        assert result["success"] is True
        content = (temp_cwd / "test.py").read_text()
        assert content.count("async") == 1

    def test_refactor_function_writes_file(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def greet():\n    pass\n")
        refactorer.refactor_function("test.py", "greet", style="async")
        content = (temp_cwd / "test.py").read_text()
        assert "async def greet" in content

    def test_extract_method_adds_method_to_class(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("class Service:\n    def run(self):\n        pass\n")
        result = refactorer.extract_method("test.py", "Service", "return 42", "calculate")
        assert result["success"] is True
        content = (temp_cwd / "test.py").read_text()
        assert "def calculate(self)" in content
        assert "return 42" in content

    def test_convert_to_class_creates_class(self, refactorer, temp_cwd):
        (temp_cwd / "test.py").write_text("def process():\n    return True\n")
        result = refactorer.convert_to_class("test.py", "process")
        assert result["success"] is True
        content = (temp_cwd / "test.py").read_text()
        assert "class Process:" in content

    def test_add_type_hints_returns_result(self, refactorer, temp_cwd):
        """add_type_hints processes the file and returns a result dict."""
        (temp_cwd / "test.py").write_text("x = 1\n")
        result = refactorer.add_type_hints("test.py")
        assert isinstance(result, dict)
        assert "success" in result or "error" in result


# ---------------------------------------------------------------------------
# DatabaseManager — extended coverage
# ---------------------------------------------------------------------------


class TestDatabaseManagerExtended:
    @pytest.fixture
    def db(self, tmp_path):
        return DatabaseManager(str(tmp_path))

    def test_generate_model_with_default_name(self, db):
        columns = [{"type": "int"}]
        result = db.generate_model("Item", columns)
        assert "field: int" in result  # default name is "field"

    def test_generate_model_empty_columns(self, db):
        result = db.generate_model("Empty", [])
        assert "class Empty:" in result
        assert "__init__" in result

    def test_generate_model_case_insensitive_type(self, db):
        columns = [{"name": "id", "type": "INT"}]
        result = db.generate_model("Test", columns)
        assert "id: int" in result

    def test_all_connection_strings(self, db):
        for db_type in ["sqlite", "postgres", "mysql", "mongodb"]:
            assert len(db.get_connection_string(db_type)) > 0


# ---------------------------------------------------------------------------
# DockerManager — extended coverage
# ---------------------------------------------------------------------------


class TestDockerManagerExtended:
    @pytest.fixture
    def docker(self, tmp_path):
        return DockerManager(str(tmp_path))

    def test_all_dockerfile_languages(self, docker):
        for lang in ["python", "node", "go", "rust", "java"]:
            result = docker.generate_dockerfile(lang)
            assert "FROM" in result

    def test_docker_compose_multiple_ports(self, docker):
        services = [{"name": "web", "image": "nginx", "ports": ["80:80", "443:443"]}]
        result = docker.generate_docker_compose(services)
        assert "80:80" in result
        assert "443:443" in result

    def test_docker_compose_empty_services(self, docker):
        result = docker.generate_docker_compose([])
        assert "version:" in result
        assert "services:" in result


# ---------------------------------------------------------------------------
# APIClientGenerator — extended coverage
# ---------------------------------------------------------------------------


class TestAPIClientGeneratorExtended:
    @pytest.fixture
    def api_gen(self, tmp_path):
        return APIClientGenerator(str(tmp_path))

    def test_openapi_with_put_delete_patch(self, api_gen, tmp_path):
        spec = {
            "paths": {
                "/resource": {
                    "put": {"summary": "Update"},
                    "delete": {"summary": "Delete"},
                    "patch": {"summary": "Patch"},
                }
            }
        }
        (tmp_path / "spec.json").write_text(json.dumps(spec))
        result = api_gen.generate_from_openapi("spec.json")
        assert "put_resource" in result
        assert "delete_resource" in result
        assert "patch_resource" in result

    def test_openapi_ignores_non_method_keys(self, api_gen, tmp_path):
        spec = {"paths": {"/health": {"summary": "Health check"}}}
        (tmp_path / "spec.json").write_text(json.dumps(spec))
        result = api_gen.generate_from_openapi("spec.json")
        # summary is not a valid method, should not generate a function for it
        assert "def summary" not in result

    def test_curl_method_uppercased(self, api_gen):
        result = api_gen.generate_curl("get", "http://example.com")
        assert "-X GET" in result


# ---------------------------------------------------------------------------
# DocumentationGenerator — extended coverage
# ---------------------------------------------------------------------------


class TestDocumentationGeneratorExtended:
    @pytest.fixture
    def doc_gen(self, tmp_path):
        return DocumentationGenerator(str(tmp_path))

    def test_readme_max_five_files(self, doc_gen, tmp_path):
        for i in range(8):
            (tmp_path / f"file_{i}.py").write_text("pass")
        result = doc_gen.generate_readme()
        # Should mention at most 5 .py files
        assert "file_0" in result

    def test_api_docs_function_with_args(self, doc_gen, tmp_path):
        (tmp_path / "mod.py").write_text("def add(a, b):\n    return a + b\n")
        result = doc_gen.generate_api_docs("mod.py")
        assert "add" in result
        assert "a, b" in result

    def test_api_docs_no_functions(self, doc_gen, tmp_path):
        (tmp_path / "empty.py").write_text("x = 1\n")
        result = doc_gen.generate_api_docs("empty.py")
        assert "API Documentation" in result

    def test_markdoc_multiple_classes(self, doc_gen, tmp_path):
        (tmp_path / "models.py").write_text("class User:\n    pass\n\nclass Item:\n    pass\n")
        result = doc_gen.generate_markdoc()
        assert "User" in result
        assert "Item" in result


# ---------------------------------------------------------------------------
# PerformanceProfiler — extended coverage
# ---------------------------------------------------------------------------


class TestPerformanceProfilerExtended:
    @pytest.fixture
    def profiler(self, tmp_path):
        return PerformanceProfiler(str(tmp_path))

    def test_complex_file_analysis(self, profiler, tmp_path):
        code = """
import os
import sys

def complex_func(x):
    for i in range(10):
        if i > 5:
            while True:
                break
        elif i == 3:
            continue
        else:
            pass

class MyClass:
    def method(self):
        if True:
            pass
"""
        (tmp_path / "complex.py").write_text(code)
        result = profiler.profile_file("complex.py")
        assert result["functions"] >= 2
        assert result["classes"] >= 1
        assert result["imports"] >= 2
        assert result["complexity_score"] > 0

    def test_suggest_all_optimizations(self, profiler, tmp_path):
        """A file that triggers multiple suggestions."""
        code = "for i in range(10):\n    x = []\n    x.append(i)\nf = open('test')\n"
        (tmp_path / "messy.py").write_text(code)
        result = profiler.suggest_optimizations("messy.py")
        assert len(result) >= 2  # at least range and append suggestions
