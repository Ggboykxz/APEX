"""Configuration system for APEX - models, API keys, and user config."""

import json
import os
from pathlib import Path
from typing import Any

MODELS: dict[str, str] = {
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-opus": "anthropic/claude-opus-4-20250514",
    "claude-flash": "anthropic/claude-3-5-haiku-20241022",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "o1": "openai/o1",
    "o3-mini": "openai/o3-mini",
    "gemini-2": "google/gemini-2.0-flash-exp",
    "gemini-flash": "google/gemini-1.5-flash",
    "llama-groq": "groq/llama-3.3-70b-versatile",
    "mixtral-groq": "groq/mixtral-8x7b-32768",
    "mistral-large": "mistral/mistral-large-latest",
    "codestral": "mistral/codestral-latest",
    "deepseek": "deepseek/deepseek-chat",
    "deepseek-r1": "deepseek/deepseek-reasoner",
    "ollama-llama3": "ollama/llama3",
    "ollama-llama3.1": "ollama/llama3.1",
    "ollama-codellama": "ollama/codellama",
    "ollama-deepseek": "ollama/deepseek-coder",
    "command-r": "cohere/command-r",
    "command-r-plus": "cohere/command-r-plus",
}

MODEL_PROVIDERS: dict[str, str] = {
    "claude-sonnet": "ANTHROPIC_API_KEY",
    "claude-opus": "ANTHROPIC_API_KEY",
    "claude-flash": "ANTHROPIC_API_KEY",
    "gpt-4o": "OPENAI_API_KEY",
    "gpt-4o-mini": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "o3-mini": "OPENAI_API_KEY",
    "gemini-2": "GEMINI_API_KEY",
    "gemini-flash": "GEMINI_API_KEY",
    "llama-groq": "GROQ_API_KEY",
    "mixtral-groq": "GROQ_API_KEY",
    "mistral-large": "MISTRAL_API_KEY",
    "codestral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "deepseek-r1": "DEEPSEEK_API_KEY",
    "ollama-llama3": None,
    "ollama-llama3.1": None,
    "ollama-codellama": None,
    "ollama-deepseek": None,
    "command-r": "COHERE_API_KEY",
    "command-r-plus": "COHERE_API_KEY",
}

DEFAULT_MODEL = "claude-sonnet"

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

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()