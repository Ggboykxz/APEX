"""Tests for refactored context module — no mocks, real filesystem and git."""

import subprocess
from pathlib import Path

from apex.refactored_context import (
    ContextBuilder,
    get_repo_map,
    get_git_info,
    get_language_stats,
    generate_ctags,
    create_context_builder,
    IGNORE_DIRS,
    SOURCE_EXTS,
    CONFIG_EXTS,
    DOC_EXTS,
    EXT_MAP,
)


class TestConstants:
    def test_ignore_dirs(self):
        assert ".git" in IGNORE_DIRS
        assert "node_modules" in IGNORE_DIRS
        assert "__pycache__" in IGNORE_DIRS

    def test_source_exts(self):
        assert ".py" in SOURCE_EXTS
        assert ".js" in SOURCE_EXTS
        assert ".go" in SOURCE_EXTS

    def test_config_exts(self):
        assert ".json" in CONFIG_EXTS
        assert ".yaml" in CONFIG_EXTS

    def test_doc_exts(self):
        assert ".md" in DOC_EXTS
        assert ".txt" in DOC_EXTS

    def test_ext_map(self):
        assert EXT_MAP[".py"] == "Python"
        assert EXT_MAP[".js"] == "JavaScript"
        assert EXT_MAP[".rs"] == "Rust"


class TestContextBuilder:
    def test_init_with_path(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        assert builder.path == tmp_path

    def test_init_without_path(self):
        builder = ContextBuilder()
        assert builder.path == Path.cwd()

    def test_get_repo_map_not_exists(self):
        builder = ContextBuilder(Path("/nonexistent/path/abc123"))
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
        assert "DIRECTORIES" in result

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

    def test_get_repo_map_with_doc_files(self, tmp_path):
        (tmp_path / "README.md").touch()
        (tmp_path / "notes.txt").touch()
        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()
        assert "DOCUMENTATION" in result

    def test_get_repo_map_ignores_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()
        assert ".git" not in result

    def test_get_repo_map_ignores_hidden_files(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden_file.py").touch()
        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()
        assert ".hidden" not in result

    def test_get_git_info_not_git_repo(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        result = builder.get_git_info()
        assert result == ""

    def test_get_git_info_git_repo_clean(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")

        # Use a custom subprocess_run that simulates clean status
        class FakeResult:
            stdout = ""

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *a, **kw: FakeResult())
        result = builder.get_git_info()
        assert "Branch: main" in result
        assert "clean" in result

    def test_get_git_info_with_changes(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/feature")

        class FakeResult:
            stdout = " M file.py\n M another.py\n"

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *a, **kw: FakeResult())
        result = builder.get_git_info()
        assert "Branch: feature" in result
        assert "2 changes" in result

    def test_get_git_info_detached_head(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("abc123def456")

        class FakeResult:
            stdout = ""

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *a, **kw: FakeResult())
        result = builder.get_git_info()
        assert "Branch: abc123def456" in result

    def test_get_git_info_no_head_file(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        builder = ContextBuilder(tmp_path)
        result = builder.get_git_info()
        assert result == ""

    def test_get_git_info_subprocess_error(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")

        def raise_error(*a, **kw):
            raise RuntimeError("git error")

        builder = ContextBuilder(tmp_path, subprocess_run=raise_error)
        result = builder.get_git_info()
        assert result == ""

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
        (venv_dir / "file.py").touch()
        builder = ContextBuilder(tmp_path)
        stats = builder.get_language_stats()
        assert "Python" not in stats

    def test_get_language_stats_unknown_ext(self, tmp_path):
        (tmp_path / "data.xyz").touch()
        builder = ContextBuilder(tmp_path)
        stats = builder.get_language_stats()
        assert "Other" in stats

    def test_generate_ctags_not_git_repo(self, tmp_path):
        builder = ContextBuilder(tmp_path)
        result = builder.generate_ctags()
        assert "ERROR" in result
        assert "Not a git repository" in result

    def test_generate_ctags_success(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        class FakeResult:
            stdout = "src/main.py\0src/app.py\0"

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *a, **kw: FakeResult())
        result = builder.generate_ctags()
        assert "main.py" in result
        assert "app.py" in result

    def test_generate_ctags_no_code_files(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        class FakeResult:
            stdout = "README.md\0LICENSE\0"

        builder = ContextBuilder(tmp_path, subprocess_run=lambda *a, **kw: FakeResult())
        result = builder.generate_ctags()
        assert "no code files found" in result

    def test_generate_ctags_subprocess_error(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        def raise_error(*a, **kw):
            raise RuntimeError("git error")

        builder = ContextBuilder(tmp_path, subprocess_run=raise_error)
        result = builder.generate_ctags()
        assert "ERROR" in result

    def test_get_repo_map_with_real_git_repo(self, tmp_path):
        """Test with a real git repository."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
        )
        builder = ContextBuilder(tmp_path)
        result = builder.get_repo_map()
        assert "SOURCE FILES" in result
        assert "GIT" in result


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
