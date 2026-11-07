"""Tests for apex/install_manager.py — no network, no host installation."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile

import pytest

from apex import install_manager as im


def _tarball(name: str = "apex-rs", body: bytes = b"#!/bin/sh\necho apex-rs\n") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        info = tarfile.TarInfo(name)
        info.size = len(body)
        info.mode = 0o755
        bundle.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def _zip(name: str = "apex-rs.exe", body: bytes = b"MZ fake binary") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr(name, body)
    return buffer.getvalue()


class TestPlatformMapping:
    def test_targets(self):
        assert im.target_triple("linux", "x86_64") == "x86_64-unknown-linux-gnu"
        assert im.target_triple("linux", "AMD64") == "x86_64-unknown-linux-gnu"
        assert im.target_triple("linux", "aarch64") == "aarch64-unknown-linux-gnu"
        assert im.target_triple("darwin", "arm64") == "aarch64-apple-darwin"
        assert im.target_triple("darwin", "x86_64") == "x86_64-apple-darwin"
        assert im.target_triple("win32", "x86_64") == "x86_64-pc-windows-msvc"

    def test_unknown_platform_or_cpu(self):
        assert im.target_triple("freebsd", "x86_64") is None
        assert im.target_triple("linux", "mips") is None

    def test_asset_names(self):
        assert im.asset_name("x86_64-unknown-linux-gnu") == (
            "apex-rs-x86_64-unknown-linux-gnu.tar.gz"
        )
        assert im.asset_name("x86_64-pc-windows-msvc") == "apex-rs-x86_64-pc-windows-msvc.zip"

    def test_binary_name(self):
        assert im.binary_name("linux") == "apex-rs"
        assert im.binary_name("darwin") == "apex-rs"
        assert im.binary_name("win32") == "apex-rs.exe"

    def test_release_base(self):
        latest = "https://github.com/Ggboykxz/APEX/releases/latest/download"
        assert im.release_base(None) == latest
        assert im.release_base("latest") == latest
        assert im.release_base("2.5.0") == (
            "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0"
        )
        assert im.release_base("v2.5.0") == (
            "https://github.com/Ggboykxz/APEX/releases/download/v2.5.0"
        )

    def test_native_paths(self, tmp_path):
        env = {"APEX_INSTALL_DIR": str(tmp_path / "custom")}
        assert im.native_install_dir(env, tmp_path) == tmp_path / "custom"
        assert im.native_binary({}, tmp_path, "linux") == tmp_path / ".apex" / "bin" / "apex-rs"
        assert im.native_binary({}, tmp_path, "win32").name == "apex-rs.exe"


class TestDetection:
    def test_pipx_venv(self, tmp_path):
        detection = im.detect(
            which=lambda _: None,
            home=tmp_path,
            env={},
            executable="/home/u/.local/pipx/venvs/apex-ai/bin/python",
        )
        assert detection.methods == ("pipx", "pip")
        assert detection.primary == "pipx"

    def test_uv_tool_venv(self, tmp_path):
        detection = im.detect(
            which=lambda _: None,
            home=tmp_path,
            env={},
            executable="/home/u/.local/share/uv/tools/apex-ai/bin/python",
        )
        assert detection.methods == ("uv", "pip")
        assert detection.primary == "uv"

    def test_managed_native_binary(self, tmp_path):
        binary = im.native_binary({}, tmp_path)
        binary.parent.mkdir(parents=True)
        binary.write_text("")
        detection = im.detect(
            which=lambda _: None, home=tmp_path, env={}, executable="/usr/bin/python"
        )
        assert detection.methods == ("native", "pip")
        assert detection.details["native"] == str(binary)
        assert detection.primary == "native"

    def test_native_on_path(self, tmp_path):
        detection = im.detect(
            which=lambda name: "/opt/apex-rs" if name == "apex-rs" else None,
            home=tmp_path,
            env={},
            executable="/usr/bin/python",
        )
        assert detection.primary == "native"

    def test_plain_pip(self, tmp_path):
        detection = im.detect(
            which=lambda _: None, home=tmp_path, env={}, executable="/usr/bin/python"
        )
        assert detection.methods == ("pip",)
        assert detection.primary == "pip"

    def test_requested_method_wins_and_validates(self, tmp_path):
        detection = im.detect(which=lambda _: None, home=tmp_path, env={})
        assert im.primary_method(detection, "npm") == "npm"
        with pytest.raises(im.InstallError):
            im.primary_method(detection, "conda")


class TestUpgradeCommands:
    def test_pip(self):
        assert im.upgrade_command("pip", python="/usr/bin/python") == [
            "/usr/bin/python",
            "-m",
            "pip",
            "install",
            "--upgrade",
            "apex-ai",
        ]

    def test_pipx_and_uv(self):
        assert im.upgrade_command("pipx") == ["pipx", "upgrade", "apex-ai"]
        assert im.upgrade_command("pipx", "2.5.0") == ["pipx", "install", "apex-ai==2.5.0"]
        assert im.upgrade_command("uv") == ["uv", "tool", "upgrade", "apex-ai"]
        assert im.upgrade_command("uv", "v2.5.0") == ["uv", "tool", "install", "apex-ai==2.5.0"]

    def test_npm(self):
        assert im.upgrade_command("npm") == ["npm", "install", "-g", "apex-ai"]
        assert im.upgrade_command("npm", "2.5.0") == ["npm", "install", "-g", "apex-ai@2.5.0"]

    def test_native_has_no_command(self):
        with pytest.raises(im.InstallError):
            im.upgrade_command("native")


class TestRelease:
    def test_fetch_latest_release(self):
        payload = json.dumps({"tag_name": "v2.5.0"}).encode()
        assert im.fetch_latest_release(lambda _: payload) == "2.5.0"

    def test_fetch_latest_release_rejects_bad_tag(self):
        payload = json.dumps({"tag_name": "nightly"}).encode()
        with pytest.raises(im.InstallError):
            im.fetch_latest_release(lambda _: payload)

    def test_fetch_latest_release_falls_back_to_tags(self):
        def fetch(url: str) -> bytes:
            if "releases/latest" in url:
                raise RuntimeError("HTTP 404")
            return json.dumps(
                [{"name": "v2.0.0"}, {"name": "v2.5.0"}, {"name": "nightly"}]
            ).encode()

        assert im.fetch_latest_release(fetch) == "2.5.0"

    def test_fetch_latest_release_fails_when_nothing_is_published(self):
        def fetch(url: str) -> bytes:
            raise RuntimeError("HTTP 404")

        with pytest.raises(im.InstallError, match="could not resolve"):
            im.fetch_latest_release(fetch)

    def test_parse_sha256(self):
        digest = "a" * 64
        assert im.parse_sha256(f"{digest}  apex-rs.tar.gz\n") == digest
        assert im.parse_sha256("not a digest") is None


class TestNativeUpgrade:
    def test_installs_verified_tarball(self, tmp_path):
        payload = _tarball()
        digest = hashlib.sha256(payload).hexdigest()
        asset = im.asset_name("x86_64-unknown-linux-gnu")

        def fetch(url: str) -> bytes:
            if url.endswith(".sha256"):
                return f"{digest}  {asset}\n".encode()
            assert url.endswith(asset)
            return payload

        destination = im.native_upgrade(
            "2.5.0",
            fetch=fetch,
            env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
            home=tmp_path,
            sys_platform="linux",
            machine="x86_64",
        )
        assert destination == tmp_path / "bin" / "apex-rs"
        assert destination.read_bytes() == b"#!/bin/sh\necho apex-rs\n"

    def test_installs_verified_zip(self, tmp_path):
        payload = _zip()
        digest = hashlib.sha256(payload).hexdigest()
        asset = im.asset_name("x86_64-pc-windows-msvc")

        def fetch(url: str) -> bytes:
            if url.endswith(".sha256"):
                return digest.encode()
            assert url.endswith(asset)
            return payload

        destination = im.native_upgrade(
            None,
            fetch=fetch,
            env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
            home=tmp_path,
            sys_platform="win32",
            machine="x86_64",
        )
        assert destination == tmp_path / "bin" / "apex-rs.exe"
        assert destination.read_bytes() == b"MZ fake binary"

    def test_rejects_checksum_mismatch(self, tmp_path):
        payload = _tarball()
        asset = im.asset_name("x86_64-unknown-linux-gnu")

        def fetch(url: str) -> bytes:
            if url.endswith(".sha256"):
                return ("0" * 64).encode()
            return payload

        with pytest.raises(im.InstallError, match="checksum"):
            im.native_upgrade(
                "2.5.0",
                fetch=fetch,
                env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
                home=tmp_path,
                sys_platform="linux",
                machine="x86_64",
            )
        assert not (tmp_path / "bin" / asset).exists()

    def test_rejects_unsupported_platform(self, tmp_path):
        with pytest.raises(im.InstallError, match="no native backend"):
            im.native_upgrade(
                "2.5.0",
                fetch=lambda _: b"",
                env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
                home=tmp_path,
                sys_platform="freebsd",
                machine="x86_64",
            )


class TestUninstallPlan:
    def _detection(self) -> im.Detection:
        return im.Detection(("pipx", "native", "pip"), {})

    def test_removes_everything_by_default(self, tmp_path):
        (tmp_path / "bin").mkdir()
        (tmp_path / ".config" / "apex").mkdir(parents=True)
        (tmp_path / ".apex" / "sessions").mkdir(parents=True)
        (tmp_path / ".apex" / "memory").mkdir()
        (tmp_path / ".apex" / "api_keys.json").write_text("{}")

        plan = im.uninstall_plan(
            detection=self._detection(),
            home=tmp_path,
            env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
        )
        assert tmp_path / "bin" in plan.paths
        assert tmp_path / ".config" / "apex" in plan.paths
        assert tmp_path / ".apex" / "sessions" in plan.paths
        assert tmp_path / ".apex" / "memory" in plan.paths
        # Credentials are never deleted.
        assert tmp_path / ".apex" / "api_keys.json" not in plan.paths
        assert plan.commands == (("pipx", "uninstall", "apex-ai"),)
        assert plan.kept == ()

    def test_keep_config_and_data(self, tmp_path):
        (tmp_path / ".config" / "apex").mkdir(parents=True)
        (tmp_path / ".apex").mkdir()
        plan = im.uninstall_plan(
            detection=self._detection(),
            keep_config=True,
            keep_data=True,
            home=tmp_path,
            env={},
        )
        assert plan.paths == ()
        assert sorted(plan.kept) == [
            str(tmp_path / ".apex"),
            str(tmp_path / ".config" / "apex"),
        ]

    def test_pip_fallback_command(self, tmp_path):
        plan = im.uninstall_plan(
            detection=im.Detection(("pip",), {}),
            home=tmp_path,
            env={},
            python="/usr/bin/python",
        )
        assert plan.commands == (("/usr/bin/python", "-m", "pip", "uninstall", "-y", "apex-ai"),)

    def test_npm_and_uv_channels(self, tmp_path):
        npm = im.uninstall_plan(
            detection=im.Detection(("npm", "pip"), {}),
            home=tmp_path,
            env={},
        )
        assert npm.commands == (("npm", "uninstall", "-g", "apex-ai"),)
        uv = im.uninstall_plan(
            detection=im.Detection(("uv", "pip"), {}),
            home=tmp_path,
            env={},
        )
        assert uv.commands == (("uv", "tool", "uninstall", "apex-ai"),)

    def test_purge_removes_the_whole_data_tree(self, tmp_path):
        (tmp_path / ".config" / "apex").mkdir(parents=True)
        (tmp_path / ".apex" / "sessions").mkdir(parents=True)
        (tmp_path / ".apex" / "api_keys.json").write_text("{}")
        plan = im.uninstall_plan(
            detection=im.Detection(("pip",), {}),
            home=tmp_path,
            env={},
            purge=True,
        )
        assert tmp_path / ".apex" in plan.paths
        assert tmp_path / ".config" / "apex" in plan.paths
        assert plan.kept == ()
