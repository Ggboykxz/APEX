"""HTTP/SSE API server for APEX - headless agent workflows with security."""

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from aiohttp import web

from .agent import Agent
from .rate_limiter import (
    create_rate_limiter,
    RateLimitConfig,
    RateLimitResult,
)
from .api_key import (
    key_manager,
    InvalidKeyError,
    KeyExpiredError,
    KeyDisabledError,
)
from .billing import (
    billing_manager,
)
from .config_v2 import apex_config, ApexConfig
from .share import share_manager, SENSITIVE_PATTERNS
from .theme_manager import theme_manager
from .formatter import formatter_manager
from .commands_manager import commands_manager, CommandConfig
from .agents import agent_manager
from .session import SessionManager, UndoManager
from .project import ProjectInitializer
from .config import MODELS, MODEL_PROVIDERS

logger = logging.getLogger(__name__)

SENSITIVE_CONFIG_KEYS = frozenset({
    "api_key", "apikey", "token", "secret", "password", "credential",
    "auth_token", "access_key", "secret_key", "private_key",
})

_API_KEY_ENV_VARS = {
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
    "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "DASHSCOPE_API_KEY",
    "LLAMA_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY", "FIREWORKS_API_KEY", "TOGETHER_API_KEY",
    "HF_TOKEN", "PERPLEXITY_API_KEY", "NVIDIA_API_KEY",
    "CLOUDFLARE_API_KEY", "COHERE_API_KEY", "GITHUB_TOKEN",
}


def _sanitize_config(data: dict, _depth: int = 0) -> dict:
    if _depth > 10:
        return data
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_CONFIG_KEYS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_config(value, _depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_config(item, _depth + 1) if isinstance(item, dict)
                else _sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            sanitized[key] = _sanitize_string(value)
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_string(value: str) -> str:
    for pattern in SENSITIVE_PATTERNS:
        try:
            value = pattern.sub("***REDACTED***", value)
        except Exception:
            pass
    return value


def _check_provider_configured(env_var: str) -> bool:
    return bool(os.environ.get(env_var) or os.environ.get(env_var.lower()))


def _get_configured_providers() -> list[dict]:
    configured = []
    seen = set()
    for alias, model_id in MODELS.items():
        env_key = MODEL_PROVIDERS.get(alias)
        if env_key is None:
            continue
        if env_key in seen:
            continue
        seen.add(env_key)
        provider_name = env_key.replace("_API_KEY", "").replace("_TOKEN", "").replace("_", " ").title().strip()
        configured.append({
            "name": provider_name,
            "env_var": env_key,
            "configured": _check_provider_configured(env_key),
            "models": [
                a for a, e in MODEL_PROVIDERS.items() if e == env_key
            ],
        })
    return configured


class AuthMiddleware:
    """Authentication middleware for HTTP API."""

    def __init__(self, require_auth: bool = True):
        self.require_auth = require_auth
        self.key_manager = key_manager

    async def authenticate(
        self, request: web.Request
    ) -> tuple[bool, Optional[str], Optional[dict]]:
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
        self.session_manager = SessionManager()
        self.undo_manager = UndoManager()

    def _setup_routes(self):
        """Setup HTTP routes."""
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
        self.app.router.add_post("/api/v1/session/{session_id}/fork", self.api_session_fork)
        self.app.router.add_post("/api/v1/session/{session_id}/abort", self.api_session_abort)
        self.app.router.add_get("/api/v1/lsp", self.api_lsp_status)
        self.app.router.add_get("/api/v1/formatter", self.api_formatter_status)
        self.app.router.add_get("/api/v1/mcp", self.api_mcp_status)

    async def _check_auth(
        self, request: web.Request
    ) -> tuple[Optional[web.Response], Optional[dict]]:
        """Check authentication, returns error response if failed."""
        success, api_key, key_info = await self.auth_middleware.authenticate(request)
        if self.require_auth and not success:
            return web.json_response(
                {"error": "Authentication required", "code": "AUTH_REQUIRED"},
                status=401,
            ), None
        return None, key_info

    async def _check_rate_limit(
        self, key_info: Optional[dict]
    ) -> tuple[Optional[web.Response], Optional[RateLimitResult]]:
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
            <li>GET /api/v1/config - Get config</li>
            <li>POST /api/v1/config - Update config</li>
            <li>GET /api/v1/agents - List agents</li>
            <li>GET /api/v1/agents/{name} - Get agent</li>
            <li>GET /api/v1/sessions - List sessions</li>
            <li>DELETE /api/v1/sessions/{id} - Delete session</li>
            <li>POST /api/v1/share - Share session</li>
            <li>POST /api/v1/unshare/{share_id} - Unshare session</li>
            <li>GET /api/v1/shares - List shared sessions</li>
            <li>GET /api/v1/themes - List themes</li>
            <li>POST /api/v1/themes - Set theme</li>
            <li>GET /api/v1/stats - Usage statistics</li>
            <li>GET /api/v1/formatters - List formatters</li>
            <li>POST /api/v1/format - Format code</li>
            <li>POST /api/v1/compact - Compact context</li>
            <li>POST /api/v1/models/refresh - Refresh models</li>
            <li>GET /api/v1/providers - List providers</li>
            <li>POST /api/v1/auth/login - Add API key</li>
            <li>POST /api/v1/auth/logout - Remove API key</li>
            <li>GET /api/v1/auth/status - Auth status</li>
            <li>POST /api/v1/commands/execute - Execute command</li>
            <li>GET /api/v1/commands - List commands</li>
            <li>POST /api/v1/undo - Undo</li>
            <li>POST /api/v1/redo - Redo</li>
            <li>POST /api/v1/init - Initialize project</li>
            <li>GET /api/v1/export/{session_id} - Export session</li>
            <li>POST /api/v1/import - Import session</li>
        </ul>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    async def health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        from apex import __version__
        return web.json_response(
            {
                "status": "ok",
                "agent": self.agent.model,
                "version": __version__,
                "timestamp": time.time(),
            }
        )

    async def api_global_health(self, request: web.Request) -> web.Response:
        """OpenCode-compatible global health endpoint."""
        from apex import __version__
        return web.json_response({
            "healthy": True,
            "version": __version__,
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

            return web.json_response(
                {
                    "response": response,
                    "model": self.agent.model,
                    "usage": self.agent.usage,
                    "rate_limit": {
                        "remaining_minute": result.remaining_minute,
                        "remaining_hour": result.remaining_hour,
                        "remaining_day": result.remaining_day,
                    }
                    if result
                    else None,
                }
            )
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
                rate_limit_data = {"rate_limit": {"remaining_minute": result.remaining_minute}}
                await response.write(f"data: {json.dumps(rate_limit_data)}\n\n".encode())
            return response
        except Exception as e:
            logger.error(f"Stream error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def list_models(self, request: web.Request) -> web.Response:
        """List available models."""
        from .config import MODELS

        models = [{"alias": alias, "model": model_id} for alias, model_id in MODELS.items()]
        return web.json_response({"models": models})

    async def session_save(self, request: web.Request) -> web.Response:
        """Save current session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            name = data.get("name", "http_session")
            path = self.session_manager.save(self.agent, name)
            return web.json_response({"saved": str(path)})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def session_load(self, request: web.Request) -> web.Response:
        """Load a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"error": "name required"}, status=400)

            success = self.session_manager.load(name, self.agent)
            if success:
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

    # ── API v1: Config ─────────────────────────────────────

    async def api_config_get(self, request: web.Request) -> web.Response:
        """Get current config (sanitized, no API keys)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        raw = apex_config.raw()
        sanitized = _sanitize_config(raw)
        return web.json_response({"config": sanitized})

    async def api_config_set(self, request: web.Request) -> web.Response:
        """Update config."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            for key, value in data.items():
                apex_config.set(key, value)
            raw = apex_config.raw()
            sanitized = _sanitize_config(raw)
            return web.json_response({"config": sanitized})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Agents ─────────────────────────────────────

    async def api_agents_list(self, request: web.Request) -> web.Response:
        """List available agents."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        agents = []
        for agent_cfg in agent_manager.agents.values():
            agents.append({
                "name": agent_cfg.name,
                "description": agent_cfg.description,
                "mode": agent_cfg.mode,
                "model": agent_cfg.model,
                "hidden": agent_cfg.hidden,
                "disabled": agent_cfg.disabled,
                "color": agent_cfg.color,
                "permission": dict(agent_cfg.permission),
            })
        return web.json_response({"agents": agents})

    async def api_agents_get(self, request: web.Request) -> web.Response:
        """Get agent details."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        name = request.match_info.get("name", "")
        agent_cfg = agent_manager.get(name)
        if not agent_cfg:
            return web.json_response({"error": f"Agent '{name}' not found"}, status=404)

        return web.json_response({
            "name": agent_cfg.name,
            "description": agent_cfg.description,
            "system_prompt": agent_cfg.system_prompt,
            "mode": agent_cfg.mode,
            "model": agent_cfg.model,
            "temperature": agent_cfg.temperature,
            "top_p": agent_cfg.top_p,
            "max_steps": agent_cfg.max_steps,
            "hidden": agent_cfg.hidden,
            "disabled": agent_cfg.disabled,
            "color": agent_cfg.color,
            "permission": dict(agent_cfg.permission),
        })

    # ── API v1: Sessions ───────────────────────────────────

    async def api_sessions_list(self, request: web.Request) -> web.Response:
        """List all sessions."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        sessions = self.session_manager.list_sessions()
        return web.json_response({"sessions": sessions})

    async def api_sessions_delete(self, request: web.Request) -> web.Response:
        """Delete a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        session_id = request.match_info.get("id", "")
        try:
            sessions_dir = Path.home() / ".apex" / "sessions"
            found = False
            for fpath in sessions_dir.glob(f"*{session_id}*"):
                if fpath.is_file() and not fpath.is_symlink():
                    fpath.unlink()
                    found = True
                    break
            if not found:
                for fpath in sessions_dir.glob("*.json"):
                    if fpath.is_symlink():
                        continue
                    try:
                        data = json.loads(fpath.read_text())
                        if data.get("name") == session_id or data.get("session_id") == session_id:
                            fpath.unlink()
                            found = True
                            break
                    except Exception:
                        continue
            if found:
                return web.json_response({"deleted": session_id})
            return web.json_response({"error": "session not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Share ──────────────────────────────────────

    async def api_share(self, request: web.Request) -> web.Response:
        """Share current session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            title = data.get("title", "")
            session_id = data.get("session_id", "default")

            url = share_manager.share_session(session_id, title=title)
            if not url:
                return web.json_response({"error": "sharing is disabled"}, status=403)
            return web.json_response({"url": url, "share_id": url.rstrip("/").split("/")[-1]})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_unshare(self, request: web.Request) -> web.Response:
        """Unshare a session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        share_id = request.match_info.get("share_id", "")
        success = share_manager.unshare_session(share_id)
        if success:
            return web.json_response({"unshared": share_id})
        return web.json_response({"error": "share not found"}, status=404)

    async def api_shares_list(self, request: web.Request) -> web.Response:
        """List shared sessions."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        shares = share_manager.list_shared()
        return web.json_response({"shares": shares})

    # ── API v1: Themes ─────────────────────────────────────

    async def api_themes_list(self, request: web.Request) -> web.Response:
        """List available themes."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        themes = theme_manager.list_themes()
        current = theme_manager.current_name
        return web.json_response({
            "themes": themes,
            "current": current,
        })

    async def api_themes_set(self, request: web.Request) -> web.Response:
        """Set theme."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            name = data.get("theme", "")
            if not name:
                return web.json_response({"error": "theme name required"}, status=400)
            theme_manager.set_theme(name)
            return web.json_response({
                "theme": theme_manager.current_name,
                "resolved": theme_manager.current_theme,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Stats ──────────────────────────────────────

    async def api_stats(self, request: web.Request) -> web.Response:
        """Get usage statistics."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        usage = self.agent.usage or {}
        stats = {
            "sessions_count": len(self.session_manager.list_sessions()),
            "current_model": self.agent.model,
            "current_agent": self.agent.current_agent,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "undo_available": self.undo_manager.can_undo(),
            "redo_available": self.undo_manager.can_redo(),
            "shares_count": len(share_manager.list_shared()),
        }
        if key_info:
            stats["rate_limit"] = self.rate_limiter.get_status(f"key:{key_info['key_id']}")

        return web.json_response(stats)

    # ── API v1: Formatters ─────────────────────────────────

    async def api_formatters_list(self, request: web.Request) -> web.Response:
        """List available formatters."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        available = formatter_manager.list_available()
        formatters = [
            {
                "name": f.name,
                "command": f.command,
                "extensions": f.extensions,
            }
            for f in available
        ]
        return web.json_response({"formatters": formatters})

    async def api_format(self, request: web.Request) -> web.Response:
        """Format a file or code snippet."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            file_path = data.get("file_path", "")
            code = data.get("code", "")
            extension = data.get("extension", "")

            if file_path:
                success = formatter_manager.format_file(file_path)
                if success:
                    return web.json_response({"formatted": True, "file": file_path})
                return web.json_response({"error": "no formatter available for this file"}, status=400)

            if code:
                formatted = formatter_manager.format_code(code, extension)
                return web.json_response({"formatted": True, "code": formatted})

            return web.json_response({"error": "file_path or code required"}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Compact ────────────────────────────────────

    async def api_compact(self, request: web.Request) -> web.Response:
        """Compact session context."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            strategy = data.get("strategy", "summarize")

            from .context_tracking import ContextManager
            ctx = ContextManager()
            for msg in self.agent.history:
                ctx.add_message(msg.get("role", "user"), msg.get("content", ""))

            saved = ctx.compact(strategy=strategy)
            self.agent.history = ctx.get_messages()

            return web.json_response({
                "compacted": True,
                "strategy": strategy,
                "tokens_saved": saved,
                "history_length": len(self.agent.history),
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Models ─────────────────────────────────────

    async def api_models_refresh(self, request: web.Request) -> web.Response:
        """Refresh model list."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        models = [{"alias": alias, "model": model_id} for alias, model_id in MODELS.items()]
        return web.json_response({"models": models, "count": len(models)})

    # ── API v1: Providers ──────────────────────────────────

    async def api_providers_list(self, request: web.Request) -> web.Response:
        """List configured providers."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        providers = _get_configured_providers()
        return web.json_response({"providers": providers})

    # ── API v1: Auth ───────────────────────────────────────

    _VALID_PROVIDERS = {
        "ANTHROPIC", "OPENAI", "GEMINI", "DEEPSEEK", "MISTRAL", "COHERE",
        "GROQ", "XAI", "TOGETHER", "FIREWORKS", "CEREBRAS", "PERPLEXITY",
        "HF", "GITHUB", "NVIDIA", "CLOUDFLARE", "DASHSCOPE", "LLAMA",
        "OPENROUTER", "HUGGINGFACE", "BEDROCK", "AZURE",
        "OPENCODE", "OPENCODE_GO", "APEX_FREE", "APEX_PRO",
    }

    async def api_auth_login(self, request: web.Request) -> web.Response:
        """Add/update provider API key."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            provider = data.get("provider", "").upper().replace(" ", "_")
            api_key_value = data.get("api_key", "")

            if not provider or not api_key_value:
                return web.json_response({"error": "provider and api_key required"}, status=400)

            if provider not in self._VALID_PROVIDERS:
                return web.json_response({"error": f"Unknown provider: {provider}"}, status=400)

            env_var = f"{provider}_API_KEY"
            if provider == "HF":
                env_var = "HF_TOKEN"
            elif provider == "GITHUB":
                env_var = "GITHUB_TOKEN"

            os.environ[env_var] = api_key_value

            return web.json_response({
                "configured": True,
                "provider": provider,
                "env_var": env_var,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_auth_logout(self, request: web.Request) -> web.Response:
        """Remove provider API key."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            provider = data.get("provider", "").upper().replace(" ", "_")

            if provider:
                env_var = f"{provider}_API_KEY"
                if provider == "HF":
                    env_var = "HF_TOKEN"
                elif provider == "GITHUB":
                    env_var = "GITHUB_TOKEN"
                os.environ.pop(env_var, None)
                os.environ.pop(env_var.lower(), None)
                return web.json_response({"removed": True, "env_var": env_var})

            removed = []
            for env_var in _API_KEY_ENV_VARS:
                if os.environ.pop(env_var, None):
                    removed.append(env_var)
                if os.environ.pop(env_var.lower(), None):
                    removed.append(env_var.lower())
            return web.json_response({"removed": True, "env_vars": removed})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_auth_status(self, request: web.Request) -> web.Response:
        """Check which providers are configured."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        providers = _get_configured_providers()
        configured = [p for p in providers if p["configured"]]
        return web.json_response({
            "providers": providers,
            "configured_count": len(configured),
            "any_configured": len(configured) > 0,
        })

    # ── API v1: Commands ───────────────────────────────────

    async def api_commands_list(self, request: web.Request) -> web.Response:
        """List available custom commands."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        commands_manager.load_all(str(self.agent.cwd))
        cmds = commands_manager.list()
        commands = [
            {
                "name": c.name,
                "description": c.description,
                "agent": c.agent,
                "model": c.model,
                "subtask": c.subtask,
            }
            for c in cmds
        ]
        return web.json_response({"commands": commands})

    async def api_commands_execute(self, request: web.Request) -> web.Response:
        """Execute a custom command."""
        auth_error, key_info = await self._check_auth(request)
        if auth_error:
            return auth_error

        rate_error, result = await self._check_rate_limit(key_info)
        if rate_error:
            return rate_error

        try:
            data = await request.json()
            name = data.get("name", "")
            args = data.get("args", [])

            if not name:
                return web.json_response({"error": "command name required"}, status=400)

            commands_manager.load_all(str(self.agent.cwd))
            cmd_config = commands_manager.get(name)
            if not cmd_config:
                return web.json_response({"error": f"Unknown command: {name}"}, status=404)

            response = commands_manager.execute(name, args, self.agent)
            return web.json_response({
                "command": name,
                "response": response,
                "executed": True,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Undo/Redo ──────────────────────────────────

    async def api_undo(self, request: web.Request) -> web.Response:
        """Undo last action."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        action = self.undo_manager.undo()
        if action:
            return web.json_response({
                "undone": True,
                "action": action.get("type"),
                "details": action.get("details"),
            })
        return web.json_response({"error": "nothing to undo"}, status=400)

    async def api_redo(self, request: web.Request) -> web.Response:
        """Redo last undone action."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        action = self.undo_manager.redo()
        if action:
            return web.json_response({
                "redone": True,
                "action": action.get("type"),
                "details": action.get("details"),
            })
        return web.json_response({"error": "nothing to redo"}, status=400)

    # ── API v1: Init ───────────────────────────────────────

    async def api_init(self, request: web.Request) -> web.Response:
        """Initialize project (create AGENTS.md)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            cwd = data.get("cwd", str(self.agent.cwd))

            initializer = ProjectInitializer(cwd)
            analysis = initializer.analyze()
            path = initializer.create_context_file()

            return web.json_response({
                "initialized": True,
                "path": path,
                "analysis": analysis,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Export/Import ──────────────────────────────

    async def api_export(self, request: web.Request) -> web.Response:
        """Export session as JSON."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        session_id = request.match_info.get("session_id", "default")

        export_data = share_manager.export_session(session_id)
        if not export_data:
            return web.json_response({"error": "session not found"}, status=404)

        return web.json_response(export_data)

    async def api_import(self, request: web.Request) -> web.Response:
        """Import session from JSON."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            file_path = data.get("file_path", "")
            session_data = data.get("data")

            if file_path:
                session_id = share_manager.import_session(file_path)
                if session_id:
                    return web.json_response({"imported": True, "session_id": session_id})
                return web.json_response({"error": "import failed"}, status=400)

            if session_data:
                import uuid as _uuid
                from datetime import datetime as _datetime

                session_id = session_data.get("session_id", _uuid.uuid4().hex[:12])
                safe = share_manager.sanitize_session_data(session_data)

                sessions_dir = Path.home() / ".apex" / "sessions"
                sessions_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{_datetime.now().strftime('%Y%m%d_%H%M%S')}_imported_{session_id}.json"
                filepath = sessions_dir / filename
                filepath.write_text(json.dumps(safe, indent=2))

                return web.json_response({"imported": True, "session_id": session_id})

            return web.json_response({"error": "file_path or data required"}, status=400)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Files ─────────────────────────────────────

    async def api_files_list(self, request: web.Request) -> web.Response:
        """List project files for @ autocomplete."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        import fnmatch
        files: list[str] = []
        cwd = self.agent.cwd
        ignore_patterns = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", "target", ".tox", "coverage",
            ".apex", ".opencode", ".gitignore", ".gitattributes",
        }
        try:
            for entry in cwd.rglob("*"):
                parts = entry.relative_to(cwd).parts
                if any(p in ignore_patterns for p in parts):
                    continue
                if any(p.startswith(".") for p in parts[:-1]):
                    continue
                rel = str(entry.relative_to(cwd))
                if entry.is_dir():
                    rel += "/"
                files.append(rel)
        except Exception:
            pass
        return web.json_response({"files": sorted(files)})

    # ── Find / File (OpenCode compat) ─────────────────────

    async def api_find_file(self, request: web.Request) -> web.Response:
        """Fuzzy file search (OpenCode /find/file compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        query = request.query.get("query", "")
        file_type = request.query.get("type", "")
        limit_str = request.query.get("limit", "50")
        try:
            limit = min(int(limit_str), 200)
        except (ValueError, TypeError):
            limit = 50

        if not query:
            return web.json_response([])

        import fnmatch
        query_lower = query.lower()
        results: list[str] = []
        cwd = self.agent.cwd
        ignore_patterns = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", "target", ".tox", "coverage",
            ".apex", ".opencode",
        }

        def fuzzy_match(name: str, q: str) -> bool:
            qi = 0
            for ch in name.lower():
                if qi < len(q) and ch == q[qi]:
                    qi += 1
            return qi == len(q)

        try:
            for entry in cwd.rglob("*"):
                parts = entry.relative_to(cwd).parts
                if any(p in ignore_patterns for p in parts):
                    continue
                if any(p.startswith(".") for p in parts[:-1]):
                    continue
                name = entry.name
                rel = str(entry.relative_to(cwd))
                if file_type == "file" and entry.is_dir():
                    continue
                if file_type == "directory" and entry.is_file():
                    continue
                if entry.is_dir():
                    name += "/"
                    rel += "/"
                if fuzzy_match(rel, query_lower):
                    results.append(rel)
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        return web.json_response(results)

    # ── API v1: Bash ──────────────────────────────────────

    async def api_bash(self, request: web.Request) -> web.Response:
        """Execute a bash command (for TUI !bash inline)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        from .tools import ToolExecutor
        try:
            data = await request.json()
            command = data.get("command", "")
            if not command:
                return web.json_response({"error": "command required"}, status=400)
            executor = ToolExecutor(cwd=self.agent.cwd)
            result = executor.execute("run_command", {"command": command})
            return web.json_response({"output": result, "command": command})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: Event bus ─────────────────────────────────

    _sse_clients: list = []

    async def api_global_event(self, request: web.Request) -> web.Response:
        """SSE event stream (OpenCode /global/event compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        await response.prepare(request)
        self._sse_clients.append(response)
        try:
            from apex import __version__
            await response.write(f"data: {{\"event\": \"connected\", \"version\": \"{__version__}\"}}\n\n".encode())
            while True:
                await asyncio.sleep(30)
                await response.write(": keepalive\n\n".encode())
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        finally:
            try:
                self._sse_clients.remove(response)
            except ValueError:
                pass
        return response

    # ── API v1: Session operations ────────────────────────

    async def api_session_diff(self, request: web.Request) -> web.Response:
        """Get session diff (OpenCode /session/:id/diff compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        session_id = request.match_info.get("session_id", "")
        try:
            import subprocess
            stat = subprocess.run(["git", "diff", "--stat"], cwd=self.agent.cwd, capture_output=True, text=True)
            diff = subprocess.run(["git", "diff"], cwd=self.agent.cwd, capture_output=True, text=True)
            return web.json_response({
                "files": stat.stdout.strip() or "(clean)",
                "diff": diff.stdout or "",
                "session_id": session_id,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_session_fork(self, request: web.Request) -> web.Response:
        """Fork current session (OpenCode /session/:id/fork compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        self.agent.reset_history()
        return web.json_response({"forked": True, "session_id": request.match_info.get("session_id", "")})

    async def api_session_abort(self, request: web.Request) -> web.Response:
        """Abort running session."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        return web.json_response({"aborted": True})

    # ── API v1: Status endpoints ──────────────────────────

    async def api_lsp_status(self, request: web.Request) -> web.Response:
        """LSP server status (OpenCode /lsp compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        return web.json_response([])

    async def api_formatter_status(self, request: web.Request) -> web.Response:
        """Formatter status (OpenCode /formatter compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        from .formatter import formatter_manager
        available = formatter_manager.list_available()
        return web.json_response([
            {"name": f.name, "available": True, "extensions": f.extensions}
            for f in available
        ])

    async def api_mcp_status(self, request: web.Request) -> web.Response:
        """MCP server status (OpenCode /mcp compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        from .mcp import mcp_manager
        servers = mcp_manager.list_servers() if hasattr(mcp_manager, "list_servers") else []
        return web.json_response({
            s.name: {"enabled": getattr(s, "enabled", True)} for s in servers
        })

    # ── API v1: Command ───────────────────────────────────

    async def api_command(self, request: web.Request) -> web.Response:
        """Execute a slash command locally."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            command = data.get("command", "")
            if not command:
                return web.json_response({"error": "command required"}, status=400)

            from .main import handle_command
            from .ui import UI
            import io, sys

            ui = UI()
            result_holder = {}

            class CaptureUI:
                def print_success(self, msg): result_holder["output"] = msg
                def print_error(self, msg): result_holder["output"] = f"ERROR: {msg}"
                def print_info(self, msg): result_holder["output"] = msg
                def console(self):
                    class C:
                        def print(self, *a, **k): pass
                    return C()

            capture_ui = CaptureUI()
            handled = handle_command(command, self.agent, capture_ui)
            return web.json_response({
                "handled": handled,
                "output": result_holder.get("output", ""),
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── API v1: TUI Config ────────────────────────────────

    async def api_tui_config(self, request: web.Request) -> web.Response:
        """Return the merged TUI config for frontend customization."""
        from .config_v2 import tui_config as tc
        return web.json_response({
            "keybinds": tc.keybinds,
            "theme": tc.theme,
            "scroll_speed": tc.scroll_speed,
            "scroll_acceleration": tc.scroll_acceleration,
            "diff_style": tc.diff_style,
            "mouse": tc.mouse,
            "leader_timeout": tc.leader_timeout,
        })

    # ── Server lifecycle ───────────────────────────────────

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

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
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


def start_tui_server(port: int = 8080, agent: "Agent | None" = None) -> object:
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
        except Exception:
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
            except Exception:
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
            pass  # Loop already stopped
