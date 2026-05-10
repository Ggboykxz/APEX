"""API key management with workspaces for APEX."""

import ast
import hashlib
import logging
import secrets
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _safe_parse(data: str, default):
    """Safely parse a JSON-like string without using eval()."""
    if not data:
        return default
    try:
        return ast.literal_eval(data)
    except (ValueError, SyntaxError):
        try:
            import json
            return json.loads(data)
        except Exception:
            return default


class InvalidKeyError(Exception):
    pass


class KeyExpiredError(Exception):
    pass


class KeyDisabledError(Exception):
    pass


class WorkspaceNotFoundError(Exception):
    pass


@dataclass
class APIKeyInfo:
    key_id: str
    key_hash: str
    workspace_id: str
    name: str
    created_at: float
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    request_count: int = 0
    is_active: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    permissions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Workspace:
    workspace_id: str
    name: str
    owner_id: str
    created_at: float
    is_active: bool = True
    settings: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class KeyManager:
    def __init__(self, db_path: str = "~/.apex/api_keys.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    settings TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    last_used REAL,
                    request_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    rate_limit_per_minute INTEGER DEFAULT 60,
                    rate_limit_per_hour INTEGER DEFAULT 1000,
                    permissions TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key_hash ON api_keys(key_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workspace ON api_keys(workspace_id)")
            conn.commit()

    def create_workspace(self, name: str, owner_id: str, settings: Optional[dict] = None) -> Workspace:
        workspace_id = str(uuid.uuid4())
        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            owner_id=owner_id,
            created_at=time.time(),
            settings=settings or {}
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO workspaces (workspace_id, name, owner_id, created_at, is_active, settings, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (workspace_id, name, owner_id, workspace.created_at, 1, str(settings or {}), "{}")
            )
            conn.commit()
        logger.info(f"Created workspace: {workspace_id}")
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT workspace_id, name, owner_id, created_at, is_active, settings, metadata FROM workspaces WHERE workspace_id = ?",
                (workspace_id,)
            )
            row = cursor.fetchone()
            if row:
                return Workspace(
                    workspace_id=row[0],
                    name=row[1],
                    owner_id=row[2],
                    created_at=row[3],
                    is_active=bool(row[4]),
                    settings=_safe_parse(row[5]) if row[5] else {},
                    metadata=_safe_parse(row[6]) if row[6] else {}
                )
        return None

    def create_key(self, workspace_id: str, name: str, expires_in: Optional[int] = None,
                   rate_limit_per_minute: int = 60, rate_limit_per_hour: int = 1000,
                   permissions: Optional[list[str]] = None, metadata: Optional[dict] = None) -> tuple[str, APIKeyInfo]:
        key = f"apex_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = str(uuid.uuid4())[:8]
        created_at = time.time()
        expires_at = created_at + expires_in if expires_in else None
        key_info = APIKeyInfo(
            key_id=key_id,
            key_hash=key_hash,
            workspace_id=workspace_id,
            name=name,
            created_at=created_at,
            expires_at=expires_at,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            permissions=permissions or [],
            metadata=metadata or {}
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO api_keys (key_id, key_hash, workspace_id, name, created_at, expires_at, 
                   rate_limit_per_minute, rate_limit_per_hour, permissions, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (key_id, key_hash, workspace_id, name, created_at, expires_at,
                 rate_limit_per_minute, rate_limit_per_hour, str(permissions or []), str(metadata or {}))
            )
            conn.commit()
        logger.info(f"Created API key: {key_id} for workspace {workspace_id}")
        return key, key_info

    def validate_key(self, key: str) -> APIKeyInfo:
        if not key or not key.startswith("apex_"):
            raise InvalidKeyError("Invalid API key format")
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT key_id, key_hash, workspace_id, name, created_at, expires_at, last_used,
                   request_count, is_active, rate_limit_per_minute, rate_limit_per_hour, permissions, metadata
                   FROM api_keys WHERE key_hash = ?""",
                (key_hash,)
            )
            row = cursor.fetchone()
            if not row:
                raise InvalidKeyError("API key not found")
            key_info = APIKeyInfo(
                key_id=row[0],
                key_hash=row[1],
                workspace_id=row[2],
                name=row[3],
                created_at=row[4],
                expires_at=row[5],
                last_used=row[6],
                request_count=row[7],
                is_active=bool(row[8]),
                rate_limit_per_minute=row[9],
                rate_limit_per_hour=row[10],
                permissions=_safe_parse(row[11]) if row[11] else [],
                metadata=_safe_parse(row[12]) if row[12] else {}
            )
        if not key_info.is_active:
            raise KeyDisabledError("API key is disabled")
        if key_info.expires_at and time.time() > key_info.expires_at:
            raise KeyExpiredError("API key has expired")
        conn.execute(
            "UPDATE api_keys SET last_used = ?, request_count = request_count + 1 WHERE key_id = ?",
            (time.time(), key_info.key_id)
        )
        conn.commit()
        return key_info

    def revoke_key(self, key_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("UPDATE api_keys SET is_active = 0 WHERE key_id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_keys(self, workspace_id: str) -> list[APIKeyInfo]:
        keys = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT key_id, key_hash, workspace_id, name, created_at, expires_at, last_used,
                   request_count, is_active, rate_limit_per_minute, rate_limit_per_hour, permissions, metadata
                   FROM api_keys WHERE workspace_id = ?""",
                (workspace_id,)
            )
            for row in cursor:
                keys.append(APIKeyInfo(
                    key_id=row[0], key_hash=row[1], workspace_id=row[2], name=row[3],
                    created_at=row[4], expires_at=row[5], last_used=row[6], request_count=row[7],
                    is_active=bool(row[8]), rate_limit_per_minute=row[9], rate_limit_per_hour=row[10],
                    permissions=_safe_parse(row[11]) if row[11] else [], metadata=_safe_parse(row[12]) if row[12] else {}
                ))
        return keys

    def delete_key(self, key_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM api_keys WHERE key_id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0


key_manager = KeyManager()


def create_key_manager(db_path: Optional[str] = None) -> KeyManager:
    return KeyManager(db_path=db_path) if db_path else KeyManager()