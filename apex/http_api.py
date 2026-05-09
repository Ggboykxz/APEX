"""HTTP/SSE API server for APEX - headless agent workflows."""

import json
import asyncio

from aiohttp import web

from .agent import Agent


class APEXHTTPServer:
    """HTTP server with SSE support for APEX."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self.agent = Agent()
        self.runner = None

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/health", self.health)
        self.app.router.add_post("/chat", self.chat)
        self.app.router.add_get("/stream", self.stream)
        self.app.router.add_post("/chat/stream", self.chat_stream)
        self.app.router.add_get("/models", self.list_models)
        self.app.router.add_post("/session/save", self.session_save)
        self.app.router.add_post("/session/load", self.session_load)
        self.app.router.add_get("/metrics", self.metrics)

    async def index(self, request: web.Request) -> web.Response:
        """Serve API documentation."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>APEX API</title></head>
        <body>
        <h1>APEX Agent API</h1>
        <ul>
            <li>POST /chat - Send a chat message</li>
            <li>GET /stream - SSE stream endpoint</li>
            <li>POST /chat/stream - Chat with streaming</li>
            <li>GET /models - List available models</li>
            <li>POST /session/save - Save session</li>
            <li>POST /session/load - Load session</li>
            <li>GET /metrics - Get usage metrics</li>
        </ul>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    async def health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "ok", "agent": self.agent.model})

    async def chat(self, request: web.Request) -> web.Response:
        """Standard chat endpoint."""
        try:
            data = await request.json()
            message = data.get("message", "")
            model = data.get("model")
            
            if model:
                self.agent.switch_model(model)
            
            response = self.agent.chat(message)
            return web.json_response({
                "response": response,
                "model": self.agent.model,
                "usage": self.agent.usage
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def stream(self, request: web.Request) -> web.Response:
        """SSE stream endpoint."""
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
            
            await response.write(f"data: {json.dumps({'usage': self.agent.usage})}\n\n".encode())
            return response
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def list_models(self, request: web.Request) -> web.Response:
        """List available models."""
        from .config import MODELS
        models = [
            {"alias": alias, "model": model_id}
            for alias, model_id in MODELS.items()
        ]
        return web.json_response({"models": models})

    async def session_save(self, request: web.Request) -> web.Response:
        """Save current session."""
        from .session import SessionManager
        try:
            data = await request.json()
            name = data.get("name", "http_session")
            sm = SessionManager()
            path = sm.save(self.agent, name)
            return web.json_response({"saved": str(path)})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def session_load(self, request: web.Request) -> web.Response:
        """Load a session."""
        from .session import SessionManager
        try:
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"error": "name required"}, status=400)
            
            sm = SessionManager()
            session = sm.load(name)
            if session:
                self.agent.history = session.get("history", [])
                return web.json_response({"loaded": name})
            return web.json_response({"error": "session not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def metrics(self, request: web.Request) -> web.Response:
        """Get usage metrics."""
        usage = self.agent.usage
        return web.json_response({
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": self.agent.model,
        })

    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self.runner = runner
        print(f"APEX HTTP API running at http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
        if self.runner:
            await self.runner.cleanup()


async def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the APEX HTTP server."""
    server = APEXHTTPServer(host, port)
    await server.start()
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    asyncio.run(run_server(port=port))