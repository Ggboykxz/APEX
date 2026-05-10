"""Tests for workspace module."""

import tempfile
import pytest
from pathlib import Path
from apex.workspace import WorkspaceManager, WorkspaceContext, GitContext


class TestGitContext:
    """Test GitContext dataclass."""

    def test_default_values(self):
        """Test GitContext default values."""
        ctx = GitContext()
        assert ctx.branch == ""
        assert ctx.remote == ""
        assert ctx.is_dirty is False
        assert ctx.commits_ahead == 0
        assert ctx.commits_behind == 0
        assert ctx.pr_number is None

    def test_custom_values(self):
        """Test GitContext with custom values."""
        ctx = GitContext(
            branch="main",
            remote="origin",
            is_dirty=True,
            commits_ahead=3,
            commits_behind=1,
            pr_number=42,
        )
        assert ctx.branch == "main"
        assert ctx.is_dirty is True
        assert ctx.pr_number == 42


class TestWorkspaceContext:
    """Test WorkspaceContext dataclass."""

    def test_default_values(self):
        """Test WorkspaceContext default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(root=Path(tmpdir))
            assert ctx.root == Path(tmpdir)
            assert ctx.git is None
            assert ctx.language == ""
            assert ctx.package_manager == ""


class TestWorkspaceManager:
    """Test WorkspaceManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_with_cwd(self):
        """Test initialization with current directory."""
        manager = WorkspaceManager()
        assert manager._root == Path.cwd()

    def test_init_with_custom_path(self, temp_dir):
        """Test initialization with custom path."""
        manager = WorkspaceManager(temp_dir)
        assert manager._root == temp_dir

    def test_analyze_non_git(self, temp_dir):
        """Test analyzing non-git directory."""
        manager = WorkspaceManager(temp_dir)
        context = manager.analyze()
        assert context.root == temp_dir
        assert context.git is None

    def test_analyze_git_directory(self, temp_dir):
        """Test analyzing git directory."""
        (temp_dir / ".git").mkdir()

        manager = WorkspaceManager(temp_dir)
        context = manager.analyze()
        assert context.root == temp_dir
        assert context.git is not None

    def test_get_context(self, temp_dir):
        """Test get_context method."""
        manager = WorkspaceManager(temp_dir)
        manager.analyze()
        context = manager._context
        assert context is not None
        assert context.root == temp_dir

    def test_get_system_prompt_context(self, temp_dir):
        """Test system prompt context."""
        manager = WorkspaceManager(temp_dir)
        prompt = manager.get_system_prompt_context()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
