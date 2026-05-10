"""Tests for refactored context module."""

from pathlib import Path
from unittest.mock import MagicMock

from apex.refactored_context import (
    ContextBuilder,
    get_repo_map,
    get_git_info,
    get_language_stats,
    generate_ctags,
    create_context_builder,
)


class TestContextBuilder:
    def test_init_with_path(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        assert builder.path == tmp_path

    def test_init_without_path(self):
        builder = ContextBuilder()
        assert builder.path == Path.cwd()

    def test_get_repo_map_not_exists(self):
        builder = ContextBuilder(Path("/nonexistent/path"))
        result = builder.get_repo_map()
        assert "ERROR" in result

    def test_get_repo_map_empty_dir(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()

        assert f"Repository: {tmp_path.name}" in result

    def test_get_repo_map_with_subdirs(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()

        assert "src/" in result
        assert "tests/" in result

    def test_get_repo_map_with_source_files(self, tmp_path):
        (tmp_path / "main.py").touch()
        (tmp_path / "app.py").touch()

        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()

        assert "SOURCE FILES" in result
        assert "main.py" in result
        assert "app.py" in result

    def test_get_repo_map_with_config_files(self, tmp_path):
        (tmp_path / "config.json").touch()
        (tmp_path / "settings.yaml").touch()

        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()

        assert "CONFIG FILES" in result

    def test_get_repo_map_ignores_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()

        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()

        assert ".git" not in result

    def test_get_git_info_not_git_repo(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        result = builder.get_git_info()

        assert result == ""

    def test_get_git_info_git_repo_clean(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")

        mock_result = MagicMock()
        mock_result.stdout = ""

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *args, **kwargs: mock_result)
        result = builder.get_git_info()

        assert "Branch: main" in result
        assert "clean" in result

    def test_get_git_info_with_changes(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")

        mock_result = MagicMock()
        mock_result.stdout = " M file.py\n M another.py\n"

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *args, **kwargs: mock_result)
        result = builder.get_git_info()

        assert "2 changes" in result

    def test_get_language_stats_empty(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        stats = builder.get_language_stats()

        assert stats == {}

    def test_get_language_stats_with_files(self, tmp_path):
        (tmp_path / "main.py").touch()
        (tmp_path / "app.py").touch()
        (tmp_path / "index.js").touch()

        builder = ContextBuilder(tmp_path)
        stats = builder.get_language_stats()

        assert stats.get("Python", 0) >= 2
        assert stats.get("JavaScript", 0) >= 1

    def test_get_language_stats_ignores_venv(self, tmp_path):
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "python").mkdir()
        (venv_dir / "python" / "file.py").touch()

        builder = ContextBuilder(tmp_path)
        stats = builder.get_language_stats()

        assert "Python" not in stats

    def test_generate_ctags_not_git_repo(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        result = builder.generate_ctags()

        assert "ERROR" in result
        assert "Not a git repository" in result

    def test_generate_ctags_success(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        mock_result = MagicMock()
        mock_result.stdout = "src/main.py\0src/app.py\0"

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *args, **kwargs: mock_result)
        result = builder.generate_ctags()

        assert "main.py" in result


class TestFunctions:
    def test_get_repo_map(self, tmp_path):
        result = get_repo_map(tmp_path)
        assert f"Repository: {tmp_path.name}" in result

    def test_get_git_info(self, tmp_path):
        result = get_git_info(tmp_path)
        assert result == ""

    def test_get_language_stats(self, tmp_path):
        stats = get_language_stats(tmp_path)
        assert isinstance(stats, dict)

    def test_generate_ctags(self, tmp_path):
        result = generate_ctags(tmp_path)
        assert "ERROR" in result

    def test_create_context_builder(self):
        builder = create_context_builder()
        assert isinstance(builder, ContextBuilder)

    def test_create_context_builder_with_path(self, tmp_path):
        builder = create_context_builder(tmp_path)
        assert builder.path == tmp_path
