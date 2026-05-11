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


class TestGlobalInstance:
    def test_workspace_manager(self):
        assert isinstance(workspace_manager, WorkspaceManager)
