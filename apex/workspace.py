"""Workspace awareness for APEX - Git context, branch, PR information."""

import subprocess
from pathlib import Path
from dataclasses import dataclass, field


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

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ctx.branch = result.stdout.strip()

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ctx.commit = result.stdout.strip()[:8]

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            ctx.is_dirty = bool(result.stdout.strip())

            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ctx.remote_url = result.stdout.strip()

                if "github.com" in ctx.remote_url:
                    owner_repo = ctx.remote_url.replace(".git", "").split("github.com/")[-1]
                    ctx.remote = owner_repo

                    result = subprocess.run(
                        ["git", "fetch", "--dry-run"],
                        cwd=self._root, capture_output=True, text=True, timeout=5
                    )

            result = subprocess.run(
                ["git", "log", "@{u}..HEAD", "--oneline"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            ctx.commits_ahead = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

            result = subprocess.run(
                ["git", "log", "HEAD..@{u}", "--oneline"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            ctx.commits_behind = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

            if "GITHUB_HEAD_REF" in subprocess.os.environ:
                ctx.pr_number = int(subprocess.os.environ.get("GITHUB_PR_NUMBER", 0))

            result = subprocess.run(
                ["git", "tag", "--list", "-l", "--sort=-creatordate"],
                cwd=self._root, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ctx.tags = result.stdout.strip().split("\n")[:5]

        except Exception:
            pass

        return ctx

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