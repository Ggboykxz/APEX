"""Session sharing system for APEX."""

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    re.compile(
        r"(?i)(ANTHROPIC|OPENAI|GEMINI|DEEPSEEK|MISTRAL|COHERE|GROQ|XAI|TOGETHER|FIREWORKS|CEREBRAS|PERPLEXITY|HF|NVIDIA|CLOUDFLARE|DASHSCOPE|LLAMA|OPENROUTER)_API_KEY"
    ),
]

ENVVAR_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)_API_KEY"),
    re.compile(r"(?i)_TOKEN"),
    re.compile(r"(?i)_SECRET"),
    re.compile(r"(?i)_PASSWORD"),
    re.compile(r"(?i)_CREDENTIALS"),
]


def _is_sensitive_key(key: object) -> bool:
    """Whether a key names a secret and must be dropped."""
    return any(pattern.search(str(key)) for pattern in ENVVAR_PATTERNS)


def _sanitize_value(value: Any) -> Any:
    """Sanitize one value of a session."""
    if isinstance(value, dict):
        return ShareManager.sanitize_session_data(value)
    if isinstance(value, list):
        return [_sanitize_list_item(item) for item in value]
    if isinstance(value, str):
        return ShareManager._sanitize_string(value)
    return value


def _sanitize_list_item(item: Any) -> Any:
    """Sanitize one item of a list."""
    if isinstance(item, dict):
        return ShareManager.sanitize_session_data(item)
    if isinstance(item, str):
        return ShareManager._sanitize_string(item)
    return item


def _drop_sensitive_keys(sanitized: dict[str, Any]) -> None:
    """Remove the keys that name a secret."""
    for key in [key for key in sanitized if any(p.search(str(key)) for p in SENSITIVE_PATTERNS)]:
        del sanitized[key]


class ShareManager:
    def __init__(self, config_path: Path | None = None):
        self._shares_dir = Path.home() / ".config" / "apex" / "shares"
        self._shares_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = config_path

    @property
    def _mode(self) -> str:
        value = self._mode_from_path(self._config_path)
        if value is not None:
            return value
        value = self._mode_from_path(Path.home() / ".apex" / "config.json")
        if value is not None:
            return value
        return "manual"

    def _mode_from_path(self, path: Path | None) -> str | None:
        """The share mode declared by a config file, or ``None``."""
        if not path or not path.exists():
            return None
        try:
            with open(path) as handle:
                cfg = json.load(handle)
        except Exception:  # noqa: BLE001
            return None
        val = cfg.get("share", "manual") if isinstance(cfg, dict) else "manual"
        if val in ("manual", "auto", "disabled"):
            return val
        return None

    @staticmethod
    def sanitize_session_data(data: dict) -> dict:
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if _is_sensitive_key(key):
                continue
            sanitized[key] = _sanitize_value(value)
        _drop_sensitive_keys(sanitized)
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
        now = datetime.now(UTC).isoformat()
        url = f"https://apex-ai.dev/s/{share_id}"

        session_data = self._load_session_data(session_id)
        safe_data = self.sanitize_session_data(session_data) if session_data else {}
        messages = safe_data.get("history", safe_data.get("messages", []))
        metadata = {
            k: safe_data.get(k) for k in ("model", "agent", "created_at", "cwd") if k in safe_data
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
                results.append(
                    {
                        "id": data.get("id"),
                        "session_id": data.get("session_id"),
                        "title": data.get("title", ""),
                        "created_at": data.get("created_at"),
                        "url": data.get("url"),
                        "messages_count": data.get("messages_count", 0),
                    }
                )
            except Exception:  # noqa: BLE001, S112
                continue
        return results

    def get_share_url(self, share_id: str) -> str:
        filepath = self._shares_dir / f"{share_id}.json"
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                return data.get("url", f"https://apex-ai.dev/s/{share_id}")
            except Exception:  # noqa: BLE001, S110
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
            "exported_at": datetime.now(UTC).isoformat(),
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
        except Exception:  # noqa: BLE001
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
            data = self._load_from_base(base, session_id)
            if data:
                return data
        return {}

    def _load_from_base(self, base: Path, session_id: str) -> dict:
        """Load a session from one base directory."""
        data = self._load_by_name(base, session_id)
        if data:
            return data
        return self._load_by_glob(base, session_id)

    def _load_by_name(self, base: Path, session_id: str) -> dict:
        """Load a session whose content carries the id."""
        for fpath in base.glob("*"):
            if not fpath.is_file() or fpath.suffix != ".json":
                continue
            try:
                with open(fpath) as handle:
                    data = json.load(handle)
            except Exception:  # noqa: BLE001, S112
                continue
            if data.get("session_id") == session_id or data.get("name") == session_id:
                return data
        return {}

    def _load_by_glob(self, base: Path, session_id: str) -> dict:
        """Load a session whose file name carries the id."""
        for fpath in base.glob(f"*{session_id}*"):
            if not fpath.is_file() or fpath.suffix != ".json":
                continue
            try:
                with open(fpath) as handle:
                    return json.load(handle)
            except Exception:  # noqa: BLE001, S112
                continue
        return {}


share_manager = ShareManager()
