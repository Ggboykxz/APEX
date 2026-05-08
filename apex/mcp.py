"""MCP (Model Context Protocol) client for APEX - Connect to external tools and services."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field


@dataclass
class MCPResource:
    uri: str
    name: str
    description: str = ""
    mime_type: str = ""


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCP_SERVER:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


class MCPClient:
    def __init__(self, server: MCP_SERVER):
        self.server = server
        self.process: subprocess.Popen | None = None
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._request_id = 0

    async def connect(self) -> bool:
        if not self.server.enabled:
            return False

        try:
            self.process = subprocess.Popen(
                [self.server.command] + self.server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.server.env,
                text=True,
            )
            await asyncio.sleep(0.5)

            initialized = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "apex", "version": "0.1.0"}
            })
            return initialized is not None
        except Exception:
            return False

    async def disconnect(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)

    async def _send_request(self, method: str, params: dict | None = None) -> Any:
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }

        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()

            response_line = self.process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                return response.get("result")
        except Exception:
            pass
        return None

    async def list_tools(self) -> list[MCPTool]:
        result = await self._send_request("tools/list")
        if result and "tools" in result:
            self._tools = [
                MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {})
                ) for t in result["tools"]
            ]
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        if result and "content" in result:
            return self._format_content(result["content"])
        return "ERROR: Tool call failed"

    async def list_resources(self) -> list[MCPResource]:
        result = await self._send_request("resources/list")
        if result and "resources" in result:
            self._resources = [
                MCPResource(
                    uri=r["uri"],
                    name=r.get("name", ""),
                    description=r.get("description", ""),
                    mime_type=r.get("mimeType", "")
                ) for r in result["resources"]
            ]
        return self._resources

    async def read_resource(self, uri: str) -> str:
        result = await self._send_request("resources/read", {"uri": uri})
        if result and "contents" in result:
            return self._format_content(result["contents"])
        return "ERROR: Resource not found"

    def _format_content(self, contents: list[dict]) -> str:
        parts = []
        for item in contents:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif item.get("type") == "blob":
                parts.append(f"[{item.get('mimeType', 'unknown')} data]")
        return "\n".join(parts)

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"mcp_{self.server.name}_{tool.name}",
                    "description": f"[{self.server.name}] {tool.description}",
                    "parameters": tool.input_schema
                }
            }
            for tool in self._tools
        ]


class MCPManager:
    def __init__(self):
        self._servers: dict[str, MCPClient] = {}

    def add_server(self, name: str, command: str, args: list[str] | None = None, env: dict | None = None, enabled: bool = True) -> None:
        server = MCP_SERVER(
            name=name,
            command=command,
            args=args or [],
            env=env or {},
            enabled=enabled
        )
        self._servers[name] = MCPClient(server)

    async def connect_all(self) -> dict[str, bool]:
        results = {}
        for name, client in self._servers.items():
            results[name] = await client.connect()
        return results

    async def disconnect_all(self) -> None:
        for client in self._servers.values():
            await client.disconnect()

    def get_all_tools(self) -> list[dict]:
        tools = []
        for name, client in self._servers.items():
            client_tools = client.get_tool_schemas()
            tools.extend(client_tools)
        return tools

    async def call_tool(self, full_name: str, arguments: dict) -> str:
        parts = full_name.split("_", 1)
        if len(parts) != 2:
            return "ERROR: Invalid tool name format"

        server_name = parts[0]
        tool_name = parts[1]

        if server_name not in self._servers:
            return f"ERROR: Unknown server: {server_name}"

        return await self._servers[server_name].call_tool(tool_name, arguments)

    def list_servers(self) -> list[dict]:
        return [
            {"name": name, "enabled": client.server.enabled}
            for name, client in self._servers.items()
        ]

    def get_all_resources(self) -> list[dict]:
        resources = []
        for name, client in self._servers.items():
            for r in client._resources:
                resources.append({
                    "server": name,
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description
                })
        return resources


mcp_manager = MCPManager()


def load_mcp_config(config_path: Path) -> None:
    if not config_path.exists():
        return

    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config or "mcp_servers" not in config:
            return

        for name, server_config in config["mcp_servers"].items():
            mcp_manager.add_server(
                name=name,
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                enabled=server_config.get("enabled", True)
            )
    except Exception:
        pass