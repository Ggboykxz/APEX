"""APEX MCP client enhancements (Phase 2 — OpenCode parity).

Extends the existing ``apex.mcp`` with:

- Socket (HTTP/SSE) transport for remote MCP servers
- Streamable HTTP transport support
- Connection pool
- OAuth-ready scaffolding (the actual OAuth flow hooks into the
  existing credential store)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request

__all__ = [
    "MCPConnection",
    "MCPConnectionPool",
    "MCPServerConfig",
    "MCPTransportError",
]


class MCPTransportError(Exception):
    """Raised when an MCP transport operation fails."""


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP server configuration (schema-compatible)."""

    name: str
    type: str  # "remote" | "local"
    url: str | None = None
    command: tuple[str, ...] | None = None
    environment: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


class MCPConnection:
    """A single MCP connection (streamable HTTP / SSE)."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.session_id: str | None = None
        self.protocol_version: str | None = None
        self.server_info: dict[str, Any] | None = None
        self._closed = False

    # -- lifecycle ----------------------------------------------------------

    def open(self) -> None:
        """Perform the MCP handshake (initialize)."""
        if self._closed:
            raise MCPTransportError("connection is closed")
        if self.config.type != "remote" or not self.config.url:
            raise MCPTransportError("socket transport requires a remote url")

        result = self._post_jsonrpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "apex", "version": "0.1.0"},
            },
        )
        if result is None or "result" not in result:
            raise MCPTransportError(f"initialize failed: {result}")

        info = result["result"]
        self.protocol_version = info.get("protocolVersion")
        self.server_info = info.get("serverInfo")

        # notifications/initialized (fire-and-forget)
        self._post_jsonrpc("notifications/initialized", {}, notify=True)

    def close(self) -> None:
        self._closed = True

    # -- JSON-RPC ----------------------------------------------------------

    def _post_jsonrpc(self, method: str, params: dict, notify: bool = False) -> dict | None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notify:
            payload["id"] = 1

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        headers.update(self.config.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = request.Request(self.config.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                self.session_id = resp.headers.get("Mcp-Session-Id") or self.session_id
        except error.URLError as exc:
            raise MCPTransportError(f"transport error: {exc}") from exc

        if notify:
            return None
        return self._parse_response(body)

    @staticmethod
    def _parse_response(body: str) -> dict:
        """Parse the JSON or SSE response body."""
        if body.lstrip().startswith("event:"):
            # SSE stream — take the last data line
            data_lines = [l for l in body.splitlines() if l.startswith("data:")]
            if not data_lines:
                return {}
            body = data_lines[-1][len("data:"):].strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    # -- typed helpers ------------------------------------------------------

    def list_tools(self) -> list[dict]:
        result = self._post_jsonrpc("tools/list", {})
        if not result or "result" not in result:
            return []
        return result["result"].get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict | None:
        result = self._post_jsonrpc("tools/call", {"name": name, "arguments": arguments})
        if not result or "result" not in result:
            return None
        return result["result"]


class MCPConnectionPool:
    """Pool of MCP connections, one per server name."""

    def __init__(self) -> None:
        self._connections: dict[str, MCPConnection] = {}

    def get(self, name: str) -> MCPConnection | None:
        return self._connections.get(name)

    def add(self, connection: MCPConnection) -> None:
        if connection.config.name in self._connections:
            self._connections[connection.config.name].close()
        self._connections[connection.config.name] = connection

    def remove(self, name: str) -> None:
        conn = self._connections.pop(name, None)
        if conn is not None:
            conn.close()

    def close_all(self) -> None:
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
