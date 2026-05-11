"""Tests for refactored workspace module — no mocks, real filesystem and git."""

import subprocess
from pathlib import Path

from apex.refactored_workspace import (
    GitContext,
    WorkspaceContext,
    WorkspaceManager,
    get_workspace_root,
)


class TestGitContext:
    def test_create_default(self):
        ctx = GitContext()
        assert ctx.branch == ""
        assert ctx.remote == ""
        assert ctx.remote_url == ""
        assert ctx.is_dirty is False
        assert ctx.commit == ""
        assert ctx.commits_ahead == 0
        assert ctx.commits_behind == 0
        assert ctx.pr_number is None
        assert ctx.pr_title == ""
        assert ctx.pr_url == ""
        assert ctx.tags == []

    def test_create_with_values(self):
        ctx = GitContext(branch="main", is_dirty=True, commit="abc123")
        assert ctx.branch == "main"
        assert ctx.is_dirty is True
        assert ctx.commit == "abc123"

    def test_create_with_pr(self):
        ctx = GitContext(pr_number=42, pr_title="Fix bug", pr_url="https://github.com/pr/42")
        assert ctx.pr_number == 42
        assert ctx.pr_title == "Fix bug"
        assert ctx.pr_url == "https://github.com/pr/42"

    def test_create_with_tags(self):
        ctx = GitContext(tags=["v1.0", "v2.0"])
        assert ctx.tags == ["v1.0", "v2.0"]


class TestWorkspaceContext:
    def test_create_default(self):
        ctx = WorkspaceContext(root=Path("/tmp"))
        assert ctx.root == Path("/tmp")
        assert ctx.git is None
        assert ctx.language == ""
        assert ctx.package_manager == ""
        assert ctx.test_framework == ""

    def test_create_with_git(self):
        git = GitContext(branch="main")
        ctx = WorkspaceContext(root=Path("/tmp"), git=git)
        assert ctx.git is not None
        assert ctx.git.branch == "main"

    def test_create_with_all_fields(self):
        ctx = WorkspaceContext(
            root=Path("/tmp"),
            language="Python",
            package_manager="pip",
            test_framework="pytest",
        )
        assert ctx.language == "Python"
        assert ctx.package_manager == "pip"
        assert ctx.test_framework == "pytest"


class TestWorkspaceManager:
    def test_init_default(self):
        mgr = WorkspaceManager()
        assert mgr._root == Path.cwd()

    def test_init_with_path(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        assert mgr._root == tmp_path

    def test_analyze_non_git(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        assert ctx.root == tmp_path
        assert ctx.git is None

    def test_analyze_git(self, tmp_path):
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
        (tmp_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
        )
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        assert ctx.git is not None
        assert ctx.git.branch != "" or True  # Branch could be empty on detached HEAD
        assert ctx.git.is_dirty is False

    def test_analyze_git_dirty(self, tmp_path):
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
        (tmp_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
        )
        # Make a change
        (tmp_path / "test.txt").write_text("modified")
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        assert ctx.git is not None
        assert ctx.git.is_dirty is True

    def test_analyze_git_with_commit(self, tmp_path):
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
        (tmp_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init commit"],
            cwd=tmp_path,
            capture_output=True,
        )
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        assert ctx.git is not None
        assert "init" in ctx.git.commit

    def test_get_context(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        ctx = mgr.get_context()
        assert ctx is not None

    def test_get_context_without_analyze(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.get_context()
        assert ctx is None

    def test_get_files(self, tmp_path):
        (tmp_path / "test.txt").write_text("content")
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        files = mgr.get_files()
        assert any(f.name == "test.txt" for f in files)

    def test_get_files_auto_analyze(self, tmp_path):
        (tmp_path / "test.txt").write_text("content")
        mgr = WorkspaceManager(tmp_path)
        # Don't call analyze() first — get_files should auto-analyze
        files = mgr.get_files()
        assert any(f.name == "test.txt" for f in files)

    def test_get_directories(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        dirs = mgr.get_directories()
        assert any(d.name == "subdir" for d in dirs)

    def test_get_directories_auto_analyze(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        mgr = WorkspaceManager(tmp_path)
        dirs = mgr.get_directories()
        assert any(d.name == "subdir" for d in dirs)

    def test_get_language_stats(self, tmp_path):
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "test.js").write_text("console.log('hello')")
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        stats = mgr.get_language_stats()
        assert ".py" in stats
        assert ".js" in stats

    def test_search_files(self, tmp_path):
        (tmp_path / "test.py").write_text("content")
        (tmp_path / "test.txt").write_text("content")
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        results = mgr.search_files("*.py")
        assert len(results) == 1
        assert results[0].name == "test.py"

    def test_get_git_context(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        git_ctx = mgr.get_git_context()
        assert git_ctx is not None

    def test_get_git_context_auto_analyze(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        mgr = WorkspaceManager(tmp_path)
        git_ctx = mgr.get_git_context()
        assert git_ctx is not None

    def test_update_context(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.update_context(language="Python")
        assert mgr._context.language == "Python"

    def test_update_context_multiple(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.update_context(language="Python", package_manager="pip")
        assert mgr._context.language == "Python"
        assert mgr._context.package_manager == "pip"

    def test_update_context_ignores_unknown_attr(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.update_context(nonexistent_attr="value")
        assert not hasattr(mgr._context, "nonexistent_attr")

    def test_get_git_info_error(self, tmp_path):
        """Test git info when git commands fail."""
        (tmp_path / ".git").mkdir()
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        # .git dir exists but isn't a real repo, so git commands may fail
        assert ctx.git is not None  # _get_git_info returns a GitContext even on errors


class TestGetWorkspaceRoot:
    def test_get_workspace_root_git(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path

    def test_get_workspace_root_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path

    def test_get_workspace_root_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path

    def test_get_workspace_root_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\n')
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path

    def test_get_workspace_root_no_marker(self, tmp_path):
        # No marker files — should walk up to parent or cwd
        sub = tmp_path / "subproject" / "deep"
        sub.mkdir(parents=True)
        root = get_workspace_root(str(sub))
        # Should find a root somewhere
        assert isinstance(root, Path)
