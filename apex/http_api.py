"""HTTP/SSE API server for APEX - headless agent workflows with security."""

import json
import logging
import time
from typing import Optional

from aiohttp import web

from .agent import Agent
from .rate_limiter import (
    RateLimiter,
    create_rate_limiter,
    RateLimitConfig,
    RateLimitResult,
)
from .api_key import (
    key_manager,
    create_key_manager,
    InvalidKeyError,
    KeyExpiredError,
    KeyDisabledError,
)
from .billing import (
    billing_manager,
    calculate_cost,
    InsufficientBalanceError,
    TrialExpiredError,
    QuotaExceededError,
)

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for HTTP API."""

    def __init__(self, require_auth: bool = True):
        self.require_auth = require_auth
        self.key_manager = key_manager

    async def authenticate(self, request: web.Request) -> tuple[bool, Optional[str], Optional[dict]]:
        """Authenticate request and return (success, api_key, key_info)."""
        if not self.require_auth:
            return True, None, None

        auth_header = request.headers.get("Authorization", "")
        api_key = None

        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        else:
            api_key = request.query.get("api_key") or request.headers.get("X-API-Key")

        if not api_key:
            return False, None, None

        try:
            key_info = self.key_manager.validate_key(api_key)
            return True, api_key, key_info
        except (InvalidKeyError, KeyExpiredError, KeyDisabledError) as e:
            logger.warning(f"Authentication failed: {e}")
            return False, api_key, None


class HTTPServer:
    """HTTP server with integrated security features."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        require_auth: bool = True,
        rate_limit_config: Optional[RateLimitConfig] = None,
        use_sqlite_storage: bool = False,
    ):
        self.host = host
        self.port = port
        self.require_auth = require_auth
        self.app = web.Application()
        self.auth_middleware = AuthMiddleware(require_auth=require_auth)
        self.rate_limiter = create_rate_limiter(
            config=rate_limit_config or RateLimitConfig(),
            use_sqlite=use_sqlite_storage,
        )
        self._setup_routes()
        self.agent = Agent()
        self.runner = None

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/health", self.health)
        self.app.router.add_post("/chat", self.chat)
        self.app.router.add_get("/stream", self.stream)
        self.app.router.add_post("/chat/stream", self.chat_stream)
        self.app.router.add_get("/models", self.list_models)
        self.app.router.add_post("/session/save", self.session_save)
        self.app.router.add_post("/session/load", self.session_load)
        self.app.router.add_get("/metrics", self.metrics)
        self.app.router.add_get("/rate-limit/status", self.rate_limit_status)

    async def _check_auth(self, request: web.Request) -> tuple[Optional[web.Response], Optional[dict]]:
        """Check authentication, returns error response if failed."""
        success, api_key, key_info = await self.auth_middleware.authenticate(request)
        if self.require_auth and not success:
            return web.json_response(
                {"error": "Authentication required", "code": "AUTH_REQUIRED"},
                status=401,
            ), None
        return None, key_info

    async def _check_rate_limit(self, key_info: Optional[dict]) -> tuple[Optional[web.Response], Optional[RateLimitResult]]:
        """Check rate limit, returns error response if exceeded."""
        key = f"key:{key_info['key_id']}" if key_info else "anonymous"
        result = self.rate_limiter.check_rate_limit(key)
        if not result.allowed:
            return web.json_response(
                {
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMITED",
                    "retry_after": result.retry_after,
                    "remaining": {
                        "minute": result.remaining_minute,
                        "hour": result.remaining_hour,
                        "day": result.remaining_day,
                    },
                },
                status=429,
                headers={"Retry-After": str(result.retry_after or 60)},
            ), result
        return None, result

    async def index(self, request: web.Request) -> web.Response:
        """Serve API documentation."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>APEX API</title></head>
        <body>
        <h1>APEX Agent API</h1>
        <h2>Authentication</h2>
        <p>Use <code>Authorization: Bearer YOUR_API_KEY</code> header or <code>?api_key=YOUR_API_KEY</code> query parameter.</p>
        <h2>Endpoints</h2>
        <ul>
            <li>POST /chat - Send a chat message</li>
            <li>GET /stream - SSE stream endpoint</li>
            <li>POST /chat/stream - Chat with streaming</li>
            <li>GET /models - List available models</li>
            <li>POST /session/save - Save session</li>
            <li>POST /session/load - Load session</li>
            <li>GET /metrics - Get usage metrics</li>
            <li>GET /health - Health check</li>
            <li>GET /rate-limit/status - Rate limit status</li>
        </ul>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    async def health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "ok",
            "agent": self.agent.model,
            "timestamp": time.time(),
        })

    async def chat(self, request: web.Request) -> web.Response:
        """Standard chat endpoint."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        rate_error, result = await self._check_rate_limit(key_info)
        if rate_error:
            return rate_error

        try:
            data = await request.json()
            message = data.get("message", "")
            model = data.get("model")

            if model:
                self.agent.switch_model(model)

            response = self.agent.chat(message)

            if key_info:
                usage = self.agent.usage or {}
                billing_manager.record_usage(
                    user_id=key_info["workspace_id"],
                    model=self.agent.model,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    workspace_id=key_info["workspace_id"],
                )

            return web.json_response({
                "response": response,
                "model": self.agent.model,
                "usage": self.agent.usage,
                "rate_limit": {
                    "remaining_minute": result.remaining_minute,
                    "remaining_hour": result.remaining_hour,
                    "remaining_day": result.remaining_day,
                } if result else None,
            })
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def stream(self, request: web.Request) -> web.Response:
        """SSE stream endpoint."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        await response.prepare(request)

        async for chunk in self.agent.chat_streaming("ping"):
            await response.write(f"data: {json.dumps({'chunk': chunk})}\n\n".encode())

        return response

    async def chat_stream(self, request: web.Request) -> web.Response:
        """Chat with streaming response."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        rate_error, result = await self._check_rate_limit(key_info)
        if rate_error:
            return rate_error

        try:
            data = await request.json()
            message = data.get("message", "")
            model = data.get("model")

            if model:
                self.agent.switch_model(model)

            response = web.StreamResponse()
            response.content_type = "text/event-stream"
            response.headers["Cache-Control"] = "no-cache"
            await response.prepare(request)

            async for chunk in self.agent.chat_streaming(message):
                await response.write(f"data: {json.dumps({'chunk': chunk})}\n\n".encode())

            usage = self.agent.usage or {}
            if key_info:
                billing_manager.record_usage(
                    user_id=key_info["workspace_id"],
                    model=self.agent.model,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    workspace_id=key_info["workspace_id"],
                )

            await response.write(f"data: {json.dumps({'usage': usage})}\n\n".encode())
            if result:
                await response.write(f"data: {json.dumps({'rate_limit': {{'remaining_minute': {result.remaining_minute}}}}}\n\n".encode())
            return response
        except Exception as e:
            logger.error(f"Stream error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def list_models(self, request: web.Request) -> web.Response:
        """List available models."""
        from .config import MODELS
        models = [
            {"alias": alias, "model": model_id}
            for alias, model_id in MODELS.items()
        ]
        return web.json_response({"models": models})

    async def session_save(self, request: web.Request) -> web.Response:
        """Save current session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        from .session import SessionManager
        try:
            data = await request.json()
            name = data.get("name", "http_session")
            sm = SessionManager()
            path = sm.save(self.agent, name)
            return web.json_response({"saved": str(path)})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def session_load(self, request: web.Request) -> web.Response:
        """Load a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        from .session import SessionManager
        try:
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"error": "name required"}, status=400)

            sm = SessionManager()
            session = sm.load(name)
            if session:
                self.agent.history = session.get("history", [])
                return web.json_response({"loaded": name})
            return web.json_response({"error": "session not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def metrics(self, request: web.Request) -> web.Response:
        """Get usage metrics."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        usage = self.agent.usage
        metrics = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": self.agent.model,
        }

        if key_info:
            metrics["rate_limit"] = self.rate_limiter.get_status(f"key:{key_info['key_id']}")
            metrics["usage_summary"] = billing_manager.get_usage_summary(key_info["workspace_id"])

        return web.json_response(metrics)

    async def rate_limit_status(self, request: web.Request) -> web.Response:
        """Get rate limit status."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        key = f"key:{key_info['key_id']}" if key_info else "anonymous"
        return web.json_response(self.rate_limiter.get_status(key))

    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self.runner = runner
        logger.info(f"APEX HTTP API running at http://{self.host}:{self.port}")
        print(f"APEX HTTP API running at http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
        if self.runner:
            await self.runner.cleanup()


class APEXHTTPServer(HTTPServer):
    """Backward compatibility wrapper."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(
            host=host,
            port=port,
            require_auth=False,
            rate_limit_config=RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=500,
            ),
        )


async def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    require_auth: bool = True,
):
    """Run the APEX HTTP server."""
    server = HTTPServer(host=host, port=port, require_auth=require_auth)
    await server.start()
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    asyncio.run(run_server(port=port))