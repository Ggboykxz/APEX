"""Contrat minimal du client TUI — endpoints utilisés par tui-frontend/src/api/client.ts.

Le client TUI (APIClient) s'appuie sur :
  - GET  /api/v1/tui-config   (config TUI : thème, keybinds, …)
  - GET  /api/v1/agents        (agents disponibles)
  - GET  /api/v1/providers     (providers configurés)
  - GET  /api/v1/stats         (stats/sessions)
  - POST /chat/stream          (flux SSE de chat)
  - GET  /api/v1/sessions      (liste des sessions)
  - WS   /ws/events            (EventBus)

Ce fichier capture ce contrat pour empêcher les régressions silencieuses
(si un endpoint change de forme ou disparaît, le TUI casse).
"""

import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from apex.agent import Agent
from apex.config import Config
from apex.http_api import APEXHTTPServer, RateLimitConfig


@pytest.fixture
def tui_server(tmp_path):
    """Serveur équivalent à celui du TUI (sans auth, rate limits larges)."""
    config = Config(config_path=tmp_path / "cfg.json")
    config._data["model"] = "gpt-4o-mini"
    agent = Agent(config=config)

    server = APEXHTTPServer(host="127.0.0.1", port=0)
    server.agent = agent
    return server


async def test_tui_contract_endpoints(tui_server):
    """Les endpoints du client TUI répondent 200 avec la forme attendue."""
    async with TestClient(TestServer(tui_server.app)) as client:
        # 1. tui-config — forme attendue par le TUI
        r = await client.get("/api/v1/tui-config")
        assert r.status == 200, await r.text()
        data = await r.json()
        for key in ("theme", "keybinds", "scroll_speed"):
            assert key in data, f"tui-config: clé {key} manquante"

        # 2. stats
        r = await client.get("/api/v1/stats")
        assert r.status == 200, await r.text()
        stats = await r.json()
        assert "sessions_count" in stats
        assert "current_model" in stats

        # 3. agents — la route existe (le contenu peut varier)
        r = await client.get("/api/v1/agents")
        assert r.status == 200, await r.text()

        # 4. providers
        r = await client.get("/api/v1/providers")
        assert r.status == 200, await r.text()

        # 5. sessions (liste)
        r = await client.get("/api/v1/sessions")
        assert r.status == 200, await r.text()

        # 6. chat/stream — la route répond (POST)
        r = await client.post("/chat/stream", json={"message": "ping"})
        assert r.status == 200, await r.text()

        # 7. ws/events — handshake WebSocket accepté
        ws = await client.ws_connect("/ws/events")
        assert ws.closed is False
        await ws.close()


async def test_chat_stream_emits_typed_events(tui_server):
    """Le flux SSE de chat émet des événements typés (chunk/usage/rate_limit)."""
    async with TestClient(TestServer(tui_server.app)) as client:
        async with client.post("/chat/stream", json={"message": "hi"}) as resp:
            assert resp.status == 200

            # En l'absence de clé LLM, le stream émet au moins un événement
            # (chunk d'erreur ou usage) — mais le canal n'est jamais vide ni
            # mort : on vérifie qu'il produit des lignes "data:".
            buffer = []
            async for line in resp.content:
                if line.startswith(b"data:"):
                    buffer.append(line)
                    if len(buffer) >= 2:
                        break

            assert buffer, "le stream /chat/stream n'a émis aucun événement"
            first = json.loads(buffer[0][5:])
            assert "chunk" in first or "usage" in first
