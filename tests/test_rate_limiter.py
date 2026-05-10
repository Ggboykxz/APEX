"""Tests for rate_limiter.py module."""

import pytest
import time
import tempfile
import os
from apex.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitResult,
    MemoryStorage,
    SQLiteStorage,
    create_rate_limiter,
)


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
            requests_per_minute=10, requests_per_hour=100, requests_per_day=500
        )
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 100
        assert config.requests_per_day == 500


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
        counts = storage.get_counts("key1")
        assert counts["minute"] == 2

    def test_cleanup_expired(self, storage):
        storage._counts["key1"]["minute"] = (5, time.time() - 120)
        storage.cleanup_expired()
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0


class TestSQLiteStorage:
    """Test SQLiteStorage class."""

    @pytest.fixture
    def storage(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        storage = SQLiteStorage(db_path)
        yield storage
        os.unlink(db_path)

    def test_get_counts_initial(self, storage):
        counts = storage.get_counts("key1")
        assert counts["minute"] == 0
        assert counts["hour"] == 0
        assert counts["day"] == 0

    def test_increment(self, storage):
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

    def test_cleanup_expired(self, storage):
        storage.increment("key1", "minute")
        storage._storage__db_path  # Force using private attribute
        time.sleep(0.1)
        storage.cleanup_expired()


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=50)
        return RateLimiter(config=config)

    def test_check_rate_limit_allowed(self, limiter):
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True
        assert result.remaining_minute == 4

    def test_check_rate_limit_multiple(self, limiter):
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 60

    def test_check_rate_limit_hour_exceeded(self):
        config = RateLimitConfig(
            requests_per_minute=1000, requests_per_hour=5, requests_per_day=100
        )
        limiter = RateLimiter(config=config)
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 3600

    def test_check_rate_limit_day_exceeded(self):
        config = RateLimitConfig(
            requests_per_minute=1000, requests_per_hour=1000, requests_per_day=5
        )
        limiter = RateLimiter(config=config)
        for _ in range(5):
            limiter.check_rate_limit("user1")
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.retry_after == 86400

    def test_different_keys_independent(self, limiter):
        result1 = limiter.check_rate_limit("user1")
        result2 = limiter.check_rate_limit("user2")
        assert result1.remaining_minute == result2.remaining_minute == 4

    def test_reset(self, limiter):
        limiter.check_rate_limit("user1")
        limiter.reset("user1")
        result = limiter.check_rate_limit("user1")
        assert result.remaining_minute == 4

    def test_get_status(self, limiter):
        limiter.check_rate_limit("user1")
        status = limiter.get_status("user1")
        assert status["minute"]["used"] == 1
        assert status["minute"]["limit"] == 5
        assert status["hour"]["used"] == 1
        assert status["hour"]["limit"] == 20

    def test_auto_cleanup(self):
        config = RateLimitConfig(requests_per_minute=60)
        storage = MemoryStorage()
        limiter = RateLimiter(config=config, storage=storage)
        limiter._last_cleanup = time.time() - 4000
        limiter.check_rate_limit("user1")
        assert limiter._last_cleanup > time.time() - 10


class TestCreateRateLimiter:
    """Test create_rate_limiter function."""

    def test_create_memory_limiter(self):
        limiter = create_rate_limiter(use_sqlite=False)
        assert isinstance(limiter, RateLimiter)
        result = limiter.check_rate_limit("test")
        assert result.allowed is True

    def test_create_sqlite_limiter(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        os.unlink(db_path)
        limiter = create_rate_limiter(use_sqlite=True)
        assert isinstance(limiter, RateLimiter)
        result = limiter.check_rate_limit("test")
        assert result.allowed is True

    def test_create_with_config(self):
        config = RateLimitConfig(requests_per_minute=10)
        limiter = create_rate_limiter(config=config)
        assert limiter.config.requests_per_minute == 10
