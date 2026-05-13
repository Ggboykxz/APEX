"""Database-backed rate limiting for APEX HTTP API."""

import logging
import sqlite3
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10


@dataclass
class RateLimitResult:
    allowed: bool
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_at: float
    retry_after: Optional[int] = None


class StorageBackend(ABC):
    @abstractmethod
    def get_counts(self, key: str) -> dict[str, int]:
        pass

    @abstractmethod
    def increment(self, key: str, window: str) -> None:
        pass

    @abstractmethod
    def cleanup_expired(self) -> None:
        pass


class MemoryStorage(StorageBackend):
    def __init__(self):
        self._counts: dict[str, dict[str, tuple[int, float]]] = defaultdict(
            lambda: {"minute": (0, 0), "hour": (0, 0), "day": (0, 0)}
        )

    def get_counts(self, key: str) -> dict[str, int]:
        now = time.time()
        counts = {}
        windows = self._counts.get(key)
        if windows is None:
            return {"minute": 0, "hour": 0, "day": 0}
        for window, (count, timestamp) in windows.items():
            window_duration = {"minute": 60, "hour": 3600, "day": 86400}[window]
            if now - timestamp > window_duration:
                counts[window] = 0
            else:
                counts[window] = count
        return counts

    def increment(self, key: str, window: str) -> None:
        now = time.time()
        count, timestamp = self._counts[key][window]
        window_duration = {"minute": 60, "hour": 3600, "day": 86400}[window]
        if now - timestamp > window_duration:
            self._counts[key][window] = (1, now)
        else:
            self._counts[key][window] = (count + 1, timestamp)

    def cleanup_expired(self) -> None:
        now = time.time()
        for key, windows in list(self._counts.items()):
            expired_windows = []
            for window, (count, timestamp) in windows.items():
                window_duration = {"minute": 60, "hour": 3600, "day": 86400}[window]
                if now - timestamp > window_duration:
                    expired_windows.append(window)
            for w in expired_windows:
                del self._counts[key][w]
            if not self._counts[key]:
                del self._counts[key]


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: str = "~/.apex/rate_limits.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    window TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    timestamp REAL NOT NULL,
                    UNIQUE(key, window)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON rate_limits(key)")
            conn.commit()

    def get_counts(self, key: str) -> dict[str, int]:
        now = time.time()
        counts = {"minute": 0, "hour": 0, "day": 0}
        window_durations = {"minute": 60, "hour": 3600, "day": 86400}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT window, count, timestamp FROM rate_limits WHERE key = ?", (key,)
            )
            for window, count, timestamp in cursor:
                if window in window_durations:
                    if now - timestamp > window_durations[window]:
                        counts[window] = 0
                    else:
                        counts[window] = count
        return counts

    def increment(self, key: str, window: str) -> None:
        now = time.time()
        window_durations = {"minute": 60, "hour": 3600, "day": 86400}
        duration = window_durations.get(window, 60)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT count, timestamp FROM rate_limits WHERE key = ? AND window = ?",
                (key, window),
            )
            row = cursor.fetchone()
            if row:
                count, timestamp = row
                if now - timestamp > duration:
                    conn.execute(
                        "UPDATE rate_limits SET count = 1, timestamp = ? WHERE key = ? AND window = ?",
                        (now, key, window),
                    )
                else:
                    conn.execute(
                        "UPDATE rate_limits SET count = count + 1 WHERE key = ? AND window = ?",
                        (key, window),
                    )
            else:
                conn.execute(
                    "INSERT INTO rate_limits (key, window, count, timestamp) VALUES (?, ?, 1, ?)",
                    (key, window, now),
                )
            conn.commit()

    def cleanup_expired(self) -> None:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            for window, duration in [("minute", 60), ("hour", 3600), ("day", 86400)]:
                conn.execute(
                    "DELETE FROM rate_limits WHERE window = ? AND timestamp < ?",
                    (window, now - duration),
                )
            conn.commit()


class RateLimiter:
    def __init__(
        self, config: Optional[RateLimitConfig] = None, storage: Optional[StorageBackend] = None
    ):
        self.config = config or RateLimitConfig()
        self.storage = storage or MemoryStorage()
        self._cleanup_interval = 3600
        self._last_cleanup = time.time()

    def check_rate_limit(self, key: str) -> RateLimitResult:
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self.storage.cleanup_expired()
            self._last_cleanup = time.time()
        counts = self.storage.get_counts(key)
        now = time.time()
        if counts["minute"] >= self.config.requests_per_minute:
            reset_at = now + 60
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=max(0, self.config.requests_per_hour - counts["hour"]),
                remaining_day=max(0, self.config.requests_per_day - counts["day"]),
                reset_at=reset_at,
                retry_after=60,
            )
        if counts["hour"] >= self.config.requests_per_hour:
            reset_at = now + 3600
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=max(0, self.config.requests_per_day - counts["day"]),
                reset_at=reset_at,
                retry_after=3600,
            )
        if counts["day"] >= self.config.requests_per_day:
            reset_at = now + 86400
            return RateLimitResult(
                allowed=False,
                remaining_minute=0,
                remaining_hour=0,
                remaining_day=0,
                reset_at=reset_at,
                retry_after=86400,
            )
        self.storage.increment(key, "minute")
        self.storage.increment(key, "hour")
        self.storage.increment(key, "day")
        return RateLimitResult(
            allowed=True,
            remaining_minute=self.config.requests_per_minute - counts["minute"] - 1,
            remaining_hour=self.config.requests_per_hour - counts["hour"] - 1,
            remaining_day=self.config.requests_per_day - counts["day"] - 1,
            reset_at=now + 60,
        )

    def reset(self, key: str) -> None:
        logger.info(f"Rate limit reset for key: {key}")

    def get_status(self, key: str) -> dict:
        counts = self.storage.get_counts(key)
        return {
            "minute": {"used": counts["minute"], "limit": self.config.requests_per_minute},
            "hour": {"used": counts["hour"], "limit": self.config.requests_per_hour},
            "day": {"used": counts["day"], "limit": self.config.requests_per_day},
        }


def create_rate_limiter(
    config: Optional[RateLimitConfig] = None, use_sqlite: bool = False
) -> RateLimiter:
    if use_sqlite:
        return RateLimiter(config=config, storage=SQLiteStorage())
    return RateLimiter(config=config, storage=MemoryStorage())
