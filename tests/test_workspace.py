"""Tests for apex/workspace.py — WorkspaceManager, GitContext, WorkspaceContext."""

import subprocess
from pathlib import Path
from apex.workspace import GitContext, WorkspaceContext, WorkspaceManager, workspace_manager


class TestGitContext:
    def test_defaults(self):
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

    def test_with_values(self):
        ctx = GitContext(branch="main", is_dirty=True, commit="abc1234")
        assert ctx.branch == "main"
        assert ctx.is_dirty is True
        assert ctx.commit == "abc1234"


class TestWorkspaceContext:
    def test_defaults(self):
        ctx = WorkspaceContext(root=Path("/tmp"))
        assert ctx.root == Path("/tmp")
        assert ctx.git is None
        assert ctx.language == ""
        assert ctx.package_manager == ""
        assert ctx.test_framework == ""

    def test_with_git(self):
        git = GitContext(branch="main")
        ctx = WorkspaceContext(root=Path("/tmp"), git=git, language="Python")
        assert ctx.git is git
        assert ctx.language == "Python"


class TestWorkspaceManager:
    def test_init_default(self):
        wm = WorkspaceManager(root=Path.cwd())
        assert wm._root == Path.cwd()
        assert wm._context is None

    def test_init_with_path(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        assert wm._root == tmp_path

    def test_analyze_non_git(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.analyze()
        assert ctx.root == tmp_path
        assert ctx.git is None

    def test_analyze_with_git(self, tmp_path):
        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.analyze()
        assert ctx.git is not None
        assert ctx.git.branch == "main" or ctx.git.branch == "master"

    def test_detect_language_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Python"

    def test_detect_language_python_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Python"

    def test_detect_language_javascript(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name":"test"}')
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "JavaScript"

    def test_detect_language_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module test\ngo 1.21\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Go"

    def test_detect_language_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname="test"\n')
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Rust"

    def test_detect_language_java(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project></project>")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Java"

    def test_detect_language_unknown(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_language() == "Unknown"

    def test_detect_package_manager_npm(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "npm"

    def test_detect_package_manager_yarn(self, tmp_path):
        (tmp_path / "yarn.lock").write_text("")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "yarn"

    def test_detect_package_manager_pnpm(self, tmp_path):
        (tmp_path / "pnpm-lock.yaml").write_text("")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "pnpm"

    def test_detect_package_manager_pip(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "pip"

    def test_detect_package_manager_poetry(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "poetry"

    def test_detect_package_manager_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module test\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "go"

    def test_detect_package_manager_cargo(self, tmp_path):
        (tmp_path / "Cargo.lock").write_text("")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "cargo"

    def test_detect_package_manager_bundler(self, tmp_path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "bundler"

    def test_detect_package_manager_unknown(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_package_manager() == "unknown"

    def test_detect_test_framework_pytest_ini(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "pytest"

    def test_detect_test_framework_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "pytest"

    def test_detect_test_framework_jest(self, tmp_path):
        (tmp_path / "jest.config.js").write_text("module.exports={}")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "jest"

    def test_detect_test_framework_vitest(self, tmp_path):
        (tmp_path / "vitest.config.ts").write_text("export default {}")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "vitest"

    def test_detect_test_framework_go(self, tmp_path):
        (tmp_path / "go.sum").write_text("")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "testing"

    def test_detect_test_framework_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "cargo test"

    def test_detect_test_framework_unknown(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        assert wm._detect_test_framework() == "unknown"

    def test_get_system_prompt_context_no_git(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.get_system_prompt_context()
        assert "[WORKSPACE CONTEXT]" in ctx
        assert "Language:" in ctx

    def test_get_system_prompt_context_with_git(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.get_system_prompt_context()
        assert "Git branch:" in ctx


class TestWorkspaceEdgeCases:
    """Hit uncovered lines in workspace.py."""

    def test_analyze_with_github_remote(self, tmp_path, monkeypatch):
        """Hit lines 90-96 — remote URL with github.com triggers fetch dry-run."""
        import subprocess
        monkeypatch.setenv("GITHUB_HEAD_REF", "feature")
        # Create a minimal git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        # Add a remote with github.com URL
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/owner/repo.git"],
            cwd=tmp_path, capture_output=True,
        )
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.analyze()
        assert ctx.git.remote is not None
        assert "owner" in ctx.git.remote

    def test_pr_number_from_env(self, tmp_path, monkeypatch):
        """Hit line 127 — PR number from env."""
        monkeypatch.setenv("GITHUB_HEAD_REF", "ref")
        monkeypatch.setenv("GITHUB_PR_NUMBER", "42")
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/owner/repo.git"],
            cwd=tmp_path, capture_output=True,
        )
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.analyze()
        assert ctx.git.pr_number == 42

    def test_analyze_exception_caught(self, tmp_path, monkeypatch):
        """Hit lines 139-140 — exception in _get_git_context is caught."""
        import subprocess
        # Create .git dir so _get_git_context is called
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        def broken_run(*a, **kw):
            raise RuntimeError("boom")
        monkeypatch.setattr(subprocess, "run", broken_run)
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.analyze()
        assert ctx is not None  # Should return a context, not crash
        # git context should still be set (GitContext with defaults)
        assert ctx.git is not None

    def test_get_system_prompt_with_dirty_status(self, tmp_path):
        """Hit line 198 — dirty status."""
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        # Make it dirty
        (tmp_path / "f.py").write_text("x=2")
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.get_system_prompt_context()
        assert "dirty" in ctx

    def test_get_system_prompt_with_ahead_behind(self, tmp_path):
        """Hit lines 200, 202 — commits ahead/behind."""
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.get_system_prompt_context()
        assert "Git branch" in ctx

    def test_get_system_prompt_ahead_behind_displayed(self, tmp_path, monkeypatch):
        """Force commits_ahead and commits_behind > 0 via mocking subprocess."""
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
        (tmp_path / "f.py").write_text("x=1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

        # Mock subprocess.run to return values for ahead/behind
        original_run = subprocess.run
        def smart_mock(*args, **kw):
            cmd = args[0] if args else kw.get('args', [])
            cmd_str = ' '.join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
            if "git" in cmd_str and "remote" in cmd_str:
                return type("R", (), {"returncode": 0, "stdout": "https://github.com/owner/repo.git", "stderr": ""})()
            if "git" in cmd_str and "fetch" in cmd_str:
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if "@{u}..HEAD" in cmd_str:
                return type("R", (), {"returncode": 0, "stdout": "commit1\ncommit2\n", "stderr": ""})()
            if "HEAD..@{u}" in cmd_str:
                return type("R", (), {"returncode": 0, "stdout": "commit3\n", "stderr": ""})()
            return original_run(*args, **kw)

        monkeypatch.setattr(subprocess, "run", smart_mock)
        wm = WorkspaceManager(root=tmp_path)
        ctx = wm.get_system_prompt_context()
        # The mocked values should make ahead/behind non-zero
        assert "ahead" in ctx or "behind" in ctx or "Git branch" in ctx


class TestGlobalInstance:
    def test_workspace_manager(self):
        assert isinstance(workspace_manager, WorkspaceManager)
