"""Gateway configuration — tiers, limits, defaults."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TierConfig:
    daily_requests: int
    daily_tokens: int
    rate_per_minute: int
    models: list[str]


DEFAULT_TIERS: dict[str, TierConfig] = {
    "free": TierConfig(
        daily_requests=50,
        daily_tokens=500_000,
        rate_per_minute=10,
        models=[
            "free-or-qwen3-235b",
            "free-or-qwen3-coder",
            "free-or-qwen3-next-80b",
            "free-or-nemotron-super",
            "free-or-nemotron-nano",
            "free-or-gemma-4-26b",
            "free-or-gemma-4-31b",
            "free-or-ring-2.6",
            "free-or-deepseek-v3.2",
            "free-or-deepseek-r1",
            "free-or-llama-3.3-70b",
            "free-or-minimax-m2.5",
            "free-or-glm-4.6",
            "free-or-poolside-laguna-m",
            "free-or-poolside-laguna-xs",
            "free-or-gpt-oss-120b",
            "free-or-gpt-oss-20b",
            "free-or-liquid-thinking",
            "free-or-router",
        ],
    ),
    "pro": TierConfig(
        daily_requests=500,
        daily_tokens=5_000_000,
        rate_per_minute=60,
        models=[
            "pro-glm-5",
            "pro-glm-5.1",
            "pro-kimi-k2.5",
            "pro-kimi-k2.6",
            "pro-minimax-m2.5",
            "pro-minimax-m2.7",
            "pro-qwen3.5-plus",
            "pro-qwen3.6-plus",
            "pro-deepseek-v4-pro",
            "pro-deepseek-v4-flash",
        ],
    ),
    "unlimited": TierConfig(
        daily_requests=999999,
        daily_tokens=100_000_000,
        rate_per_minute=300,
        models=["*"],
    ),
}


@dataclass
class GatewayConfig:
    host: str = "127.0.0.1"
    port: int = 9090
    db_path: Path = Path.home() / ".apex" / "gateway.db"
    data_dir: Path = Path.home() / ".apex" / "gateway"
    tiers: dict[str, TierConfig] = field(default_factory=lambda: DEFAULT_TIERS)
    upstream_base: str = "https://openrouter.ai/api/v1"
    upstream_api_key: Optional[str] = None
    default_tier: str = "free"
    admin_key: Optional[str] = None
    register_enabled: bool = True

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        import os
        c = cls()
        c.host = os.environ.get("APEX_GATEWAY_HOST", c.host)
        c.port = int(os.environ.get("APEX_GATEWAY_PORT", str(c.port)))
        c.upstream_api_key = os.environ.get("APEX_GATEWAY_KEY") or os.environ.get("OPENROUTER_API_KEY")
        c.admin_key = os.environ.get("APEX_GATEWAY_ADMIN_KEY")
        return c
