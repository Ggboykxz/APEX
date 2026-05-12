"""Session sharing system for APEX."""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import __version__

SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|apikey|token|secret|password|passwd|credential|auth[_-]?token)"),
    re.compile(r"(?i)(openai|anthropic|gemini|deepseek|mistral|cohere|groq)[_-]?api[_-]?key"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36,}"),
    re.compile(r"gho_[a-zA-Z0-9]{36,}"),
    re.compile(r"xox[bpras]-[a-zA-Z0-9-]{10,}"),
    re.compile(r"(?i)(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"(?i)(ANTHROPIC|OPENAI|GEMINI|DEEPSEEK|MISTRAL|COHERE|GROQ|XAI|TOGETHER|FIREWORKS|CEREBRAS|PERPLEXITY|HF|NVIDIA|CLOUDFLARE|DASHSCOPE|LLAMA|OPENROUTER)_API_KEY"),
]

ENVVAR_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)_API_KEY"),
    re.compile(r"(?i)_TOKEN"),
    re.compile(r"(?i)_SECRET"),
    re.compile(r"(?i)_PASSWORD"),
    re.compile(r"(?i)_CREDENTIALS"),
]


class ShareManager:
    def __init__(self, config_path: Optional[Path] = None):
        self._shares_dir = Path.home() / ".config" / "apex" / "shares"
        self._shares_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = config_path

    @property
    def _mode(self) -> str:
        try:
            if self._config_path and self._config_path.exists():
                with open(self._config_path) as f:
                    cfg = json.load(f)
                val = cfg.get("share", "manual")
                if val in ("manual", "auto", "disabled"):
                    return val
        except Exception:
            pass
        apex_config_path = Path.home() / ".apex" / "config.json"
        if apex_config_path.exists():
            try:
                with open(apex_config_path) as f:
                    cfg = json.load(f)
                val = cfg.get("share", "manual")
                if val in ("manual", "auto", "disabled"):
                    return val
            except Exception:
                pass
        return "manual"

    @staticmethod
    def sanitize_session_data(data: dict) -> dict:
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if any(p.search(str(key)) for p in ENVVAR_PATTERNS):
                continue
            if isinstance(value, dict):
                sanitized[key] = ShareManager.sanitize_session_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    ShareManager.sanitize_session_data(item) if isinstance(item, dict)
                    else ShareManager._sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                sanitized[key] = ShareManager._sanitize_string(value)
            else:
                sanitized[key] = value

        for key in list(sanitized.keys()):
            if any(p.search(str(key)) for p in SENSITIVE_PATTERNS):
                del sanitized[key]

        return sanitized

    @staticmethod
    def _sanitize_string(value: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            value = pattern.sub("***REDACTED***", value)
        return value

    def _generate_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def share_session(self, session_id: str, title: str = "") -> str:
        if self._mode == "disabled":
            return ""

        share_id = self._generate_id()
        now = datetime.now(timezone.utc).isoformat()
        url = f"https://apex-ai.dev/s/{share_id}"

        session_data = self._load_session_data(session_id)
        safe_data = self.sanitize_session_data(session_data) if session_data else {}
        messages = safe_data.get("history", safe_data.get("messages", []))
        metadata = {
            k: safe_data.get(k)
            for k in ("model", "agent", "created_at", "cwd")
            if k in safe_data
        }

        share = {
            "id": share_id,
            "session_id": session_id,
            "title": title or safe_data.get("name", ""),
            "created_at": now,
            "url": url,
            "messages_count": len(messages),
            "messages": messages,
            "metadata": metadata,
        }

        filepath = self._shares_dir / f"{share_id}.json"
        with open(filepath, "w") as f:
            json.dump(share, f, indent=2)

        return url

    def unshare_session(self, share_id: str) -> bool:
        filepath = self._shares_dir / f"{share_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_shared(self) -> list[dict]:
        results: list[dict] = []
        for filepath in sorted(self._shares_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                results.append({
                    "id": data.get("id"),
                    "session_id": data.get("session_id"),
                    "title": data.get("title", ""),
                    "created_at": data.get("created_at"),
                    "url": data.get("url"),
                    "messages_count": data.get("messages_count", 0),
                })
            except Exception:
                continue
        return results

    def get_share_url(self, share_id: str) -> str:
        filepath = self._shares_dir / f"{share_id}.json"
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                return data.get("url", f"https://apex-ai.dev/s/{share_id}")
            except Exception:
                pass
        return ""

    def is_shared(self, share_id: str) -> bool:
        filepath = self._shares_dir / f"{share_id}.json"
        return filepath.exists()

    def export_session(self, session_id: str) -> dict:
        data = self._load_session_data(session_id)
        if not data:
            return {}
        safe = self.sanitize_session_data(data)
        export = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "apex_version": __version__,
            "data": safe,
        }
        return export

    def import_session(self, file_path: str) -> str | None:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            return None

        session_data = data.get("data", data)
        session_id = session_data.get("session_id") or uuid.uuid4().hex[:12]
        safe = self.sanitize_session_data(session_data)

        sessions_dir = Path.home() / ".apex" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_imported_{session_id}.json"
        filepath = sessions_dir / filename
        with open(filepath, "w") as f:
            json.dump(safe, f, indent=2)
        return session_id

    def _load_session_data(self, session_id: str) -> dict:
        base_dirs = [
            Path.home() / ".apex" / "sessions",
            Path.home() / ".config" / "apex" / "sessions",
        ]
        for base in base_dirs:
            if not base.exists():
                continue
            for fpath in base.glob("*"):
                if fpath.is_file() and fpath.suffix == ".json":
                    try:
                        with open(fpath) as f:
                            data = json.load(f)
                        if data.get("session_id") == session_id or data.get("name") == session_id:
                            return data
                    except Exception:
                        continue
            for fpath in base.glob(f"*{session_id}*"):
                if fpath.is_file() and fpath.suffix == ".json":
                    try:
                        with open(fpath) as f:
                            return json.load(f)
                    except Exception:
                        continue
        return {}


share_manager = ShareManager()
