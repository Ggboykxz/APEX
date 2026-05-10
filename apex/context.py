"""Context builder for APEX - repository mapping and intelligent context."""

import os
import subprocess
from pathlib import Path


def get_repo_map(path: Path | None = None) -> str:
    """Generate a repository map showing file structure and key files."""
    path = path or Path.cwd()
    if not path.exists():
        return f"ERROR: Path does not exist: {path}"

    lines = [f"Repository: {path.name}", "=" * 50]

    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "target", "dist", "build", ".pytest_cache"}

    source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt"}
    config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
    doc_exts = {".md", ".txt", ".rst", ".adoc"}

    source_files = []
    config_files = []
    doc_files = []
    subdirs = []

    try:
        for item in path.iterdir():
            if item.name.startswith(".") or item.name in ignore_dirs:
                continue
            if item.is_dir():
                subdirs.append(item.name)
            elif item.suffix in source_exts:
                source_files.append(item.name)
            elif item.suffix in config_exts:
                config_files.append(item.name)
            elif item.suffix in doc_exts:
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

    git_info = get_git_info(path)
    if git_info:
        lines.append(f"\n{git_info}")

    return "\n".join(lines)


def get_git_info(path: Path) -> str:
    """Get git branch and status info."""
    git_dir = path / ".git"
    if not git_dir.exists():
        return ""

    try:
        branch = (git_dir / "HEAD").read_text().strip()
        if branch.startswith("ref: "):
            branch = branch[5:].split("/")[-1]

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )
        changes = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        return f"[GIT] Branch: {branch}" + (f" ({changes} changes)" if changes else " (clean)")
    except Exception:
        return ""


def get_language_stats(path: Path | None = None) -> dict[str, int]:
    """Get language statistics for the repository."""
    path = path or Path.cwd()
    stats = {}

    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React", ".tsx": "React", ".go": "Go",
        ".rs": "Rust", ".java": "Java", ".c": "C", ".cpp": "C++",
        ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
        ".kt": "Kotlin", ".scala": "Scala"
    }

    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "target"}

    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in files:
                ext = Path(f).suffix
                lang = ext_map.get(ext, "Other")
                stats[lang] = stats.get(lang, 0) + 1
    except PermissionError:
        pass

    return stats


def generate_ctags(path: Path | None = None) -> str:
    """Generate ctags-like output for the repository."""
    path = path or Path.cwd()
    if not (path / ".git").exists():
        return "ERROR: Not a git repository"

    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10
        )
        files = result.stdout.split("\0")[:-1]

        code_files = [f for f in files if any(f.endswith(ext) for ext in [".py", ".js", ".ts", ".go", ".rs", ".java"])]
        return "\n".join(code_files[:50]) if code_files else "[no code files found]"
    except Exception as e:
        return f"ERROR: {e}"