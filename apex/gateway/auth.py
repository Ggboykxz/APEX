"""API key generation, storage, and validation for the gateway."""

import logging
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuthManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS keys (
                    key_id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    tier TEXT NOT NULL DEFAULT 'free',
                    label TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    last_used_at REAL,
                    is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS usage (
                    key_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    requests INTEGER DEFAULT 0,
                    tokens INTEGER DEFAULT 0,
                    PRIMARY KEY (key_id, date),
                    FOREIGN KEY (key_id) REFERENCES keys(key_id)
                );
            """)

    def generate_key(self, tier: str = "free", label: str = "") -> str:
        api_key = f"apex_{secrets.token_hex(24)}"
        key_id = secrets.token_hex(8)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO keys (key_id, api_key, tier, label, created_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                (key_id, api_key, tier, label, time.time()),
            )
        logger.info(f"Generated {tier} key: {key_id} ({label})")
        return api_key

    def validate_key(self, api_key: str) -> Optional[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT key_id, tier, is_active FROM keys WHERE api_key = ?", (api_key,)
            ).fetchone()
        if not row:
            return None
        key_id, tier, is_active = row
        if not is_active:
            return None
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("UPDATE keys SET last_used_at = ? WHERE key_id = ?", (time.time(), key_id))
        return {"key_id": key_id, "tier": tier}

    def list_keys(self) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT key_id, tier, label, created_at, last_used_at, is_active FROM keys ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "key_id": r[0],
                "tier": r[1],
                "label": r[2],
                "created_at": r[3],
                "last_used_at": r[4],
                "is_active": bool(r[5]),
            }
            for r in rows
        ]

    def revoke_key(self, api_key: str) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            c = conn.execute("UPDATE keys SET is_active = 0 WHERE api_key = ?", (api_key,))
            return c.rowcount > 0

    def get_or_create_day_usage(self, key_id: str, date: str) -> tuple[int, int]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT requests, tokens FROM usage WHERE key_id = ? AND date = ?", (key_id, date)
            ).fetchone()
        if row:
            return (row[0], row[1])
        return (0, 0)

    def record_usage(self, key_id: str, date: str, requests: int = 1, tokens: int = 0):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO usage (key_id, date, requests, tokens)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key_id, date) DO UPDATE SET
                       requests = requests + excluded.requests,
                       tokens = tokens + excluded.tokens""",
                (key_id, date, requests, tokens),
            )
