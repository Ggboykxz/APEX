"""Model, provider, agent, theme and formatter routes.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

from aiohttp import web

from .agents import agent_manager
from .config import MODELS
from .formatter import formatter_manager
from .http_helpers import _get_configured_providers
from .theme_manager import theme_manager

__all__ = [
    "CatalogRoutesMixin",
]


class CatalogRoutesMixin:
    async def list_models(self, request: web.Request) -> web.Response:
        """List available models."""
        from .config import MODELS

        models = [{"alias": alias, "model": model_id} for alias, model_id in MODELS.items()]
        return web.json_response({"models": models})

    async def api_models_refresh(self, request: web.Request) -> web.Response:
        """Refresh model list."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        models = [{"alias": alias, "model": model_id} for alias, model_id in MODELS.items()]
        return web.json_response({"models": models, "count": len(models)})

    async def api_providers_list(self, request: web.Request) -> web.Response:
        """List configured providers."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        providers = _get_configured_providers()
        return web.json_response({"providers": providers})

    async def api_agents_list(self, request: web.Request) -> web.Response:
        """List available agents."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        agents = []
        for agent_cfg in agent_manager.agents.values():
            agents.append(
                {
                    "name": agent_cfg.name,
                    "description": agent_cfg.description,
                    "mode": agent_cfg.mode,
                    "model": agent_cfg.model,
                    "hidden": agent_cfg.hidden,
                    "disabled": agent_cfg.disabled,
                    "color": agent_cfg.color,
                    "permission": dict(agent_cfg.permission),
                }
            )
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

        return web.json_response(
            {
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
            }
        )

    async def api_themes_list(self, request: web.Request) -> web.Response:
        """List available themes."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        themes = theme_manager.list_themes()
        current = theme_manager.current_name
        return web.json_response(
            {
                "themes": themes,
                "current": current,
            }
        )

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
            await self.event_bus.publish("theme_changed", {"theme": theme_manager.current_name})
            return web.json_response(
                {
                    "theme": theme_manager.current_name,
                    "resolved": theme_manager.current_theme,
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

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
                return web.json_response(
                    {"error": "no formatter available for this file"}, status=400
                )

            if code:
                formatted = formatter_manager.format_code(code, extension)
                return web.json_response({"formatted": True, "code": formatted})

            return web.json_response({"error": "file_path or code required"}, status=400)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_formatter_status(self, request: web.Request) -> web.Response:
        """Formatter status (OpenCode /formatter compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        from .formatter import formatter_manager

        available = formatter_manager.list_available()
        return web.json_response(
            [{"name": f.name, "available": True, "extensions": f.extensions} for f in available]
        )

    async def api_mcp_status(self, request: web.Request) -> web.Response:
        """MCP server status (OpenCode /mcp compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        from .mcp import mcp_manager

        servers = mcp_manager.list_servers() if hasattr(mcp_manager, "list_servers") else []
        return web.json_response(
            {
                s.get("name", str(i)): {
                    "enabled": s.get("enabled", True),
                    "tools_count": s.get("tools_count", 0),
                }
                for i, s in enumerate(servers)
            }
        )

    async def api_lsp_status(self, request: web.Request) -> web.Response:
        """LSP server status (OpenCode /lsp compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        return web.json_response([])
