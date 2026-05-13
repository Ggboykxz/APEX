"""Request routing — proxies to OpenRouter with rate limits and usage tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from .auth import AuthManager
from .config import GatewayConfig, TierConfig

if TYPE_CHECKING:
    import aiohttp
    from aiohttp import web

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str, max_per_minute: int) -> bool:
        now = time.time()
        if key not in self._buckets:
            self._buckets[key] = []
        self._buckets[key] = [t for t in self._buckets[key] if now - t < 60]
        if len(self._buckets[key]) >= max_per_minute:
            return False
        self._buckets[key].append(now)
        return True

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str, max_per_minute: int) -> bool:
        now = time.time()
        if key not in self._buckets:
            self._buckets[key] = []
        self._buckets[key] = [t for t in self._buckets[key] if now - t < 60]
        if len(self._buckets[key]) >= max_per_minute:
            return False
        self._buckets[key].append(now)
        return True


class RequestRouter:
    def __init__(self, config: GatewayConfig, auth: AuthManager):
        self.config = config
        self.auth = auth
        self.rate_limiter = RateLimiter()
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp as _ahttp
            self._session = _ahttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=_ahttp.ClientTimeout(total=120),
            )
        return self._session

    def _get_tier(self, tier_name: str) -> TierConfig:
        return self.config.tiers.get(tier_name, self.config.tiers["free"])

    def _model_allowed(self, model: str, tier: TierConfig) -> bool:
        if "*" in tier.models:
            return True
        return model in tier.models

    async def proxy_request(self, request: web.Request) -> web.StreamResponse:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.json_response({"error": "Missing or invalid Authorization header"}, status=401)

        api_key = auth_header[7:]
        key_info = self.auth.validate_key(api_key)
        if not key_info:
            return web.json_response({"error": "Invalid or revoked API key"}, status=401)

        body = await request.json()
        model = body.get("model", "")
        tier = self._get_tier(key_info["tier"])

        if not self._model_allowed(model, tier):
            return web.json_response(
                {"error": f"Model '{model}' not available in '{key_info['tier']}' tier"},
                status=403,
            )

        rate_key = f"{key_info['key_id']}:{key_info['tier']}"
        if not self.rate_limiter.check(rate_key, tier.rate_per_minute):
            return web.json_response(
                {"error": f"Rate limit exceeded ({tier.rate_per_minute}/minute)"},
                status=429,
            )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_req, day_tok = self.auth.get_or_create_day_usage(key_info["key_id"], today)

        if day_req >= tier.daily_requests:
            return web.json_response(
                {"error": f"Daily request limit reached ({tier.daily_requests})"},
                status=429,
            )

        response = await self._proxy_to_upstream(model, body, tier, rate_key)
        return response

    async def _proxy_to_upstream(self, model: str, body: dict, tier: TierConfig, rate_key: str) -> web.StreamResponse:
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.config.upstream_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with session.post(
                f"{self.config.upstream_base}/chat/completions",
                json=body,
                headers=headers,
            ) as upstream_resp:
                upstream_data = await upstream_resp.json()
                if upstream_resp.status != 200:
                    return web.json_response(upstream_data, status=upstream_resp.status)

                usage = upstream_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens

                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                key_id = rate_key.split(":")[0]
                self.auth.record_usage(key_id, today, requests=1, tokens=total_tokens)

                upstream_data["usage"]["apex_gateway"] = {
                    "tier": tier,
                    "requests_today": 1,
                }

                return web.json_response(upstream_data)

        except asyncio.TimeoutError:
            return web.json_response({"error": "Upstream request timed out"}, status=504)
        except aiohttp.ClientError as e:
            return web.json_response({"error": f"Upstream error: {str(e)}"}, status=502)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def status(self, key_info: dict) -> dict:
        tier = self._get_tier(key_info["tier"])
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        req, tok = self.auth.get_or_create_day_usage(key_info["key_id"], today)
        return {
            "tier": key_info["tier"],
            "requests_today": req,
            "requests_limit": tier.daily_requests,
            "tokens_today": tok,
            "tokens_limit": tier.daily_tokens,
            "rate_per_minute": tier.rate_per_minute,
            "monthly_value_usd": tier.monthly_value_usd,
            "max_concurrent": tier.max_concurrent,
        }
