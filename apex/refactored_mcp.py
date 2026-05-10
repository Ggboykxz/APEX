"""Refactored MCP module - More testable and modular."""

import asyncio
import json
import subprocess
from typing import Any, Optional
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict = field(default_factory=dict)
    enabled: bool = True
    transport: str = "stdio"


class MCPProtocolHandler:
    """Testable protocol handler for MCP."""

    def __init__(self):
        self.request_id = 0

    def create_request(self, method: str, params: dict = None) -> dict:
        """Create a JSON-RPC request."""
        self.request_id += 1
        request = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params:
            request["params"] = params
        return request

    def create_response(self, request_id: int, result: Any = None, error: dict = None) -> dict:
        """Create a JSON-RPC response."""
        response = {"jsonrpc": "2.0", "id": request_id}
        if result is not None:
            response["result"] = result
        if error:
            response["error"] = error
        return response

    def parse_message(self, data: str) -> Optional[dict]:
        """Parse a JSON-RPC message."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    def serialize_message(self, message: dict) -> str:
        """Serialize a message to JSON."""
        return json.dumps(message)


class MCPToolManager:
    """Testable tool manager."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}

    def add_tool(self, tool: MCPTool) -> None:
        """Add a tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> list[MCPTool]:
        """Get all tools."""
        return list(self._tools.values())

    def get_tool_schemas(self) -> list[dict]:
        """Get tool schemas for LLM."""
        return [tool.to_dict() for tool in self._tools.values()]


class MCPClient:
    """Refactored MCP client - more testable."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.protocol = MCPProtocolHandler()
        self.tool_manager = MCPToolManager()
        self.process: Optional[subprocess.Popen] = None
        self._capabilities: dict = {}
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        if not self.config.enabled:
            return False

        try:
            env = {**subprocess.os.environ.copy(), **self.config.env}
            self.process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
            )
            return True
        except Exception:
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._reader_task:
            self._reader_task.cancel()

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()

    def list_tools(self) -> list[MCPTool]:
        """List available tools."""
        return self.tool_manager.get_all_tools()

    def get_tool_schemas(self) -> list[dict]:
        """Get tool schemas."""
        return self.tool_manager.get_tool_schemas()

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool."""
        tool = self.tool_manager.get_tool(name)
        if not tool:
            return f"ERROR: Unknown tool: {name}"

        # In real implementation, would send request to server
        return f"Called {name} with {arguments}"


class MCPManager:
    """Testable MCP server manager."""

    def __init__(self):
        self._servers: dict[str, MCPClient] = {}
        self._configs: dict[str, MCPServerConfig] = {}

    def add_server(
        self, name: str, command: str, args: list = None, env: dict = None, enabled: bool = True
    ) -> None:
        """Add an MCP server."""
        config = MCPServerConfig(
            name=name, command=command, args=args or [], env=env or {}, enabled=enabled
        )
        self._configs[name] = config
        self._servers[name] = MCPClient(config)

    async def connect_all(self) -> dict[str, bool]:
        """Connect to all servers."""
        results = {}
        for name, client in self._servers.items():
            results[name] = await client.connect()
        return results

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self._servers.values():
            await client.disconnect()

    def get_all_tools(self) -> list[dict]:
        """Get tools from all servers."""
        tools = []
        for client in self._servers.values():
            tools.extend(client.get_tool_schemas())
        return tools

    async def call_tool(self, full_name: str, arguments: dict) -> str:
        """Call a tool on a specific server."""
        parts = full_name.split("_", 1)
        if len(parts) != 2:
            return f"ERROR: Invalid tool name: {full_name}"

        server_name = parts[0]
        tool_name = parts[1]

        if server_name not in self._servers:
            return f"ERROR: Unknown server: {server_name}"

        client = self._servers[server_name]
        return await client.call_tool(tool_name, arguments)


# Testable factory functions
def create_mcp_client(
    name: str, command: str, args: list = None, env: dict = None, enabled: bool = True
) -> MCPClient:
    """Create an MCP client."""
    config = MCPServerConfig(name=name, command=command, args=args, env=env, enabled=enabled)
    return MCPClient(config)


def create_mcp_manager() -> MCPManager:
    """Create an MCP manager."""
    return MCPManager()
