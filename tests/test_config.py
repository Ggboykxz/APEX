"""Tests for config module."""

import tempfile
import pytest
from pathlib import Path
from apex.config import Config, MODELS


class TestConfig:
    """Test Config class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create config file."""
        config_path = temp_dir / "config.json"
        yield config_path

    def test_config_default(self):
        """Test default config values."""
        config = Config()
        assert isinstance(config.model, str)
        assert isinstance(config.max_tool_rounds, int)

    def test_config_model_property(self, temp_dir):
        """Test model property getter/setter."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.model = "gpt-4o"
        assert config.model == "gpt-4o"

    def test_config_cwd_property(self, temp_dir):
        """Test cwd property getter/setter."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.cwd = Path("/custom/path")
        assert str(config.cwd) == "/custom/path"

    def test_config_max_tool_rounds_property(self, temp_dir):
        """Test max_tool_rounds property getter/setter."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.max_tool_rounds = 50
        assert config.max_tool_rounds == 50

    def test_config_theme_property(self, temp_dir):
        """Test theme property getter/setter."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.theme = "dracula"
        assert config.theme == "dracula"

    def test_config_auto_commit_property(self, temp_dir):
        """Test auto_commit property getter/setter."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.auto_commit = True
        assert config.auto_commit is True

    def test_config_get_method(self, temp_dir):
        """Test get method."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {"custom_key": "custom_value"}

        assert config.get("custom_key") == "custom_value"
        assert config.get("missing_key", "default") == "default"

    def test_config_set_method(self, temp_dir):
        """Test set method."""
        config = Config()
        config._apex_dir = temp_dir
        config._config_file = temp_dir / "config.json"
        config._data = {}

        config.set("new_key", "new_value")
        assert config.get("new_key") == "new_value"


class TestModels:
    """Test MODELS dict."""

    def test_models_not_empty(self):
        """Test models dict is not empty."""
        assert len(MODELS) > 0

    def test_models_are_strings(self):
        """Test each model value is a string."""
        for alias, model_id in MODELS.items():
            assert isinstance(model_id, str)
            assert "/" in model_id  # Format: provider/model

    def test_models_valid_providers(self):
        """Test all models have valid provider prefix."""
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
            "azure/",
            "microsoft/",
            "groq/",
            "ollama/",
            "meta-llama/",
        ]
        for alias, model_id in MODELS.items():
            has_valid_provider = any(model_id.startswith(p) for p in valid_providers)
            assert has_valid_provider, f"Invalid provider in {alias}: {model_id}"
