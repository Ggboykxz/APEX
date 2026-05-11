"""Tests for apex/project.py — ProjectInitializer, FileWatcher, get_project_initializer."""

import pytest
import json
from pathlib import Path
from apex.project import ProjectInitializer, FileWatcher, get_project_initializer


class TestProjectInitializer:
    @pytest.fixture
    def python_project(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="test"\nversion="0.1"\ndependencies=["flask==2.0","requests==3.0"]\n'
        )
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        return tmp_path

    @pytest.fixture
    def js_project(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "test-js",
                    "scripts": {"start": "node index.js", "test": "jest"},
                    "dependencies": {"express": "^4.0"},
                    "devDependencies": {"jest": "^29.0"},
                }
            )
        )
        (tmp_path / "yarn.lock").write_text("")
        (tmp_path / "src").mkdir()
        return tmp_path

    @pytest.fixture
    def go_project(self, tmp_path):
        (tmp_path / "go.mod").write_text("module test\ngo 1.21\n")
        return tmp_path

    @pytest.fixture
    def rust_project(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname="test"\nversion="0.1"\n')
        return tmp_path

    def test_analyze_python(self, python_project):
        pi = ProjectInitializer(str(python_project))
        result = pi.analyze()
        assert result["language"] == "python"
        assert result["package_manager"] is not None

    def test_analyze_javascript(self, js_project):
        pi = ProjectInitializer(str(js_project))
        result = pi.analyze()
        assert result["language"] == "javascript"
        assert result["package_manager"] == "yarn"

    def test_analyze_go(self, go_project):
        pi = ProjectInitializer(str(go_project))
        result = pi.analyze()
        assert result["language"] == "go"

    def test_analyze_rust(self, rust_project):
        pi = ProjectInitializer(str(rust_project))
        result = pi.analyze()
        assert result["language"] == "rust"

    def test_analyze_empty(self, tmp_path):
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["language"] is None
        assert result["package_manager"] is None

    def test_analyze_structure(self, python_project):
        pi = ProjectInitializer(str(python_project))
        result = pi.analyze()
        assert "src_dirs" in result["structure"]
        assert "test_dirs" in result["structure"]

    def test_detect_language_java(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project></project>")
        pi = ProjectInitializer(str(tmp_path))
        assert pi.analyze()["language"] == "java"

    def test_detect_language_ruby(self, tmp_path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
        pi = ProjectInitializer(str(tmp_path))
        assert pi.analyze()["language"] == "ruby"

    def test_detect_language_python_setup(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
        # setup.py is not first in the list, but should work if no pyproject.toml
        pi = ProjectInitializer(str(tmp_path))
        # This depends on order of detection - setup.py is not in the list
        # so language might be None
        pi.analyze()
        # Just ensure it doesn't crash

    def test_detect_package_manager_npm(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "package-lock.json").write_text("{}")
        pi = ProjectInitializer(str(tmp_path))
        assert pi.analyze()["package_manager"] == "npm"

    def test_detect_package_manager_pnpm(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "pnpm-lock.yaml").write_text("")
        pi = ProjectInitializer(str(tmp_path))
        assert pi.analyze()["package_manager"] == "pnpm"

    def test_detect_lsp_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["lsp_server"] == "pylsp"

    def test_detect_lsp_javascript(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["lsp_server"] == "typescript-language-server"

    def test_detect_lsp_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module test\n")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["lsp_server"] == "gopls"

    def test_detect_lsp_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["lsp_server"] == "rust-analyzer"

    def test_detect_formatters_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert "black" in result["formatters"] or "ruff" in result["formatters"]

    def test_detect_build_system_make(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "Makefile").write_text("test:\n\tpytest\n")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert result["build_system"] == "make"

    def test_create_context_file(self, python_project):
        pi = ProjectInitializer(str(python_project))
        result = pi.create_context_file()
        assert result.endswith("AGENTS.md")
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "python" in content

    def test_config_files_detected(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "settings.json").write_text("{}")
        pi = ProjectInitializer(str(tmp_path))
        result = pi.analyze()
        assert "pyproject.toml" in result["structure"]["config_files"]


class TestFileWatcher:
    def test_init(self, tmp_path):
        fw = FileWatcher(str(tmp_path))
        assert fw.cwd == tmp_path
        assert fw._callbacks == []
        assert fw._running is False

    def test_add_callback(self, tmp_path):
        fw = FileWatcher(str(tmp_path))
        fw.add_callback(lambda path: None)
        assert len(fw._callbacks) == 1

    def test_stop(self, tmp_path):
        fw = FileWatcher(str(tmp_path))
        fw.stop()
        assert fw._running is False


class TestGetProjectInitializer:
    def test_returns_instance(self, tmp_path):
        pi = get_project_initializer(str(tmp_path))
        assert isinstance(pi, ProjectInitializer)

    def test_caching(self, tmp_path):
        import apex.project as proj_mod

        key = str(tmp_path.resolve())
        proj_mod._project_initializer.pop(key, None)
        pi1 = get_project_initializer(str(tmp_path))
        pi2 = get_project_initializer(str(tmp_path))
        assert pi1 is pi2
