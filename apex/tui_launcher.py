"""TUI launcher: locate, install and start the Ink/React frontend."""

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .agent import Agent
from .http_api import start_tui_server, stop_tui_server
from .session import SessionManager
from .ui import UI

logger = logging.getLogger("apex")


def _find_tui_dir() -> Path | None:
    dev_path = Path(__file__).parent.parent / "tui-frontend"
    if (dev_path / "src" / "App.tsx").exists():
        return dev_path
    for candidate in [
        Path(__file__).parent.parent.parent / "tui-frontend",
        Path.home() / ".apex" / "tui-frontend",
    ]:
        if (candidate / "src" / "App.tsx").exists():
            return candidate
    return None


def _find_bun() -> str | None:
    bun_candidates = [
        Path.home() / ".bun" / "bin" / "bun",
        Path("/usr/local/bin/bun"),
        Path("/usr/bin/bun"),
    ]
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        user_profile = os.environ.get("USERPROFILE", "")
        bun_candidates.extend(
            [
                Path(user_profile) / ".bun" / "bin" / "bun.exe",
                Path(user_profile) / ".bun" / "bin" / "bun",
                Path(local_app) / "bun" / "bun.exe",
            ]
        )
    for candidate in bun_candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("bun")


def _find_node() -> str | None:
    return shutil.which("node")


def _find_npx() -> str | None:
    return shutil.which("npx")


def _install_bun(ui: UI) -> str | None:
    ui.print_info("Bun not found. Installing bun runtime via npm...")
    try:
        npx_path = _find_npx()
        if not npx_path:
            ui.print_error("npx not found. Install Node.js first: https://nodejs.org")
            return None
        result = subprocess.run(
            [npx_path, "--yes", "bun@1", "--version"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "npm_config_prefix": str(Path.home() / ".npm-global")},
            check=False,
        )
        if result.returncode != 0:
            ui.print_error("Failed to install bun via npx")
            return None
        bun_path = shutil.which("bun") or Path.home() / ".npm-global" / "bin" / "bun"
        if bun_path and Path(bun_path).exists():
            ui.print_success("Bun installed successfully!")
            return str(bun_path)
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def _clear_stale_lockfiles(tui_dir: Path) -> None:
    """Remove stale lockfiles that may reference wrong React versions."""
    for lockfile in ("bun.lock", "bun.lockb", "package-lock.json"):
        lock_path = tui_dir / lockfile
        if not lock_path.exists():
            continue
        try:
            lock_path.unlink()
        except OSError:
            pass


def _run_dependency_install(command: list[str], tui_dir: Path, timeout: int) -> bool:
    try:
        result = subprocess.run(
            command,
            cwd=str(tui_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return False
    return result.returncode == 0


def _setup_tui_frontend(tui_dir: Path, ui: UI) -> bool:
    node_modules = tui_dir / "node_modules"
    if node_modules.exists() and (node_modules / "ink").exists():
        return True

    _clear_stale_lockfiles(tui_dir)
    ui.print_info("Installing TUI dependencies (first run)...")

    bun_path = _find_bun()
    if bun_path and _run_dependency_install([bun_path, "install"], tui_dir, 120):
        ui.print_success("TUI dependencies installed!")
        return True

    npm_path = shutil.which("npm")
    if npm_path and _run_dependency_install([npm_path, "install"], tui_dir, 180):
        ui.print_success("TUI dependencies installed with npm!")
        return True

    ui.print_error("Could not install TUI dependencies. Neither bun nor npm is available.")
    return False


def _tui_env(tui_dir: Path, port: int) -> dict[str, str]:
    env = os.environ.copy()
    path_sep = ";" if sys.platform == "win32" else ":"
    local_bin = tui_dir / "node_modules" / ".bin"
    if local_bin.exists():
        env["PATH"] = str(local_bin) + path_sep + env.get("PATH", "")
    bun_path = _find_bun()
    if bun_path:
        env["PATH"] = str(Path(bun_path).parent) + path_sep + env.get("PATH", "")
    env["APEX_HTTP_PORT"] = str(port)
    env["APEX"] = "1"
    env["APEX_PID"] = str(os.getpid())
    return env


def _try_run_tui_process(tui_dir: Path, runtime: tuple[list[str], str], ui: UI, port: int) -> bool:
    runtime_cmd, runtime_name = runtime
    ui.print_info(f"Starting APEX TUI with {runtime_name} (Ctrl+C to exit)...")
    try:
        # Ink requires TTY for raw mode \u2014 pass stdin/stdout/stderr directly
        proc = subprocess.Popen(
            runtime_cmd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=_tui_env(tui_dir, port),
            cwd=str(tui_dir),
        )
        while proc.poll() is None:
            time.sleep(0.1)
        return proc.returncode == 0
    except FileNotFoundError:
        ui.print_error(f"{runtime_name} executable not found: {runtime_cmd[0]}")
        return False
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"{runtime_name} error: {e}")
        return False


def _ensure_tsx(tui_dir: Path) -> str | None:
    local_tsx = (
        tui_dir / "node_modules" / ".bin" / ("tsx.cmd" if sys.platform == "win32" else "tsx")
    )
    if local_tsx.exists():
        return str(local_tsx)
    return shutil.which("tsx")


def _install_tsx(tui_dir: Path, ui: UI) -> str | None:
    npm_path = shutil.which("npm")
    if not npm_path:
        return None
    ui.print_info("Installing tsx runtime for Node.js TUI support...")
    try:
        result = subprocess.run(
            [npm_path, "install", "--save-dev", "tsx"],
            cwd=str(tui_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            ui.print_success("tsx installed successfully!")
            return _ensure_tsx(tui_dir)
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def _find_free_port() -> int:
    """Find a random free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _require_tui_dir(ui: UI) -> Path:
    tui_dir = _find_tui_dir()
    if not tui_dir:
        ui.print_error("TUI frontend not found. Install with: apex install-tui")
        sys.exit(1)
    return tui_dir


def _resolve_tui_runtime(tui_dir: Path, ui: UI) -> tuple[list[str], str]:
    tsx_path = _ensure_tsx(tui_dir) or _install_tsx(tui_dir, ui)
    tui_entry = str(tui_dir / "src" / "App.tsx")
    if tsx_path:
        return [tsx_path, tui_entry], "Node.js + tsx"
    node_path = _find_node()
    if node_path:
        return [node_path, "--experimental-strip-types", tui_entry], "Node.js (native TS)"
    ui.print_error("TUI requires Node.js. Install from https://nodejs.org")
    sys.exit(1)


def _restore_tui_session(agent: Agent, ui: UI, resume: bool, session_id: str | None) -> None:
    sm = SessionManager()
    if resume:
        sessions = sm.list_sessions()
        if sessions:
            sm.load(sessions[0]["name"], agent)
            ui.print_success(f"Resumed session: {sessions[0]['name']}")
    elif session_id:
        sm.load(session_id, agent)
        ui.print_success(f"Loaded session: {session_id}")


def run_apex_tui(
    agent: Agent,
    ui: UI,
    resume: bool = False,
    session_id: str | None = None,
) -> None:
    tui_dir = _require_tui_dir(ui)

    # Ensure package.json has React 18 (not 19) before installing deps
    _patch_tui_package_json(tui_dir)
    if not _setup_tui_frontend(tui_dir, ui):
        ui.print_error("TUI dependencies not installed. Run: apex install-tui")
        sys.exit(1)

    runtime = _resolve_tui_runtime(tui_dir, ui)
    _restore_tui_session(agent, ui, resume, session_id)

    # Use a random free port instead of hardcoded 8080
    port = _find_free_port()
    ui.print_info(f"Starting APEX HTTP API server on port {port}...")
    server = start_tui_server(port=port, agent=agent)

    logger.info(f"APEX v{__version__} starting...")
    logger.info(f"Project: {agent.cwd}")
    logger.info(f"Model: {agent.model}")
    logger.info(f"Agent: {agent.current_agent}")
    logger.info(f"HTTP API: http://127.0.0.1:{port}")

    try:
        if _try_run_tui_process(tui_dir, runtime, ui, port):
            return
    finally:
        stop_tui_server(server)

    ui.print_error("TUI failed. Run: apex install-tui")
    sys.exit(1)


def _patch_package_versions(deps: dict, dev_deps: dict) -> bool:
    """Apply the React 18 / Ink compatibility fixes; return True when patched."""
    patched = False
    if "react" in deps and deps["react"].startswith("^19"):
        deps["react"] = "^18.3.1"
        patched = True
    if "react-reconciler" not in deps:
        deps["react-reconciler"] = "^0.29.2"
        patched = True
    if "@types/react" in dev_deps and dev_deps["@types/react"].startswith("^19"):
        dev_deps["@types/react"] = "^18.3.0"
        patched = True
    if "typescript" in dev_deps and dev_deps["typescript"].startswith("^6"):
        dev_deps["typescript"] = "^5.7.0"
        patched = True
    return patched


def _patch_tui_package_json(tui_dir: Path) -> None:
    """Patch tui-frontend/package.json to ensure React 18 + react-reconciler for Ink compatibility.

    Ink 5.x requires react-reconciler which only supports React ^18.3.1.
    If the repo's package.json still has React 19, this patches it after download.
    """
    pkg_path = tui_dir / "package.json"
    if not pkg_path.exists():
        return
    try:
        data = json.loads(pkg_path.read_text())
        if not _patch_package_versions(
            data.get("dependencies", {}), data.get("devDependencies", {})
        ):
            return
        pkg_path.write_text(json.dumps(data, indent=2) + "\n")
        logger.info("Patched tui-frontend/package.json for React 18 / Ink compatibility")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to patch tui-frontend/package.json: {e}")


def _ensure_bun(ui: UI) -> bool:
    bun_path = _find_bun()
    if bun_path:
        ui.print_success(f"Bun already installed: {bun_path}")
        return True
    ui.print_info("Installing Bun runtime...")
    bun_path = _install_bun(ui)
    if not bun_path:
        ui.print_error("Failed to install Bun. Run: curl -fsSL https://bun.sh/install | bash")
        return False
    ui.print_success(f"Bun installed: {bun_path}")
    return True


def _clone_tui_frontend(tmp_dir: Path, tui_target: Path, ui: UI) -> Path | None:
    result = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/Ggboykxz/APEX.git",
            str(tmp_dir / "apex-repo"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        ui.print_error(f"Failed to download: {result.stderr[:200]}")
        return None
    repo_dir = next((tmp_dir / "apex-repo").iterdir(), None)
    if repo_dir and (repo_dir / "tui-frontend").exists():
        shutil.copytree(str(repo_dir / "tui-frontend"), str(tui_target))
        ui.print_success(f"TUI frontend installed: {tui_target}")
        return tui_target
    ui.print_error("tui-frontend directory not found in repository")
    return None


def _extract_tui_frontend(
    tarball_path: Path, tmp_dir: Path, tui_target: Path, ui: UI
) -> Path | None:
    import tarfile

    with tarfile.open(str(tarball_path), "r:gz") as tar:
        members = [m for m in tar.getmembers() if "/tui-frontend/" in m.name]
        if not members:
            ui.print_error("tui-frontend directory not found in repository")
            return None
        # Extract to a temp dir first, then copy the tui-frontend tree.
        tar.extractall(path=str(tmp_dir), members=members)
    extracted = list(tmp_dir.rglob("tui-frontend"))
    if not extracted or not extracted[0].is_dir():
        return None
    shutil.copytree(str(extracted[0]), str(tui_target))
    ui.print_success(f"TUI frontend installed: {tui_target}")
    return tui_target


def _download_tui_frontend(tui_target: Path, ui: UI) -> Path | None:
    import tempfile
    import urllib.request

    # Use a tarball download instead of a full git clone (much smaller).
    tarball_url = "https://api.github.com/repos/Ggboykxz/APEX/tarball/main"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tarball_path = tmp_path / "apex.tar.gz"
        try:
            urllib.request.urlretrieve(tarball_url, str(tarball_path))
        except Exception:  # noqa: BLE001
            return _clone_tui_frontend(tmp_path, tui_target, ui)
        return _extract_tui_frontend(tarball_path, tmp_path, tui_target, ui)


def _ensure_tui_frontend(ui: UI) -> Path | None:
    tui_dir = _find_tui_dir()
    if tui_dir:
        ui.print_success(f"TUI frontend found: {tui_dir}")
        return tui_dir
    apex_dir = Path.home() / ".apex"
    apex_dir.mkdir(parents=True, exist_ok=True)
    tui_target = apex_dir / "tui-frontend"
    if tui_target.exists():
        ui.print_success(f"TUI frontend already at: {tui_target}")
        return tui_target
    ui.print_info("Downloading TUI frontend from GitHub...")
    try:
        return _download_tui_frontend(tui_target, ui)
    except Exception as e:  # noqa: BLE001
        ui.print_error(f"Failed to download TUI frontend: {e}")
        return None


def _install_tui_command(ui: UI) -> None:
    if not _ensure_bun(ui):
        return
    tui_dir = _ensure_tui_frontend(ui)
    if tui_dir is None:
        return

    # Post-install: patch package.json to ensure React 18 compatibility with Ink.
    _patch_tui_package_json(tui_dir)
    if not _find_bun():
        tsx_path = _ensure_tsx(tui_dir)
        if not tsx_path:
            _install_tsx(tui_dir, ui)

    if _setup_tui_frontend(tui_dir, ui):
        ui.print_success("TUI setup complete! Run: apex")
    else:
        ui.print_error("Failed to install TUI dependencies.")
