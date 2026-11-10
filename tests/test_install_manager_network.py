"""Tests for network-failure paths in install_manager (audit recommendation U4)."""

from __future__ import annotations

import hashlib

import pytest

from apex import install_manager as im


def _tarball(name: str = "apex-rs", body: bytes = b"#!/bin/sh\necho apex-rs\n") -> bytes:
    import io
    import tarfile

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        info = tarfile.TarInfo(name)
        info.size = len(body)
        info.mode = 0o755
        bundle.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def test_fetch_latest_release_network_error_on_release_api_propagates(tmp_path):
    """A non-404 error on the releases/latest API must surface as InstallError."""

    def fetch(url: str) -> bytes:
        if "releases/latest" in url:
            raise RuntimeError("network unreachable")
        return b""

    with pytest.raises(im.InstallError, match="could not resolve"):
        im.fetch_latest_release(fetch=fetch)


def test_fetch_latest_release_404_then_tags_network_error(tmp_path):
    """404 on releases/latest + network error on tags API => InstallError, not ReleaseUnavailable."""

    def fetch(url: str) -> bytes:
        if "releases/latest" in url:
            raise RuntimeError("HTTP 404")
        raise RuntimeError("network unreachable")

    with pytest.raises(im.InstallError, match="could not resolve") as info:
        im.fetch_latest_release(fetch=fetch)
    assert not isinstance(info.value, im.ReleaseUnavailable)


def test_native_upgrade_download_failure_aborts_before_install(tmp_path):
    """A failed asset download must not create the install directory."""

    asset = im.asset_name("x86_64-unknown-linux-gnu")

    def fetch(url: str) -> bytes:
        if url.endswith(".sha256"):
            digest = "0" * 64
            return f"{digest}  {asset}\n".encode()
        raise RuntimeError("asset download failed")

    with pytest.raises(im.InstallError, match="asset download failed"):
        im.native_upgrade(
            "2.5.0",
            options=im.NativeUpgradeOptions(
                fetch=fetch,
                env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
                home=tmp_path,
                sys_platform="linux",
                machine="x86_64",
            ),
        )
    assert not (tmp_path / "bin").exists()


def test_native_upgrade_corrupt_asset_aborts_before_install(tmp_path):
    """A checksum mismatch must abort before anything touches the install dir."""

    asset = im.asset_name("x86_64-unknown-linux-gnu")
    digest = hashlib.sha256(b"wrong payload").hexdigest()

    def fetch(url: str) -> bytes:
        if url.endswith(".sha256"):
            return f"{digest}  {asset}\n".encode()
        return b"actual payload bytes"

    with pytest.raises(im.InstallError, match="checksum"):
        im.native_upgrade(
            "2.5.0",
            options=im.NativeUpgradeOptions(
                fetch=fetch,
                env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
                home=tmp_path,
                sys_platform="linux",
                machine="x86_64",
            ),
        )
    assert not (tmp_path / "bin").exists()


def test_native_upgrade_missing_archive_member_aborts(tmp_path):
    """An archive lacking the expected binary must abort cleanly."""

    import io
    import tarfile

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        info = tarfile.TarInfo("other-file")
        info.size = 0
        bundle.addfile(info, io.BytesIO(b""))
    payload = buffer.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    asset = im.asset_name("x86_64-unknown-linux-gnu")

    def fetch(url: str) -> bytes:
        if url.endswith(".sha256"):
            return f"{digest}  {asset}\n".encode()
        return payload

    with pytest.raises(im.InstallError, match="does not contain"):
        im.native_upgrade(
            "2.5.0",
            options=im.NativeUpgradeOptions(
                fetch=fetch,
                env={"APEX_INSTALL_DIR": str(tmp_path / "bin")},
                home=tmp_path,
                sys_platform="linux",
                machine="x86_64",
            ),
        )
    assert not (tmp_path / "bin").exists()
