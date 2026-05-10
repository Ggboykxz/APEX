"""Refactored context module - More testable."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict


IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "target",
    "dist",
    "build",
    ".pytest_cache",
}

SOURCE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".swift",
    ".kt",
}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}

EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React",
    ".tsx": "React",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
}


class ContextBuilder:
    def __init__(
        self,
        path: Optional[Path] = None,
        path_cwd: Optional[Callable[[], Path]] = None,
        subprocess_run: Optional[Callable] = None,
        os_walk: Optional[Callable] = None,
    ):
        self._path = path
        self._path_cwd = path_cwd or Path.cwd
        self._subprocess_run = subprocess_run or subprocess.run
        self._os_walk = os_walk or os.walk

    @property
    def path(self) -> Path:
        return self._path or self._path_cwd()

    def get_repo_map(self) -> str:
        path = self.path
        if not path.exists():
            return f"ERROR: Path does not exist: {path}"

        lines = [f"Repository: {path.name}", "=" * 50]

        source_files = []
        config_files = []
        doc_files = []
        subdirs = []

        try:
            for item in path.iterdir():
                if item.name.startswith(".") or item.name in IGNORE_DIRS:
                    continue
                if item.is_dir():
                    subdirs.append(item.name)
                elif item.suffix in SOURCE_EXTS:
                    source_files.append(item.name)
                elif item.suffix in CONFIG_EXTS:
                    config_files.append(item.name)
                elif item.suffix in DOC_EXTS:
                    doc_files.append(item.name)
        except PermissionError:
            return "ERROR: Permission denied"

        if subdirs:
            lines.append("\n[DIRECTORIES]")
            for d in sorted(subdirs)[:10]:
                lines.append(f"  📁 {d}/")

        if source_files:
            lines.append("\n[SOURCE FILES]")
            for f in sorted(source_files)[:15]:
                lines.append(f"  • {f}")

        if config_files:
            lines.append("\n[CONFIG FILES]")
            for f in sorted(config_files):
                lines.append(f"  ⚙ {f}")

        if doc_files:
            lines.append("\n[DOCUMENTATION]")
            for f in sorted(doc_files)[:5]:
                lines.append(f"  📄 {f}")

        git_info = self.get_git_info()
        if git_info:
            lines.append(f"\n{git_info}")

        return "\n".join(lines)

    def get_git_info(self) -> str:
        path = self.path
        git_dir = path / ".git"
        if not git_dir.exists():
            return ""

        try:
            head_file = git_dir / "HEAD"
            if not head_file.exists():
                return ""
            branch = head_file.read_text().strip()
            if branch.startswith("ref: "):
                branch = branch[5:].split("/")[-1]

            result = self._subprocess_run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            changes = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

            return f"[GIT] Branch: {branch}" + (f" ({changes} changes)" if changes else " (clean)")
        except Exception:
            return ""

    def get_language_stats(self) -> Dict[str, int]:
        path = self.path
        stats: Dict[str, int] = {}

        try:
            for root, dirs, files in self._os_walk(path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    ext = Path(f).suffix
                    lang = EXT_MAP.get(ext, "Other")
                    stats[lang] = stats.get(lang, 0) + 1
        except PermissionError:
            pass

        return stats

    def generate_ctags(self) -> str:
        path = self.path
        if not (path / ".git").exists():
            return "ERROR: Not a git repository"

        try:
            result = self._subprocess_run(
                ["git", "ls-files", "-z"], cwd=path, capture_output=True, text=True, timeout=10
            )
            files = result.stdout.split("\0")[:-1]

            code_exts = {".py", ".js", ".ts", ".go", ".rs", ".java"}
            code_files = [f for f in files if any(f.endswith(ext) for ext in code_exts)]
            return "\n".join(code_files[:50]) if code_files else "[no code files found]"
        except Exception as e:
            return f"ERROR: {e}"


def get_repo_map(path: Optional[Path] = None) -> str:
    builder = ContextBuilder(path)
    return builder.get_repo_map()


def get_git_info(path: Path) -> str:
    builder = ContextBuilder(path)
    return builder.get_git_info()


def get_language_stats(path: Optional[Path] = None) -> Dict[str, int]:
    builder = ContextBuilder(path)
    return builder.get_language_stats()


def generate_ctags(path: Optional[Path] = None) -> str:
    builder = ContextBuilder(path)
    return builder.generate_ctags()


def create_context_builder(
    path: Optional[Path] = None,
    path_cwd: Optional[Callable] = None,
    subprocess_run: Optional[Callable] = None,
    os_walk: Optional[Callable] = None,
) -> ContextBuilder:
    return ContextBuilder(path, path_cwd, subprocess_run, os_walk)
