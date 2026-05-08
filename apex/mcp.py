"""MCP (Model Context Protocol) client for APEX - Full stdio-based implementation."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
import uuid


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
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    transport: str = "stdio"


@dataclass
class MCPMessage:
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict | None = None
    result: Any = None
    error: dict | None = None


class MCPClient:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: subprocess.Popen | None = None
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._capabilities: dict = {}
        self._request_id = 0
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._notification_handlers: dict[str, Callable] = {}

    async def connect(self) -> bool:
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

            self._reader_task = asyncio.create_task(self._read_messages())

            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "clientInfo": {
                    "name": "apex",
                    "version": "0.5.0"
                }
            })

            if response:
                self._capabilities = response.get("capabilities", {})
                await self._send_notification("initialized", {})
                return True
            return False

        except Exception as e:
            print(f"MCP connection error: {e}")
            return False

    async def _read_messages(self) -> None:
        if not self.process or not self.process.stdout:
            return

        buffer = ""
        try:
            while True:
                if self.process.stdout is None:
                    break
                char = self.process.stdout.read(1)
                if not char:
                    await asyncio.sleep(0.01)
                    continue

                if char == "\n":
                    if buffer.strip():
                        await self._handle_message(buffer)
                    buffer = ""
                else:
                    buffer += char
        except Exception:
            pass

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
            msg_id = msg.get("id")

            if msg_id and str(msg_id) in self._pending_requests:
                future = self._pending_requests.pop(str(msg_id))
                if "result" in msg:
                    future.set_result(msg["result"])
                elif "error" in msg:
                    future.set_exception(Exception(msg["error"].get("message", "Error")))
            elif "method" in msg:
                method = msg["method"]
                if method in self._notification_handlers:
                    await self._notification_handlers[method](msg.get("params"))
        except Exception:
            pass

    async def _send_request(self, method: str, params: dict | None = None) -> Any:
        if not self.process or not self.process.stdin:
            return None

        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            return await asyncio.wait_for(future, timeout=30)
        except Exception:
            self._pending_requests.pop(request_id, None)
            return None

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        try:
            self.process.stdin.write(json.dumps(notification) + "\n")
            self.process.stdin.flush()
        except Exception:
            pass

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

    async def list_prompts(self) -> list[dict]:
        result = await self._send_request("prompts/list")
        return result.get("prompts", []) if result else []

    async def get_prompt(self, name: str, args: dict | None = None) -> str:
        result = await self._send_request("prompts/get", {"name": name, "arguments": args or {}})
        if result and "messages" in result:
            return self._format_content(result["messages"])
        return "ERROR: Prompt not found"

    def _format_content(self, contents: list[dict]) -> str:
        parts = []
        for item in contents:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif item.get("type") == "image":
                mime = item.get("mimeType", "unknown")
                parts.append(f"[Image: {mime}]")
            elif item.get("type") == "resource":
                parts.append(f"[Resource: {item.get('resource', {}).get('uri', 'unknown')}]")
        return "\n".join(parts)

    def get_tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"mcp_{self.config.name}_{tool.name}",
                    "description": f"[{self.config.name}] {tool.description}",
                    "parameters": tool.input_schema
                }
            }
            for tool in self._tools
        ]

    def register_notification_handler(self, method: str, handler: Callable) -> None:
        self._notification_handlers[method] = handler

    async def disconnect(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()


class MCPManager:
    def __init__(self):
        self._servers: dict[str, MCPClient] = {}
        self._configs: dict[str, MCPServerConfig] = {}

    def add_server(self, name: str, command: str, args: list[str] | None = None,
                   env: dict | None = None, enabled: bool = True) -> None:
        config = MCPServerConfig(
            name=name,
            command=command,
            args=args or [],
            env=env or {},
            enabled=enabled
        )
        self._configs[name] = config
        self._servers[name] = MCPClient(config)

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
            try:
                client_tools = client.get_tool_schemas()
                tools.extend(client_tools)
            except Exception:
                pass
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
            {
                "name": name,
                "enabled": config.enabled,
                "tools_count": len(client._tools) if client in self._servers else 0
            }
            for name, config in self._configs.items()
            for client in [self._servers.get(name)]
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
    except Exception as e:
        print(f"Failed to load MCP config: {e}")