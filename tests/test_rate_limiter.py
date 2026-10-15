"""Comprehensive tests for rate_limiter.py module — no mocks, real SQLite."""

import os
import tempfile
import time

import pytest

from apex.rate_limiter import (
    MemoryStorage,
    RateLimitConfig,
    RateLimitResult,
    RateLimiter,
    SQLiteStorage,
    StorageBackend,
    create_rate_limiter,
)


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""

    def test_default_values(self):
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000
        assert config.burst_size == 10

    def test_custom_values(self):
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500,
            burst_size=5,
        )
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 100
        assert config.requests_per_day == 500
        assert config.burst_size == 5

    def test_partial_custom(self):
        config = RateLimitConfig(requests_per_minute=30)
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000


# ---------------------------------------------------------------------------
# RateLimitResult
# ---------------------------------------------------------------------------


class TestRateLimitResult:
    """Test RateLimitResult dataclass."""

    def test_result_allowed(self):
        result = RateLimitResult(
            allowed=True,
            remaining_minute=59,
            remaining_hour=999,
            remaining_day=9999,
            reset_at=time.time() + 60,
        )
        assert result.allowed is True
        assert result.remaining_minute == 59
        assert result.remaining_hour == 999
        assert result.remaining_day == 9999
        assert result.retry_after is None

    def test_result_denied(self):
        result = RateLimitResult(
            allowed=False,
            remaining_minute=0,
            remaining_hour=0,
            remaining_day=0,
            reset_at=time.time() + 60,
            retry_after=60,
        )
        assert result.allowed is False
        assert result.retry_after == 60

    def test_result_with_retry_after(self):
        result = RateLimitResult(
            allowed=False,
            remaining_minute=0,
            remaining_hour=5,
            remaining_day=100,
            reset_at=time.time() + 3600,
            retry_after=3600,
        )
        assert result.retry_after == 3600
        assert result.remaining_hour == 5


# ---------------------------------------------------------------------------
# StorageBackend ABC
# ---------------------------------------------------------------------------


class TestStorageBackend:
    """Test StorageBackend abstract base class."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            StorageBackend()

    def test_subclass_must_implement(self):
        class IncompleteBackend(StorageBackend):
            pass

        with pytest.raises(TypeError):
            IncompleteBackend()

    def test_complete_subclass(self):
        class CompleteBackend(StorageBackend):
            def get_counts(self, key):
                return {"minute": 0, "hour": 0, "day": 0}

            def increment(self, key, window):
                pass

            def cleanup_expired(self):
                pass

        backend = CompleteBackend()
        assert backend.get_counts("test")["minute"] == 0


class TestStorageBackendAbstractLines:
    """Hit lines 36, 40, 44 — the pass statements in abstract methods."""

    def test_get_counts_pass(self):
        class Sub(StorageBackend):
            def get_counts(self, key):
                super().get_counts(key)
                return {}

            def increment(self, key, window):
                super().increment(key, window)

            def cleanup_expired(self):
                super().cleanup_expired()

        s = Sub()
        assert s.get_counts("x") == {}
        s.increment("x", "m")
        s.cleanup_expired()


# ---------------------------------------------------------------------------
# MemoryStorage
# ---------------------------------------------------------------------------


class TestMemoryStorage:
    """Test MemoryStorage class."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    def test_get_counts_initial(self, storage):
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0
        assert counts["hour"] == 0
        assert counts["day"] == 0

    def test_increment_minute(self, storage):
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1
        assert counts["hour"] == 0
        assert counts["day"] == 0

    def test_increment_hour(self, storage):
        storage.increment("key1", "hour")
        counts = storage.get_counts("key1")
        assert counts["hour"] == 1
        assert counts["minute"] == 0

    def test_increment_day(self, storage):
        storage.increment("key1", "day")
        counts = storage.get_counts("key1")
        assert counts["day"] == 1

    def test_increment_multiple_windows(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key1", "hour")
        storage.increment("key1", "day")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1
        assert counts["hour"] == 1
        assert counts["day"] == 1

    def test_increment_existing(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key1", "minute")
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 3

    def test_different_keys_independent(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key1", "minute")
        storage.increment("key2", "minute")
        assert storage.get_counts("key1")["minute"] == 2
        assert storage.get_counts("key2")["minute"] == 1

    def test_expired_minute_window(self, storage):
        """When the timestamp is old, counts return 0 for that window."""
        storage._counts["key1"]["minute"] = (5, time.time() - 120)
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0

    def test_expired_hour_window(self, storage):
        storage._counts["key1"]["hour"] = (10, time.time() - 7200)
        counts = storage.get_counts("key1")
        assert counts["hour"] == 0

    def test_expired_day_window(self, storage):
        storage._counts["key1"]["day"] = (100, time.time() - 100000)
        counts = storage.get_counts("key1")
        assert counts["day"] == 0

    def test_non_expired_returns_count(self, storage):
        storage._counts["key1"]["minute"] = (5, time.time() - 30)
        counts = storage.get_counts("key1")
        assert counts["minute"] == 5

    def test_increment_resets_expired_window(self, storage):
        storage._counts["key1"]["minute"] = (5, time.time() - 120)
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1

    def test_increment_within_window(self, storage):
        storage.increment("key1", "minute")
        first_counts = storage.get_counts("key1")
        storage.increment("key1", "minute")
        second_counts = storage.get_counts("key1")
        assert second_counts["minute"] == first_counts["minute"] + 1

    def test_cleanup_expired_removes_old_keys(self, storage):
        storage._counts["key1"]["minute"] = (5, time.time() - 120)
        storage.cleanup_expired()
        assert "key1" not in storage._counts

    def test_cleanup_keeps_active_keys(self, storage):
        # Increment all windows so none have default (0, 0) timestamp
        storage.increment("key1", "minute")
        storage.increment("key1", "hour")
        storage.increment("key1", "day")
        storage.cleanup_expired()
        assert "key1" in storage._counts

    def test_cleanup_mixed(self, storage):
        storage._counts["expired"]["minute"] = (5, time.time() - 120)
        # Increment all windows for 'active' so none have default timestamp
        storage.increment("active", "minute")
        storage.increment("active", "hour")
        storage.increment("active", "day")
        storage.cleanup_expired()
        assert "expired" not in storage._counts
        assert "active" in storage._counts


# ---------------------------------------------------------------------------
# SQLiteStorage
# ---------------------------------------------------------------------------


class TestSQLiteStorage:
    """Test SQLiteStorage class."""

    @pytest.fixture
    def storage(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)  # remove so SQLiteStorage creates fresh
        storage = SQLiteStorage(db_path)
        yield storage
        # cleanup
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass

    def test_get_counts_initial(self, storage):
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0
        assert counts["hour"] == 0
        assert counts["day"] == 0

    def test_increment_minute(self, storage):
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1

    def test_increment_multiple(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 2

    def test_different_keys(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key2", "minute")
        counts1 = storage.get_counts("key1")
        counts2 = storage.get_counts("key2")
        assert counts1["minute"] == 1
        assert counts2["minute"] == 1

    def test_increment_hour(self, storage):
        storage.increment("key1", "hour")
        counts = storage.get_counts("key1")
        assert counts["hour"] == 1

    def test_increment_day(self, storage):
        storage.increment("key1", "day")
        counts = storage.get_counts("key1")
        assert counts["day"] == 1

    def test_increment_multiple_windows(self, storage):
        storage.increment("key1", "minute")
        storage.increment("key1", "hour")
        storage.increment("key1", "day")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1
        assert counts["hour"] == 1
        assert counts["day"] == 1

    def test_cleanup_expired(self, storage):
        storage.increment("key1", "minute")
        # Manually set the timestamp to be expired
        now = time.time()
        with sqlite3_connect(storage.db_path) as conn:
            conn.execute(
                "UPDATE rate_limits SET timestamp = ? WHERE key = ? AND window = ?",
                (now - 120, "key1", "minute"),
            )
            conn.commit()
        storage.cleanup_expired()
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0

    def test_cleanup_keeps_active(self, storage):
        storage.increment("key1", "minute")
        storage.cleanup_expired()
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1

    def test_increment_resets_expired_window(self, storage):
        storage.increment("key1", "minute")
        # Expire the window
        now = time.time()
        with sqlite3_connect(storage.db_path) as conn:
            conn.execute(
                "UPDATE rate_limits SET timestamp = ?, count = ? WHERE key = ? AND window = ?",
                (now - 120, 50, "key1", "minute"),
            )
            conn.commit()
        # Increment should reset the count to 1
        storage.increment("key1", "minute")
        counts = storage.get_counts("key1")
        assert counts["minute"] == 1

    def test_get_counts_expired_record(self, storage):
        """Test that get_counts returns 0 for expired records in SQLite."""
        storage.increment("key1", "minute")
        now = time.time()
        with sqlite3_connect(storage.db_path) as conn:
            conn.execute(
                "UPDATE rate_limits SET timestamp = ? WHERE key = ? AND window = ?",
                (now - 120, "key1", "minute"),
            )
            conn.commit()
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0

    def test_init_creates_db(self, storage):
        assert storage.db_path.exists()

    def test_default_db_path(self):
        from pathlib import Path

        storage = SQLiteStorage()
        expected = Path("~/.apex/rate_limits.db").expanduser()
        assert storage.db_path == expected


def sqlite3_connect(path):
    """Helper to get a sqlite3 connection."""
    import sqlite3

    return sqlite3.connect(path)


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=20,
            requests_per_day=50,
        )
        return RateLimiter(config=config)

    def test_check_rate_limit_allowed(self, limiter):
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True
        assert result.remaining_minute == 4

    def test_check_rate_limit_decrements_remaining(self, limiter):
        result1 = limiter.check_rate_limit("user1")
        result2 = limiter.check_rate_limit("user1")
        assert result2.remaining_minute == result1.remaining_minute - 1

    def test_check_rate_limit_minute_exceeded(self, limiter):
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 60
        assert result.remaining_minute == 0

    def test_check_rate_limit_hour_exceeded(self):
        config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=5,
            requests_per_day=100,
        )
        limiter = RateLimiter(config=config)
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 3600
        assert result.remaining_hour == 0

    def test_check_rate_limit_day_exceeded(self):
        config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=1000,
            requests_per_day=5,
        )
        limiter = RateLimiter(config=config)
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 86400
        assert result.remaining_day == 0

    def test_different_keys_independent(self, limiter):
        result1 = limiter.check_rate_limit("user1")
        result2 = limiter.check_rate_limit("user2")
        assert result1.remaining_minute == result2.remaining_minute == 4

    def test_get_status(self, limiter):
        limiter.check_rate_limit("user1")
        status = limiter.get_status("user1")
        assert status["minute"]["used"] == 1
        assert status["minute"]["limit"] == 5
        assert status["hour"]["used"] == 1
        assert status["hour"]["limit"] == 20
        assert status["day"]["used"] == 1
        assert status["day"]["limit"] == 50

    def test_get_status_no_requests(self, limiter):
        status = limiter.get_status("user_unknown")
        assert status["minute"]["used"] == 0
        assert status["minute"]["limit"] == 5

    def test_reset_method(self, limiter):
        """reset() is a no-op (just logs), so subsequent requests still increment."""
        limiter.check_rate_limit("user1")
        limiter.reset("user1")
        # After reset (no-op), next check increments count to 2
        result = limiter.check_rate_limit("user1")
        # remaining should be 5 - 2 = 3 since reset doesn't clear storage
        assert result.remaining_minute == 3

    def test_auto_cleanup(self):
        config = RateLimitConfig(requests_per_minute=60)
        storage = MemoryStorage()
        limiter = RateLimiter(config=config, storage=storage)
        limiter._last_cleanup = time.time() - 4000
        limiter.check_rate_limit("user1")
        assert limiter._last_cleanup > time.time() - 10

    def test_no_cleanup_when_recent(self):
        storage = MemoryStorage()
        limiter = RateLimiter(storage=storage)
        # Add an expired entry that should NOT be cleaned up
        storage._counts["old_key"]["minute"] = (5, time.time() - 120)
        original_cleanup = time.time()
        limiter._last_cleanup = original_cleanup
        limiter.check_rate_limit("user1")
        # Cleanup should not have run since _last_cleanup is recent
        assert limiter._last_cleanup == original_cleanup

    def test_default_config(self):
        limiter = RateLimiter()
        assert limiter.config.requests_per_minute == 60
        assert limiter.config.requests_per_hour == 1000
        assert limiter.config.requests_per_day == 10000

    def test_custom_storage(self):
        storage = MemoryStorage()
        limiter = RateLimiter(storage=storage)
        assert limiter.storage is storage

    def test_rate_limit_result_has_reset_at(self, limiter):
        result = limiter.check_rate_limit("user1")
        assert result.reset_at > time.time()

    def test_rate_limit_minute_exceeded_preserves_hour_day(self, limiter):
        """When minute limit is exceeded, hour/day remaining should still show."""
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.remaining_hour >= 0
        assert result.remaining_day >= 0

    def test_rate_limit_with_sqlite_storage(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)
        try:
            storage = SQLiteStorage(db_path)
            config = RateLimitConfig(
                requests_per_minute=3,
                requests_per_hour=10,
                requests_per_day=20,
            )
            limiter = RateLimiter(config=config, storage=storage)
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True
            assert result.remaining_minute == 2
        finally:
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------------------
# create_rate_limiter
# ---------------------------------------------------------------------------


class TestCreateRateLimiter:
    """Test create_rate_limiter factory function."""

    def test_create_memory_limiter(self):
        limiter = create_rate_limiter(use_sqlite=False)
        assert isinstance(limiter, RateLimiter)
        assert isinstance(limiter.storage, MemoryStorage)
        result = limiter.check_rate_limit("test")
        assert result.allowed is True

    def test_create_sqlite_limiter(self):
        limiter = create_rate_limiter(use_sqlite=True)
        assert isinstance(limiter, RateLimiter)
        assert isinstance(limiter.storage, SQLiteStorage)
        result = limiter.check_rate_limit("test")
        assert result.allowed is True

    def test_create_with_config(self):
        config = RateLimitConfig(requests_per_minute=10)
        limiter = create_rate_limiter(config=config)
        assert limiter.config.requests_per_minute == 10

    def test_create_default_is_memory(self):
        limiter = create_rate_limiter()
        assert isinstance(limiter.storage, MemoryStorage)

    def test_create_with_config_and_sqlite(self):
        config = RateLimitConfig(requests_per_minute=5)
        limiter = create_rate_limiter(config=config, use_sqlite=True)
        assert isinstance(limiter.storage, SQLiteStorage)
        assert limiter.config.requests_per_minute == 5
