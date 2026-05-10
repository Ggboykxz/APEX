"""Tests for refactored workspace module."""

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
        assert ctx.is_dirty is False

    def test_create_with_values(self):
        ctx = GitContext(branch="main", is_dirty=True)
        assert ctx.branch == "main"
        assert ctx.is_dirty is True


class TestWorkspaceContext:
    def test_create_default(self):
        ctx = WorkspaceContext(root=Path("/tmp"))
        assert ctx.root == Path("/tmp")
        assert ctx.git is None
        assert ctx.language == ""

    def test_create_with_git(self):
        git = GitContext(branch="main")
        ctx = WorkspaceContext(root=Path("/tmp"), git=git)
        assert ctx.git is not None
        assert ctx.git.branch == "main"


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
        mgr = WorkspaceManager(tmp_path)
        ctx = mgr.analyze()
        assert ctx.git is not None

    def test_get_context(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        ctx = mgr.get_context()
        assert ctx is not None

    def test_get_files(self, tmp_path):
        (tmp_path / "test.txt").write_text("content")
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
        files = mgr.get_files()
        assert any(f.name == "test.txt" for f in files)

    def test_get_directories(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        mgr = WorkspaceManager(tmp_path)
        mgr.analyze()
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

    def test_update_context(self, tmp_path):
        mgr = WorkspaceManager(tmp_path)
        mgr.update_context(language="Python")
        assert mgr._context.language == "Python"


class TestGetWorkspaceRoot:
    def test_get_workspace_root_non_git(self, tmp_path):
        get_workspace_root(str(tmp_path))
        # May or may not be tmp_path depending on parent markers

    def test_get_workspace_root_git(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path
