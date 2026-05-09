"""Configuration system for APEX - models, API keys, and user config."""

import json
import os
from pathlib import Path
from typing import Any

MODELS: dict[str, str] = {
    # Anthropic Claude (2024-2026)
    "claude-3.5-haiku": "anthropic/claude-3-5-haiku-20241022",
    "claude-3.5-sonnet": "anthropic/claude-3-5-sonnet-20241022",
    "claude-sonnet-4": "anthropic/claude-sonnet-4-20250514",
    "claude-opus-4": "anthropic/claude-opus-4-20250514",
    "claude-4-sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-4-opus": "anthropic/claude-opus-4-20250514",
    "claude-4.5-sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-4.6-opus": "anthropic/claude-opus-4-20250514",
    "claude-4.7-opus": "anthropic/claude-opus-4-20250514",

    # OpenAI GPT (2020-2025)
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "o1": "openai/o1",
    "o1-mini": "openai/o1-mini",
    "o3": "openai/o3",
    "o3-mini": "openai/o3-mini",
    "o4-mini": "openai/o4-mini",

    # Google DeepMind Gemini (2022-2025)
    "gemini-1.5-flash": "google/gemini-1.5-flash",
    "gemini-1.5-pro": "google/gemini-1.5-pro",
    "gemini-2.0-flash": "google/gemini-2.0-flash-exp",
    "gemini-2.0-flash-lite": "google/gemini-2.0-flash-lite",
    "gemini-2.0-pro": "google/gemini-2.0-pro",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",

    # xAI Grok (2023-2025)
    "grok-1": "xai/grok-1",
    "grok-2": "xai/grok-2",
    "grok-3": "xai/grok-3",
    "grok-3-beta": "xai/grok-3-beta",
    "grok-4": "xai/grok-4",

    # Amazon Nova (2024-2025)
    "nova-micro": "amazon/nova-micro-v1",
    "nova-lite": "amazon/nova-lite-v1",
    "nova-pro": "amazon/nova-pro-v1",
    "nova-premier": "amazon/nova-premier-v1",

    # Alibaba Qwen (2024-2025)
    "qwen2-7b": "qwen/qwen2-7b",
    "qwen2-72b": "qwen/qwen2-72b",
    "qwen2.5-7b": "qwen/qwen2.5-7b",
    "qwen2.5-72b": "qwen/qwen2.5-72b",
    "qwen2.5-coder-7b": "qwen/qwen2.5-coder-7b",
    "qwen3-8b": "qwen/qwen3-8b",
    "qwen3-72b": "qwen/qwen3-72b",
    "qwen3-235b": "qwen/qwen3-235b",

    # Meta Llama (2023-2025)
    "llama-3-8b": "meta/llama-3-8b",
    "llama-3-70b": "meta/llama-3-70b",
    "llama-3.1-8b": "meta/llama-3.1-8b",
    "llama-3.1-70b": "meta/llama-3.1-70b",
    "llama-3.1-405b": "meta/llama-3.1-405b",
    "llama-4-scout": "meta/llama-4-scout",
    "llama-4-maverick": "meta/llama-4-maverick",

    # Mistral AI (2023-2025)
    "mistral-7b": "mistral/mistral-7b-v0.1",
    "mixtral-8x7b": "mistral/mixtral-8x7b-v0.1",
    "mixtral-8x22b": "mistral/mixtral-8x22b-v0.1",
    "mistral-large-2": "mistral/mistral-large-2",
    "mistral-large-3": "mistral/mistral-large-3",
    "mistral-small-3": "mistral/mistral-small-3",
    "mistral-small-3.0": "mistral/mistral-small-3.0",
    "codestral": "mistral/codestral-latest",
    "devstral": "mistral/devstral-latest",
    "ministral-14b": "mistral/ministral-14b",
    "ministral-8b": "mistral/ministral-8b",

    # DeepSeek (2024-2025)
    "deepseek-chat": "deepseek/deepseek-chat",
    "deepseek-coder": "deepseek/deepseek-coder",
    "deepseek-v3": "deepseek/deepseek-v3",
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
    "deepseek-r1": "deepseek/deepseek-reasoner",
    "deepseek-r1-0528": "deepseek/deepseek-reasoner",

    # Microsoft Phi (2023-2024)
    "phi-3-mini": "microsoft/phi-3-mini-128k",
    "phi-3-small": "microsoft/phi-3-small-128k",
    "phi-4-mini": "microsoft/phi-4-mini",

    # Cohere (2023-2024)
    "command-r": "cohere/command-r",
    "command-r-plus": "cohere/command-r-plus-08-2024",
    "command-a": "cohere/command-a",

    # Google Gemma (2024)
    "gemma-2b": "google/gemma-2b",
    "gemma-7b": "google/gemma-7b",
    "gemma-2-9b": "google/gemma-2-9b",
    "gemma-2-27b": "google/gemma-2-27b",

    # Groq hosted models
    "llama-groq-3.3-70b": "groq/llama-3.3-70b-versatile",
    "mixtral-groq-8x7b": "groq/mixtral-8x7b-32768",

    # Ollama local models
    "ollama-llama3": "ollama/llama3",
    "ollama-llama3.1": "ollama/llama3.1",
    "ollama-llama3.2": "ollama/llama3.2",
    "ollama-codellama": "ollama/codellama",
    "ollama-deepseek-coder": "ollama/deepseek-coder",
    "ollama-qwen2.5": "ollama/qwen2.5",
    "ollama-mistral": "ollama/mistral",
    "ollama-gemma2": "ollama/gemma2",

    # OpenRouter (paid, use OPENROUTER_API_KEY)
    "or-gpt4o": "openrouter/openai/gpt-4o",
    "or-gpt4o-mini": "openrouter/openai/gpt-4o-mini",
    "or-claude": "openrouter/anthropic/claude-3.5-sonnet",
    "or-deepseek": "openrouter/deepseek/deepseek-chat",
    "or-llama": "openrouter/meta-llama/llama-3.3-70b-versatile",

    # OpenRouter FREE models (no credit card required)
    "free-router": "openrouter/free",
    "deepseek-r1-free": "deepseek/deepseek-reasoner:free",
    "llama-3.2-3b-free": "meta-llama/llama-3.2-3b-instruct:free",
    "llama-3.1-8b-free": "meta-llama/llama-3.1-8b-instruct:free",
    "qwen-2.5-7b-free": "qwen/qwen2.5-7b-instruct:free",
}

MODEL_PROVIDERS: dict[str, str] = {
    # Anthropic
    "claude-3.5-haiku": "ANTHROPIC_API_KEY",
    "claude-3.5-sonnet": "ANTHROPIC_API_KEY",
    "claude-sonnet-4": "ANTHROPIC_API_KEY",
    "claude-opus-4": "ANTHROPIC_API_KEY",
    "claude-4-sonnet": "ANTHROPIC_API_KEY",
    "claude-4-opus": "ANTHROPIC_API_KEY",
    "claude-4.5-sonnet": "ANTHROPIC_API_KEY",
    "claude-4.6-opus": "ANTHROPIC_API_KEY",
    "claude-4.7-opus": "ANTHROPIC_API_KEY",

    # OpenAI
    "gpt-4o": "OPENAI_API_KEY",
    "gpt-4o-mini": "OPENAI_API_KEY",
    "gpt-4-turbo": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "o1-mini": "OPENAI_API_KEY",
    "o3": "OPENAI_API_KEY",
    "o3-mini": "OPENAI_API_KEY",
    "o4-mini": "OPENAI_API_KEY",

    # Google DeepMind
    "gemini-1.5-flash": "GEMINI_API_KEY",
    "gemini-1.5-pro": "GEMINI_API_KEY",
    "gemini-2.0-flash": "GEMINI_API_KEY",
    "gemini-2.0-flash-lite": "GEMINI_API_KEY",
    "gemini-2.0-pro": "GEMINI_API_KEY",
    "gemini-2.5-flash": "GEMINI_API_KEY",
    "gemini-2.5-pro": "GEMINI_API_KEY",

    # xAI Grok
    "grok-1": "XAI_API_KEY",
    "grok-2": "XAI_API_KEY",
    "grok-3": "XAI_API_KEY",
    "grok-3-beta": "XAI_API_KEY",
    "grok-4": "XAI_API_KEY",

    # Amazon Nova
    "nova-micro": "AWS_ACCESS_KEY",
    "nova-lite": "AWS_ACCESS_KEY",
    "nova-pro": "AWS_ACCESS_KEY",
    "nova-premier": "AWS_ACCESS_KEY",

    # Alibaba Qwen
    "qwen2-7b": "ALIBABA_API_KEY",
    "qwen2-72b": "ALIBABA_API_KEY",
    "qwen2.5-7b": "ALIBABA_API_KEY",
    "qwen2.5-72b": "ALIBABA_API_KEY",
    "qwen2.5-coder-7b": "ALIBABA_API_KEY",
    "qwen3-8b": "ALIBABA_API_KEY",
    "qwen3-72b": "ALIBABA_API_KEY",
    "qwen3-235b": "ALIBABA_API_KEY",

    # Meta Llama
    "llama-3-8b": "META_API_KEY",
    "llama-3-70b": "META_API_KEY",
    "llama-3.1-8b": "META_API_KEY",
    "llama-3.1-70b": "META_API_KEY",
    "llama-3.1-405b": "META_API_KEY",
    "llama-4-scout": "META_API_KEY",
    "llama-4-maverick": "META_API_KEY",

    # Mistral AI
    "mistral-7b": "MISTRAL_API_KEY",
    "mixtral-8x7b": "MISTRAL_API_KEY",
    "mixtral-8x22b": "MISTRAL_API_KEY",
    "mistral-large-2": "MISTRAL_API_KEY",
    "mistral-large-3": "MISTRAL_API_KEY",
    "mistral-small-3": "MISTRAL_API_KEY",
    "mistral-small-3.0": "MISTRAL_API_KEY",
    "codestral": "MISTRAL_API_KEY",
    "devstral": "MISTRAL_API_KEY",
    "ministral-14b": "MISTRAL_API_KEY",
    "ministral-8b": "MISTRAL_API_KEY",

    # DeepSeek
    "deepseek-chat": "DEEPSEEK_API_KEY",
    "deepseek-coder": "DEEPSEEK_API_KEY",
    "deepseek-v3": "DEEPSEEK_API_KEY",
    "deepseek-v3.2": "DEEPSEEK_API_KEY",
    "deepseek-r1": "DEEPSEEK_API_KEY",
    "deepseek-r1-0528": "DEEPSEEK_API_KEY",

    # Microsoft Phi
    "phi-3-mini": "MICROSOFT_API_KEY",
    "phi-3-small": "MICROSOFT_API_KEY",
    "phi-4-mini": "MICROSOFT_API_KEY",

    # Cohere
    "command-r": "COHERE_API_KEY",
    "command-r-plus": "COHERE_API_KEY",
    "command-a": "COHERE_API_KEY",

    # Google Gemma
    "gemma-2b": "GEMINI_API_KEY",
    "gemma-7b": "GEMINI_API_KEY",
    "gemma-2-9b": "GEMINI_API_KEY",
    "gemma-2-27b": "GEMINI_API_KEY",

    # Groq
    "llama-groq-3.3-70b": "GROQ_API_KEY",
    "mixtral-groq-8x7b": "GROQ_API_KEY",

    # Ollama (local, no API key needed)
    "ollama-llama3": None,
    "ollama-llama3.1": None,
    "ollama-llama3.2": None,
    "ollama-codellama": None,
    "ollama-deepseek-coder": None,
    "ollama-qwen2.5": None,
    "ollama-mistral": None,
    "ollama-gemma2": None,

    # OpenRouter (use OPENROUTER_API_KEY)
    "or-gpt4o": "OPENROUTER_API_KEY",
    "or-gpt4o-mini": "OPENROUTER_API_KEY",
    "or-claude": "OPENROUTER_API_KEY",
    "or-deepseek": "OPENROUTER_API_KEY",
    "or-llama": "OPENROUTER_API_KEY",

    # OpenRouter FREE (don't support tools)
    "free-router": "OPENROUTER_API_KEY",
    "deepseek-r1-free": "OPENROUTER_API_KEY",
    "llama-3.2-3b-free": "OPENROUTER_API_KEY",
    "llama-3.1-8b-free": "OPENROUTER_API_KEY",
    "qwen-2.5-7b-free": "OPENROUTER_API_KEY",
}

DEFAULT_MODEL = "or-gpt4o-mini"

SYSTEM_PROMPT = """You are APEX, an expert coding agent built in Gabon for the world.

Your role is to act as a senior, opinionated developer who delivers complete, production-ready code.
Never truncate code. Never use placeholders. Never leave TODOs in committed code.

Key behaviors:
- ALWAYS read files before editing them
- ALWAYS verify your work by running tests, checking syntax, or running the code
- Be language-agnostic (Python, JavaScript, Rust, Go, etc.)
- Keep explanations concise — code speaks first
- Return ERROR strings when tools fail, never silently continue

You have access to tools: read_file, write_file, edit_file, run_command, list_files, search_in_files, delete_file, create_directory.

Output complete solutions. When asked to write code, write the FULL code without truncation."""


class Config:
    def __init__(self, config_path: Path | None = None):
        self._apex_dir = Path.home() / ".apex"
        self._config_file = config_path or self._apex_dir / "config.json"
        self._env_file = self._apex_dir / ".env"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._apex_dir.mkdir(parents=True, exist_ok=True)
        if self._config_file.exists():
            try:
                with open(self._config_file) as f:
                    self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = {}
        self._load_env()

    def _load_env(self) -> None:
        env_paths = [self._env_file, Path.cwd() / ".env", Path.home() / ".env"]
        for env_path in env_paths:
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" in line:
                                key, value = line.split("=", 1)
                                os.environ[key.strip()] = value.strip()
                break

    def save(self) -> None:
        self._apex_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def model(self) -> str:
        return self._data.get("model", DEFAULT_MODEL)

    @model.setter
    def model(self, value: str) -> None:
        self._data["model"] = value
        self.save()

    @property
    def cwd(self) -> Path:
        cwd = self._data.get("cwd", str(Path.cwd()))
        return Path(cwd).expanduser().resolve()

    @cwd.setter
    def cwd(self, value: Path) -> None:
        self._data["cwd"] = str(value)
        self.save()

    @property
    def theme(self) -> str:
        return self._data.get("theme", "monokai")

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self.save()

    @property
    def max_tool_rounds(self) -> int:
        return self._data.get("max_tool_rounds", 20)

    @max_tool_rounds.setter
    def max_tool_rounds(self, value: int) -> None:
        self._data["max_tool_rounds"] = value
        self.save()

    @property
    def auto_commit(self) -> bool:
        return self._data.get("auto_commit", False)

    @auto_commit.setter
    def auto_commit(self, value: bool) -> None:
        self._data["auto_commit"] = value
        self.save()

    @property
    def auto_model(self) -> bool:
        return self._data.get("auto_model", False)

    @auto_model.setter
    def auto_model(self, value: bool) -> None:
        self._data["auto_model"] = value
        self.save()

    @property
    def reasoning_effort(self) -> str:
        return self._data.get("reasoning_effort", "off")

    @reasoning_effort.setter
    def reasoning_effort(self, value: str) -> None:
        if value not in ("off", "high", "max"):
            value = "off"
        self._data["reasoning_effort"] = value
        self.save()

    @property
    def agent_mode(self) -> str:
        return self._data.get("agent_mode", "agent")

    @agent_mode.setter
    def agent_mode(self, value: str) -> None:
        if value not in ("plan", "agent", "yolo"):
            value = "agent"
        self._data["agent_mode"] = value
        self.save()

    @property
    def context_max_tokens(self) -> int:
        return self._data.get("context_max_tokens", 1000000)

    @context_max_tokens.setter
    def context_max_tokens(self, value: int) -> None:
        self._data["context_max_tokens"] = value
        self.save()

    @property
    def http_api(self) -> bool:
        return self._data.get("http_api", False)

    @http_api.setter
    def http_api(self, value: bool) -> None:
        self._data["http_api"] = value
        self.save()

    @property
    def http_port(self) -> int:
        return self._data.get("http_port", 8080)

    @http_port.setter
    def http_port(self, value: int) -> None:
        self._data["http_port"] = value
        self.save()

    @property
    def locale(self) -> str:
        return self._data.get("locale", "auto")

    @locale.setter
    def locale(self, value: str) -> None:
        self._data["locale"] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
