"""
APEX Server - HTTP/WebSocket server for multi-client connections.
Can be run with Bun/Node.js or standalone Python.
"""

import json
import asyncio
from datetime import datetime
import uuid


class APEXClient:
    """Represents a connected client."""

    def __init__(self, client_id: str, name: str = "anonymous"):
        self.id = client_id
        self.name = name
        self.connected_at = datetime.now().isoformat()
        self.last_activity = datetime.now().isoformat()
        self.model = "gpt-4o-mini"
        self.agent_mode = "build"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "model": self.model,
            "agent_mode": self.agent_mode
        }


class APEXServer:
    """Multi-client APEX server with WebSocket support."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.clients: dict[str, APEXClient] = {}
        self._agent = None
        self._runner = None
        self._websockets = set()

    def set_agent(self, agent):
        """Set the agent instance for this server."""
        self._agent = agent

    async def handle_websocket(self, ws, path: str = "/ws"):
        """Handle WebSocket connections."""
        client_id = str(uuid.uuid4())
        client = APEXClient(client_id)
        self.clients[client_id] = client
        self._websockets.add(ws)

        try:
            await ws.send_json({
                "type": "welcome",
                "client_id": client_id,
                "message": "Connected to APEX server"
            })

            async for msg in ws:
                if isinstance(msg, str):
                    await self._handle_message(client_id, msg, ws)

        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.clients.pop(client_id, None)
            self._websockets.discard(ws)

    async def _handle_message(self, client_id: str, msg: str, ws):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(msg)
            msg_type = data.get("type", "chat")

            if msg_type == "chat":
                response = await self._process_chat(client_id, data)
                await ws.send_json(response)

            elif msg_type == "switch_model":
                model = data.get("model")
                if self._agent:
                    self._agent.switch_model(model)
                self.clients[client_id].model = model
                await ws.send_json({"type": "success", "message": f"Model: {model}"})

            elif msg_type == "switch_agent":
                agent_name = data.get("agent")
                if self._agent:
                    self._agent.switch_agent(agent_name)
                self.clients[client_id].agent_mode = agent_name
                await ws.send_json({"type": "success", "message": f"Agent: {agent_name}"})

            elif msg_type == "execute":
                tool = data.get("tool")
                args = data.get("args", {})
                result = await self._execute_tool(tool, args)
                await ws.send_json({"type": "tool_result", "tool": tool, "result": result})

            self.clients[client_id].last_activity = datetime.now().isoformat()

        except json.JSONDecodeError:
            await ws.send_json({"type": "error", "message": "Invalid JSON"})
        except Exception as e:
            await ws.send_json({"type": "error", "message": str(e)})

    async def _process_chat(self, client_id: str, data: dict) -> dict:
        """Process chat message."""
        message = data.get("message", "")
        stream = data.get("stream", False)

        if self._agent:
            if stream:
                return {"type": "chat_stream", "message": "Use /stream endpoint for SSE"}
            else:
                response = self._agent.chat(message)
                return {"type": "chat", "response": response, "usage": self._agent.usage}

        return {"type": "error", "message": "Agent not initialized"}

    async def _execute_tool(self, tool: str, args: dict) -> str:
        """Execute a tool."""
        if not self._agent:
            return "ERROR: Agent not initialized"

        from .tools import TOOL_SCHEMAS

        tool_map = {t["function"]["name"]: t for t in TOOL_SCHEMAS}
        if tool not in tool_map:
            return f"ERROR: Unknown tool {tool}"

        return f"Tool {tool} called with {args}"

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for ws in self._websockets:
            try:
                await ws.send_json(message)
            except:
                pass

    async def get_status(self) -> dict:
        """Get server status."""
        return {
            "host": self.host,
            "port": self.port,
            "clients": len(self.clients),
            "client_list": [c.to_dict() for c in self.clients.values()],
            "agent_model": self._agent.model if self._agent else None,
            "agent_mode": self._agent.current_agent if self._agent else None
        }


async def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the APEX server."""
    from aiohttp import web

    server = APEXServer(host, port)

    async def index(request):
        return web.Response(text="""<!DOCTYPE html>
<html>
<head>
    <title>APEX Server</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        .client { background: #f0f0f0; padding: 10px; margin: 5px; }
    </style>
</head>
<body>
    <h1>APEX Multi-Client Server</h1>
    <p>WebSocket: ws://host:port/ws</p>
    <p>REST API: POST /chat, GET /status, POST /execute</p>
</body>
</html>""", content_type="text/html")

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await server.handle_websocket(ws)
        return ws

    async def status_handler(request):
        return web.json_response(await server.get_status())

    async def chat_handler(request):
        data = await request.json()
        message = data.get("message", "")

        if server._agent:
            response = server._agent.chat(message)
            return web.json_response({
                "response": response,
                "usage": server._agent.usage
            })

        return web.json_response({"error": "Agent not initialized"}, status=500)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/status", status_handler)
    app.router.add_post("/chat", chat_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"APEX Server running at http://{host}:{port}")
    print(f"WebSocket: ws://{host}:{port}/ws")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_server())