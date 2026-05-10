"""Tests for extras module."""

import pytest
import tempfile
import os
from pathlib import Path
from apex.extras import ShellExpander, EnvManager


class TestShellExpander:
    """Test ShellExpander class."""

    def test_expand_no_vars(self):
        """Test expand with no variables."""
        result = ShellExpander.expand("hello world")
        assert result == "hello world"

    def test_expand_env_var(self):
        """Test expand with environment variable."""
        os.environ["TEST_VAR"] = "test_value"
        result = ShellExpander.expand("$TEST_VAR")
        assert result == "test_value"

    def test_expand_curly_braces(self):
        """Test expand with curly braces."""
        os.environ["TEST_VAR"] = "test_value"
        result = ShellExpander.expand("${TEST_VAR}")
        assert result == "test_value"

    def test_expand_unknown_var(self):
        """Test expand with unknown variable."""
        result = ShellExpander.expand("$UNKNOWN_VAR")
        assert result == "$UNKNOWN_VAR"  # Unchanged

    def test_expand_custom_env(self):
        """Test expand with custom environment."""
        custom_env = {"CUSTOM": "custom_value"}
        result = ShellExpander.expand("$CUSTOM", env=custom_env)
        assert result == "custom_value"

    def test_expand_path(self):
        """Test expand_path."""
        result = ShellExpander.expand_path("~/test")
        assert result.endswith("test")

    def test_expand_path_absolute(self):
        """Test expand_path with absolute path."""
        result = ShellExpander.expand_path("/tmp/test")
        assert result == "/tmp/test"

    def test_expand_command(self):
        """Test expand_command."""
        os.environ["ECHO"] = "echo"
        result = ShellExpander.expand_command("$ECHO test")
        assert result == "echo test"


class TestEnvManager:
    """Test EnvManager class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def env_manager(self, temp_cwd):
        """Create EnvManager instance."""
        return EnvManager(temp_cwd)

    def test_init(self, temp_cwd):
        """Test initialization."""
        manager = EnvManager(temp_cwd)
        assert manager.cwd == Path(temp_cwd)

    def test_get_from_environ(self, env_manager):
        """Test get from environment."""
        os.environ["TEST_KEY"] = "test_value"
        result = env_manager.get("TEST_KEY")
        assert result == "test_value"

    def test_get_default(self, env_manager):
        """Test get with default."""
        result = env_manager.get("NONEXISTENT", "default_value")
        assert result == "default_value"

    def test_set(self, env_manager):
        """Test set method."""
        env_manager.set("NEW_KEY", "new_value")
        assert env_manager.get("NEW_KEY") == "new_value"

    def test_set_overrides_environ(self, env_manager):
        """Test set overrides environment."""
        os.environ["OVERRIDE_KEY"] = "environ_value"
        env_manager.set("OVERRIDE_KEY", "local_value")
        assert env_manager.get("OVERRIDE_KEY") == "local_value"

    def test_unset(self, env_manager):
        """Test unset method."""
        env_manager.set("UNSET_TEST_KEY", "test_value")
        env_manager.unset("UNSET_TEST_KEY")
        # After unset, should fall back to os.environ which might have it
        # Just verify _local_env no longer has it
        assert "UNSET_TEST_KEY" not in env_manager._local_env

    def test_list(self, env_manager):
        """Test list method."""
        env_manager.set("LOCAL_KEY", "local_value")
        result = env_manager.list()
        assert "LOCAL_KEY" in result

    def test_save_to_file(self, env_manager, temp_cwd):
        """Test save_to_file method."""
        env_manager.set("SAVE_KEY", "save_value")
        result = env_manager.save_to_file()
        assert Path(result).exists()

    def test_load_from_file(self, env_manager, temp_cwd):
        """Test load_from_file method."""
        env_file = Path(temp_cwd) / ".env.apex"
        env_file.write_text("LOAD_KEY=load_value\n")

        env_manager.load_from_file()
        assert env_manager.get("LOAD_KEY") == "load_value"
