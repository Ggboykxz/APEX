"""Session persistence for APEX - save and load conversation sessions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import Agent


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