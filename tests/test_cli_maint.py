"""Tests for apex/cli_maint.py — upgrade, uninstall and init commands."""

import argparse
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex import __version__
from apex import cli_maint as cm


def _ns(**kw):
    base = {
        "method": None,
        "check": False,
        "dry_run": False,
        "force": False,
        "keep_config": False,
        "keep_data": False,
        "purge": False,
    }
    base.update(kw)
    return argparse.Namespace(**base)


class FakeInstall:
    SOURCE_METHOD = "source"
    ReleaseUnavailable = type("ReleaseUnavailable", (Exception,), {})
    InstallError = type("InstallError", (Exception,), {})

    def version_key(self, v):
        return tuple(int(x) for x in v.split(".") if x.isdigit())

    def fetch_latest_release(self):
        return "9.9.9"

    def detect(self):
        return "source"

    def primary_method(self, detection, requested):
        return requested or detection

    def native_upgrade(self, pinned):
        return "/fake/apex-rs"

    def upgrade_command(self, method, pinned):
        return ["cmd", method]

    def uninstall_plan(self, **kw):
        plan = MagicMock()
        plan.paths = [Path("/p1")]
        plan.commands = [["cmd1"]]
        plan.kept = ["/kept"]
        return plan


class TestPrintUnknownVersions:
    def test_current(self):
        ui = MagicMock()
        cm._print_unknown_versions(FakeInstall(), __version__, ui)
        assert "up to date" in ui.print_success.call_args.args[0]

    def test_other(self):
        ui = MagicMock()
        cm._print_unknown_versions(FakeInstall(), "9.9.9", ui)
        assert "Latest release: 9.9.9" in ui.print_info.call_args.args[0]


class TestPrintVersionComparison:
    def test_update_available(self):
        ui = MagicMock()
        cm._print_version_comparison(FakeInstall(), "9.9.9", ui)
        assert "Update available" in ui.print_info.call_args_list[0].args[0]

    def test_current(self):
        ui = MagicMock()
        cm._print_version_comparison(FakeInstall(), __version__, ui)
        assert "up to date" in ui.print_success.call_args.args[0]

    def test_ahead(self):
        ui = MagicMock()
        cm._print_version_comparison(FakeInstall(), "0.0.1", ui)
        assert "ahead of the latest release" in ui.print_info.call_args.args[0]

    def test_none_keys(self):
        ui = MagicMock()
        install = FakeInstall()
        install.version_key = lambda v: None
        cm._print_version_comparison(install, "9.9.9", ui)
        assert "Latest release" in ui.print_info.call_args.args[0]


class TestReportUpgradeCheck:
    def test_fetch_ok(self):
        ui = MagicMock()
        with patch.object(cm, "_print_version_comparison") as mock_print:
            cm._report_upgrade_check(FakeInstall(), ui)
        mock_print.assert_called_once()
        assert mock_print.call_args.args[1] == "9.9.9"

    def test_unavailable(self):
        ui = MagicMock()
        install = FakeInstall()
        install.fetch_latest_release = lambda: (_ for _ in ()).throw(install.ReleaseUnavailable)
        cm._report_upgrade_check(install, ui)
        assert "No published release yet" in ui.print_info.call_args.args[0]

    def test_other_error_exits(self):
        ui = MagicMock()
        install = FakeInstall()
        install.fetch_latest_release = lambda: (_ for _ in ()).throw(RuntimeError("net"))
        with pytest.raises(SystemExit) as exc:
            cm._report_upgrade_check(install, ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once()


class TestResolveUpgradeMethod:
    def test_requested(self):
        install = FakeInstall()
        assert cm._resolve_upgrade_method(_ns(method="npm"), install, MagicMock()) == "npm"

    def test_auto_uses_detect(self):
        install = FakeInstall()
        assert cm._resolve_upgrade_method(_ns(method="auto"), install, MagicMock()) == "source"

    def test_install_error_exits(self):
        ui = MagicMock()
        install = FakeInstall()
        install.primary_method = lambda d, r: (_ for _ in ()).throw(install.InstallError("bad"))
        with pytest.raises(SystemExit) as exc:
            cm._resolve_upgrade_method(_ns(method=None), install, ui)
        assert exc.value.code == 1
        ui.print_error.assert_called_once_with("bad")


class TestUpgradeNative:
    def test_success(self):
        ui = MagicMock()
        cm._upgrade_native(FakeInstall(), None, ui)
        assert "Native backend updated" in ui.print_success.call_args.args[0]

    def test_install_error_exits(self):
        ui = MagicMock()
        install = FakeInstall()
        install.native_upgrade = lambda p: (_ for _ in ()).throw(install.InstallError("boom"))
        with pytest.raises(SystemExit) as exc:
            cm._upgrade_native(install, None, ui)
        assert exc.value.code == 1


class TestUpgradeWithCommand:
    def test_success(self):
        ui = MagicMock()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            cm._upgrade_with_command(["x"], ui)
        assert "upgraded successfully" in ui.print_success.call_args.args[0]

    def test_failure_exits(self):
        ui = MagicMock()
        with (
            patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="oops")),
            pytest.raises(SystemExit) as exc,
        ):
            cm._upgrade_with_command(["x"], ui)
        assert exc.value.code == 1
        assert "oops" in ui.print_error.call_args.args[0]

    def test_exception_exits(self):
        ui = MagicMock()
        with (
            patch("subprocess.run", side_effect=OSError("spawn")),
            pytest.raises(SystemExit) as exc,
        ):
            cm._upgrade_with_command(["x"], ui)
        assert exc.value.code == 1


class TestUpgradeSourceNotice:
    def test_notice(self):
        ui = MagicMock()
        cm._upgrade_source_notice(ui)
        assert "git pull" in ui.print_info.call_args.args[0]


class TestRunChannelUpgrade:
    def test_native(self):
        ui = MagicMock()
        with patch.object(cm, "_upgrade_native") as mock_native:
            cm._run_channel_upgrade(FakeInstall(), "native", None, ui)
        mock_native.assert_called_once()

    def test_command_channel(self):
        ui = MagicMock()
        with (
            patch.object(cm, "_upgrade_with_command") as mock_cmd,
            patch.object(cm, "_upgrade_native") as mock_native,
        ):
            cm._run_channel_upgrade(FakeInstall(), "npm", None, ui)
        mock_cmd.assert_called_once()
        mock_native.assert_not_called()

    def test_install_error_exits(self):
        ui = MagicMock()
        install = FakeInstall()
        install.upgrade_command = lambda m, p: (_ for _ in ()).throw(
            install.InstallError("no channel")
        )
        with pytest.raises(SystemExit) as exc:
            cm._run_channel_upgrade(install, "npm", None, ui)
        assert exc.value.code == 1


def _patch_install_manager(install):
    """Make `from . import install_manager` inside cli_maint resolve to fake.

    Patch the attribute on the ``apex`` package: once the real module has
    been imported, `from . import install_manager` returns the cached
    package attribute, so a ``sys.modules`` entry alone is not enough.
    """
    import apex

    return patch.object(apex, "install_manager", install, create=True)


class TestCmdUpgrade:
    def test_check(self):
        ui = MagicMock()
        install = FakeInstall()
        with (
            _patch_install_manager(install),
            patch.object(cm, "_report_upgrade_check") as mock_report,
        ):
            cm._cmd_upgrade(_ns(check=True), ui)
        mock_report.assert_called_once_with(install, ui)

    def test_source(self):
        ui = MagicMock()
        install = FakeInstall()
        install.detect = lambda: "source"
        with (
            _patch_install_manager(install),
            patch.object(cm, "_upgrade_source_notice") as mock_notice,
            patch.object(cm, "_run_channel_upgrade") as mock_channel,
        ):
            cm._cmd_upgrade(_ns(method="auto"), ui)
        mock_notice.assert_called_once()
        mock_channel.assert_not_called()

    def test_native_channel(self):
        ui = MagicMock()
        install = FakeInstall()
        install.detect = lambda: "npm"
        with (
            _patch_install_manager(install),
            patch.object(cm, "_upgrade_source_notice"),
            patch.object(cm, "_run_channel_upgrade") as mock_channel,
        ):
            cm._cmd_upgrade(_ns(method="native"), ui)
        mock_channel.assert_called_once()
        assert mock_channel.call_args.args[1] == "native"

    def test_pinned_version_env(self, monkeypatch):
        ui = MagicMock()
        install = FakeInstall()
        install.detect = lambda: "npm"
        monkeypatch.setenv("APEX_VERSION", "9.0.0")
        with (
            _patch_install_manager(install),
            patch.object(cm, "_run_channel_upgrade") as mock_channel,
        ):
            cm._cmd_upgrade(_ns(method="npm"), ui)
        assert mock_channel.call_args.args[2] == "9.0.0"


class TestConfirmUninstall:
    def test_dry_run(self):
        assert cm._confirm_uninstall(_ns(dry_run=True), MagicMock()) is True

    def test_force(self):
        assert cm._confirm_uninstall(_ns(force=True), MagicMock()) is True

    def test_yes(self):
        ui = MagicMock()
        ui.console.input.return_value = "  YES "
        assert cm._confirm_uninstall(_ns(), ui) is True

    def test_no(self):
        ui = MagicMock()
        ui.console.input.return_value = "no"
        assert cm._confirm_uninstall(_ns(), ui) is False
        assert "cancelled" in ui.print_info.call_args.args[0]


class TestPrintUninstallPlan:
    def test_prints(self):
        ui = MagicMock()
        plan = MagicMock()
        plan.paths = [Path("/a")]
        plan.commands = [["rm", "-rf", "/a"]]
        plan.kept = ["/cfg"]
        cm._print_uninstall_plan(plan, ui)
        joined = " ".join(str(c) for c in ui.print_info.call_args_list)
        assert "DRY RUN" in joined
        assert "Would remove: /a" in joined
        assert "Would run: rm -rf /a" in joined
        assert "Would keep: /cfg" in joined


class TestRemoveSinglePath:
    def test_directory(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        ui = MagicMock()
        cm._remove_single_path(d, ui)
        assert not d.exists()
        assert "Removed" in ui.print_success.call_args.args[0]

    def test_file(self, tmp_path):
        f = tmp_path / "f"
        f.write_text("")
        ui = MagicMock()
        cm._remove_single_path(f, ui)
        assert not f.exists()

    def test_missing(self, tmp_path):
        ui = MagicMock()
        cm._remove_single_path(tmp_path / "gone", ui)
        # Parity: a missing path still reports success (no-op).
        ui.print_success.assert_called_once()

    def test_error_warns(self, tmp_path, monkeypatch):
        ui = MagicMock()
        monkeypatch.setattr(shutil, "rmtree", lambda p: (_ for _ in ()).throw(OSError("busy")))
        d = tmp_path / "d"
        d.mkdir()
        cm._remove_single_path(d, ui)
        assert "Could not remove" in ui.print_warning.call_args.args[0]


class TestRemoveInstallPaths:
    def test_removes_all(self):
        ui = MagicMock()
        plan = MagicMock()
        plan.paths = [Path("/a"), Path("/b")]
        with patch.object(cm, "_remove_single_path") as mock_rm:
            cm._remove_install_paths(plan, ui)
        assert mock_rm.call_count == 2


class TestRunUninstallCommand:
    def test_success(self):
        ui = MagicMock()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            cm._run_uninstall_command(["cmd1"], ui)
        assert "Ran: cmd1" in ui.print_success.call_args.args[0]

    def test_failure_warns(self):
        ui = MagicMock()
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="err")):
            cm._run_uninstall_command(["cmd1"], ui)
        assert "cmd1" in ui.print_warning.call_args.args[0]

    def test_exception_warns(self):
        ui = MagicMock()
        with patch("subprocess.run", side_effect=OSError("spawn")):
            cm._run_uninstall_command(["cmd1"], ui)
        assert "failed" in ui.print_warning.call_args.args[0]


class TestRunUninstallCommands:
    def test_runs_all(self):
        ui = MagicMock()
        plan = MagicMock()
        plan.commands = [["a"], ["b"]]
        with patch.object(cm, "_run_uninstall_command") as mock_run:
            cm._run_uninstall_commands(plan, ui)
        assert mock_run.call_count == 2


class TestCmdUninstall:
    def test_cancelled(self):
        ui = MagicMock()
        with (
            patch.object(cm, "_confirm_uninstall", return_value=False),
            patch.object(cm, "_remove_install_paths") as mock_rm,
        ):
            cm._cmd_uninstall(_ns(), ui)
        mock_rm.assert_not_called()

    def test_dry_run(self):
        ui = MagicMock()
        install = FakeInstall()
        with (
            _patch_install_manager(install),
            patch.object(cm, "_confirm_uninstall", return_value=True),
            patch.object(cm, "_print_uninstall_plan") as mock_plan,
            patch.object(cm, "_remove_install_paths") as mock_rm,
        ):
            cm._cmd_uninstall(_ns(dry_run=True), ui)
        mock_plan.assert_called_once()
        mock_rm.assert_not_called()

    def test_full(self):
        ui = MagicMock()
        install = FakeInstall()
        with (
            _patch_install_manager(install),
            patch.object(cm, "_confirm_uninstall", return_value=True),
            patch.object(cm, "_remove_install_paths") as mock_rm,
            patch.object(cm, "_run_uninstall_commands") as mock_run,
        ):
            cm._cmd_uninstall(_ns(), ui)
        mock_rm.assert_called_once()
        mock_run.assert_called_once()
        msgs = " ".join(str(c) for c in ui.print_info.call_args_list)
        assert "Kept: /kept" in msgs
        assert "APEX has been removed" in msgs


class TestCmdInit:
    def test_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("x")
        ui = MagicMock()
        cm._cmd_init(ui)
        ui.print_info.assert_called_once_with("AGENTS.md already exists")

    def test_creates(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ui = MagicMock()
        cm._cmd_init(ui)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / ".apex" / "commands").is_dir()
        assert (tmp_path / ".apex" / "agents").is_dir()
        success_msgs = " ".join(str(c) for c in ui.print_success.call_args_list)
        assert "Created" in success_msgs
        assert "Initialized .apex" in success_msgs
