"""Tests for extras module - improved."""

import pytest
import os
import tempfile
from pathlib import Path
from apex.extras import ShellExpander, EnvManager


class TestShellExpanderFull:
    """Full tests for ShellExpander."""

    def test_expand_no_vars(self):
        result = ShellExpander.expand("hello world")
        assert result == "hello world"

    def test_expand_env_var(self):
        os.environ["TEST_VAR"] = "test_value"
        result = ShellExpander.expand("$TEST_VAR")
        assert result == "test_value"

    def test_expand_curly_braces(self):
        os.environ["TEST_VAR"] = "test_value"
        result = ShellExpander.expand("${TEST_VAR}")
        assert result == "test_value"

    def test_expand_unknown_var(self):
        result = ShellExpander.expand("$UNKNOWN_VAR")
        assert result == "$UNKNOWN_VAR"

    def test_expand_custom_env(self):
        result = ShellExpander.expand("$CUSTOM", env={"CUSTOM": "value"})
        assert result == "value"

    def test_expand_path(self):
        result = ShellExpander.expand_path("~/test")
        assert "test" in result

    def test_expand_path_absolute(self):
        result = ShellExpander.expand_path("/tmp/test")
        assert result == "/tmp/test"

    def test_expand_command(self):
        os.environ["CMD"] = "echo"
        result = ShellExpander.expand_command("$CMD hello")
        assert "echo" in result


class TestEnvManagerFull:
    """Full tests for EnvManager."""

    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def env_mgr(self, temp_cwd):
        return EnvManager(str(temp_cwd))

    def test_init(self, temp_cwd):
        mgr = EnvManager(str(temp_cwd))
        assert mgr.cwd == Path(temp_cwd)

    def test_get_environ(self, env_mgr):
        os.environ["TEST_KEY"] = "test_value"
        assert env_mgr.get("TEST_KEY") == "test_value"

    def test_get_default(self, env_mgr):
        assert env_mgr.get("NONEXISTENT", "default") == "default"

    def test_set(self, env_mgr):
        env_mgr.set("NEW_KEY", "new_value")
        assert env_mgr.get("NEW_KEY") == "new_value"

    def test_set_override(self, env_mgr):
        os.environ["KEY"] = "env_value"
        env_mgr.set("KEY", "local_value")
        assert env_mgr.get("KEY") == "local_value"

    def test_unset(self, env_mgr):
        env_mgr.set("TEST_KEY", "value")
        env_mgr.unset("TEST_KEY")
        assert "TEST_KEY" not in env_mgr._local_env

    def test_list(self, env_mgr):
        env_mgr.set("LOCAL", "value")
        result = env_mgr.list()
        assert "LOCAL" in result

    def test_save_load(self, env_mgr, temp_cwd):
        env_mgr.set("KEY", "value")
        path = env_mgr.save_to_file(".env.test")
        assert Path(path).exists()

        new_mgr = EnvManager(str(temp_cwd))
        new_mgr.load_from_file(".env.test")
        assert new_mgr.get("KEY") == "value"