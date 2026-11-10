"""File watcher for APEX — polling-based, zero external deps.

Mirrors OpenCode's watcher UX: background thread, debounced, gitignore-aware.
"""

from __future__ import annotations

import fnmatch
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .config_v2 import apex_config

# ────────────────────────────────────────────────────────────
# Default ignore patterns
# ────────────────────────────────────────────────────────────

DEFAULT_IGNORE_PATTERNS: list[str] = [
    "**/node_modules/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/target/**",
]

# ────────────────────────────────────────────────────────────
# Utility: pattern matching
# ────────────────────────────────────────────────────────────


def _is_bare_glob(pattern: str) -> bool:
    """Whether the pattern is a glob without any directory part."""
    if "/" in pattern:
        return False
    return pattern.startswith("*")


def _is_bare_name(pattern: str) -> bool:
    """Whether the pattern is a plain file name."""
    if "/" in pattern:
        return False
    return "*" not in pattern and "?" not in pattern


def _matches_pattern(path: str, pattern: str) -> bool:
    """Match path against a glob pattern.

    Supports:
      - **/.../**  (directory recursion)
      - *.ext       (extension match)
      - standard fnmatch patterns
    """
    # Normalise to forward slashes
    normalised = path.replace(os.sep, "/")

    if pattern.startswith("*."):
        return fnmatch.fnmatch(normalised, pattern)
    if pattern.startswith("**/"):
        return _matches_tree_pattern(normalised, pattern)
    if _is_bare_glob(pattern):
        return fnmatch.fnmatch(normalised, pattern)
    if _is_bare_name(pattern):
        # Bare filename without glob (e.g. ".env") — match any file with that name
        base = normalised.rsplit("/", 1)[-1]
        return base == pattern
    # Standard fnmatch
    return fnmatch.fnmatch(normalised, pattern)


def _matches_tree_pattern(normalised: str, pattern: str) -> bool:
    """Match a ``**/`` pattern against the path."""
    if pattern.endswith("/**"):
        middle = pattern[3:-3]
        return middle in normalised.split("/")
    # For **/X (match anywhere in tree)
    suffix = pattern[3:]
    return normalised.endswith(suffix) or f"/{suffix}" in normalised or normalised == suffix


def is_ignored(path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the given ignore patterns."""
    normalised = path.replace(os.sep, "/")
    for pattern in patterns:
        cleaned = pattern.strip()
        if not cleaned:
            continue
        if _matches_pattern(normalised, cleaned):
            return True
    return False


# ────────────────────────────────────────────────────────────
# Gitignore parsing
# ────────────────────────────────────────────────────────────


def _load_gitignore_patterns(project_dir: str) -> list[str]:
    """Load patterns from .gitignore files in the project tree."""
    patterns: list[str] = []
    root = Path(project_dir).resolve()

    # Walk up from project_dir to find .gitignore (root and parent dirs)
    for parent in [root] + list(root.parents):
        patterns.extend(_gitignore_patterns(parent / ".gitignore"))
        # Stop at filesystem root
        if parent.parent == parent:
            break

    return patterns


def _gitignore_patterns(gitignore: Path) -> list[str]:
    """The ignore patterns of one .gitignore file."""
    if not gitignore.is_file():
        return []
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    patterns: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Folders: "some_dir/" -> "**/some_dir/**"
        if line.endswith("/"):
            line = f"**/{line}**"
        # Already a glob
        patterns.append(line)
    return patterns


# ────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────


@dataclass
class _Walk:
    """The state of one directory walk."""

    dirpath: str
    rel_dir: str
    patterns: list[str]
    seen: set[str]
    now: float


@dataclass
class WatcherConfig:
    ignore_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    enabled: bool = False


# ────────────────────────────────────────────────────────────
# FileWatcher
# ────────────────────────────────────────────────────────────


class FileWatcher:
    """Polling-based file watcher that runs in a background daemon thread.

    Tracks file mtimes and fires a callback when changes are detected.
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._project_dir: str | None = None
        self._callback: Callable[[str], None] | None = None
        self._mtimes: dict[str, float] = {}
        self._config = WatcherConfig()
        self._poll_interval: float = 1.0
        self._debounce_ms: float = 300.0
        self._pending: dict[str, float] = {}  # path -> detection timestamp
        self._last_fired: dict[str, float] = {}  # path -> last callback timestamp
        self._debounce_timer: threading.Timer | None = None
        self._debounce_lock = threading.Lock()

    def start(self, project_dir: str, callback: Callable[[str], None]) -> None:
        """Start watching *project_dir* for file changes.

        Calls *callback(path)* for each changed file.
        """
        if self._thread and self._thread.is_alive():
            return

        self._project_dir = str(Path(project_dir).resolve())
        self._callback = callback
        self._stop_event.clear()

        # Load config from apex_config.watcher
        raw = apex_config.watcher if hasattr(apex_config, "watcher") else {}
        patterns = list(raw.get("ignore", DEFAULT_IGNORE_PATTERNS))
        enabled = bool(raw.get("enabled", True))
        self._config = WatcherConfig(ignore_patterns=patterns, enabled=enabled)

        if not self._config.enabled:
            return

        # Build initial mtime snapshot
        self._scan()

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the watcher thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._debounce_lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._pending.clear()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_ignored_patterns(self) -> list[str]:
        with self._lock:
            return list(self._config.ignore_patterns)

    def should_ignore(self, file_path: str) -> bool:
        """Check if *file_path* should be ignored."""
        with self._lock:
            return is_ignored(file_path, self._config.ignore_patterns)

    def set_poll_interval(self, seconds: float) -> None:
        self._poll_interval = max(0.1, seconds)

    def set_debounce_ms(self, ms: float) -> None:
        self._debounce_ms = max(0.0, ms)

    # ── Internal ────────────────────────────────────────────

    def _all_patterns(self) -> list[str]:
        """Return config patterns + gitignore patterns."""
        with self._lock:
            patterns = list(self._config.ignore_patterns)
        if self._project_dir:
            patterns.extend(_load_gitignore_patterns(self._project_dir))
        return patterns

    def _scan(self) -> None:
        """Walk *project_dir* and record mtimes for non-ignored files."""
        if not self._project_dir:
            return
        patterns = self._all_patterns()
        new_mtimes: dict[str, float] = {}
        root = Path(self._project_dir)
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                rel_dir = os.path.relpath(dirpath, root)
                if rel_dir == ".":
                    rel_dir = ""
                # Prune ignored directories in-place
                dirnames[:] = self._keep_dirs(dirnames, rel_dir, patterns)

                new_mtimes.update(dict(self._scan_files(dirpath, rel_dir, filenames, patterns)))
        except OSError:
            return

        self._mtimes = new_mtimes

    def _file_mtime(
        self, dirpath: str, rel_dir: str, name: str, patterns: list[str]
    ) -> float | None:
        """The modification time of a file, or ``None`` when it is ignored."""
        fpath = os.path.join(rel_dir, name) if rel_dir else name
        if is_ignored(fpath, patterns):
            return None
        try:
            return os.stat(os.path.join(dirpath, name)).st_mtime
        except OSError:
            return None

    def _scan_files(
        self, dirpath: str, rel_dir: str, filenames: list[str], patterns: list[str]
    ) -> list[tuple[str, float]]:
        """The files of one directory with their modification time."""
        entries = [self._file_entry(dirpath, rel_dir, name, patterns) for name in filenames]
        return [entry for entry in entries if entry is not None]

    def _file_entry(
        self, dirpath: str, rel_dir: str, name: str, patterns: list[str]
    ) -> tuple[str, float] | None:
        """The path and the modification time of a file, when it is tracked."""
        mtime = self._file_mtime(dirpath, rel_dir, name, patterns)
        if mtime is None:
            return None
        return os.path.join(dirpath, name), mtime

    def _poll_loop(self) -> None:
        # Wait one interval first so the initial scan settles before detecting changes
        while not self._stop_event.wait(self._poll_interval):
            self._check_changes()

    def _check_changes(self) -> None:
        if not self._project_dir:
            return
        patterns = self._all_patterns()
        now = time.time()
        seen: set[str] = set()

        for dirpath, dirnames, filenames in os.walk(self._project_dir):
            rel_dir = self._rel_dir(dirpath)
            # Prune ignored dirs
            dirnames[:] = self._keep_dirs(dirnames, rel_dir, patterns)
            self._check_files(_Walk(dirpath, rel_dir, patterns, seen, now), filenames)

        # Remove tracked files that no longer exist
        self._forget_missing(seen)

    def _rel_dir(self, dirpath: str) -> str:
        """The path of a directory relative to the watched root."""
        rel_dir = os.path.relpath(dirpath, self._project_dir or ".")
        return "" if rel_dir == "." else rel_dir

    def _check_files(self, walk: _Walk, filenames: list[str]) -> None:
        """Track every file of one directory."""
        for name in filenames:
            self._check_file(walk, name)

    def _forget_missing(self, seen: set[str]) -> None:
        """Stop tracking the files that no longer exist."""
        for full in list(self._mtimes):
            if full not in seen:
                del self._mtimes[full]

    def _keep_dirs(self, dirnames: list[str], rel_dir: str, patterns: list[str]) -> list[str]:
        """The sub-directories that are not ignored."""
        kept: list[str] = []
        for name in dirnames:
            dpath = os.path.join(rel_dir, name) if rel_dir else name
            if not is_ignored(dpath, patterns):
                kept.append(name)
        return kept

    def _check_file(self, walk: _Walk, name: str) -> None:
        """Track one file and fire the callback when it changed."""
        fpath = os.path.join(walk.rel_dir, name) if walk.rel_dir else name
        full = os.path.join(walk.dirpath, name)
        if is_ignored(fpath, walk.patterns):
            return
        walk.seen.add(full)
        try:
            mtime = os.stat(full).st_mtime
        except OSError:
            return

        prev = self._mtimes.get(full)
        if prev is None or abs(mtime - prev) > 1e-6:
            self._on_change(full, walk.now)
        self._mtimes[full] = mtime

    def _on_change(self, path: str, timestamp: float) -> None:
        """Debounce and fire the callback."""
        with self._debounce_lock:
            # Skip if we already fired for this path within the cooldown window
            last = self._last_fired.get(path, 0.0)
            if (timestamp - last) * 1000.0 < self._debounce_ms:
                return

            self._pending[path] = timestamp
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                self._debounce_ms / 1000.0, self._flush_debounced
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _flush_debounced(self) -> None:
        """Fire the callback for all pending paths."""
        with self._debounce_lock:
            pending = list(self._pending.keys())
            now = time.time()
            for p in pending:
                self._last_fired[p] = now
            self._pending.clear()
            self._debounce_timer = None

        cb = self._callback
        if cb is not None:
            for path in pending:
                try:
                    cb(path)
                except Exception:  # noqa: S110, BLE001
                    pass


# ────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────

watcher = FileWatcher()


__all__ = [
    "FileWatcher",
    "WatcherConfig",
    "is_ignored",
    "watcher",
]
