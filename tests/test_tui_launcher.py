"""Tests for apex/tui_launcher.py — runtime discovery, dependencies and React/Ink patching."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import tui_launcher
from apex.tui_launcher import (
    _clear_stale_lockfiles,
    _ensure_bun,
    _ensure_tsx,
    _find_bun,
    _find_node,
    _find_npx,
    _install_bun,
    _install_tsx,
    _patch_package_versions,
    _patch_tui_package_json,
    _run_dependency_install,
    _setup_tui_frontend,
)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


class TestFindTuiDir:
    def test_dev_path(self, tmp_path, monkeypatch):
        dev = tmp_path / "repo" / "tui-frontend"
        (dev / "src").mkdir(parents=True)
        (dev / "src" / "App.tsx").write_text("")
        monkeypatch.setattr(tui_launcher, "__file__", str(tmp_path / "repo" / "apex" / "main.py"))
        assert tui_launcher._find_tui_dir() == dev

    def test_grandparent_candidate(self, tmp_path, monkeypatch):
        candidate = tmp_path / "root" / "tui-frontend"
        (candidate / "src").mkdir(parents=True)
        (candidate / "src" / "App.tsx").write_text("")
        monkeypatch.setattr(
            tui_launcher, "__file__", str(tmp_path / "root" / "apex" / "pkg" / "main.py")
        )
        assert tui_launcher._find_tui_dir() == candidate

    def test_home_candidate(self, tmp_path, fake_home, monkeypatch):
        candidate = fake_home / ".apex" / "tui-frontend"
        (candidate / "src").mkdir(parents=True)
        (candidate / "src" / "App.tsx").write_text("")
        monkeypatch.setattr(tui_launcher, "__file__", str(tmp_path / "elsewhere" / "main.py"))
        assert tui_launcher._find_tui_dir() == candidate

    def test_not_found(self, tmp_path, fake_home, monkeypatch):
        monkeypatch.setattr(tui_launcher, "__file__", str(tmp_path / "nowhere" / "main.py"))
        assert tui_launcher._find_tui_dir() is None


class TestFindBun:
    def test_home_candidate(self, fake_home):
        bun = fake_home / ".bun" / "bin" / "bun"
        bun.parent.mkdir(parents=True)
        bun.write_text("")
        assert _find_bun() == str(bun)

    def test_win32_candidates(self, fake_home, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        profile = fake_home / "profile"
        bun = profile / ".bun" / "bin" / "bun.exe"
        bun.parent.mkdir(parents=True)
        bun.write_text("")
        monkeypatch.setenv("USERPROFILE", str(profile))
        monkeypatch.setenv("LOCALAPPDATA", str(fake_home / "local"))
        assert _find_bun() == str(bun)

    def test_falls_back_to_which(self, fake_home, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/bun" if name == "bun" else None)
        assert _find_bun() == "/fake/bun"

    def test_not_found_anywhere(self, fake_home, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        assert _find_bun() is None


class TestFindNodeNpx:
    def test_find_node(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/node" if name == "node" else None)
        assert _find_node() == "/fake/node"

    def test_find_node_missing(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        assert _find_node() is None

    def test_find_npx(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/npx" if name == "npx" else None)
        assert _find_npx() == "/fake/npx"


class TestInstallBun:
    def _ui(self):
        return MagicMock()

    def test_no_npx(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_npx", lambda: None)
        ui = self._ui()
        assert _install_bun(ui) is None
        ui.print_error.assert_called_once()

    def test_npx_fails(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_npx", lambda: "/fake/npx")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=1))
        ui = self._ui()
        assert _install_bun(ui) is None

    def test_install_succeeds(self, monkeypatch, fake_home, tmp_path):
        bun = tmp_path / "installed-bun"
        bun.write_text("")
        monkeypatch.setattr(tui_launcher, "_find_npx", lambda: "/fake/npx")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        monkeypatch.setattr(shutil, "which", lambda name: str(bun) if name == "bun" else None)
        ui = self._ui()
        assert _install_bun(ui) == str(bun)
        ui.print_success.assert_called_once()

    def test_installed_but_not_on_path(self, monkeypatch, fake_home):
        monkeypatch.setattr(tui_launcher, "_find_npx", lambda: "/fake/npx")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        monkeypatch.setattr(shutil, "which", lambda name: None)
        ui = self._ui()
        assert _install_bun(ui) is None

    def test_subprocess_exception(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_npx", lambda: "/fake/npx")

        def boom(*a, **k):
            raise OSError("no network")

        monkeypatch.setattr(subprocess, "run", boom)
        assert _install_bun(self._ui()) is None


class TestClearStaleLockfiles:
    def test_removes_lockfiles(self, tmp_path):
        for name in ("bun.lock", "bun.lockb", "package-lock.json"):
            (tmp_path / name).write_text("")
        _clear_stale_lockfiles(tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_missing_files_ok(self, tmp_path):
        _clear_stale_lockfiles(tmp_path)  # no-op, no error

    def test_unlink_error_swallowed(self, tmp_path):
        (tmp_path / "bun.lock").mkdir()
        _clear_stale_lockfiles(tmp_path)
        assert (tmp_path / "bun.lock").is_dir()


class TestRunDependencyInstall:
    def test_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        assert _run_dependency_install(["bun", "install"], tmp_path, 120) is True

    def test_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=1))
        assert _run_dependency_install(["bun", "install"], tmp_path, 120) is False

    def test_exception(self, tmp_path, monkeypatch):
        def boom(*a, **k):
            raise OSError("spawn failed")

        monkeypatch.setattr(subprocess, "run", boom)
        assert _run_dependency_install(["bun", "install"], tmp_path, 120) is False


class TestSetupTuiFrontend:
    def test_deps_already_present(self, tmp_path):
        (tmp_path / "node_modules" / "ink").mkdir(parents=True)
        ui = MagicMock()
        with patch.object(tui_launcher, "_run_dependency_install") as mock_install:
            assert _setup_tui_frontend(tmp_path, ui) is True
        mock_install.assert_not_called()

    def test_bun_install(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: "/fake/bun")
        monkeypatch.setattr(tui_launcher, "_run_dependency_install", lambda *a: True)
        ui = MagicMock()
        assert _setup_tui_frontend(tmp_path, ui) is True
        ui.print_success.assert_called_once()

    def test_npm_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/npm" if name == "npm" else None)

        def fake_install(command, tui_dir, timeout):
            assert command[0] == "/fake/npm"
            return True

        monkeypatch.setattr(tui_launcher, "_run_dependency_install", fake_install)
        ui = MagicMock()
        assert _setup_tui_frontend(tmp_path, ui) is True

    def test_both_fail(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(shutil, "which", lambda name: None)
        monkeypatch.setattr(tui_launcher, "_run_dependency_install", lambda *a: False)
        ui = MagicMock()
        assert _setup_tui_frontend(tmp_path, ui) is False
        ui.print_error.assert_called_once()

    def test_clears_lockfiles_before_install(self, tmp_path, monkeypatch):
        (tmp_path / "bun.lock").write_text("")
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(shutil, "which", lambda name: None)
        monkeypatch.setattr(tui_launcher, "_run_dependency_install", lambda *a: False)
        _setup_tui_frontend(tmp_path, MagicMock())
        assert not (tmp_path / "bun.lock").exists()


class TestEnsureTsx:
    def test_local_tsx(self, tmp_path):
        tsx = tmp_path / "node_modules" / ".bin" / "tsx"
        tsx.parent.mkdir(parents=True)
        tsx.write_text("")
        assert _ensure_tsx(tmp_path) == str(tsx)

    def test_which_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/tsx" if name == "tsx" else None)
        assert _ensure_tsx(tmp_path) == "/fake/tsx"

    def test_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        assert _ensure_tsx(tmp_path) is None


class TestInstallTsx:
    def test_no_npm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: None)
        assert _install_tsx(tmp_path, MagicMock()) is None

    def test_npm_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/npm" if name == "npm" else None)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: "/fake/tsx")
        ui = MagicMock()
        assert _install_tsx(tmp_path, ui) == "/fake/tsx"
        ui.print_success.assert_called_once()

    def test_npm_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/npm" if name == "npm" else None)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=1))
        assert _install_tsx(tmp_path, MagicMock()) is None

    def test_exception(self, tmp_path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda name: "/fake/npm" if name == "npm" else None)

        def boom(*a, **k):
            raise OSError("spawn failed")

        monkeypatch.setattr(subprocess, "run", boom)
        assert _install_tsx(tmp_path, MagicMock()) is None


class TestPatchPackageVersions:
    def test_react19_downgraded(self):
        deps = {"react": "^19.0.0", "react-dom": "^19.0.0"}
        assert _patch_package_versions(deps, {}) is True
        assert deps["react"] == "^18.3.1"
        assert deps["react-dom"] == "^19.0.0"

    def test_reconciler_added(self):
        deps = {"react": "^18.3.1"}
        assert _patch_package_versions(deps, {}) is True
        assert deps["react-reconciler"] == "^0.29.2"

    def test_types_react_downgraded(self):
        dev = {"@types/react": "^19.0.0"}
        assert _patch_package_versions({}, dev) is True
        assert dev["@types/react"] == "^18.3.0"

    def test_typescript_downgraded(self):
        dev = {"typescript": "^6.0.0"}
        assert _patch_package_versions({}, dev) is True
        assert dev["typescript"] == "^5.7.0"

    def test_nothing_to_patch(self):
        deps = {"react": "^18.3.1", "react-reconciler": "^0.29.2"}
        dev = {"@types/react": "^18.3.0", "typescript": "^5.7.0"}
        assert _patch_package_versions(deps, dev) is False


class TestPatchTuiPackageJson:
    def test_missing_file_noop(self, tmp_path):
        _patch_tui_package_json(tmp_path)  # no package.json, no error

    def test_patches_react19_on_disk(self, tmp_path):
        pkg = {"name": "t", "dependencies": {"react": "^19.0.0"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        _patch_tui_package_json(tmp_path)
        data = json.loads((tmp_path / "package.json").read_text())
        assert data["dependencies"]["react"] == "^18.3.1"
        assert data["dependencies"]["react-reconciler"] == "^0.29.2"

    def test_already_compatible_untouched(self, tmp_path):
        pkg = {
            "dependencies": {"react": "^18.3.1", "react-reconciler": "^0.29.2"},
            "devDependencies": {"@types/react": "^18.3.0", "typescript": "^5.7.0"},
        }
        path = tmp_path / "package.json"
        path.write_text(json.dumps(pkg))
        before = path.read_text()
        _patch_tui_package_json(tmp_path)
        assert path.read_text() == before

    def test_corrupt_json_swallowed(self, tmp_path):
        (tmp_path / "package.json").write_text("{not json")
        _patch_tui_package_json(tmp_path)  # logs a warning, no raise


class TestEnsureBun:
    def test_already_installed(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: "/fake/bun")
        ui = MagicMock()
        assert _ensure_bun(ui) is True
        ui.print_success.assert_called_once()

    def test_install_fails(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(tui_launcher, "_install_bun", lambda ui: None)
        ui = MagicMock()
        assert _ensure_bun(ui) is False
        ui.print_error.assert_called_once()

    def test_install_succeeds(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(tui_launcher, "_install_bun", lambda ui: "/new/bun")
        ui = MagicMock()
        assert _ensure_bun(ui) is True
