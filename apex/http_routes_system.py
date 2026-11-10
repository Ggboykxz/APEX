"""Health, metrics, statistics and file-system routes.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

import time
from itertools import islice
from pathlib import Path

from aiohttp import web

from .billing import billing_manager
from .share import share_manager

__all__ = [
    "SystemRoutesMixin",
]

IGNORE_PATTERNS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "target",
        ".tox",
        "coverage",
        ".apex",
        ".opencode",
    }
)

FILE_LIST_IGNORE_PATTERNS = IGNORE_PATTERNS | frozenset({".gitignore", ".gitattributes"})


class SystemRoutesMixin:
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

        return web.json_response(
            {
                "healthy": True,
                "version": __version__,
            }
        )

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

    def _list_project_files(self, cwd: Path, ignore_patterns: frozenset[str]) -> list[str]:
        """The project files of the working tree, for @ autocomplete."""
        files: list[str] = []
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
        except Exception:  # noqa: BLE001, S110
            pass
        return files

    async def api_files_list(self, request: web.Request) -> web.Response:
        """List project files for @ autocomplete."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        files = self._list_project_files(self.agent.cwd, FILE_LIST_IGNORE_PATTERNS)
        return web.json_response({"files": sorted(files)})

    @staticmethod
    def _fuzzy_match(name: str, query: str) -> bool:
        """Whether the characters of *query* appear in order inside *name*."""
        qi = 0
        for ch in name.lower():
            if qi < len(query) and ch == query[qi]:
                qi += 1
        return qi == len(query)

    @staticmethod
    def _is_ignored(parts: tuple[str, ...]) -> bool:
        """Whether the entry sits in an ignored or hidden directory."""
        if any(p in IGNORE_PATTERNS for p in parts):
            return True
        return any(p.startswith(".") for p in parts[:-1])

    @staticmethod
    def _entry_matches_type(entry: Path, file_type: str) -> bool:
        """Whether the entry matches the requested file type."""
        if file_type == "file":
            return not entry.is_dir()
        if file_type == "directory":
            return not entry.is_file()
        return True

    def _match_entry(self, entry: Path, cwd: Path, file_type: str) -> str | None:
        """The relative name of an entry when it passes the query filters."""
        parts = entry.relative_to(cwd).parts
        if self._is_ignored(parts):
            return None
        if not self._entry_matches_type(entry, file_type):
            return None
        rel = str(entry.relative_to(cwd))
        if entry.is_dir():
            rel += "/"
        return rel

    def _find_file_matches(
        self, cwd: Path, query_lower: str, file_type: str, limit: int
    ) -> list[str]:
        """The files of the working tree matching a fuzzy query."""
        try:
            candidates = (self._match_entry(entry, cwd, file_type) for entry in cwd.rglob("*"))
            matches = (
                rel for rel in candidates if rel is not None and self._fuzzy_match(rel, query_lower)
            )
            return list(islice(matches, limit))
        except Exception:  # noqa: BLE001
            return []

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

        results = self._find_file_matches(self.agent.cwd, query.lower(), file_type, limit)
        return web.json_response(results)

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
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)
