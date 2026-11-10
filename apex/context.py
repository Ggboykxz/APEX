"""Context builder for APEX - repository mapping and intelligent context."""

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def get_repo_map(path: Path | None = None) -> str:
    """Generate a repository map showing file structure and key files."""
    path = path or Path.cwd()
    if not path.exists():
        return f"ERROR: Path does not exist: {path}"

    lines = [f"Repository: {path.name}", "=" * 50]

    try:
        subdirs, source_files, config_files, doc_files = _classify_root_entries(path)
    except PermissionError:
        return "ERROR: Permission denied"

    _render_directories(lines, subdirs)
    _render_source_files(lines, source_files)
    _render_config_files(lines, config_files)
    _render_doc_files(lines, doc_files)

    git_info = get_git_info(path)
    if git_info:
        lines.append(f"\n{git_info}")

    return "\n".join(lines)


def _classify_root_entries(path: Path):
    """The sub-directories and the files of the root, grouped by kind."""
    buckets = _RootBuckets([], [], [], [])
    kinds = _FileKinds(
        ignore_dirs=frozenset(
            {
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
        ),
        source_exts=frozenset(
            {
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
        ),
        config_exts=frozenset({".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}),
        doc_exts=frozenset({".md", ".txt", ".rst", ".adoc"}),
    )

    for item in path.iterdir():
        bucket = _entry_bucket(item, kinds)
        if bucket is None:
            continue
        _append_entry(bucket, item.name, buckets)

    return buckets.subdirs, buckets.source_files, buckets.config_files, buckets.doc_files


@dataclass(frozen=True)
class _FileKinds:
    """The extensions that belong to each bucket."""

    ignore_dirs: frozenset[str]
    source_exts: frozenset[str]
    config_exts: frozenset[str]
    doc_exts: frozenset[str]


def _entry_bucket(item: Path, kinds: _FileKinds) -> str | None:
    """The bucket an entry of the root belongs to, or ``None``."""
    if item.name.startswith(".") or item.name in kinds.ignore_dirs:
        return None
    if item.is_dir():
        return "dir"
    return _suffix_bucket(item.suffix, kinds)


def _suffix_bucket(suffix: str, kinds: _FileKinds) -> str | None:
    """The bucket a file suffix belongs to, or ``None``."""
    if suffix in kinds.source_exts:
        return "source"
    if suffix in kinds.config_exts:
        return "config"
    if suffix in kinds.doc_exts:
        return "doc"
    return None


@dataclass
class _RootBuckets:
    """The four buckets of a root scan."""

    subdirs: list[str]
    source_files: list[str]
    config_files: list[str]
    doc_files: list[str]


def _append_entry(bucket: str, name: str, buckets: _RootBuckets) -> None:
    """Append an entry to the bucket it belongs to."""
    target = _bucket_list(bucket, buckets)
    if target is not None:
        target.append(name)


def _bucket_list(bucket: str, buckets: _RootBuckets) -> list[str] | None:
    """The list a bucket name maps to, or ``None``."""
    mapping = {
        "dir": buckets.subdirs,
        "source": buckets.source_files,
        "config": buckets.config_files,
        "doc": buckets.doc_files,
    }
    return mapping.get(bucket)


def _render_directories(lines: list[str], subdirs: list[str]) -> None:
    """Append the directory section to the map."""
    if not subdirs:
        return
    lines.append("\n[DIRECTORIES]")
    for directory in sorted(subdirs)[:10]:
        lines.append(f"  📁 {directory}/")


def _render_source_files(lines: list[str], source_files: list[str]) -> None:
    """Append the source-files section to the map."""
    if not source_files:
        return
    lines.append("\n[SOURCE FILES]")
    for filename in sorted(source_files)[:15]:
        lines.append(f"  • {filename}")


def _render_config_files(lines: list[str], config_files: list[str]) -> None:
    """Append the config-files section to the map."""
    if not config_files:
        return
    lines.append("\n[CONFIG FILES]")
    for filename in sorted(config_files):
        lines.append(f"  ⚙ {filename}")


def _render_doc_files(lines: list[str], doc_files: list[str]) -> None:
    """Append the documentation section to the map."""
    if not doc_files:
        return
    lines.append("\n[DOCUMENTATION]")
    for filename in sorted(doc_files)[:5]:
        lines.append(f"  📄 {filename}")


def get_symbol_map(path: Path | None = None, max_tokens: int = 2000) -> str:
    """Generate a symbol-level repository map for LLM context.

    Delegates to :func:`apex.repomap.build_repo_map`, which extracts classes,
    functions, methods and types with line numbers and trims the result to a
    token budget. Unlike :func:`get_repo_map`, this includes nested source
    files and emits declaration signatures only.
    """
    path = Path(path) if path is not None else Path.cwd()
    if not path.exists():
        return f"ERROR: Path does not exist: {path}"
    if not path.is_dir():
        return f"ERROR: Not a directory: {path}"

    from .repomap import build_repo_map

    try:
        return build_repo_map(path, max_tokens=max_tokens)
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {type(e).__name__}: {e}"


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
            timeout=5,
            check=False,
        )
        changes = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        return f"[GIT] Branch: {branch}" + (f" ({changes} changes)" if changes else " (clean)")
    except Exception:  # noqa: BLE001
        return ""


def get_language_stats(path: Path | None = None) -> dict[str, int]:
    """Get language statistics for the repository."""
    path = path or Path.cwd()
    stats: dict[str, int] = {}
    ignore_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "target"}
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for filename in files:
                lang = _LANGUAGE_EXTENSIONS.get(Path(filename).suffix, "Other")
                stats[lang] = stats.get(lang, 0) + 1
    except PermissionError as exc:
        logger.debug("cannot walk %s: %s", path, exc)
    return stats


_LANGUAGE_EXTENSIONS = {
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
            timeout=10,
            check=False,
        )
        files = result.stdout.split("\0")[:-1]

        code_files = [
            f
            for f in files
            if any(f.endswith(ext) for ext in [".py", ".js", ".ts", ".go", ".rs", ".java"])
        ]
        return "\n".join(code_files[:50]) if code_files else "[no code files found]"
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"
