"""Installation surface for APEX.

Detects which distribution channel installed the running CLI, builds upgrade
and uninstall plans, and provisions the native Rust backend (``apex-rs``)
from GitHub release assets.

Channels:

* ``npm`` — the ``apex-ai`` npm wrapper (downloads and runs ``apex-rs``).
* ``native`` — the Rust backend ``apex-rs`` (headless: serve/run/tools).
* ``source`` — a checkout or editable install of this Python CLI. It is a
  developer channel, not a distribution channel: ``apex upgrade`` cannot
  update it through a package manager.

PyPI, pip, pipx and uv are no longer supported distribution channels.

The planning functions are pure or take their filesystem/network access as
injected callables, so ``tests/test_install_manager.py`` never touches the
network or the host installation.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "apex-ai"
REPO = "Ggboykxz/APEX"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{REPO}/tags?per_page=100"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
VALID_METHODS = ("npm", "native")
SOURCE_METHOD = "source"

Fetch = Callable[[str], bytes]


class InstallError(RuntimeError):
    """An installation action cannot be planned or carried out."""


class ReleaseUnavailable(InstallError):
    """The repository has not published any release or tag yet."""


def version_key(value: str) -> tuple[int, int, int] | None:
    """Return a comparable tuple for a semantic version, or ``None``."""
    cleaned = str(value or "").strip().lstrip("v")
    if not SEMVER.match(cleaned):
        return None
    major, minor, patch = (int(part) for part in cleaned.split("."))
    return major, minor, patch


def _is_not_found(exc: Exception) -> bool:
    """True when a fetch failed because the endpoint returned 404."""
    return getattr(exc, "code", None) == 404 or "404" in str(exc)


# ── Platform mapping ────────────────────────────────────────────────────────


def binary_name(sys_platform: str | None = None) -> str:
    """Return the native backend executable name for a platform."""
    value = sys_platform or sys.platform
    return "apex-rs.exe" if value.startswith("win") else "apex-rs"


def target_triple(sys_platform: str | None = None, machine: str | None = None) -> str | None:
    """Map a platform/machine pair to a Rust release target triple."""
    value = sys_platform or sys.platform
    cpu = (machine or platform_module.machine()).lower()
    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }.get(cpu)
    if arch is None:
        return None
    if value.startswith("linux"):
        return f"{arch}-unknown-linux-gnu"
    if value == "darwin":
        return f"{arch}-apple-darwin"
    if value.startswith("win"):
        return f"{arch}-pc-windows-msvc"
    return None


def asset_name(triple: str) -> str:
    """Return the release asset file name for a target triple."""
    extension = "zip" if "windows" in triple else "tar.gz"
    return f"apex-rs-{triple}.{extension}"


def release_base(version: str | None = None, repo: str = REPO) -> str:
    """Return the GitHub release download base URL (latest or pinned)."""
    pinned = (version or "").strip().lstrip("v")
    if pinned and pinned != "latest":
        return f"https://github.com/{repo}/releases/download/v{pinned}"
    return f"https://github.com/{repo}/releases/latest/download"


def native_install_dir(env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    """Return the managed native install directory (``~/.apex/bin`` by default)."""
    values = os.environ if env is None else env
    override = values.get("APEX_INSTALL_DIR")
    if override:
        return Path(override).expanduser()
    root = Path.home() if home is None else home
    return root / ".apex" / "bin"


def native_binary(
    env: dict[str, str] | None = None,
    home: Path | None = None,
    sys_platform: str | None = None,
) -> Path:
    """Return the managed native backend executable path."""
    return native_install_dir(env, home) / binary_name(sys_platform)


# ── Detection ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Detection:
    """How the running APEX CLI appears to be installed."""

    methods: tuple[str, ...]
    details: dict[str, str]

    @property
    def primary(self) -> str:
        """The first distribution channel, or ``source`` as the fallback."""
        for method in self.methods:
            if method != SOURCE_METHOD:
                return method
        return SOURCE_METHOD


def detect(
    which: Callable[[str], str | None] = shutil.which,
    home: Path | None = None,
    env: dict[str, str] | None = None,
    executable: str | None = None,
) -> Detection:
    """Detect the installation channels reachable from this process.

    ``source`` is always reported: the running package is importable, which
    means a Python checkout or editable install exists. The ``native``
    channel is inferred from the managed binary or ``apex-rs`` on ``PATH``.
    """
    values = dict(os.environ) if env is None else env
    executable = executable or sys.executable

    methods: list[str] = []
    details: dict[str, str] = {}

    managed = native_binary(values, home)
    if managed.exists():
        methods.append("native")
        details["native"] = str(managed)
    else:
        found = which("apex-rs")
        if found:
            methods.append("native")
            details["native"] = found

    methods.append(SOURCE_METHOD)
    details[SOURCE_METHOD] = f"python: {executable}"
    return Detection(tuple(methods), details)


def primary_method(detection: Detection, requested: str | None = None) -> str:
    """Resolve the upgrade channel (explicit request wins)."""
    if requested:
        if requested not in VALID_METHODS:
            expected = ", ".join(VALID_METHODS)
            raise InstallError(f"unknown install method: {requested} (expected {expected})")
        return requested
    return detection.primary


# ── Upgrade planning ────────────────────────────────────────────────────────


def upgrade_command(method: str, version: str | None = None) -> list[str]:
    """Return the command that upgrades the installed channel."""
    pinned = (version or "").strip().lstrip("v")
    if method == "npm":
        return ["npm", "install", "-g", f"{PACKAGE}@{pinned}" if pinned else PACKAGE]
    if method == "native":
        raise InstallError("native upgrades use the verified downloader, not a command")
    if method == SOURCE_METHOD:
        raise InstallError(
            "a source checkout is updated with git, not a package manager "
            "(use --method native or --method npm to switch channels)"
        )
    raise InstallError(f"unknown install method: {method}")


def http_fetch(url: str) -> bytes:
    """Fetch a URL over HTTPS (the only network call in this module)."""
    request = urllib.request.Request(url, headers={"User-Agent": "apex-installer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _release_tag_from_payload(payload: dict) -> str | None:
    """Extract and validate a semver tag from a ``releases/latest`` payload."""
    tag = str(payload.get("tag_name", "")).strip().lstrip("v")
    return tag if SEMVER.match(tag) else None


def _tag_versions(reader: Fetch, tags_api: str) -> list[str]:
    """Return valid semver versions from the tags API (empty on 404)."""
    tags = json.loads(reader(tags_api))
    if not isinstance(tags, list):
        raise InstallError(f"could not resolve the latest release: {tags!r}")
    versions = [
        str(entry.get("name", "")).strip().lstrip("v") for entry in tags if isinstance(entry, dict)
    ]
    return [v for v in versions if SEMVER.match(v)]


def _highest_semver(versions: list[str]) -> str | None:
    """Return the highest semantic version, or None when the list is empty."""
    if not versions:
        return None
    return max(versions, key=lambda value: tuple(int(part) for part in value.split(".")))


def _resolve_latest_from_tags(
    reader: Fetch, tags_api: str, release_error: Exception | None
) -> str | None:
    """Try the tags API as a fallback; return the highest semver or None."""
    try:
        versions = _tag_versions(reader, tags_api)
    except Exception as exc:
        if not _is_not_found(exc):
            raise InstallError(
                f"could not resolve the latest release: {release_error or exc}"
            ) from exc
        return None
    return _highest_semver(versions)


def fetch_latest_release(
    fetch: Fetch | None = None, api: str = RELEASE_API, tags_api: str = TAGS_API
) -> str:
    """Return the latest published version (without the ``v``)."""
    reader = fetch or http_fetch
    release_error: Exception | None = None
    try:
        payload = json.loads(reader(api))
    except Exception as exc:  # 404 before the first release, network, JSON  # noqa: BLE001
        release_error = exc
    else:
        if not isinstance(payload, dict):
            raise InstallError("unexpected release payload (expected a JSON object)")
        tag = _release_tag_from_payload(payload)
        if tag is not None:
            return tag
        release_error = InstallError(f"unexpected release tag: {payload.get('tag_name')!r}")

    highest = _resolve_latest_from_tags(reader, tags_api, release_error)
    if highest is not None:
        return highest
    raise ReleaseUnavailable("no published release or tag yet")


def parse_sha256(text: str) -> str | None:
    """Extract a SHA256 digest from a ``.sha256`` file body."""
    match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
    return match.group(1).lower() if match else None


def _validate_zip_members(bundle: zipfile.ZipFile, root: Path) -> None:
    for member in bundle.namelist():
        target = (root / member).resolve()
        if target != root and root not in target.parents:
            raise InstallError(f"unsafe archive member: {member}")


def _extract_zip(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        _validate_zip_members(bundle, root)
        bundle.extractall(root)


def _validate_tar_members(bundle: tarfile.TarFile, root: Path) -> None:
    for member in bundle.getmembers():
        target = (root / member.name).resolve()
        if target != root and root not in target.parents:
            raise InstallError(f"unsafe archive member: {member.name}")


def _extract_tar(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        _validate_tar_members(bundle, root)
        for member in bundle.getmembers():
            bundle.extract(member, root)


def _extract(archive: Path, destination: Path) -> None:
    """Extract a ``.tar.gz`` or ``.zip`` archive after validating member paths."""
    if archive.suffix == ".zip":
        _extract_zip(archive, destination)
        return
    _extract_tar(archive, destination)


@dataclass(frozen=True)
class NativeUpgradeOptions:
    """Bundled options for :func:`native_upgrade`."""

    fetch: Fetch | None = None
    env: dict[str, str] | None = None
    home: Path | None = None
    sys_platform: str | None = None
    machine: str | None = None


def _resolve_triple(platform_value: str, options: NativeUpgradeOptions) -> str:
    triple = target_triple(platform_value, options.machine)
    if triple is None:
        raise InstallError(
            f"no native backend build for {platform_value}/{options.machine or platform_module.machine()}"
        )
    return triple


def _download_and_verify(reader: Fetch, base: str, asset: str) -> bytes:
    checksum = parse_sha256(reader(f"{base}/{asset}.sha256").decode("utf-8", "replace"))
    if checksum is None:
        raise InstallError("release checksum file is missing a SHA256 digest")
    try:
        payload = reader(f"{base}/{asset}")
    except Exception as exc:
        raise InstallError(f"could not download asset {asset}: {exc}") from exc
    if hashlib.sha256(payload).hexdigest() != checksum:
        raise InstallError("native backend checksum mismatch")
    return payload


@dataclass(frozen=True)
class NativeInstallContext:
    """Filesystem context for installing a native binary."""

    platform_value: str
    directory: Path


def _install_binary(
    payload: bytes,
    asset: str,
    name: str,
    context: NativeInstallContext,
) -> Path:
    with tempfile.TemporaryDirectory(prefix="apex-native-") as tmp:
        archive = Path(tmp) / asset
        archive.write_bytes(payload)
        unpacked = Path(tmp) / "unpack"
        unpacked.mkdir()
        _extract(archive, unpacked)
        found = next((path for path in unpacked.rglob(name) if path.is_file()), None)
        if found is None:
            raise InstallError(f"archive does not contain {name}")
        context.directory.mkdir(parents=True, exist_ok=True)
        destination = context.directory / name
        shutil.copy2(found, destination)
        if not context.platform_value.startswith("win"):
            destination.chmod(0o755)
        return destination


def native_upgrade(
    version: str | None = None,
    *,
    options: NativeUpgradeOptions | None = None,
) -> Path:
    """Download, verify and install the native backend; return its path.

    The checksum published next to the asset (``<asset>.sha256``) is the only
    trust anchor: a mismatch aborts before anything touches the install
    directory.
    """
    opts = options or NativeUpgradeOptions()
    reader = opts.fetch or http_fetch
    platform_value = opts.sys_platform or sys.platform
    triple = _resolve_triple(platform_value, opts)
    base = release_base(version)
    asset = asset_name(triple)
    payload = _download_and_verify(reader, base, asset)
    directory = native_install_dir(opts.env, opts.home)
    context = NativeInstallContext(platform_value=platform_value, directory=directory)
    return _install_binary(payload, asset, binary_name(platform_value), context)


@dataclass(frozen=True)
class UninstallOptions:
    """Bundled options for :func:`uninstall_plan`."""

    keep_config: bool = False
    keep_data: bool = False
    purge: bool = False
    methods: tuple[str, ...] | None = None


def _native_uninstall_paths(channels: set[str], values: dict[str, str], root: Path) -> list[Path]:
    paths: list[Path] = []
    if "native" in channels:
        managed = native_install_dir(values, root)
        if managed.exists():
            paths.append(managed)
    return paths


def _purge_config_paths(config_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    if config_dir.exists():
        paths.append(config_dir)
    return paths, kept


def _keep_config_paths(config_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    if config_dir.exists():
        kept.append(str(config_dir))
    return paths, kept


def _default_config_paths(config_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    if config_dir.exists():
        paths.append(config_dir)
    return paths, kept


def _config_uninstall_paths(
    purge: bool, keep_config: bool, config_dir: Path
) -> tuple[list[Path], list[str]]:
    if purge:
        return _purge_config_paths(config_dir)
    if keep_config:
        return _keep_config_paths(config_dir)
    return _default_config_paths(config_dir)


def _purge_data_paths(data_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    if data_dir.exists():
        paths.append(data_dir)
    return paths, kept


def _keep_data_paths(data_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    if data_dir.exists():
        kept.append(str(data_dir))
    return paths, kept


def _default_data_paths(data_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    kept: list[str] = []
    for name in ("sessions", "memory", "tasks"):
        candidate = data_dir / name
        if candidate.exists():
            paths.append(candidate)
    return paths, kept


def _data_uninstall_paths(
    purge: bool, keep_data: bool, data_dir: Path
) -> tuple[list[Path], list[str]]:
    if purge:
        return _purge_data_paths(data_dir)
    if keep_data:
        return _keep_data_paths(data_dir)
    return _default_data_paths(data_dir)


def _npm_uninstall_commands(channels: set[str]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    if "npm" in channels:
        commands.append(("npm", "uninstall", "-g", PACKAGE))
    return commands


@dataclass(frozen=True)
class UninstallPlan:
    """Filesystem removals, package-manager commands and kept paths."""

    paths: tuple[Path, ...]
    commands: tuple[tuple[str, ...], ...]
    kept: tuple[str, ...]


def uninstall_plan(
    *,
    detection: Detection,
    options: UninstallOptions | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> UninstallPlan:
    """Build the uninstall plan for the detected channels.

    By default the managed files are removed but credentials are kept:
    ``~/.apex/api_keys.json`` and ``~/.apex/gateway.json`` never enter the
    plan. ``purge=True`` removes the whole ``~/.apex`` tree instead.
    """
    root = Path.home() if home is None else home
    values = dict(os.environ) if env is None else env
    opts = options or UninstallOptions()
    channels = set(opts.methods or detection.methods)

    paths: list[Path] = []
    kept: list[str] = []

    paths.extend(_native_uninstall_paths(channels, values, root))

    config_dir = root / ".config" / "apex"
    p, k = _config_uninstall_paths(opts.purge, opts.keep_config, config_dir)
    paths.extend(p)
    kept.extend(k)

    data_dir = root / ".apex"
    p, k = _data_uninstall_paths(opts.purge, opts.keep_data, data_dir)
    paths.extend(p)
    kept.extend(k)

    commands = _npm_uninstall_commands(channels)

    return UninstallPlan(tuple(dict.fromkeys(paths)), tuple(commands), tuple(kept))
