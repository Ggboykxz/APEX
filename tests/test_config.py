"""Tests for APEX configuration."""

import json
import pytest
from pathlib import Path

from apex.config import (
    MODELS,
    MODEL_PROVIDERS,
    DEFAULT_MODEL,
    SYSTEM_PROMPT,
    Config
)


def test_models_exist():
    assert len(MODELS) > 0
    assert DEFAULT_MODEL in MODELS


def test_model_providers_match():
    for model, provider in MODEL_PROVIDERS.items():
        if provider is not None:
            assert provider.endswith("_API_KEY")


def test_claude_models():
    assert "claude-sonnet" in MODELS
    assert "anthropic/claude" in MODELS["claude-sonnet"]


def test_openai_models():
    assert "gpt-4o" in MODELS
    assert "openai/gpt-4o" in MODELS["gpt-4o"]


def test_groq_models():
    assert "llama-groq" in MODELS
    assert "groq/llama" in MODELS["llama-groq"]


def test_ollama_models():
    assert "ollama-llama3" in MODELS
    assert MODEL_PROVIDERS["ollama-llama3"] is None


def test_system_prompt_exists():
    assert len(SYSTEM_PROMPT) > 0
    assert "APEX" in SYSTEM_PROMPT


def test_config_defaults(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(config_path=config_file)
    assert config.model == DEFAULT_MODEL
    assert config.theme == "monokai"
    assert config.max_tool_rounds == 20
    assert config.auto_commit is False


def test_config_save_and_load(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(config_path=config_file)
    config.model = "gpt-4o"
    config.theme = "dark"
    config.max_tool_rounds = 50
    config.save()

    config2 = Config(config_path=config_file)
    assert config2.model == "gpt-4o"
    assert config2.theme == "dark"
    assert config2.max_tool_rounds == 50


def test_config_cwd(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(config_path=config_file)
    test_cwd = tmp_path / "projects" / "test"
    config.cwd = test_cwd
    assert config.cwd == test_cwd