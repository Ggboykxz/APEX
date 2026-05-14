"""Gateway HTTP server — handles auth, proxy, and admin endpoints."""

import json
import logging

from aiohttp import web

from .auth import AuthManager
from .config import GatewayConfig
from .router import RequestRouter

logger = logging.getLogger(__name__)


class GatewayServer:
    def __init__(self, config: GatewayConfig | None = None):
        self.config = config or GatewayConfig.from_env()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.auth = AuthManager(self.config.db_path)
        self.router = RequestRouter(self.config, self.auth)
        self._app = web.Application()
        self._setup_routes()
        self._runner: web.AppRunner | None = None

    def _setup_routes(self):
        self._app.router.add_post("/v1/chat/completions", self.handle_chat)
        self._app.router.add_post("/v1/register", self.handle_register)
        self._app.router.add_get("/v1/status", self.handle_status)
        self._app.router.add_get("/v1/health", self.handle_health)
        self._app.router.add_get("/v1/models", self.handle_models)

        admin = self._app.router.add_sub_app("/admin")
        admin.add_get("/keys", self.admin_list_keys)
        admin.add_post("/keys/generate", self.admin_generate_key)
        admin.add_post("/keys/revoke", self.admin_revoke_key)

    def _check_admin(self, request: web.Request) -> bool:
        key = request.headers.get("X-Admin-Key", "")
        return key == self.config.admin_key if self.config.admin_key else False

    async def handle_chat(self, request: web.Request) -> web.StreamResponse:
        return await self.router.proxy_request(request)

    async def handle_register(self, request: web.Request) -> web.Response:
        if not self.config.register_enabled:
            return web.json_response({"error": "Registration disabled"}, status=403)
        if request.content_length and request.content_length > 4096:
            return web.json_response({"error": "Payload too large"}, status=413)
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        except Exception:
            data = {}
        tier = data.get("tier", self.config.default_tier)
        label = data.get("label", "")
        if tier not in self.config.tiers:
            return web.json_response({"error": f"Invalid tier: {tier}"}, status=400)
        api_key = self.auth.generate_key(tier, label)
        t = self.config.tiers[tier]
        return web.json_response({
            "api_key": api_key,
            "tier": tier,
            "label": label,
            "limits": {
                "daily_requests": t.daily_requests,
                "daily_tokens": t.daily_tokens,
                "rate_per_minute": t.rate_per_minute,
                "monthly_value_usd": t.monthly_value_usd,
                "max_concurrent": t.max_concurrent,
            },
        })

    async def handle_status(self, request: web.Request) -> web.Response:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return web.json_response({"error": "Unauthorized"}, status=401)
        key_info = self.auth.validate_key(auth[7:])
        if not key_info:
            return web.json_response({"error": "Invalid key"}, status=401)
        status = await self.router.status(key_info)
        return web.json_response(status)

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "apex-gateway"})

    async def handle_models(self, request: web.Request) -> web.Response:
        from ..config import MODELS
        free_models = {k: v for k, v in MODELS.items() if k.startswith("free-") or k.startswith("pro-")}
        return web.json_response({"models": [
            {"id": k, "provider": v.split("/")[0]}
            for k, v in sorted(free_models.items())
        ]})

    async def admin_list_keys(self, request: web.Request) -> web.Response:
        if not self._check_admin(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        keys = self.auth.list_keys()
        return web.json_response({"keys": keys})

    async def admin_generate_key(self, request: web.Request) -> web.Response:
        if not self._check_admin(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        data = await request.json()
        tier = data.get("tier", "free")
        label = data.get("label", "")
        api_key = self.auth.generate_key(tier, label)
        return web.json_response({"api_key": api_key, "tier": tier, "label": label})

    async def admin_revoke_key(self, request: web.Request) -> web.Response:
        if not self._check_admin(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        data = await request.json()
        api_key = data.get("api_key", "")
        if self.auth.revoke_key(api_key):
            return web.json_response({"status": "revoked"})
        return web.json_response({"error": "Key not found"}, status=404)

    async def start(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.config.host, self.config.port)
        await site.start()
        logger.info(f"Gateway started on http://{self.config.host}:{self.config.port}")
        print(f"APEX Gateway running on http://{self.config.host}:{self.config.port}")
        print("Register: POST /v1/register")
        print("Chat:     POST /v1/chat/completions")

    async def stop(self):
        await self.router.close()
        if self._runner:
            await self._runner.cleanup()
