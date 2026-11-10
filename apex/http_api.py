"""HTTP/SSE API server for APEX - headless agent workflows with security.

The route families live in the sibling ``apex.http_routes_*`` modules; this
module holds the server core, the middleware and the entry points.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web

from .agent import Agent
from .api_key import InvalidKeyError, KeyDisabledError, KeyExpiredError, key_manager
from .rate_limiter import RateLimitConfig, RateLimitResult, create_rate_limiter
from .session import SessionManager, UndoManager

logger = logging.getLogger(__name__)


@dataclass
class RateLimiterOptions:
    """How the server's rate limiter counts its requests."""

    config: RateLimitConfig | None = None
    use_sqlite: bool = False


from .billing import billing_manager
from .formatter import formatter_manager
from .http_helpers import (
    _check_provider_configured,
    _get_configured_providers,
    _sanitize_config,
    _sanitize_string,
)
from .http_routes_auth import AuthRoutesMixin
from .http_routes_catalog import CatalogRoutesMixin
from .http_routes_chat import ChatRoutesMixin
from .http_routes_config import ConfigRoutesMixin
from .http_routes_sessions import SessionRoutesMixin
from .http_routes_system import SystemRoutesMixin
from .project import ProjectInitializer
from .share import SENSITIVE_PATTERNS, share_manager

__all__ = [
    "SENSITIVE_PATTERNS",
    "APEXHTTPServer",
    "AuthMiddleware",
    "EventBus",
    "HTTPServer",
    "Path",
    "ProjectInitializer",
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimiterOptions",
    "_check_provider_configured",
    "_get_configured_providers",
    "_sanitize_config",
    "_sanitize_string",
    "billing_manager",
    "formatter_manager",
    "run_server",
    "share_manager",
    "start_tui_server",
    "stop_tui_server",
]


class HTTPServer(
    ChatRoutesMixin,
    SessionRoutesMixin,
    CatalogRoutesMixin,
    ConfigRoutesMixin,
    AuthRoutesMixin,
    SystemRoutesMixin,
):
    """HTTP server with integrated security features."""

    _VALID_PROVIDERS = {  # noqa: RUF012
        "ANTHROPIC",
        "OPENAI",
        "GEMINI",
        "DEEPSEEK",
        "MISTRAL",
        "COHERE",
        "GROQ",
        "XAI",
        "TOGETHER",
        "FIREWORKS",
        "CEREBRAS",
        "PERPLEXITY",
        "HF",
        "GITHUB",
        "NVIDIA",
        "CLOUDFLARE",
        "DASHSCOPE",
        "LLAMA",
        "OPENROUTER",
        "HUGGINGFACE",
        "BEDROCK",
        "AZURE",
    }

    _sse_clients: list = []  # noqa: RUF012

    _DIFF_GIT_TIMEOUT = 30

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        require_auth: bool = True,
        rate_limiter: RateLimiterOptions | None = None,
    ):
        self.host = host
        self.port = port
        self.require_auth = require_auth
        self.app = web.Application()
        self.auth_middleware = AuthMiddleware(require_auth=require_auth)
        options = rate_limiter or RateLimiterOptions()
        self.rate_limiter = create_rate_limiter(
            config=options.config or RateLimitConfig(),
            use_sqlite=options.use_sqlite,
        )
        self._setup_routes()
        self.agent = Agent()
        self.runner = None
        self.session_manager = SessionManager()
        self.undo_manager = UndoManager()
        self.event_bus = EventBus()

    def _setup_routes(self):
        """Setup HTTP routes."""
        # Add CORS middleware for local TUI/web development
        self.app.middlewares.append(self._cors_middleware)

        # Existing routes
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

        # API v1 routes
        self.app.router.add_get("/api/v1/config", self.api_config_get)
        self.app.router.add_post("/api/v1/config", self.api_config_set)
        self.app.router.add_get("/api/v1/agents", self.api_agents_list)
        self.app.router.add_get("/api/v1/agents/{name}", self.api_agents_get)
        self.app.router.add_get("/api/v1/sessions", self.api_sessions_list)
        self.app.router.add_delete("/api/v1/sessions/{id}", self.api_sessions_delete)
        self.app.router.add_post("/api/v1/share", self.api_share)
        self.app.router.add_post("/api/v1/unshare/{share_id}", self.api_unshare)
        self.app.router.add_get("/api/v1/shares", self.api_shares_list)
        self.app.router.add_get("/api/v1/themes", self.api_themes_list)
        self.app.router.add_post("/api/v1/themes", self.api_themes_set)
        self.app.router.add_get("/api/v1/stats", self.api_stats)
        self.app.router.add_get("/api/v1/formatters", self.api_formatters_list)
        self.app.router.add_post("/api/v1/format", self.api_format)
        self.app.router.add_post("/api/v1/compact", self.api_compact)
        self.app.router.add_post("/api/v1/models/refresh", self.api_models_refresh)
        self.app.router.add_get("/api/v1/providers", self.api_providers_list)
        self.app.router.add_post("/api/v1/auth/login", self.api_auth_login)
        self.app.router.add_post("/api/v1/auth/logout", self.api_auth_logout)
        self.app.router.add_get("/api/v1/auth/status", self.api_auth_status)
        self.app.router.add_post("/api/v1/commands/execute", self.api_commands_execute)
        self.app.router.add_get("/api/v1/commands", self.api_commands_list)
        self.app.router.add_post("/api/v1/undo", self.api_undo)
        self.app.router.add_post("/api/v1/redo", self.api_redo)
        self.app.router.add_get("/api/v1/files", self.api_files_list)
        self.app.router.add_get("/find/file", self.api_find_file)
        self.app.router.add_post("/api/v1/bash", self.api_bash)
        self.app.router.add_post("/api/v1/command", self.api_command)
        self.app.router.add_get("/api/v1/tui-config", self.api_tui_config)
        self.app.router.add_get("/global/health", self.api_global_health)
        self.app.router.add_post("/api/v1/init", self.api_init)
        self.app.router.add_get("/api/v1/export/{session_id}", self.api_export)
        self.app.router.add_post("/api/v1/import", self.api_import)
        self.app.router.add_get("/global/event", self.api_global_event)
        self.app.router.add_get("/api/v1/session/{session_id}/diff", self.api_session_diff)
        self.app.router.add_post(
            "/api/v1/session/{session_id}/diff/decision", self.api_session_diff_decision
        )
        self.app.router.add_post("/api/v1/session/{session_id}/fork", self.api_session_fork)
        self.app.router.add_post("/api/v1/session/{session_id}/abort", self.api_session_abort)
        self.app.router.add_get("/api/v1/lsp", self.api_lsp_status)
        self.app.router.add_get("/api/v1/formatter", self.api_formatter_status)
        self.app.router.add_get("/api/v1/mcp", self.api_mcp_status)
        self.app.router.add_get("/ws/events", self.ws_events)

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        """CORS middleware — allows all origins for localhost-only server."""
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        return response

    async def _check_rate_limit(
        self, key_info: dict | None
    ) -> tuple[web.Response | None, RateLimitResult | None]:
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


class AuthMiddleware:
    """Authentication middleware for HTTP API."""

    def __init__(self, require_auth: bool = True):
        self.require_auth = require_auth
        self.key_manager = key_manager

    async def authenticate(self, request: web.Request) -> tuple[bool, str | None, dict | None]:
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


class EventBus:
    """Real-time event bus for TUI synchronization (OpenCode-like)."""

    def __init__(self):
        self._subscribers: list = []
        self._history: list[dict] = []

    async def publish(self, event_type: str, data: dict | None = None) -> None:
        """Publish an event to all subscribers."""
        payload = {"event": event_type, "data": data or {}, "timestamp": time.time()}
        self._history.append(payload)
        if len(self._history) > 1000:
            self._history = self._history[-500:]
        dead = await self._send_to_subscribers(payload)
        self._drop_subscribers(dead)

    async def _send_to_subscribers(self, payload: dict) -> list:
        """Send the payload to every subscriber; returns the dead ones."""
        dead = []
        for ws in self._subscribers:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        return dead

    def _drop_subscribers(self, dead: list) -> None:
        """Unsubscribe the subscribers that could not be reached."""
        for ws in dead:
            try:
                self._subscribers.remove(ws)
            except ValueError:
                pass

    def subscribe(self, ws) -> None:
        self._subscribers.append(ws)

    def unsubscribe(self, ws) -> None:
        try:
            self._subscribers.remove(ws)
        except ValueError:
            pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class APEXHTTPServer(HTTPServer):
    """Backward compatibility wrapper — local TUI server with no auth and relaxed rate limits."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        super().__init__(
            host=host,
            port=port,
            require_auth=False,
            rate_limiter=RateLimiterOptions(
                config=RateLimitConfig(
                    requests_per_minute=120,
                    requests_per_hour=5000,
                    requests_per_day=50000,
                ),
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


def start_tui_server(port: int = 8080, agent: Agent | None = None) -> object:
    """Start the HTTP server for TUI in a background thread.

    Returns the server instance so callers can stop it later.
    """
    import sys
    import threading

    server = APEXHTTPServer(host="127.0.0.1", port=port)
    if agent is not None:
        server.agent = agent

    # On Windows, use SelectorEventLoop to avoid ProactorEventLoop crashes
    # when the loop is stopped/cleaned up from another thread.
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.start())
            loop.run_forever()
        except Exception:  # noqa: BLE001, S110
            pass
        finally:
            try:
                # Clean up pending tasks gracefully
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception:  # noqa: BLE001, S110
                pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    # Give the server a moment to bind the port
    import time

    time.sleep(0.5)
    server._thread = thread
    server._loop = loop
    return server


def stop_tui_server(server: object) -> None:
    """Stop a TUI server started by start_tui_server."""
    if server is None:
        return
    loop = getattr(server, "_loop", None)
    if loop and loop.is_running():
        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            logger.debug("TUI server loop already stopped")
