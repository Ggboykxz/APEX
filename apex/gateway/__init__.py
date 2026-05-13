"""APEX Gateway — AI model proxy with auth, rate limiting, and usage tracking."""

from .config import GatewayConfig

__all__ = ["GatewayConfig"]


def __getattr__(name):
    if name == "GatewayServer":
        from .server import GatewayServer as _s
        return _s
    raise AttributeError(f"module apex.gateway has no attribute {name!r}")
