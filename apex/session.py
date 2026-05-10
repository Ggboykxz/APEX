"""Session persistence for APEX - save and load conversation sessions."""

import json
import hashlib
import base64
import os
import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .agent import Agent

logger = logging.getLogger(__name__)


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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.json"
        filepath = self._sessions_dir / filename

        session_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "model": agent.model,
            "cwd": str(agent.cwd),
            "history": agent.history,
            "usage": agent.usage,
        }

        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)

        latest_link = self._sessions_dir / f"latest_{name}.json"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(filepath.name)

        return filepath

    def load(self, name: str, agent: Agent) -> bool:
        latest_link = self._sessions_dir / f"latest_{name}.json"
        if not latest_link.exists():
            matching = list(self._sessions_dir.glob(f"*_{name}.json"))
            if not matching:
                return False
            filepath = max(matching, key=lambda p: p.stat().st_mtime)
        else:
            filepath = self._sessions_dir / latest_link.readlink()

        try:
            with open(filepath) as f:
                session_data = json.load(f)

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
                    sessions.append({
                        "name": data.get("name", "unknown"),
                        "timestamp": data.get("timestamp", ""),
                        "model": data.get("model", ""),
                        "history_len": len(data.get("history", [])),
                    })
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
        json_str = json.dumps(session_data, separators=(",", ":"))
        compressed = base64.b64encode(json_str.encode()).decode()
        
        full_hash = hashlib.sha256()
        full_hash.update(json_str.encode())
        full_hash.update(str(datetime.now().timestamp()).encode())
        full_hash.update(secrets.token_bytes(32))
        share_id = full_hash.hexdigest()[:16]
        
        share_dir = self._sessions_dir / "shared"
        share_dir.mkdir(exist_ok=True)
        filepath = share_dir / f"{share_id}.json"
        
        nonce = secrets.token_hex(16)
        
        with open(filepath, "w") as f:
            json.dump({
                "data": compressed,
                "nonce": nonce,
                "id": share_id
            }, f)
        
        logger.info(f"Created shared session: {share_id}")
        return f"apex://share/{share_id}"

    def load_shared(self, share_id: str, agent: Agent) -> bool:
        try:
            share_dir = self._sessions_dir / "shared"
            filepath = share_dir / f"{share_id}.json"
            if not filepath.exists():
                logger.warning(f"Shared session not found: {share_id}")
                return False
            with open(filepath) as f:
                wrapper = json.load(f)
            compressed = wrapper.get("data", "")
            
            json_str = base64.b64decode(compressed.encode()).decode()
            session_data = json.loads(json_str)
            
            agent.switch_model(session_data.get("model", "claude-sonnet"))
            agent.cwd = Path(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            logger.info(f"Loaded shared session: {share_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load shared session {share_id}: {e}")
            return False