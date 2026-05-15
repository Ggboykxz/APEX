"""File watcher for APEX — polling-based, zero external deps.

Mirrors OpenCode's watcher UX: background thread, debounced, gitignore-aware.
"""

from __future__ import annotations

import fnmatch
import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

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


def _matches_pattern(path: str, pattern: str) -> bool:
    """Match path against a glob pattern.

    Supports:
      - **/.../**  (directory recursion)
      - *.ext       (extension match)
      - standard fnmatch patterns
    """
    # Normalise to forward slashes
    normalised = path.replace(os.sep, "/")

    # If pattern is an extension pattern like *.log
    if pattern.startswith("*."):
        return fnmatch.fnmatch(normalised, pattern)

    # For **/X/** style patterns
    if pattern.startswith("**/") and pattern.endswith("/**"):
        middle = pattern[3:-3]
        parts = normalised.split("/")
        return middle in parts

    # For **/X (match anywhere in tree)
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        return normalised.endswith(suffix) or f"/{suffix}" in normalised or normalised == suffix

    # Bare filename or extension pattern (e.g. ".env", "*.log")
    if "/" not in pattern and pattern.startswith("*"):
        return fnmatch.fnmatch(normalised, pattern)

    # Bare filename without glob (e.g. ".env") — match any file with that name
    if "/" not in pattern and "*" not in pattern and "?" not in pattern:
        base = normalised.rsplit("/", 1)[-1]
        return base == pattern

    # Standard fnmatch
    return fnmatch.fnmatch(normalised, pattern)


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
        gi = parent / ".gitignore"
        if gi.is_file():
            try:
                for line in gi.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Folders: "some_dir/" -> "**/some_dir/**"
                        if line.endswith("/"):
                            line = f"**/{line}**"
                        # Already a glob
                        patterns.append(line)
            except OSError:
                pass
        # Stop at filesystem root
        if parent.parent == parent:
            break

    return patterns


# ────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────


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
                # Prune ignored directories in-place
                rel_dir = os.path.relpath(dirpath, root)
                if rel_dir == ".":
                    rel_dir = ""
                filtered: list[str] = []
                for d in dirnames:
                    dpath = os.path.join(rel_dir, d) if rel_dir else d
                    if not is_ignored(dpath, patterns):
                        filtered.append(d)
                dirnames[:] = filtered

                for f in filenames:
                    fpath = os.path.join(rel_dir, f) if rel_dir else f
                    if is_ignored(fpath, patterns):
                        continue
                    full = os.path.join(dirpath, f)
                    try:
                        st = os.stat(full)
                        new_mtimes[full] = st.st_mtime
                    except OSError:
                        pass
        except OSError:
            return

        self._mtimes = new_mtimes

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
            rel_dir = os.path.relpath(dirpath, self._project_dir)
            if rel_dir == ".":
                rel_dir = ""

            # Prune ignored dirs
            filtered: list[str] = []
            for d in dirnames:
                dpath = os.path.join(rel_dir, d) if rel_dir else d
                if not is_ignored(dpath, patterns):
                    filtered.append(d)
            dirnames[:] = filtered

            for f in filenames:
                fpath = os.path.join(rel_dir, f) if rel_dir else f
                full = os.path.join(dirpath, f)
                if is_ignored(fpath, patterns):
                    continue
                seen.add(full)
                try:
                    st = os.stat(full)
                    mtime = st.st_mtime
                except OSError:
                    continue

                prev = self._mtimes.get(full)
                if prev is None or abs(mtime - prev) > 1e-6:
                    self._on_change(full, now)
                self._mtimes[full] = mtime

        # Remove tracked files that no longer exist
        for full in list(self._mtimes):
            if full not in seen:
                del self._mtimes[full]

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
                except Exception:
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
