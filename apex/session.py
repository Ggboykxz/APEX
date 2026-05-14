"""Session persistence for APEX - save and load conversation sessions."""

import json
import re
import hashlib
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .agent import Agent

logger = logging.getLogger(__name__)

_ENCRYPTION_KEY: Optional[bytes] = None


def _get_encryption_key() -> bytes:
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is not None:
        return _ENCRYPTION_KEY
    key_file = Path.home() / ".apex" / ".session_key"
    if key_file.exists():
        _ENCRYPTION_KEY = key_file.read_bytes()
    else:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        _ENCRYPTION_KEY = hashlib.sha256(os.urandom(64)).digest()
        key_file.write_bytes(_ENCRYPTION_KEY)
        key_file.chmod(0o600)
    return _ENCRYPTION_KEY


def _encrypt(data: bytes) -> tuple[bytes, bytes, bytes]:
    key = _get_encryption_key()
    import hashlib as _h
    nonce = os.urandom(12)
    cipher = _h.shake_256(key + nonce)
    stream = cipher.digest(len(data))
    ciphertext = bytes(a ^ b for a, b in zip(data, stream))
    tag = hashlib.sha256(nonce + ciphertext + key).digest()[:16]
    return nonce, ciphertext, tag


def _decrypt(nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    key = _get_encryption_key()
    expected_tag = hashlib.sha256(nonce + ciphertext + key).digest()[:16]
    if tag != expected_tag:
        raise ValueError("Decryption failed: data integrity check failed")
    cipher = hashlib.shake_256(key + nonce)
    stream = cipher.digest(len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, stream))


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

    def undo(self) -> Optional[dict[str, Any]]:
        if not self._undo_stack:
            return None
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        return action

    def redo(self) -> Optional[dict[str, Any]]:
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


class SessionManager:
    def __init__(self):
        self._sessions_dir = Path.home() / ".apex" / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def save(self, agent: Agent, name: str = "default") -> Path:
        if not name or ".." in name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid session name: {name}")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_name}.enc"
        filepath = (self._sessions_dir / filename).resolve()
        if (
            self._sessions_dir.resolve() not in filepath.parents
            and filepath.parent != self._sessions_dir.resolve()
        ):
            raise ValueError(f"Invalid session path: {filepath}")

        session_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "model": agent.model,
            "cwd": str(agent.cwd),
            "history": agent.history,
            "usage": agent.usage,
        }

        payload = json.dumps(session_data, separators=(",", ":")).encode()
        nonce, ciphertext, tag = _encrypt(payload)

        with open(filepath, "wb") as f:
            f.write(nonce + tag + ciphertext)

        latest_link = self._sessions_dir / f"latest_{name}.json"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(filepath.name)

        return filepath

    def load(self, name: str, agent: Agent) -> bool:
        latest_link = self._sessions_dir / f"latest_{name}.json"
        if not latest_link.exists():
            matching = list(self._sessions_dir.glob(f"*_{name}.enc"))
            if not matching:
                matching = list(self._sessions_dir.glob(f"*_{name}.json"))
            if not matching:
                return False
            filepath = max(matching, key=lambda p: p.stat().st_mtime)
        else:
            resolved = (self._sessions_dir / latest_link.readlink()).resolve()
            if not str(resolved).startswith(str(self._sessions_dir.resolve())):
                return False
            filepath = resolved

        try:
            raw = filepath.read_bytes()
            if filepath.suffix == ".json":
                session_data = json.loads(raw)
            else:
                nonce, tag, ciphertext = raw[:12], raw[12:28], raw[28:]
                session_data = json.loads(_decrypt(nonce, ciphertext, tag))

            agent.switch_model(session_data.get("model", "claude-sonnet"))
            agent.cwd = Path(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            return True
        except Exception as e:
            logger.error(f"Failed to load session {name}: {e}")
            return False

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        for filepath in self._sessions_dir.glob("*.json"):
            if filepath.is_symlink():
                continue
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    sessions.append(
                        {
                            "name": data.get("name", "unknown"),
                            "timestamp": data.get("timestamp", ""),
                            "model": data.get("model", ""),
                            "history_len": len(data.get("history", [])),
                        }
                    )
            except Exception:
                continue
        for filepath in self._sessions_dir.glob("*.enc"):
            if filepath.is_symlink():
                continue
            try:
                raw = filepath.read_bytes()
                nonce, tag, ciphertext = raw[:12], raw[12:28], raw[28:]
                data = json.loads(_decrypt(nonce, ciphertext, tag))
                sessions.append(
                    {
                        "name": data.get("name", "unknown"),
                        "timestamp": data.get("timestamp", ""),
                        "model": data.get("model", ""),
                        "history_len": len(data.get("history", [])),
                    }
                )
            except Exception:
                continue
        return sorted(sessions, key=lambda s: s["timestamp"], reverse=True)

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

        encrypted_payload = b""
        for i in range(0, len(payload), 32):
            chunk = payload[i:i + 32]
            nonce, ciphertext, tag = _encrypt(chunk)
            encrypted_payload += nonce + tag + ciphertext

        encoded = hashlib.sha256(payload + os.urandom(16)).hexdigest()[:16]
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
                chunks = []
                pos = 0
                while pos < len(raw):
                    nonce = raw[pos:pos + 12]
                    tag = raw[pos + 12:pos + 28]
                    ct_len = min(32, len(raw) - pos - 28)
                    ciphertext = raw[pos + 28:pos + 28 + ct_len]
                    if len(ciphertext) < 1:
                        break
                    chunks.append(_decrypt(nonce, ciphertext, tag))
                    pos += 28 + ct_len
                session_data = json.loads(b"".join(chunks))

            agent.switch_model(session_data.get("model", "claude-sonnet"))
            agent.cwd = Path(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            logger.info(f"Loaded shared session: {share_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load shared session {share_id}: {e}")
            return False
