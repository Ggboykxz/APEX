"""Refactored session module - More testable."""

import json
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable


class UndoManager:
    def __init__(
        self,
        max_history: int = 50,
        time_factory: Optional[Callable[[], str]] = None
    ):
        self.max_history = max_history
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []
        self._time_factory = time_factory or (lambda: datetime.now().isoformat())

    def snapshot(self, action_type: str, details: dict[str, Any]) -> None:
        snapshot = {
            "type": action_type,
            "details": details,
            "timestamp": self._time_factory(),
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

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)


class SessionManager:
    def __init__(
        self,
        sessions_dir: Optional[Path] = None,
        time_factory: Optional[Callable[[], datetime]] = None,
        path_factory: Optional[Callable[[str], Path]] = None
    ):
        self._sessions_dir = sessions_dir or Path.home() / ".apex" / "sessions"
        self._time_factory = time_factory or datetime.now
        self._path_factory = path_factory or Path
        
        if hasattr(self._sessions_dir, 'mkdir'):
            self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def save(self, agent: Any, name: str = "default") -> Path:
        timestamp = self._time_factory().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.json"
        filepath = self._sessions_dir / filename

        session_data = {
            "name": name,
            "timestamp": self._time_factory().isoformat(),
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

    def load(self, name: str, agent: Any) -> bool:
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
            agent.cwd = self._path_factory(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            return True
        except Exception:
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

    def share(self, agent: Any, name: str = "default") -> str:
        session_data = {
            "name": name,
            "timestamp": self._time_factory().isoformat(),
            "model": agent.model,
            "cwd": str(agent.cwd),
            "history": agent.history,
            "usage": agent.usage,
        }
        json_str = json.dumps(session_data, separators=(",", ":"))
        compressed = base64.b64encode(json_str.encode()).decode()
        share_id = hashlib.sha256(compressed[:100].encode()).hexdigest()[:8]
        share_dir = self._sessions_dir / "shared"
        
        if hasattr(share_dir, 'mkdir'):
            share_dir.mkdir(exist_ok=True)
        
        filepath = share_dir / f"{share_id}.json"
        with open(filepath, "w") as f:
            json.dump({"data": compressed}, f)
        return f"apex://share/{share_id}"

    def load_shared(self, share_id: str, agent: Any) -> bool:
        try:
            share_dir = self._sessions_dir / "shared"
            filepath = share_dir / f"{share_id}.json"
            if not filepath.exists():
                return False
            with open(filepath) as f:
                wrapper = json.load(f)
            compressed = wrapper.get("data", "")
            json_str = base64.b64decode(compressed.encode()).decode()
            session_data = json.loads(json_str)
            agent.switch_model(session_data.get("model", "claude-sonnet"))
            agent.cwd = self._path_factory(session_data.get("cwd", "."))
            agent.history = session_data.get("history", [])
            return True
        except Exception:
            return False


def create_undo_manager(max_history: int = 50, time_factory: Optional[Callable] = None) -> UndoManager:
    return UndoManager(max_history, time_factory)


def create_session_manager(sessions_dir: Optional[Path] = None) -> SessionManager:
    return SessionManager(sessions_dir)