"""Tests for apex/tui_launcher.py — frontend download/install commands."""

import shutil
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import tui_launcher
from apex.tui_launcher import (
    _clone_tui_frontend,
    _download_tui_frontend,
    _ensure_tui_frontend,
    _extract_tui_frontend,
    _install_tui_command,
)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def _make_tarball(source: Path, arcname_prefix: str = "APEX-main", members=None) -> Path:
    source.mkdir(parents=True, exist_ok=True)
    tb = source / "repo.tar.gz"
    if members is None:
        members = ("README.md", "tui-frontend/src/App.tsx", "tui-frontend/package.json")
    with tarfile.open(tb, "w:gz") as tar:
        for name in members:
            path = source / arcname_prefix / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")
            tar.add(path, arcname=arcname_prefix + "/" + name)
    return tb


class TestCloneTuiFrontend:
    def test_clone_failure(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=128, stderr="boom")):
            assert _clone_tui_frontend(tmp_path, tmp_path / "target", MagicMock()) is None

    def test_clone_missing_tui_dir(self, tmp_path):
        repo = tmp_path / "apex-repo" / "content"
        (repo / "other").mkdir(parents=True)
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            assert _clone_tui_frontend(tmp_path, tmp_path / "target", MagicMock()) is None

    def test_clone_success(self, tmp_path):
        repo = tmp_path / "apex-repo" / "content"
        (repo / "tui-frontend" / "src").mkdir(parents=True)
        (repo / "tui-frontend" / "src" / "App.tsx").write_text("x")
        target = tmp_path / "target"
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = _clone_tui_frontend(tmp_path, target, MagicMock())
        assert result == target
        assert (target / "src" / "App.tsx").exists()


class TestExtractTuiFrontend:
    def test_extract_success(self, tmp_path):
        work = tmp_path / "work"
        work.mkdir()
        tb = _make_tarball(work)
        target = tmp_path / "target"
        result = _extract_tui_frontend(tb, tmp_path / "out", target, MagicMock())
        assert result == target
        assert (target / "src" / "App.tsx").exists()
        assert not (target / "README.md").exists()

    def test_extract_missing_tui(self, tmp_path):
        tb_path = _make_tarball(tmp_path / "work", members=("README.md",))
        ui = MagicMock()
        assert _extract_tui_frontend(tb_path, tmp_path / "out", tmp_path / "t", ui) is None
        ui.print_error.assert_called_once()


class TestDownloadTuiFrontend:
    def test_tarball_path(self, tmp_path, monkeypatch):
        tb = _make_tarball(tmp_path / "src")
        target = tmp_path / "target"

        def fake_retrieve(url, dst):
            shutil.copyfile(str(tb), dst)

        monkeypatch.setattr("urllib.request.urlretrieve", fake_retrieve)
        result = _download_tui_frontend(target, MagicMock())
        assert result == target
        assert (target / "src" / "App.tsx").exists()

    def test_falls_back_to_clone_on_download_error(self, tmp_path, monkeypatch):
        target = tmp_path / "target"

        def boom(url, dst):
            raise OSError("no network")

        monkeypatch.setattr("urllib.request.urlretrieve", boom)
        monkeypatch.setattr(tui_launcher, "_clone_tui_frontend", lambda tmp, tgt, ui: tgt)
        result = _download_tui_frontend(target, MagicMock())
        assert result == target

    def test_tarball_without_tui(self, tmp_path, monkeypatch):
        tb = _make_tarball(tmp_path / "work", members=("README.md",))
        monkeypatch.setattr(
            "urllib.request.urlretrieve", lambda url, dst: shutil.copyfile(str(tb), dst)
        )
        ui = MagicMock()
        assert _download_tui_frontend(tmp_path / "target", ui) is None


class TestEnsureTuiFrontend:
    def test_found_by_finder(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_tui_dir", lambda: Path("/dev/tui"))
        ui = MagicMock()
        assert _ensure_tui_frontend(ui) == Path("/dev/tui")

    def test_existing_target(self, fake_home, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_tui_dir", lambda: None)
        target = fake_home / ".apex" / "tui-frontend"
        target.mkdir(parents=True)
        assert _ensure_tui_frontend(MagicMock()) == target

    def test_download(self, fake_home, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_tui_dir", lambda: None)
        target = fake_home / ".apex" / "tui-frontend"

        def fake_download(tgt, ui):
            tgt.mkdir(parents=True, exist_ok=True)
            return tgt

        monkeypatch.setattr(tui_launcher, "_download_tui_frontend", fake_download)
        assert _ensure_tui_frontend(MagicMock()) == target
        assert target.exists()

    def test_download_exception(self, fake_home, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_find_tui_dir", lambda: None)

        def boom(tgt, ui):
            raise OSError("download failed")

        monkeypatch.setattr(tui_launcher, "_download_tui_frontend", boom)
        ui = MagicMock()
        assert _ensure_tui_frontend(ui) is None
        ui.print_error.assert_called_once()


class TestInstallTuiCommand:
    def _make_install_env(self, tmp_path, monkeypatch, setup_ok: bool):
        """A fake TUI frontend with bun available and a setup outcome."""
        tui_dir = tmp_path / "tui-frontend"
        (tui_dir / "node_modules" / "ink").mkdir(parents=True)
        monkeypatch.setattr(tui_launcher, "_ensure_bun", lambda ui: True)
        monkeypatch.setattr(tui_launcher, "_ensure_tui_frontend", lambda ui: tui_dir)
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: "/fake/bun")
        monkeypatch.setattr(tui_launcher, "_setup_tui_frontend", lambda d, ui: setup_ok)
        return tui_dir

    def test_bun_failure_stops(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_bun", lambda ui: False)
        with patch.object(tui_launcher, "_ensure_tui_frontend") as mock_ensure:
            _install_tui_command(MagicMock())
        mock_ensure.assert_not_called()

    def test_frontend_failure_stops(self, monkeypatch):
        monkeypatch.setattr(tui_launcher, "_ensure_bun", lambda ui: True)
        monkeypatch.setattr(tui_launcher, "_ensure_tui_frontend", lambda ui: None)
        with patch.object(tui_launcher, "_patch_tui_package_json") as mock_patch:
            _install_tui_command(MagicMock())
        mock_patch.assert_not_called()

    def test_full_success(self, tmp_path, monkeypatch):
        self._make_install_env(tmp_path, monkeypatch, setup_ok=True)
        ui = MagicMock()
        _install_tui_command(ui)
        assert "TUI setup complete" in ui.print_success.call_args.args[0]

    def test_tsx_branch_when_no_bun(self, tmp_path, monkeypatch):
        self._make_install_env(tmp_path, monkeypatch, setup_ok=True)
        monkeypatch.setattr(tui_launcher, "_find_bun", lambda: None)
        monkeypatch.setattr(tui_launcher, "_ensure_tsx", lambda d: "/fake/tsx")
        _install_tui_command(MagicMock())  # tsx present: no install needed

    def test_setup_failure_reports(self, tmp_path, monkeypatch):
        self._make_install_env(tmp_path, monkeypatch, setup_ok=False)
        ui = MagicMock()
        _install_tui_command(ui)
        ui.print_error.assert_called_once()
