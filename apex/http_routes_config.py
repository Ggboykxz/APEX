"""Configuration, command and project routes.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

from aiohttp import web

from .commands_manager import commands_manager
from .config_v2 import apex_config
from .http_helpers import _sanitize_config
from .project import ProjectInitializer

__all__ = [
    "ConfigRoutesMixin",
]


class ConfigRoutesMixin:
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
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_tui_config(self, request: web.Request) -> web.Response:
        """Return the merged TUI config for frontend customization."""
        from .config_v2 import tui_config as tc

        return web.json_response(
            {
                "keybinds": tc.keybinds,
                "theme": tc.theme,
                "scroll_speed": tc.scroll_speed,
                "scroll_acceleration": tc.scroll_acceleration,
                "diff_style": tc.diff_style,
                "mouse": tc.mouse,
                "leader_timeout": tc.leader_timeout,
            }
        )

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

            return web.json_response(
                {
                    "initialized": True,
                    "path": path,
                    "analysis": analysis,
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

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

            result_holder = {}

            class CaptureUI:
                def print_success(self, msg):
                    result_holder["output"] = msg

                def print_error(self, msg):
                    result_holder["output"] = f"ERROR: {msg}"

                def print_info(self, msg):
                    result_holder["output"] = msg

                def console(self):
                    class C:
                        def print(self, *a, **k):
                            pass

                    return C()

            capture_ui = CaptureUI()
            handled = handle_command(command, self.agent, capture_ui)
            return web.json_response(
                {
                    "handled": handled,
                    "output": result_holder.get("output", ""),
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

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

        rate_error, _result = await self._check_rate_limit(key_info)
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
            return web.json_response(
                {
                    "command": name,
                    "response": response,
                    "executed": True,
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)
