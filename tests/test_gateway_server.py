"""Tests for apex/gateway/server.py — gateway HTTP server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apex.gateway.server import GatewayServer


class TestGatewayServerInit:
    def test_init_default_config(self, monkeypatch, tmp_path):
        """GatewayServer should create default config and init sub-components."""
        fake_config = MagicMock()
        fake_config.data_dir = tmp_path
        monkeypatch.setattr("apex.gateway.server.GatewayConfig.from_env", lambda: fake_config)
        with (
            patch("apex.gateway.server.web.Application") as mock_app,
            patch("apex.gateway.server.AuthManager") as mock_auth,
            patch("apex.gateway.server.RequestRouter") as mock_router,
        ):
            mock_app.return_value = MagicMock()
            srv = GatewayServer()
            assert srv.config is fake_config
            assert srv.auth is mock_auth.return_value
            assert srv.router is mock_router.return_value
            assert srv._app is not None
            assert srv._runner is None
            mock_app.assert_called_once()
            mock_auth.assert_called_once_with(fake_config.db_path)
            mock_router.assert_called_once_with(fake_config, mock_auth.return_value)

    def test_init_with_config(self, monkeypatch, tmp_path):
        config = MagicMock()
        config.data_dir = tmp_path
        config.db_path = ":memory:"
        with (
            patch("apex.gateway.server.web.Application") as mock_app,
            patch("apex.gateway.server.RequestRouter") as mock_router,
            patch("apex.gateway.server.AuthManager") as mock_auth,
        ):
            mock_app.return_value = MagicMock()
            mock_auth.return_value = MagicMock()
            mock_router.return_value = MagicMock()
            srv = GatewayServer(config)
            assert srv.config is config
            mock_app.assert_called_once()
            mock_auth.assert_called_once_with(config.db_path)
            mock_router.assert_called_once_with(config, mock_auth.return_value)


class TestSetupRoutes:
    def test_setup_routes_registers_endpoints(self):
        config = MagicMock()
        config.data_dir = type("P", (), {"mkdir": lambda self, **kw: None})()
        config.db_path = ":memory:"
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = config
        srv.auth = MagicMock()
        srv.router = MagicMock()
        srv._app = MagicMock()
        sub_app = MagicMock()
        srv._app.router.add_sub_app.return_value = sub_app
        srv._setup_routes()
        # Check that key routes were added
        assert srv._app.router.add_post.call_count >= 2
        assert srv._app.router.add_get.call_count >= 3
        assert sub_app.add_get.call_count >= 1
        assert sub_app.add_post.call_count >= 2


class TestCheckAdmin:
    def test_check_admin_no_key_configured(self):
        config = MagicMock()
        config.admin_key = None
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = config
        request = MagicMock()
        request.headers.get.return_value = ""
        assert srv._check_admin(request) is False

    def test_check_admin_correct_key(self):
        config = MagicMock()
        config.admin_key = "secret-key"
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = config
        request = MagicMock()
        request.headers.get.return_value = "secret-key"
        assert srv._check_admin(request) is True

    def test_check_admin_wrong_key(self):
        config = MagicMock()
        config.admin_key = "secret-key"
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = config
        request = MagicMock()
        request.headers.get.return_value = "wrong-key"
        assert srv._check_admin(request) is False

    def test_check_admin_no_header(self):
        config = MagicMock()
        config.admin_key = "secret-key"
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = config
        request = MagicMock()
        request.headers.get.return_value = ""
        assert srv._check_admin(request) is False


class TestHandleChat:
    @pytest.mark.asyncio
    async def test_handle_chat_proxies(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.router = MagicMock()
        srv.router.proxy_request = AsyncMock(return_value="response")
        request = MagicMock()
        result = await srv.handle_chat(request)
        assert result == "response"
        srv.router.proxy_request.assert_called_once_with(request)


class TestHandleRegister:
    @pytest.mark.asyncio
    async def test_handle_register_disabled(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = MagicMock()
        srv.config.register_enabled = False
        request = MagicMock()
        request.content_length = None
        result = await srv.handle_register(request)
        assert result.status == 403

    @pytest.mark.asyncio
    async def test_handle_register_payload_too_large(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = MagicMock()
        srv.config.register_enabled = True
        request = MagicMock()
        request.content_length = 5000
        result = await srv.handle_register(request)
        assert result.status == 413

    @pytest.mark.asyncio
    async def test_handle_register_invalid_json(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.config = MagicMock()
        srv.config.register_enabled = True
        srv.config.tiers = {"free": MagicMock()}
        srv.auth = MagicMock()
        srv.auth.generate_key.return_value = "sk-test-key"
        request = MagicMock()
        request.content_length = 100
        request.json = AsyncMock(side_effect=ValueError("bad json"))
        result = await srv.handle_register(request)
        assert result.status == 400


class TestHandleStatus:
    @pytest.mark.asyncio
    async def test_handle_status_no_auth(self):
        srv = GatewayServer.__new__(GatewayServer)
        request = MagicMock()
        request.headers.get.return_value = ""
        result = await srv.handle_status(request)
        assert result.status == 401

    @pytest.mark.asyncio
    async def test_handle_status_invalid_key(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.auth = MagicMock()
        srv.auth.validate_key.return_value = None
        request = MagicMock()
        request.headers.get.return_value = "Bearer bad-key"
        result = await srv.handle_status(request)
        assert result.status == 401

    @pytest.mark.asyncio
    async def test_handle_status_valid(self):
        srv = GatewayServer.__new__(GatewayServer)
        srv.auth = MagicMock()
        key_info = MagicMock()
        srv.auth.validate_key.return_value = key_info
        srv.router = MagicMock()
        srv.router.status = AsyncMock(return_value={"ok": True})
        request = MagicMock()
        request.headers.get.return_value = "Bearer good-key"
        result = await srv.handle_status(request)
        assert result.status == 200


class TestHandleHealth:
    @pytest.mark.asyncio
    async def test_handle_health(self):
        srv = GatewayServer.__new__(GatewayServer)
        request = MagicMock()
        result = await srv.handle_health(request)
        assert result.status == 200


class TestHandleModels:
    @pytest.mark.asyncio
    async def test_handle_models(self):
        srv = GatewayServer.__new__(GatewayServer)
        import apex.config

        original = apex.config.MODELS
        apex.config.MODELS = {
            "free-model": "provider/free-model",
            "pro-model": "provider/pro-model",
            "paid-model": "provider/paid-model",
        }
        try:
            request = MagicMock()
            result = await srv.handle_models(request)
            assert result.status == 200
        finally:
            apex.config.MODELS = original


def make_admin_server(header_value: str):
    """A GatewayServer stub with an admin key configured."""
    srv = GatewayServer.__new__(GatewayServer)
    srv.config = MagicMock()
    srv.config.admin_key = "secret"
    srv.auth = MagicMock()
    request = MagicMock()
    request.headers.get.return_value = header_value
    return srv, request


class TestAdminRoutes:
    @pytest.mark.asyncio
    async def test_list_keys_unauthorized(self):
        srv, request = make_admin_server("wrong")
        result = await srv.admin_list_keys(request)
        assert result.status == 401

    @pytest.mark.asyncio
    async def test_list_keys_authorized(self):
        srv, request = make_admin_server("secret")
        srv.auth.list_keys.return_value = [{"key_id": "k1", "tier": "free"}]
        result = await srv.admin_list_keys(request)
        assert result.status == 200

    @pytest.mark.asyncio
    async def test_generate_key_unauthorized(self):
        srv, request = make_admin_server("wrong")
        result = await srv.admin_generate_key(request)
        assert result.status == 401

    @pytest.mark.asyncio
    async def test_generate_key_authorized(self):
        srv, request = make_admin_server("secret")
        srv.auth.generate_key.return_value = "sk-new-key"
        request.json = AsyncMock(return_value={})
        result = await srv.admin_generate_key(request)
        assert result.status == 200

    @pytest.mark.asyncio
    async def test_revoke_key_unauthorized(self):
        srv, request = make_admin_server("wrong")
        result = await srv.admin_revoke_key(request)
        assert result.status == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("revoked", "status"), [(True, 200), (False, 404)])
    async def test_revoke_key(self, revoked, status):
        srv, request = make_admin_server("secret")
        srv.auth.revoke_key.return_value = revoked
        request.json = AsyncMock(return_value={"api_key": "sk-old"})
        result = await srv.admin_revoke_key(request)
        assert result.status == status


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start(self):
        srv = GatewayServer.__new__(GatewayServer)
        runner = MagicMock()
        runner.setup = AsyncMock()
        srv._runner = runner
        srv._app = MagicMock()
        srv.config = MagicMock()
        srv.config.host = "127.0.0.1"
        srv.config.port = 8080
        site = MagicMock()
        site.start = AsyncMock()
        with (
            patch("apex.gateway.server.web.TCPSite", return_value=site),
            patch("apex.gateway.server.web.AppRunner", return_value=runner),
        ):
            await srv.start()
        assert srv._runner is runner

    @pytest.mark.asyncio
    async def test_stop(self):
        srv = GatewayServer.__new__(GatewayServer)
        runner = MagicMock()
        runner.cleanup = AsyncMock()
        srv._runner = runner
        srv.router = MagicMock()
        srv.router.close = AsyncMock()
        await srv.stop()
        srv.router.close.assert_called_once()
        runner.cleanup.assert_called_once()
