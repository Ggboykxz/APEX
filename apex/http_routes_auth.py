"""Authentication routes and the auth gate.

Split out of ``apex.http_api`` so that module keeps a single
responsibility: the HTTP server core.
"""

from __future__ import annotations

import os

from aiohttp import web

from .http_helpers import _get_configured_providers

__all__ = [
    "AuthRoutesMixin",
]

_API_KEY_ENV_VARS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "DASHSCOPE_API_KEY",
    "LLAMA_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "FIREWORKS_API_KEY",
    "TOGETHER_API_KEY",
    "HF_TOKEN",
    "PERPLEXITY_API_KEY",
    "NVIDIA_API_KEY",
    "CLOUDFLARE_API_KEY",
    "COHERE_API_KEY",
    "GITHUB_TOKEN",
}


class AuthRoutesMixin:
    async def _check_auth(self, request: web.Request) -> tuple[web.Response | None, dict | None]:
        """Check authentication, returns error response if failed."""
        success, _api_key, key_info = await self.auth_middleware.authenticate(request)
        if self.require_auth and not success:
            return web.json_response(
                {"error": "Authentication required", "code": "AUTH_REQUIRED"},
                status=401,
            ), None
        return None, key_info

    async def api_auth_login(self, request: web.Request) -> web.Response:
        """Add/update provider API key."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json()
            provider = data.get("provider", "").upper().replace(" ", "_")
            api_key_value = data.get("api_key", "")

            if not provider or not api_key_value:
                return web.json_response({"error": "provider and api_key required"}, status=400)

            if provider not in self._VALID_PROVIDERS:
                return web.json_response({"error": f"Unknown provider: {provider}"}, status=400)

            env_var = f"{provider}_API_KEY"
            if provider == "HF":
                env_var = "HF_TOKEN"
            elif provider == "GITHUB":
                env_var = "GITHUB_TOKEN"

            os.environ[env_var] = api_key_value

            return web.json_response(
                {
                    "configured": True,
                    "provider": provider,
                    "env_var": env_var,
                }
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    @staticmethod
    def _provider_env_var(provider: str) -> str:
        """The environment variable holding the API key of a provider."""
        if provider == "HF":
            return "HF_TOKEN"
        if provider == "GITHUB":
            return "GITHUB_TOKEN"
        return f"{provider}_API_KEY"

    async def api_auth_logout(self, request: web.Request) -> web.Response:
        """Remove provider API key."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        try:
            data = await request.json() if request.can_read_body else {}
            provider = data.get("provider", "").upper().replace(" ", "_")

            if provider:
                env_var = self._provider_env_var(provider)
                os.environ.pop(env_var, None)
                os.environ.pop(env_var.lower(), None)
                return web.json_response({"removed": True, "env_var": env_var})

            removed = []
            for env_var in _API_KEY_ENV_VARS:
                if os.environ.pop(env_var, None):
                    removed.append(env_var)
                if os.environ.pop(env_var.lower(), None):
                    removed.append(env_var.lower())
            return web.json_response({"removed": True, "env_vars": removed})
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": str(e)}, status=500)

    async def api_auth_status(self, request: web.Request) -> web.Response:
        """Check which providers are configured."""
        auth_error, _ = await self._check_auth(request)
        if auth_error:
            return auth_error

        providers = _get_configured_providers()
        configured = [p for p in providers if p["configured"]]
        return web.json_response(
            {
                "providers": providers,
                "configured_count": len(configured),
                "any_configured": len(configured) > 0,
            }
        )
