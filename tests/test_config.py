"""Tests for config module — no mocks, real file system."""

import json
import os
import tempfile
import pytest
from pathlib import Path

from apex.config import Config, MODELS, MODEL_PROVIDERS, DEFAULT_MODEL, SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_dir):
    """Create a Config instance that uses the temp directory for storage."""
    cfg = Config.__new__(Config)  # skip __init__ so we control paths
    cfg._apex_dir = temp_dir
    cfg._config_file = temp_dir / "config.json"
    cfg._env_file = temp_dir / ".env"
    cfg._data = {}
    return cfg


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestMODELS:
    """Test MODELS dictionary."""

    def test_models_not_empty(self):
        assert len(MODELS) > 0

    def test_models_are_strings(self):
        for alias, model_id in MODELS.items():
            assert isinstance(model_id, str)
            assert "/" in model_id

    def test_models_valid_providers(self):
        valid_providers = [
            "anthropic/",
            "openai/",
            "google/",
            "xai/",
            "amazon/",
            "qwen/",
            "cohere/",
            "meta/",
            "mistral/",
            "deepseek/",
            "openrouter/",
            "microsoft/",
            "groq/",
            "ollama/",
            "meta-llama/",
        ]
        for alias, model_id in MODELS.items():
            has_valid = any(model_id.startswith(p) for p in valid_providers)
            assert has_valid, f"Invalid provider in {alias}: {model_id}"

    def test_default_model_in_models(self):
        assert DEFAULT_MODEL in MODELS

    def test_claude_models(self):
        for alias in ["claude-3.5-haiku", "claude-3.5-sonnet", "claude-sonnet-4", "claude-opus-4"]:
            assert alias in MODELS

    def test_gpt_models(self):
        for alias in ["gpt-4o", "gpt-4o-mini", "o1", "o3", "o4-mini"]:
            assert alias in MODELS

    def test_gemini_models(self):
        assert "gemini-2.5-pro" in MODELS

    def test_ollama_models_no_api_key(self):
        """Ollama models should not require API keys."""
        for alias in ["ollama-llama3", "ollama-codellama"]:
            assert MODEL_PROVIDERS.get(alias) is None


class TestModelProviders:
    """Test MODEL_PROVIDERS dictionary."""

    def test_providers_not_empty(self):
        assert len(MODEL_PROVIDERS) > 0

    def test_all_models_have_provider_entries(self):
        for alias in MODELS:
            assert alias in MODEL_PROVIDERS, f"Missing provider for {alias}"

    def test_anthropic_uses_anthropic_key(self):
        assert MODEL_PROVIDERS["claude-sonnet-4"] == "ANTHROPIC_API_KEY"

    def test_openai_uses_openai_key(self):
        assert MODEL_PROVIDERS["gpt-4o"] == "OPENAI_API_KEY"

    def test_ollama_has_no_key(self):
        for alias in ["ollama-llama3", "ollama-mistral"]:
            assert MODEL_PROVIDERS[alias] is None


class TestDefaultModel:
    def test_default_model_is_string(self):
        assert isinstance(DEFAULT_MODEL, str)

    def test_default_model_value(self):
        assert DEFAULT_MODEL == "or-gpt4o-mini"


class TestSystemPrompt:
    def test_system_prompt_is_string(self):
        assert isinstance(SYSTEM_PROMPT, str)

    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_mentions_apex(self):
        assert "APEX" in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Config class
# ---------------------------------------------------------------------------


class TestConfigInit:
    """Test Config initialization."""

    def test_init_with_default_path(self):
        """Config can be created without arguments (uses home dir)."""
        cfg = Config()
        assert isinstance(cfg._data, dict)

    def test_init_with_custom_path(self, temp_dir):
        """Config can be created with a custom config path."""
        config_path = temp_dir / "my_config.json"
        cfg = Config(config_path=config_path)
        assert cfg._config_file == config_path

    def test_init_creates_apex_dir(self):
        """_load creates the apex directory if missing."""
        cfg = Config()
        assert cfg._apex_dir.exists()

    def test_init_loads_existing_config(self, temp_dir):
        """Config loads existing JSON data."""
        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps({"model": "gpt-4o", "theme": "dracula"}))
        cfg = Config(config_path=config_path)
        assert cfg._data["model"] == "gpt-4o"
        assert cfg._data["theme"] == "dracula"

    def test_init_handles_corrupt_json(self, temp_dir):
        """Config handles corrupt JSON gracefully."""
        config_path = temp_dir / "config.json"
        config_path.write_text("{invalid json!!!")
        cfg = Config(config_path=config_path)
        assert cfg._data == {}

    def test_init_loads_env_file(self, temp_dir, monkeypatch):
        """Config loads .env from _env_file path."""
        env_file = temp_dir / ".env"
        env_file.write_text("TEST_APEX_VAR=hello_world\n")
        monkeypatch.delenv("TEST_APEX_VAR", raising=False)

        cfg = Config.__new__(Config)
        cfg._apex_dir = temp_dir
        cfg._config_file = temp_dir / "config.json"
        cfg._env_file = env_file
        cfg._data = {}
        cfg._load()

        assert os.environ.get("TEST_APEX_VAR") == "hello_world"
        # cleanup
        monkeypatch.delenv("TEST_APEX_VAR", raising=False)

    def test_init_env_file_skips_comments(self, temp_dir, monkeypatch):
        """_load_env skips comment lines in .env."""
        env_file = temp_dir / ".env"
        env_file.write_text("# this is a comment\nTEST_ENV_SKIP=yes\n")
        monkeypatch.delenv("TEST_ENV_SKIP", raising=False)

        cfg = Config.__new__(Config)
        cfg._apex_dir = temp_dir
        cfg._config_file = temp_dir / "config.json"
        cfg._env_file = env_file
        cfg._data = {}
        cfg._load()

        assert os.environ.get("TEST_ENV_SKIP") == "yes"
        monkeypatch.delenv("TEST_ENV_SKIP", raising=False)

    def test_init_env_file_skips_empty_lines(self, temp_dir, monkeypatch):
        """_load_env skips empty lines in .env."""
        env_file = temp_dir / ".env"
        env_file.write_text("\n\nTEST_ENV_EMPTY=1\n\n")
        monkeypatch.delenv("TEST_ENV_EMPTY", raising=False)

        cfg = Config.__new__(Config)
        cfg._apex_dir = temp_dir
        cfg._config_file = temp_dir / "config.json"
        cfg._env_file = env_file
        cfg._data = {}
        cfg._load()

        assert os.environ.get("TEST_ENV_EMPTY") == "1"
        monkeypatch.delenv("TEST_ENV_EMPTY", raising=False)

    def test_init_env_file_splits_on_first_equals(self, temp_dir, monkeypatch):
        """_load_env handles values that contain '='."""
        env_file = temp_dir / ".env"
        env_file.write_text("TEST_ENV_EQ=key=value\n")
        monkeypatch.delenv("TEST_ENV_EQ", raising=False)

        cfg = Config.__new__(Config)
        cfg._apex_dir = temp_dir
        cfg._config_file = temp_dir / "config.json"
        cfg._env_file = env_file
        cfg._data = {}
        cfg._load()

        assert os.environ.get("TEST_ENV_EQ") == "key=value"
        monkeypatch.delenv("TEST_ENV_EQ", raising=False)


# ---------------------------------------------------------------------------
# Config properties
# ---------------------------------------------------------------------------


class TestConfigModel:
    def test_model_default(self, config):
        assert config.model == DEFAULT_MODEL

    def test_model_setter_and_getter(self, config):
        config.model = "gpt-4o"
        assert config.model == "gpt-4o"

    def test_model_persists_to_disk(self, config):
        config.model = "claude-sonnet-4"
        # Read the file back
        data = json.loads(config._config_file.read_text())
        assert data["model"] == "claude-sonnet-4"


class TestConfigCwd:
    def test_cwd_default(self, config):
        result = config.cwd
        assert isinstance(result, Path)
        assert result.exists()

    def test_cwd_setter_and_getter(self, config):
        config.cwd = Path("/tmp")
        result = config.cwd
        assert str(result) == "/tmp"

    def test_cwd_expands_user(self, config):
        config.cwd = Path("~")
        result = config.cwd
        assert "~" not in str(result)


class TestConfigTheme:
    def test_theme_default(self, config):
        assert config.theme == "monokai"

    def test_theme_setter(self, config):
        config.theme = "dracula"
        assert config.theme == "dracula"


class TestConfigMaxToolRounds:
    def test_max_tool_rounds_default(self, config):
        assert config.max_tool_rounds == 20

    def test_max_tool_rounds_setter(self, config):
        config.max_tool_rounds = 50
        assert config.max_tool_rounds == 50


class TestConfigAutoCommit:
    def test_auto_commit_default(self, config):
        assert config.auto_commit is False

    def test_auto_commit_setter(self, config):
        config.auto_commit = True
        assert config.auto_commit is True


class TestConfigAutoModel:
    def test_auto_model_default(self, config):
        assert config.auto_model is False

    def test_auto_model_setter(self, config):
        config.auto_model = True
        assert config.auto_model is True


class TestConfigReasoningEffort:
    def test_reasoning_effort_default(self, config):
        assert config.reasoning_effort == "off"

    def test_reasoning_effort_valid_values(self, config):
        for val in ("off", "high", "max"):
            config.reasoning_effort = val
            assert config.reasoning_effort == val

    def test_reasoning_effort_invalid_falls_back(self, config):
        config.reasoning_effort = "invalid"
        assert config.reasoning_effort == "off"

    def test_reasoning_effort_empty_falls_back(self, config):
        config.reasoning_effort = ""
        assert config.reasoning_effort == "off"


class TestConfigAgentMode:
    def test_agent_mode_default(self, config):
        assert config.agent_mode == "agent"

    def test_agent_mode_valid_values(self, config):
        for val in ("plan", "agent", "yolo"):
            config.agent_mode = val
            assert config.agent_mode == val

    def test_agent_mode_invalid_falls_back(self, config):
        config.agent_mode = "invalid"
        assert config.agent_mode == "agent"

    def test_agent_mode_empty_falls_back(self, config):
        config.agent_mode = ""
        assert config.agent_mode == "agent"


class TestConfigContextMaxTokens:
    def test_context_max_tokens_default(self, config):
        assert config.context_max_tokens == 1000000

    def test_context_max_tokens_setter(self, config):
        config.context_max_tokens = 500000
        assert config.context_max_tokens == 500000


class TestConfigHttpApi:
    def test_http_api_default(self, config):
        assert config.http_api is False

    def test_http_api_setter(self, config):
        config.http_api = True
        assert config.http_api is True


class TestConfigHttpPort:
    def test_http_port_default(self, config):
        assert config.http_port == 8080

    def test_http_port_setter(self, config):
        config.http_port = 9090
        assert config.http_port == 9090


class TestConfigLocale:
    def test_locale_default(self, config):
        assert config.locale == "auto"

    def test_locale_setter(self, config):
        config.locale = "ja"
        assert config.locale == "ja"


# ---------------------------------------------------------------------------
# Config generic get/set
# ---------------------------------------------------------------------------


class TestConfigGetSet:
    def test_get_existing_key(self, config):
        config._data["custom"] = "value"
        assert config.get("custom") == "value"

    def test_get_missing_key_returns_default(self, config):
        assert config.get("missing") is None
        assert config.get("missing", "fallback") == "fallback"

    def test_set_adds_key(self, config):
        config.set("new_key", "new_value")
        assert config.get("new_key") == "new_value"

    def test_set_persists_to_disk(self, config):
        config.set("disk_key", "disk_value")
        data = json.loads(config._config_file.read_text())
        assert data["disk_key"] == "disk_value"

    def test_set_overwrites_existing(self, config):
        config.set("key", "first")
        config.set("key", "second")
        assert config.get("key") == "second"


# ---------------------------------------------------------------------------
# Config save
# ---------------------------------------------------------------------------


class TestConfigSave:
    def test_save_creates_directory(self, temp_dir):
        """save() creates the apex directory if it doesn't exist."""
        sub = temp_dir / "nested" / "dir"
        cfg = Config.__new__(Config)
        cfg._apex_dir = sub
        cfg._config_file = sub / "config.json"
        cfg._data = {"key": "val"}
        cfg.save()
        assert sub.exists()
        assert json.loads(cfg._config_file.read_text()) == {"key": "val"}

    def test_save_overwrites_existing(self, config):
        config._data = {"a": 1}
        config.save()
        config._data = {"b": 2}
        config.save()
        data = json.loads(config._config_file.read_text())
        assert data == {"b": 2}
