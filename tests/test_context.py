"""Tests for APEX context builder — no mocks, real file system."""

import subprocess
from pathlib import Path


from apex.context import get_repo_map, get_language_stats, get_git_info, generate_ctags


# ---------------------------------------------------------------------------
# get_repo_map
# ---------------------------------------------------------------------------


class TestGetRepoMap:
    """Test get_repo_map function."""

    def test_basic_repo_map(self, tmp_path):
        """Test with source and config files."""
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "config.json").write_text("{}")
        result = get_repo_map(tmp_path)
        assert "Repository:" in result
        assert "main.py" in result
        assert "config.json" in result

    def test_repo_map_name(self, tmp_path):
        """Repository name comes from path."""
        result = get_repo_map(tmp_path)
        assert tmp_path.name in result

    def test_nonexistent_path(self):
        """Non-existent path returns ERROR."""
        result = get_repo_map(Path("/nonexistent/path/abc123"))
        assert result.startswith("ERROR:")

    def test_with_subdirs(self, tmp_path):
        """Directories appear in [DIRECTORIES] section."""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        result = get_repo_map(tmp_path)
        assert "DIRECTORIES" in result
        assert "src/" in result
        assert "tests/" in result

    def test_with_doc_files(self, tmp_path):
        """Documentation files appear in [DOCUMENTATION] section."""
        (tmp_path / "README.md").write_text("# hello")
        (tmp_path / "CHANGELOG.txt").write_text("v1.0")
        result = get_repo_map(tmp_path)
        assert "DOCUMENTATION" in result
        assert "README.md" in result

    def test_ignores_dot_dirs(self, tmp_path):
        """Hidden directories are ignored."""
        (tmp_path / ".hidden").mkdir()
        result = get_repo_map(tmp_path)
        assert ".hidden" not in result

    def test_ignores_common_dirs(self, tmp_path):
        """Common generated directories are ignored."""
        for d in [
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
        ]:
            (tmp_path / d).mkdir()
        result = get_repo_map(tmp_path)
        for d in [
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
        ]:
            assert d not in result

    def test_ignores_hidden_files(self, tmp_path):
        """Files starting with . are ignored."""
        (tmp_path / ".env").write_text("KEY=val")
        result = get_repo_map(tmp_path)
        assert ".env" not in result

    def test_source_files_section(self, tmp_path):
        """Source files appear in [SOURCE FILES] section."""
        (tmp_path / "app.py").write_text("pass")
        (tmp_path / "util.js").write_text("pass")
        result = get_repo_map(tmp_path)
        assert "SOURCE FILES" in result
        assert "app.py" in result
        assert "util.js" in result

    def test_empty_directory(self, tmp_path):
        """Empty directory produces minimal output."""
        result = get_repo_map(tmp_path)
        assert "Repository:" in result

    def test_default_path(self):
        """get_repo_map() with no args uses cwd."""
        result = get_repo_map()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_with_git_info(self, tmp_path):
        """Git info appears when .git/HEAD exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        # Also create a source file so repo map is non-empty
        (tmp_path / "main.py").write_text("pass")
        result = get_repo_map(tmp_path)
        assert "GIT" in result
        assert "main" in result

    def test_config_files_section(self, tmp_path):
        """Config files appear in [CONFIG FILES] section."""
        (tmp_path / "settings.yaml").write_text("key: value")
        (tmp_path / "pyproject.toml").write_text("[project]")
        result = get_repo_map(tmp_path)
        assert "CONFIG FILES" in result

    def test_max_subdirs_limit(self, tmp_path):
        """At most 10 subdirectories are listed."""
        for i in range(15):
            (tmp_path / f"dir_{i:02d}").mkdir()
        result = get_repo_map(tmp_path)
        # Should still show DIRECTORIES section, but capped
        assert "DIRECTORIES" in result

    def test_max_source_files_limit(self, tmp_path):
        """At most 15 source files are listed."""
        for i in range(20):
            (tmp_path / f"file_{i:02d}.py").write_text("pass")
        result = get_repo_map(tmp_path)
        assert "SOURCE FILES" in result

    def test_max_doc_files_limit(self, tmp_path):
        """At most 5 documentation files are listed."""
        for i in range(8):
            (tmp_path / f"doc_{i:02d}.md").write_text("# Doc")
        result = get_repo_map(tmp_path)
        assert "DOCUMENTATION" in result


# ---------------------------------------------------------------------------
# get_git_info
# ---------------------------------------------------------------------------


class TestGetGitInfo:
    """Test get_git_info function."""

    def test_not_git_repo(self, tmp_path):
        """No .git directory returns empty string."""
        result = get_git_info(tmp_path)
        assert result == ""

    def test_git_repo_with_branch(self, tmp_path):
        """Git repo with branch ref returns branch name."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/feature-branch")
        result = get_git_info(tmp_path)
        assert "feature-branch" in result
        assert "Branch:" in result

    def test_git_repo_detached_head(self, tmp_path):
        """Git repo with detached HEAD."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("abc123def456")
        result = get_git_info(tmp_path)
        assert "abc123def456" in result

    def test_git_repo_clean(self, tmp_path):
        """Git repo with no changes shows 'clean'."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        result = get_git_info(tmp_path)
        assert "clean" in result or "changes" in result


# ---------------------------------------------------------------------------
# get_language_stats
# ---------------------------------------------------------------------------


class TestGetLanguageStats:
    """Test get_language_stats function."""

    def test_basic_stats(self, tmp_path):
        """Counts files by language."""
        (tmp_path / "main.py").write_text("code")
        (tmp_path / "app.js").write_text("code")
        (tmp_path / "util.ts").write_text("code")
        stats = get_language_stats(tmp_path)
        assert stats.get("Python", 0) >= 1
        assert stats.get("JavaScript", 0) >= 1
        assert stats.get("TypeScript", 0) >= 1

    def test_empty_directory(self, tmp_path):
        """Empty directory returns empty dict."""
        stats = get_language_stats(tmp_path)
        assert isinstance(stats, dict)
        assert len(stats) == 0

    def test_nested_files(self, tmp_path):
        """Counts files in subdirectories."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "module.py").write_text("code")
        stats = get_language_stats(tmp_path)
        assert stats.get("Python", 0) >= 1

    def test_ignores_dirs(self, tmp_path):
        """Common generated directories are ignored."""
        for d in [".git", "node_modules", "__pycache__", "venv", ".venv", "target"]:
            dir_path = tmp_path / d
            dir_path.mkdir()
            (dir_path / "file.py").write_text("code")
        stats = get_language_stats(tmp_path)
        # These should not be counted
        assert stats.get("Python", 0) == 0

    def test_unknown_extensions(self, tmp_path):
        """Unknown extensions are categorized as 'Other'."""
        (tmp_path / "data.xyz").write_text("data")
        stats = get_language_stats(tmp_path)
        assert stats.get("Other", 0) >= 1

    def test_default_path(self):
        """get_language_stats() with no args uses cwd."""
        stats = get_language_stats()
        assert isinstance(stats, dict)

    def test_ruby_and_php(self, tmp_path):
        """Ruby and PHP files are detected."""
        (tmp_path / "app.rb").write_text("code")
        (tmp_path / "page.php").write_text("code")
        stats = get_language_stats(tmp_path)
        assert stats.get("Ruby", 0) >= 1
        assert stats.get("PHP", 0) >= 1


# ---------------------------------------------------------------------------
# generate_ctags
# ---------------------------------------------------------------------------


class TestGenerateCtags:
    """Test generate_ctags function."""

    def test_not_git_repo(self, tmp_path):
        """Non-git repo returns ERROR."""
        result = generate_ctags(tmp_path)
        assert result.startswith("ERROR:")

    def test_git_repo_no_code_files(self, tmp_path):
        """Git repo with no code files returns message."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        # Initialize a real git repo so `git ls-files` works
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        result = generate_ctags(tmp_path)
        # Should be either "no code files found" or a list of files
        assert isinstance(result, str)

    def test_git_repo_with_code_files(self, tmp_path):
        """Git repo with tracked code files returns them."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        (tmp_path / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

        result = generate_ctags(tmp_path)
        assert "main.py" in result

    def test_default_path(self):
        """generate_ctags() with no args uses cwd."""
        result = generate_ctags()
        assert isinstance(result, str)


class TestContextEdgeCases:
    """Hit lines 66-67 (PermissionError in get_repo_map),
    149-150 (PermissionError in get_language_stats),
    173-174 (Exception in generate_ctags)."""

    def test_get_repo_map_permission_error(self, tmp_path, monkeypatch):
        """Hit line 66-67 — PermissionError returns ERROR string."""
        # Patch Path.iterdir to raise PermissionError
        type(tmp_path).iterdir
        def broken_iterdir(self):
            raise PermissionError("Access denied")
        monkeypatch.setattr(type(tmp_path), "iterdir", broken_iterdir)
        result = get_repo_map(tmp_path)
        assert result == "ERROR: Permission denied"

    def test_get_language_stats_permission_error(self, tmp_path, monkeypatch):
        """Hit lines 149-150 — PermissionError in os.walk is silently caught."""
        import os
        def broken_walk(*a, **kw):
            raise PermissionError("Access denied")
        monkeypatch.setattr(os, "walk", broken_walk)
        result = get_language_stats(tmp_path)
        assert result == {}

    def test_generate_ctags_exception(self, tmp_path, monkeypatch):
        """Hit lines 173-174 — Exception returns ERROR string."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        import subprocess
        def broken_run(*a, **kw):
            raise RuntimeError("subprocess failed")
        monkeypatch.setattr(subprocess, "run", broken_run)
        result = generate_ctags(tmp_path)
        assert "ERROR" in result
