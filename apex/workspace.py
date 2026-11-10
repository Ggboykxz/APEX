"""Workspace awareness for APEX - Git context, branch, PR information."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitContext:
    branch: str = ""
    remote: str = ""
    remote_url: str = ""
    is_dirty: bool = False
    commit: str = ""
    commits_ahead: int = 0
    commits_behind: int = 0
    pr_number: int | None = None
    pr_title: str = ""
    pr_url: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class WorkspaceContext:
    root: Path
    git: GitContext | None = None
    language: str = ""
    package_manager: str = ""
    test_framework: str = ""


def _pr_number_from_env() -> int | None:
    """Return the CI pull-request number, or None outside a PR workflow."""
    if "GITHUB_HEAD_REF" not in subprocess.os.environ:
        return None
    try:
        return int(subprocess.os.environ.get("GITHUB_PR_NUMBER", 0))
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command with the standard timeout."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def _count_lines(text: str) -> int:
    """The number of non-empty lines of a git output."""
    if not text.strip():
        return 0
    return len(text.strip().split("\n"))


class WorkspaceManager:
    def __init__(self, root: Path | None = None):
        self._root = root or Path.cwd()
        self._context: WorkspaceContext | None = None

    def analyze(self) -> WorkspaceContext:
        self._context = WorkspaceContext(root=self._root)

        if (self._root / ".git").exists():
            self._context.git = self._get_git_context()

        self._context.language = self._detect_language()
        self._context.package_manager = self._detect_package_manager()
        self._context.test_framework = self._detect_test_framework()

        return self._context

    def _get_git_context(self) -> GitContext:
        ctx = GitContext()

        # Read CI PR metadata first: a slow or failing network call below must
        # never discard this information.
        ctx.pr_number = _pr_number_from_env()

        try:
            self._fill_git_branch_and_commit(ctx)
            self._fill_git_status(ctx)
            self._fill_git_remote(ctx)
            self._fill_git_ahead_behind(ctx)
            self._fill_git_tags(ctx)
        except Exception:  # noqa: S110, BLE001
            pass

        return ctx

    def _fill_git_branch_and_commit(self, ctx: GitContext) -> None:
        """The current branch and the short commit hash."""
        result = _git(self._root, ["rev-parse", "--abbrev-ref", "HEAD"])
        if result.returncode == 0:
            ctx.branch = result.stdout.strip()

        result = _git(self._root, ["rev-parse", "HEAD"])
        if result.returncode == 0:
            ctx.commit = result.stdout.strip()[:8]

    def _fill_git_status(self, ctx: GitContext) -> None:
        """Whether the working tree is dirty."""
        result = _git(self._root, ["status", "--porcelain"])
        ctx.is_dirty = bool(result.stdout.strip())

    def _fill_git_remote(self, ctx: GitContext) -> None:
        """The remote URL and the GitHub owner/repo, when available."""
        result = _git(self._root, ["remote", "get-url", "origin"])
        if result.returncode != 0:
            return
        ctx.remote_url = result.stdout.strip()
        if "github.com" not in ctx.remote_url:
            return
        ctx.remote = ctx.remote_url.replace(".git", "").split("github.com/")[-1]
        _git(self._root, ["fetch", "--dry-run"])

    def _fill_git_ahead_behind(self, ctx: GitContext) -> None:
        """The number of commits ahead of and behind the upstream."""
        ahead = _git(self._root, ["log", "@{u}..HEAD", "--oneline"])
        ctx.commits_ahead = _count_lines(ahead.stdout)
        behind = _git(self._root, ["log", "HEAD..@{u}", "--oneline"])
        ctx.commits_behind = _count_lines(behind.stdout)

    def _fill_git_tags(self, ctx: GitContext) -> None:
        """The five most recent tags."""
        result = _git(self._root, ["tag", "--list", "-l", "--sort=-creatordate"])
        if result.returncode == 0:
            ctx.tags = result.stdout.strip().split("\n")[:5]

    def _detect_language(self) -> str:
        for ext_file, lang in {
            "pyproject.toml": "Python",
            "requirements.txt": "Python",
            "setup.py": "Python",
            "package.json": "JavaScript",
            "go.mod": "Go",
            "Cargo.toml": "Rust",
            "pom.xml": "Java",
            "build.gradle": "Kotlin",
        }.items():
            if (self._root / ext_file).exists():
                return lang
        return "Unknown"

    def _detect_package_manager(self) -> str:
        managers = {
            "package-lock.json": "npm",
            "yarn.lock": "yarn",
            "pnpm-lock.yaml": "pnpm",
            "requirements.txt": "pip",
            "pyproject.toml": "poetry",
            "go.mod": "go",
            "Cargo.lock": "cargo",
            "Gemfile": "bundler",
        }
        for file, manager in managers.items():
            if (self._root / file).exists():
                return manager
        return "unknown"

    def _detect_test_framework(self) -> str:
        frameworks = {
            "pytest.ini": "pytest",
            "pyproject.toml": "pytest",
            "jest.config.js": "jest",
            "vitest.config.ts": "vitest",
            "go.sum": "testing",
            "Cargo.toml": "cargo test",
        }
        for file, fw in frameworks.items():
            if (self._root / file).exists():
                return fw
        return "unknown"

    def get_system_prompt_context(self) -> str:
        if not self._context:
            self.analyze()

        parts = ["[WORKSPACE CONTEXT]"]

        if self._context.git:
            parts.append(f"Git branch: {self._context.git.branch}")
            if self._context.git.is_dirty:
                parts.append("Git status: dirty (uncommitted changes)")
            if self._context.git.commits_ahead:
                parts.append(f"Commits ahead of remote: {self._context.git.commits_ahead}")
            if self._context.git.commits_behind:
                parts.append(f"Commits behind remote: {self._context.git.commits_behind}")

        parts.append(f"Language: {self._context.language}")
        parts.append(f"Package manager: {self._context.package_manager}")
        parts.append(f"Test framework: {self._context.test_framework}")

        return "\n".join(parts)


workspace_manager = WorkspaceManager()
