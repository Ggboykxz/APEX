"""Chat and streaming routes.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from aiohttp import WSMsgType, web

from .billing import TokenUsage, UsageContext, billing_manager
from .http_helpers import logger

__all__ = [
    "ChatRoutesMixin",
]


class ChatRoutesMixin:
    @staticmethod
    def _rate_limit_payload(result: Any) -> dict | None:
        """The rate-limit counters to send back to the client."""
        if not result:
            return None
        return {
            "remaining_minute": result.remaining_minute,
            "remaining_hour": result.remaining_hour,
            "remaining_day": result.remaining_day,
        }

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
            self._record_chat_usage(key_info)

            return web.json_response(
                {
                    "response": response,
                    "model": self.agent.model,
                    "usage": self.agent.usage,
                    "rate_limit": self._rate_limit_payload(result),
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Chat error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def stream(self, request: web.Request) -> web.Response:
        """SSE stream endpoint."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        response = await self._prepare_sse(request, keep_alive=True)

        async for chunk in self.agent.chat_streaming("ping"):
            await self._write_sse(response, {"chunk": chunk})

        return response

    @staticmethod
    async def _write_sse(response: web.StreamResponse, payload: dict) -> None:
        """Write one server-sent-event frame."""
        await response.write(f"data: {json.dumps(payload)}\n\n".encode())

    def _record_chat_usage(self, key_info: dict | None) -> dict:
        """Record the usage of a turn and return the usage counters."""
        usage = self.agent.usage or {}
        if key_info:
            billing_manager.record_usage(
                user_id=key_info["workspace_id"],
                model=self.agent.model,
                usage=TokenUsage(
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                ),
                context=UsageContext(workspace_id=key_info["workspace_id"]),
            )
        return usage

    @staticmethod
    async def _prepare_sse(request: web.Request, keep_alive: bool = False) -> web.StreamResponse:
        """Prepare a server-sent-event response."""
        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        if keep_alive:
            response.headers["Connection"] = "keep-alive"
        await response.prepare(request)
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

            response = await self._prepare_sse(request)

            async for chunk in self.agent.chat_streaming(message):
                await self._write_sse(response, {"chunk": chunk})

            await self.event_bus.publish(
                "chat_complete",
                {
                    "model": self.agent.model,
                    "usage": self.agent.usage or {},
                },
            )

            usage = self._record_chat_usage(key_info)
            await self._write_sse(response, {"usage": usage})
            if result:
                rate_limit_data = {"rate_limit": {"remaining_minute": result.remaining_minute}}
                await self._write_sse(response, rate_limit_data)
            return response
        except Exception as e:  # noqa: BLE001
            logger.error(f"Stream error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def _connected_payload(self) -> dict:
        """The initial state sent to a freshly connected WebSocket client."""
        return {
            "event": "connected",
            "data": {
                "version": __import__("apex", fromlist=["__version__"]).__version__,
                "model": self.agent.model,
                "agent": self.agent.current_agent,
                "cwd": str(self.agent.cwd),
            },
            "timestamp": time.time(),
        }

    def _state_payload(self) -> dict:
        """The current agent state, sent on demand by the TUI."""
        return {
            "event": "state",
            "data": {
                "model": self.agent.model,
                "agent": self.agent.current_agent,
                "history_length": len(self.agent.history) if hasattr(self.agent, "history") else 0,
                "undo_available": self.undo_manager.can_undo(),
                "redo_available": self.undo_manager.can_redo(),
            },
            "timestamp": time.time(),
        }

    async def _handle_ws_command(self, ws: web.WebSocketResponse, data: str) -> None:
        """Answer one RPC-like command sent by the TUI."""
        try:
            cmd = json.loads(data)
        except json.JSONDecodeError:
            return
        method = cmd.get("method")
        if method == "ping":
            await ws.send_json({"event": "pong", "data": {}, "timestamp": time.time()})
        elif method == "state":
            await ws.send_json(self._state_payload())

    async def ws_events(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket event stream for real-time TUI sync."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.event_bus.subscribe(ws)
        try:
            # Send initial state
            await ws.send_json(self._connected_payload())
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_ws_command(ws, msg.data)
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        except Exception:  # noqa: BLE001, S110
            pass
        finally:
            self.event_bus.unsubscribe(ws)
        return ws

    async def api_global_event(self, request: web.Request) -> web.Response:
        """SSE event stream (OpenCode /global/event compat)."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error
        response = await self._prepare_sse(request, keep_alive=True)
        self._sse_clients.append(response)
        try:
            from apex import __version__

            await response.write(
                f'data: {{"event": "connected", "version": "{__version__}"}}\n\n'.encode()
            )
            while True:
                await asyncio.sleep(30)
                await response.write(b": keepalive\n\n")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            logger.debug("SSE client disconnected")
        finally:
            try:
                self._sse_clients.remove(response)
            except ValueError:
                logger.debug("SSE client already removed from the subscriber list")
        return response
