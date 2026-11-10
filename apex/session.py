"""Session persistence for APEX - save and load conversation sessions."""

import base64
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .agent import Agent

logger = logging.getLogger(__name__)

_FERNET_KEY: bytes | None = None


def _get_fernet() -> "Fernet":
    """Get or create a Fernet cipher using a key stored in the user's home directory.

    Uses cryptography.fernet (AES-128-CBC with HMAC-SHA256) for authenticated
    encryption instead of a custom XOR stream cipher.
    """
    global _FERNET_KEY

    if _FERNET_KEY is not None:
        return Fernet(_FERNET_KEY)

    key_file = Path.home() / ".apex" / ".session_key"
    if key_file.exists():
        raw = key_file.read_bytes()
        # If the old key was a raw 32-byte SHA-256 hash, derive a proper Fernet key from it
        if len(raw) == 32:
            import hashlib

            _FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(raw + b":fernet").digest())
        else:
            # Already a valid Fernet key (url-safe base64 of 32 bytes)
            _FERNET_KEY = raw
    else:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        _FERNET_KEY = Fernet.generate_key()
        key_file.write_bytes(_FERNET_KEY)
        key_file.chmod(0o600)

    return Fernet(_FERNET_KEY)


def _encrypt(data: bytes) -> bytes:
    """Encrypt data using Fernet (AES-128-CBC + HMAC-SHA256 authenticated encryption)."""
    f = _get_fernet()
    return f.encrypt(data)


def _decrypt(token: bytes) -> bytes:
    """Decrypt data using Fernet. Raises InvalidToken if tampered."""
    f = _get_fernet()
    return f.decrypt(token)


class UndoManager:
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []

    def snapshot(self, action_type: str, details: dict[str, Any]):
        snapshot = {
            "type": action_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> dict[str, Any] | None:
        if not self._undo_stack:
            return None
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        return action

    def redo(self) -> dict[str, Any] | None:
        if not self._redo_stack:
            return None
        action = self._redo_stack.pop()
        self._undo_stack.append(action)
        return action

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> str:
        if not self._undo_stack:
            return ""
        return self._undo_stack[-1].get("type", "unknown")

    def get_redo_description(self) -> str:
        if not self._redo_stack:
            return ""
        return self._redo_stack[-1].get("type", "unknown")

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()


def _validate_session_name(name: str) -> None:
    """Raise when the session name is not safe to use as a file name."""
    if _is_invalid_session_name(name):
        raise ValueError(f"Invalid session name: {name}")


def _is_invalid_session_name(name: str) -> bool:
    """Whether a session name may not be used as a file name."""
    if not name:
        return True
    if ".." in name:
        return True
    if "/" in name:
        return True
    return "\\" in name


def _validate_session_path(filepath: Path, sessions_dir: Path) -> None:
    """Raise when the session file would escape the sessions directory."""
    resolved_dir = sessions_dir.resolve()
    if resolved_dir not in filepath.parents and filepath.parent != resolved_dir:
        raise ValueError(f"Invalid session path: {filepath}")


def _session_payload(agent: Agent, name: str) -> dict[str, Any]:
    """The data persisted for a session."""
    return {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "model": agent.model,
        "cwd": str(agent.cwd),
        "history": agent.history,
        "usage": agent.usage,
    }


def _fallback_latest_pointer(tmp_link: Path, latest_link: Path, filename: str) -> None:
    """Write a plain pointer file when symlinking is unavailable."""
    try:
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
    except OSError as exc:
        logger.debug("failed to remove temporary link %s: %s", tmp_link, exc)
    latest_link.write_text(filename, encoding="utf-8")


def _latest_matching_file(sessions_dir: Path, name: str) -> Path | None:
    """The most recent session file matching a name."""
    matching = list(sessions_dir.glob(f"*_{name}.enc"))
    if not matching:
        matching = list(sessions_dir.glob(f"*_{name}.json"))
    if not matching:
        return None
    return max(matching, key=lambda p: p.stat().st_mtime)


def _read_session_file(filepath: Path) -> dict[str, Any]:
    """Read and decrypt a session file."""
    raw = filepath.read_bytes()
    if filepath.suffix == ".json":
        return json.loads(raw)
    return json.loads(_decrypt(raw))


class SessionManager:
    def __init__(self):
        self._sessions_dir = Path.home() / ".apex" / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def save(self, agent: Agent, name: str = "default") -> Path:
        _validate_session_name(name)
        filepath = self._session_filepath(name)
        session_data = _session_payload(agent, name)
        payload = json.dumps(session_data, separators=(",", ":")).encode()
        encrypted = _encrypt(payload)

        with open(filepath, "wb") as handle:
            handle.write(encrypted)

        self._update_latest_pointer(name, filepath)
        return filepath

    def _session_filepath(self, name: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_name}.enc"
        filepath = (self._sessions_dir / filename).resolve()
        _validate_session_path(filepath, self._sessions_dir)
        return filepath

    def _update_latest_pointer(self, name: str, filepath: Path) -> None:
        latest_link = self._sessions_dir / f"latest_{name}.json"
        tmp_link = self._sessions_dir / f".latest_{name}.tmp"
        try:
            if tmp_link.exists() or tmp_link.is_symlink():
                tmp_link.unlink()
            tmp_link.symlink_to(filepath.name)
            os.replace(str(tmp_link), str(latest_link))
        except OSError:
            _fallback_latest_pointer(tmp_link, latest_link, filepath.name)

    def load(self, name: str, agent: Agent) -> bool:
        filepath = self._resolve_latest(name)
        if filepath is None:
            return False
        try:
            session_data = _read_session_file(filepath)
            self._apply_session_data(agent, session_data)
            return True
        except Exception:
            logger.exception(
                "Failed to load session %s", name.replace("\n", "\\n").replace("\r", "\\r")
            )
            return False

    def _resolve_latest(self, name: str) -> Path | None:
        latest_link = self._sessions_dir / f"latest_{name}.json"
        if not latest_link.exists():
            return _latest_matching_file(self._sessions_dir, name)
        try:
            resolved = (self._sessions_dir / latest_link.readlink()).resolve()
        except OSError:
            # Plain pointer file fallback (symlinks unavailable).
            pointer = latest_link.read_text(encoding="utf-8").strip()
            resolved = (self._sessions_dir / pointer).resolve()
        if not str(resolved).startswith(str(self._sessions_dir.resolve())):
            return None
        return resolved

    def _apply_session_data(self, agent: Agent, data: dict[str, Any]) -> None:
        agent.switch_model(data.get("model", "claude-sonnet"))
        agent.cwd = Path(data.get("cwd", "."))
        agent.history = data.get("history", [])

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        sessions: list[dict[str, Any]] = []
        for filepath in self._sessions_dir.glob("*.enc"):
            session = _read_session_summary(filepath)
            if session is not None:
                sessions.append(session)
        return sorted(sessions, key=lambda item: item["timestamp"], reverse=True)

    def share(self, agent: Agent, name: str = "default") -> str:
        session_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "model": agent.model,
            "cwd": str(agent.cwd),
            "history": agent.history,
            "usage": agent.usage,
        }
        payload = json.dumps(session_data, separators=(",", ":")).encode()
        encrypted_payload = _encrypt(payload)

        import hashlib as _hl

        encoded = _hl.sha256(payload + os.urandom(16)).hexdigest()[:16]
        share_id = encoded

        share_dir = self._sessions_dir / "shared"
        share_dir.mkdir(exist_ok=True)
        filepath = share_dir / f"{share_id}.enc"

        with open(filepath, "wb") as f:
            f.write(encrypted_payload)

        logger.info(f"Created shared session: {share_id}")
        return f"apex://share/{share_id}"

    def load_shared(self, share_id: str, agent: Agent) -> bool:
        try:
            share_dir = self._sessions_dir / "shared"
            filepath = share_dir / f"{share_id}.enc"
            if not filepath.exists():
                filepath = share_dir / f"{share_id}.json"
            if not filepath.exists():
                logger.warning(f"Shared session not found: {share_id}")
                return False

            raw = filepath.read_bytes()
            if filepath.suffix == ".json":
                import base64

                wrapper = json.loads(raw)
                compressed = wrapper.get("data", "")
                json_str = base64.b64decode(compressed.encode()).decode()
                session_data = json.loads(json_str)
            else:
                # Fernet-encrypted: single token, decrypt directly
                session_data = json.loads(_decrypt(raw))

            agent.switch_model(session_data.get("model", "claude-sonnet"))
            agent.cwd = Path(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            logger.info(f"Loaded shared session: {share_id}")
            return True
        except Exception:
            logger.exception("Failed to load shared session %s", share_id)
            return False


def _read_session_summary(filepath: Path) -> dict[str, Any] | None:
    """The summary of one session file, or ``None`` when it cannot be read."""
    try:
        raw = filepath.read_bytes()
        data = json.loads(_decrypt(raw))
    except Exception:  # noqa: BLE001
        return None
    return {
        "name": data.get("name", filepath.stem),
        "timestamp": data.get("timestamp", ""),
        "model": data.get("model", ""),
        "history_len": len(data.get("history", [])),
        "path": str(filepath),
    }
