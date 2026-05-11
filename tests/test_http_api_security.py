"""Tests for http_api.py security features — no mocks, real objects only."""

import time

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from apex.http_api import (
    HTTPServer,
    AuthMiddleware,
    RateLimitConfig,
    RateLimitResult,
)
from apex.api_key import (
    KeyManager,
    InvalidKeyError,
    KeyExpiredError,
    KeyDisabledError,
)
from apex.rate_limiter import (
    create_rate_limiter,
    RateLimitConfig as RLConfig,
    RateLimiter,
    MemoryStorage,
    SQLiteStorage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def key_db(tmp_path):
    """Create an in-memory KeyManager with a workspace and a valid key."""
    db_path = str(tmp_path / "test_api_keys.db")
    km = KeyManager(db_path=db_path)
    ws = km.create_workspace("test-ws", "test-owner")
    raw_key, key_info = km.create_key(
        workspace_id=ws.workspace_id,
        name="test-key",
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000,
    )
    return km, raw_key, key_info, ws


@pytest.fixture
def key_db_expired(tmp_path):
    """Create a KeyManager with an expired key."""
    db_path = str(tmp_path / "expired_keys.db")
    km = KeyManager(db_path=db_path)
    ws = km.create_workspace("exp-ws", "exp-owner")
    raw_key, key_info = km.create_key(
        workspace_id=ws.workspace_id,
        name="expired-key",
        expires_in=-1,  # Already expired
    )
    return km, raw_key, key_info, ws


@pytest.fixture
def key_db_disabled(tmp_path):
    """Create a KeyManager with a disabled key."""
    db_path = str(tmp_path / "disabled_keys.db")
    km = KeyManager(db_path=db_path)
    ws = km.create_workspace("dis-ws", "dis-owner")
    raw_key, key_info = km.create_key(
        workspace_id=ws.workspace_id,
        name="disabled-key",
    )
    # Revoke the key to disable it
    km.revoke_key(key_info.key_id)
    return km, raw_key, key_info, ws


# ---------------------------------------------------------------------------
# AuthMiddleware tests
# ---------------------------------------------------------------------------


class TestAuthMiddlewareNoAuth:
    """Test AuthMiddleware with require_auth=False."""

    @pytest.mark.asyncio
    async def test_auth_disabled_returns_true(self):
        mw = AuthMiddleware(require_auth=False)

        # Use a real aiohttp test server to produce a proper request
        async def handler(request):
            success, api_key, key_info = await mw.authenticate(request)
            return web.json_response({"success": success, "api_key": api_key})

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test")
            data = await resp.json()
            assert data["success"] is True
            assert data["api_key"] is None


class TestAuthMiddlewareBearerToken:
    """Test AuthMiddleware with Bearer token auth."""

    @pytest.mark.asyncio
    async def test_bearer_token_valid(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response(
                {
                    "success": success,
                    "key_id": info.key_id if info else None,
                }
            )

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {raw_key}"})
            data = await resp.json()
            assert data["success"] is True
            assert data["key_id"] == key_info.key_id

    @pytest.mark.asyncio
    async def test_bearer_token_invalid(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response({"success": success})

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test", headers={"Authorization": "Bearer apex_invalid_key"})
            data = await resp.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_expired_key_fails(self, key_db_expired):
        km, raw_key, key_info, ws = key_db_expired
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response({"success": success})

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {raw_key}"})
            data = await resp.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_disabled_key_fails(self, key_db_disabled):
        km, raw_key, key_info, ws = key_db_disabled
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response({"success": success})

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {raw_key}"})
            data = await resp.json()
            assert data["success"] is False


class TestAuthMiddlewareXAPIKeyHeader:
    """Test AuthMiddleware with X-API-Key header."""

    @pytest.mark.asyncio
    async def test_x_api_key_valid(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response(
                {
                    "success": success,
                    "key_id": info.key_id if info else None,
                }
            )

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test", headers={"X-API-Key": raw_key})
            data = await resp.json()
            assert data["success"] is True
            assert data["key_id"] == key_info.key_id


class TestAuthMiddlewareQueryParam:
    """Test AuthMiddleware with api_key query parameter."""

    @pytest.mark.asyncio
    async def test_query_param_valid(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response(
                {
                    "success": success,
                    "key_id": info.key_id if info else None,
                }
            )

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get(f"/test?api_key={raw_key}")
            data = await resp.json()
            assert data["success"] is True
            assert data["key_id"] == key_info.key_id


class TestAuthMiddlewareNoKey:
    """Test AuthMiddleware when no key is provided."""

    @pytest.mark.asyncio
    async def test_no_key_returns_false(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response(
                {
                    "success": success,
                    "api_key": api_key,
                    "key_info": info is not None,
                }
            )

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/test")
            data = await resp.json()
            assert data["success"] is False
            assert data["api_key"] is None
            assert data["key_info"] is False


class TestAuthMiddlewareBearerTakesPrecedence:
    """Bearer token should take precedence over X-API-Key and query param."""

    @pytest.mark.asyncio
    async def test_bearer_over_x_api_key(self, key_db):
        km, raw_key, key_info, ws = key_db
        mw = AuthMiddleware(require_auth=True)
        mw.key_manager = km

        async def handler(request):
            success, api_key, info = await mw.authenticate(request)
            return web.json_response(
                {
                    "success": success,
                    "api_key": api_key,
                }
            )

        app = web.Application()
        app.router.add_get("/test", handler)
        async with TestClient(TestServer(app)) as client:
            # Both headers present — Bearer should be used
            resp = await client.get(
                "/test",
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "X-API-Key": "apex_bad_key",
                },
            )
            data = await resp.json()
            assert data["success"] is True


# ---------------------------------------------------------------------------
# RateLimitConfig tests
# ---------------------------------------------------------------------------


class TestRateLimitConfigValues:
    """Test RateLimitConfig dataclass."""

    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.requests_per_minute == 60
        assert cfg.requests_per_hour == 1000
        assert cfg.requests_per_day == 10000
        assert cfg.burst_size == 10

    def test_custom_values(self):
        cfg = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=2000,
            requests_per_day=50000,
            burst_size=20,
        )
        assert cfg.requests_per_minute == 100
        assert cfg.requests_per_hour == 2000
        assert cfg.requests_per_day == 50000
        assert cfg.burst_size == 20


# ---------------------------------------------------------------------------
# Rate limiter integration with HTTPServer
# ---------------------------------------------------------------------------


class TestRateLimitIntegration:
    """Test rate limiting integrated into HTTPServer handlers."""

    @pytest.mark.asyncio
    async def test_rate_limit_429_response(self):
        cfg = RateLimitConfig(requests_per_minute=1, requests_per_hour=1, requests_per_day=1)
        server = HTTPServer(require_auth=False, rate_limit_config=cfg)
        # Exhaust the rate limiter
        server.rate_limiter.check_rate_limit("anonymous")
        server.rate_limiter.check_rate_limit("anonymous")

        async with TestClient(TestServer(server.app)) as client:
            resp = await client.post("/chat", json={"message": "hello"})
            assert resp.status == 429
            data = await resp.json()
            assert "RATE_LIMITED" in data["code"]
            assert "retry_after" in data
            assert "remaining" in data

    @pytest.mark.asyncio
    async def test_rate_limit_status_endpoint(self):
        server = HTTPServer(require_auth=False)
        async with TestClient(TestServer(server.app)) as client:
            resp = await client.get("/rate-limit/status")
            assert resp.status == 200
            data = await resp.json()
            assert "minute" in data
            assert "hour" in data
            assert "day" in data
            assert "used" in data["minute"]
            assert "limit" in data["minute"]


class TestRateLimitResultDataclass:
    """Test RateLimitResult dataclass."""

    def test_allowed_result(self):
        result = RateLimitResult(
            allowed=True,
            remaining_minute=59,
            remaining_hour=999,
            remaining_day=9999,
            reset_at=time.time() + 60,
        )
        assert result.allowed is True
        assert result.remaining_minute == 59
        assert result.retry_after is None

    def test_denied_result(self):
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


# ---------------------------------------------------------------------------
# Rate limiter backends
# ---------------------------------------------------------------------------


class TestMemoryStorage:
    """Test the MemoryStorage backend directly."""

    def test_initial_counts_are_zero(self):
        ms = MemoryStorage()
        counts = ms.get_counts("test_key")
        assert counts == {"minute": 0, "hour": 0, "day": 0}

    def test_increment(self):
        ms = MemoryStorage()
        ms.increment("k", "minute")
        ms.increment("k", "minute")
        counts = ms.get_counts("k")
        assert counts["minute"] == 2

    def test_cleanup(self):
        ms = MemoryStorage()
        ms.increment("k", "minute")
        ms.cleanup_expired()
        # Should not raise


class TestSQLiteStorage:
    """Test the SQLiteStorage backend directly."""

    def test_sqlite_storage_init(self, tmp_path):
        db_path = str(tmp_path / "rl.db")
        ss = SQLiteStorage(db_path=db_path)
        assert ss.db_path.exists()

    def test_sqlite_increment_and_get(self, tmp_path):
        db_path = str(tmp_path / "rl2.db")
        ss = SQLiteStorage(db_path=db_path)
        ss.increment("k1", "minute")
        ss.increment("k1", "minute")
        counts = ss.get_counts("k1")
        assert counts["minute"] == 2

    def test_sqlite_cleanup(self, tmp_path):
        db_path = str(tmp_path / "rl3.db")
        ss = SQLiteStorage(db_path=db_path)
        ss.increment("k1", "minute")
        ss.cleanup_expired()
        # Should not raise


class TestCreateRateLimiter:
    """Test the create_rate_limiter factory function."""

    def test_memory_limiter(self):
        rl = create_rate_limiter(use_sqlite=False)
        assert isinstance(rl, RateLimiter)
        assert isinstance(rl.storage, MemoryStorage)

    def test_sqlite_limiter(self, tmp_path):
        rl = create_rate_limiter(use_sqlite=True)
        assert isinstance(rl, RateLimiter)
        assert isinstance(rl.storage, SQLiteStorage)

    def test_custom_config(self):
        cfg = RLConfig(requests_per_minute=10)
        rl = create_rate_limiter(config=cfg, use_sqlite=False)
        assert rl.config.requests_per_minute == 10


# ---------------------------------------------------------------------------
# KeyManager direct security tests
# ---------------------------------------------------------------------------


class TestKeyManagerSecurity:
    """Test KeyManager security edge cases."""

    def test_validate_invalid_format(self, tmp_path):
        km = KeyManager(db_path=str(tmp_path / "sec.db"))
        with pytest.raises(InvalidKeyError):
            km.validate_key("not_apex_key")

    def test_validate_empty_key(self, tmp_path):
        km = KeyManager(db_path=str(tmp_path / "sec2.db"))
        with pytest.raises(InvalidKeyError):
            km.validate_key("")

    def test_validate_nonexistent_key(self, tmp_path):
        km = KeyManager(db_path=str(tmp_path / "sec3.db"))
        with pytest.raises(InvalidKeyError):
            km.validate_key("apex_nonexistent_key_1234567890")

    def test_validate_expired_key(self, key_db_expired):
        km, raw_key, key_info, ws = key_db_expired
        with pytest.raises(KeyExpiredError):
            km.validate_key(raw_key)

    def test_validate_disabled_key(self, key_db_disabled):
        km, raw_key, key_info, ws = key_db_disabled
        with pytest.raises(KeyDisabledError):
            km.validate_key(raw_key)

    def test_revoke_key(self, key_db):
        km, raw_key, key_info, ws = key_db
        result = km.revoke_key(key_info.key_id)
        assert result is True
        with pytest.raises(KeyDisabledError):
            km.validate_key(raw_key)

    def test_revoke_nonexistent(self, tmp_path):
        km = KeyManager(db_path=str(tmp_path / "sec4.db"))
        result = km.revoke_key("nonexistent")
        assert result is False

    def test_delete_key(self, key_db):
        km, raw_key, key_info, ws = key_db
        result = km.delete_key(key_info.key_id)
        assert result is True
        with pytest.raises(InvalidKeyError):
            km.validate_key(raw_key)

    def test_list_keys(self, key_db):
        km, raw_key, key_info, ws = key_db
        keys = km.list_keys(ws.workspace_id)
        assert len(keys) >= 1

    def test_get_workspace(self, key_db):
        km, raw_key, key_info, ws = key_db
        fetched = km.get_workspace(ws.workspace_id)
        assert fetched is not None
        assert fetched.name == "test-ws"

    def test_get_nonexistent_workspace(self, tmp_path):
        km = KeyManager(db_path=str(tmp_path / "sec5.db"))
        assert km.get_workspace("nonexistent") is None
