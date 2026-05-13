"""Tests for apex/watcher.py — 100% line coverage."""

from __future__ import annotations

import os
import time
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from apex.watcher import (
    FileWatcher,
    WatcherConfig,
    DEFAULT_IGNORE_PATTERNS,
    _matches_pattern,
    _load_gitignore_patterns,
    is_ignored,
    watcher,
)


# ────────────────────────────────────────────────────────────
# _matches_pattern  (full branch coverage)
# ────────────────────────────────────────────────────────────


class TestMatchesPattern:
    def test_extension_pattern_star_dot(self):
        """pattern.startswith('*.') branch"""
        assert _matches_pattern("server.log", "*.log")
        assert not _matches_pattern("server.txt", "*.log")

    def test_double_star_directory_recursion(self):
        """pattern.startswith('**/') and pattern.endswith('/**') branch"""
        assert _matches_pattern("a/node_modules/pkg/index.js", "**/node_modules/**")
        assert not _matches_pattern("a/node_dist/pkg/index.js", "**/node_modules/**")

    def test_double_star_prefix_only(self):
        """pattern.startswith('**/') without trailing /** branch"""
        assert _matches_pattern("some/deep/.env", "**/.env")
        assert _matches_pattern(".env", "**/.env")
        assert _matches_pattern("dir/.env", "**/.env")
        assert not _matches_pattern(".environ", "**/.env")

    def test_bare_glob_starting_with_star(self):
        """/ not in pattern and pattern.startswith('*') branch"""
        assert _matches_pattern("foo_test", "*test")
        assert not _matches_pattern("foo", "*test")

    def test_bare_filename_no_glob_chars(self):
        """Bare filename without *, ?, / branch"""
        assert _matches_pattern("/some/path/.env", ".env")
        assert _matches_pattern(".env", ".env")
        assert not _matches_pattern("/some/path/.envx", ".env")

    def test_standard_fnmatch_with_path(self):
        """Fallback fnmatch branch"""
        assert _matches_pattern("src/main.py", "src/*.py")
        assert not _matches_pattern("src/main.txt", "src/*.py")
        assert _matches_pattern("src/util/helper.py", "src/**/*.py")

    def test_empty_pattern(self):
        assert not _matches_pattern("foo.log", "")


# ────────────────────────────────────────────────────────────
# is_ignored
# ────────────────────────────────────────────────────────────


class TestIsIgnored:
    def test_matches_pattern(self):
        assert is_ignored("server.log", ["*.log", "**/node_modules/**"])
        assert is_ignored("app/node_modules/pkg/index.js", ["*.log", "**/node_modules/**"])

    def test_no_match(self):
        assert not is_ignored("main.py", ["*.log", "**/node_modules/**"])

    def test_empty_patterns_list(self):
        assert not is_ignored("foo.log", [])

    def test_blank_lines_skipped(self):
        assert is_ignored("foo.log", ["", "  ", "*.log"])

    def test_os_sep_normalized(self):
        assert is_ignored("foo/bar.log", ["*.log"])

    def test_double_star_node_modules_pattern(self):
        assert is_ignored("project/node_modules/pkg/index.js", ["**/node_modules/**"])


# ────────────────────────────────────────────────────────────
# _load_gitignore_patterns
# ────────────────────────────────────────────────────────────


class TestLoadGitignorePatterns:
    def test_no_gitignore_returns_empty(self, tmp_path):
        assert _load_gitignore_patterns(str(tmp_path)) == []

    def test_loads_simple_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\nbuild/\n# comment\n\n.env\n")
        patterns = _load_gitignore_patterns(str(tmp_path))
        assert "*.log" in patterns
        assert "**/build/**" in patterns
        assert ".env" in patterns
        assert "# comment" not in patterns

    def test_walks_parent_directories(self, tmp_path):
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (tmp_path / ".gitignore").write_text("*.log\n")
        patterns = _load_gitignore_patterns(str(sub))
        assert "*.log" in patterns

    def test_stops_at_filesystem_root(self):
        patterns = _load_gitignore_patterns("/")
        assert isinstance(patterns, list)

    def test_oserror_on_read_is_silenced(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        with patch.object(Path, "read_text", side_effect=OSError("permission")):
            patterns = _load_gitignore_patterns(str(tmp_path))
        assert patterns == []


# ────────────────────────────────────────────────────────────
# WatcherConfig
# ────────────────────────────────────────────────────────────


class TestWatcherConfig:
    def test_default_ignore_patterns(self):
        cfg = WatcherConfig()
        assert cfg.ignore_patterns == DEFAULT_IGNORE_PATTERNS
        assert cfg.enabled is False

    def test_custom_values(self):
        cfg = WatcherConfig(ignore_patterns=["*.tmp"], enabled=True)
        assert cfg.ignore_patterns == ["*.tmp"]
        assert cfg.enabled is True


# ────────────────────────────────────────────────────────────
# FileWatcher — unit-level
# ────────────────────────────────────────────────────────────


class TestFileWatcherUnit:
    def test_init_state(self):
        fw = FileWatcher()
        assert fw._thread is None
        assert fw._project_dir is None
        assert fw._callback is None
        assert not fw.is_running()

    def test_is_running_false_initially(self):
        fw = FileWatcher()
        assert not fw.is_running()

    def test_get_ignored_patterns_returns_copy(self):
        fw = FileWatcher()
        patterns = fw.get_ignored_patterns()
        assert patterns == DEFAULT_IGNORE_PATTERNS
        patterns.append("*.new")
        assert fw.get_ignored_patterns() == DEFAULT_IGNORE_PATTERNS

    def test_should_ignore_default_patterns(self):
        fw = FileWatcher()
        assert fw.should_ignore("node_modules/pkg/index.js")
        assert fw.should_ignore(".git/config")
        assert fw.should_ignore("__pycache__/foo.pyc")
        assert fw.should_ignore("dist/bundle.js")
        assert not fw.should_ignore("src/main.py")

    def test_should_ignore_custom(self):
        fw = FileWatcher()
        fw._config.ignore_patterns = ["*.secret"]
        assert fw.should_ignore("keys.secret")
        assert not fw.should_ignore("main.py")

    def test_set_poll_interval_clamps(self):
        fw = FileWatcher()
        fw.set_poll_interval(0.01)
        assert fw._poll_interval == 0.1
        fw.set_poll_interval(5.0)
        assert fw._poll_interval == 5.0

    def test_set_debounce_ms_clamps(self):
        fw = FileWatcher()
        fw.set_debounce_ms(-1)
        assert fw._debounce_ms == 0.0
        fw.set_debounce_ms(500)
        assert fw._debounce_ms == 500.0

    def test_stop_when_not_running_does_nothing(self):
        fw = FileWatcher()
        fw.stop()

    def test_stop_cancels_debounce_timer(self):
        fw = FileWatcher()
        timer = threading.Timer(10.0, lambda: None)
        timer.daemon = True
        fw._debounce_timer = timer
        fw._pending["test.py"] = time.time()
        fw.stop()
        assert fw._debounce_timer is None
        assert fw._pending == {}


# ────────────────────────────────────────────────────────────
# FileWatcher — start / stop lifecycle
# ────────────────────────────────────────────────────────────


class TestLifecycle:
    def test_start_stops_cleanly(self, tmp_path):
        fw = FileWatcher()
        calls: list[str] = []
        fw.set_poll_interval(0.2)
        fw.set_debounce_ms(50)
        fw.start(str(tmp_path), calls.append)
        assert fw.is_running()
        fw.stop()
        assert not fw.is_running()

    def test_start_disabled_does_not_start_thread(self, tmp_path):
        fw = FileWatcher()
        fw._config.enabled = False
        with patch("apex.watcher.apex_config") as mock_cfg:
            mock_cfg.watcher = {"enabled": False, "ignore": []}
            fw.start(str(tmp_path), lambda p: None)
        assert not fw.is_running()
        assert fw._thread is None

    def test_start_when_already_running_returns_early(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.2)
        fw.set_debounce_ms(50)
        fw.start(str(tmp_path), lambda p: None)
        thread = fw._thread
        fw.start(str(tmp_path), lambda p: None)
        assert fw._thread is thread
        fw.stop()

    def test_start_uses_apex_config_watcher(self, tmp_path):
        custom_patterns = ["*.custom"]
        with patch("apex.watcher.apex_config") as mock_cfg:
            mock_cfg.watcher = {"ignore": custom_patterns, "enabled": True}
            fw = FileWatcher()
            fw.set_poll_interval(0.2)
            fw.set_debounce_ms(50)
            fw.start(str(tmp_path), lambda p: None)
            assert fw.get_ignored_patterns() == custom_patterns
            fw.stop()

    def test_is_running_reflects_thread_state(self, tmp_path):
        fw = FileWatcher()
        assert not fw.is_running()
        fw.set_poll_interval(0.2)
        fw.start(str(tmp_path), lambda p: None)
        assert fw.is_running()
        fw.stop()
        assert not fw.is_running()


# ────────────────────────────────────────────────────────────
# FileWatcher — callback invocation & debounce
# ────────────────────────────────────────────────────────────


class TestCallbackAndDebounce:
    def test_callback_fires_when_file_created(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        results: list[str] = []
        fw.start(str(tmp_path), results.append)
        (tmp_path / "new.txt").write_text("hello")
        time.sleep(0.6)
        fw.stop()
        assert any("new.txt" in p for p in results)

    def test_callback_fires_when_file_modified(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("v1")
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        results: list[str] = []
        fw.start(str(tmp_path), results.append)
        time.sleep(0.3)
        f.write_text("v2")
        time.sleep(0.6)
        fw.stop()
        assert any("existing.txt" in p for p in results)

    def test_exception_in_callback_does_not_crash(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        call_count: list[int] = [0]

        def cb(path: str) -> None:
            call_count[0] += 1
            raise RuntimeError("boom")

        fw.start(str(tmp_path), cb)
        (tmp_path / "boom.txt").write_text("x")
        time.sleep(0.6)
        fw.stop()
        assert call_count[0] >= 1
        assert fw._thread is None  # stopped cleanly

    def test_cooldown_skips_rapid_repeated_changes(self, tmp_path):
        """_on_change early-returns when within cooldown of last fire."""
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.enabled = True
        fw._callback = lambda p: None
        now = time.time()
        fw._last_fired["fast.py"] = now
        fw._on_change("fast.py", now)
        assert "fast.py" not in fw._pending

    def test_cooldown_allows_different_path(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.enabled = True
        fw._callback = lambda p: None
        now = time.time()
        fw._last_fired["fast.py"] = now
        fw._on_change("slow.py", now)
        assert "slow.py" in fw._pending
        fw._pending.clear()

    def test_debounce_timer_cancelled_on_new_change(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.enabled = True
        fw._callback = lambda p: None
        fw._on_change("a.py", time.time())
        t1 = fw._debounce_timer
        assert t1 is not None
        fw._on_change("a.py", time.time())
        t2 = fw._debounce_timer
        assert t2 is not t1
        t2.cancel()
        fw._pending.clear()

    def test_flush_debounced_with_no_callback(self):
        fw = FileWatcher()
        fw._pending["orphan.py"] = time.time()
        fw._flush_debounced()
        assert fw._pending == {}
        assert fw._debounce_timer is None


# ────────────────────────────────────────────────────────────
# FileWatcher — _scan & _check_changes internals
# ────────────────────────────────────────────────────────────


class TestScan:
    def test_scan_with_no_project_dir_does_nothing(self):
        fw = FileWatcher()
        fw._scan()
        assert fw._mtimes == {}

    def test_scan_populates_mtimes(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.txt").write_text("world")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._scan()
        assert str(tmp_path / "a.txt") in fw._mtimes
        assert str(tmp_path / "sub" / "b.txt") in fw._mtimes

    def test_scan_skips_ignored_files(self, tmp_path):
        (tmp_path / "app.log").write_text("log")
        (tmp_path / "main.py").write_text("code")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.ignore_patterns = ["*.log"]
        fw._scan()
        assert str(tmp_path / "main.py") in fw._mtimes
        assert str(tmp_path / "app.log") not in fw._mtimes

    def test_scan_prunes_ignored_directories(self, tmp_path):
        (tmp_path / "node_modules" / "pkg" / "index.js").parents[0].mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "index.js").write_text("x")
        (tmp_path / "src" / "main.py").parents[0].mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("x")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.ignore_patterns = ["**/node_modules/**"]
        fw._scan()
        assert str(tmp_path / "src" / "main.py") in fw._mtimes
        node_files = [p for p in fw._mtimes if "node_modules" in p]
        assert node_files == []

    def test_scan_oserror_caught(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path / "nonexistent")
        fw._scan()
        assert fw._mtimes == {}

    def test_scan_handles_oserror_on_stat(self, tmp_path):
        f = tmp_path / "ghost.txt"
        f.write_text("x")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._scan()
        full = str(f)
        assert full in fw._mtimes
        os.remove(full)
        fw._scan()
        assert full not in fw._mtimes

    def test_scan_oserror_on_walk_caught(self, tmp_path):
        """The outer try/except OSError around os.walk in _scan."""
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        with patch("os.walk", side_effect=OSError("permission denied")):
            fw._scan()
        assert fw._mtimes == {}


class TestCheckChanges:
    def test_check_changes_no_project_dir(self):
        fw = FileWatcher()
        fw._check_changes()
        assert fw._mtimes == {}

    def test_check_changes_detects_new_file(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.enabled = True
        (tmp_path / "pre.txt").write_text("x")
        fw._scan()

        _before = dict(fw._mtimes)
        (tmp_path / "new.txt").write_text("y")
        fw._check_changes()
        assert str(tmp_path / "new.txt") in fw._mtimes
        assert str(tmp_path / "pre.txt") in fw._mtimes

    def test_check_changes_removes_stale_mtimes(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        ghost = str(tmp_path / "ghost.txt")
        fw._mtimes[ghost] = 100.0
        fw._check_changes()
        assert ghost not in fw._mtimes

    def test_check_changes_skips_ignored_dirs(self, tmp_path):
        nd = tmp_path / "node_modules" / "p"
        nd.mkdir(parents=True)
        (nd / "i.js").write_text("x")
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("x")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.ignore_patterns = ["**/node_modules/**"]
        fw._scan()
        # _scan already prunes
        assert str(src / "main.py") in fw._mtimes
        node_files = [p for p in fw._mtimes if "node_modules" in p]
        assert node_files == []

    def test_check_changes_prunes_ignored_dirs(self, tmp_path):
        nd = tmp_path / "node_modules" / "p"
        nd.mkdir(parents=True)
        (nd / "i.js").write_text("x")
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("x")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.ignore_patterns = ["**/node_modules/**"]
        fw._config.enabled = True
        fw._scan()
        fw._check_changes()
        assert str(src / "main.py") in fw._mtimes
        node_files = [p for p in fw._mtimes if "node_modules" in p]
        assert node_files == []

    def test_check_changes_ignored_file_skipped(self, tmp_path):
        (tmp_path / "app.log").write_text("log")
        (tmp_path / "main.py").write_text("code")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.ignore_patterns = ["*.log"]
        fw._config.enabled = True
        fw._scan()
        fw._check_changes()
        # main.py tracked, app.log not
        assert str(tmp_path / "main.py") in fw._mtimes
        assert str(tmp_path / "app.log") not in fw._mtimes

    def test_check_changes_handles_dangling_symlink(self, tmp_path):
        """OSError from os.stat in _check_changes caught by except."""
        target = tmp_path / "nonexistent_target"
        link = tmp_path / "dangling"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlinks not supported on this platform")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._config.enabled = True
        link2 = tmp_path / "good.txt"
        link2.write_text("ok")
        fw._scan()
        assert str(link2) in fw._mtimes
        # _check_changes stat on dangling symlink → OSError caught
        fw._check_changes()
        assert str(link2) in fw._mtimes
        assert str(link) not in fw._mtimes


# ────────────────────────────────────────────────────────────
# _all_patterns
# ────────────────────────────────────────────────────────────


class TestAllPatterns:
    def test_returns_config_patterns(self):
        fw = FileWatcher()
        patterns = fw._all_patterns()
        assert DEFAULT_IGNORE_PATTERNS[0] in patterns

    def test_extends_with_gitignore_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.custom\n")
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        patterns = fw._all_patterns()
        assert "*.custom" in patterns

    def test_no_project_dir_no_gitignore(self):
        fw = FileWatcher()
        patterns = fw._all_patterns()
        _gitignore_patterns = _load_gitignore_patterns(".")
        # No gitignore loaded since _project_dir is None
        assert patterns == DEFAULT_IGNORE_PATTERNS


# ────────────────────────────────────────────────────────────
# watcher singleton
# ────────────────────────────────────────────────────────────


class TestWatcherSingleton:
    def test_singleton_is_filewatcher(self):
        from apex.watcher import watcher as w

        assert isinstance(w, FileWatcher)

    def test_singleton_not_running_initially(self):
        assert not watcher.is_running()


# ────────────────────────────────────────────────────────────
# __all__
# ────────────────────────────────────────────────────────────


class TestAllExports:
    def test_all_exports(self):
        from apex.watcher import __all__ as all_

        assert "FileWatcher" in all_
        assert "WatcherConfig" in all_
        assert "is_ignored" in all_
        assert "watcher" in all_


# ────────────────────────────────────────────────────────────
# Integration — end-to-end watcher with real file changes
# ────────────────────────────────────────────────────────────


class TestIntegration:
    def test_watcher_ignores_non_existent_directory(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        fw.start(str(tmp_path / "does_not_exist"), lambda p: None)
        time.sleep(0.3)
        # os.walk silently handles non-existent dirs — watcher runs but finds nothing
        # Then stop, verifying no crash
        fw.stop()
        assert not fw.is_running()

    def test_watcher_does_not_crash_on_empty_project(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        fw.start(str(tmp_path), lambda p: None)
        time.sleep(0.3)
        assert fw.is_running()
        fw.stop()

    def test_multiple_files_detected(self, tmp_path):
        fw = FileWatcher()
        fw.set_poll_interval(0.1)
        fw.set_debounce_ms(30)
        results: list[str] = []
        fw.start(str(tmp_path), results.append)
        time.sleep(0.2)
        (tmp_path / "f1.txt").write_text("a")
        (tmp_path / "f2.txt").write_text("b")
        time.sleep(0.6)
        fw.stop()
        detected = {Path(p).name for p in results}
        assert "f1.txt" in detected
        assert "f2.txt" in detected

    def test_pending_cleared_on_stop(self, tmp_path):
        fw = FileWatcher()
        fw._project_dir = str(tmp_path)
        fw._pending["stuck.py"] = time.time()
        fw.stop()
        assert fw._pending == {}
