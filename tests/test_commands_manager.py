"""Tests for apex/commands_manager.py — 100 % line coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from apex.commands_manager import (
    CommandConfig,
    CustomCommandManager,
    _parse_yaml_frontmatter,
    _render_template,
    commands_manager,
)
from apex.config_v2 import apex_config


# ──────────────────────────────────────────────
# Helpers — directly manipulate config storage
# to avoid triggering the property setter/save.
# ──────────────────────────────────────────────


def _set_cfg(cmds: dict) -> None:
    apex_config._data["command"] = cmds


def _pop_cfg() -> None:
    apex_config._data.pop("command", None)


@pytest.fixture(autouse=True)
def _auto_clean_cfg():
    saved = apex_config._data.get("command")
    yield
    if saved is not None:
        apex_config._data["command"] = saved
    else:
        apex_config._data.pop("command", None)


# ──────────────────────────────────────────────
# CommandConfig dataclass
# ──────────────────────────────────────────────


class TestCommandConfig:
    def test_minimal(self):
        c = CommandConfig(name="x", template="do {x}")
        assert c.name == "x"
        assert c.template == "do {x}"
        assert c.description == ""
        assert c.agent is None
        assert c.model is None
        assert c.subtask is False

    def test_all_fields(self):
        c = CommandConfig(
            name="test",
            template="run tests",
            description="Run tests",
            agent="build",
            model="claude-3",
            subtask=True,
        )
        assert c.name == "test"
        assert c.description == "Run tests"
        assert c.agent == "build"
        assert c.model == "claude-3"
        assert c.subtask is True

    def test_defaults(self):
        c = CommandConfig(name="n", template="t")
        assert c.description == ""
        assert c.agent is None
        assert c.model is None
        assert c.subtask is False


# ──────────────────────────────────────────────
# _parse_yaml_frontmatter
# ──────────────────────────────────────────────


class TestParseYamlFrontmatter:
    def test_no_frontmatter(self):
        meta, body = _parse_yaml_frontmatter("just text\nhello")
        assert meta == {}
        assert body == "just text\nhello"

    def test_empty_string(self):
        meta, body = _parse_yaml_frontmatter("")
        assert meta == {}
        assert body == ""

    def test_only_delimiter(self):
        meta, body = _parse_yaml_frontmatter("---")
        assert meta == {}
        assert body == "---"

    def test_unclosed_delimiter(self):
        meta, body = _parse_yaml_frontmatter("---\nkey: val\nno close")
        assert meta == {}
        assert body == "---\nkey: val\nno close"

    def test_full_frontmatter(self):
        text = (
            "---\ndescription: Run tests\nagent: build\nmodel: claude"
            "\nsubtask: true\n---\nbody text"
        )
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {
            "description": "Run tests",
            "agent": "build",
            "model": "claude",
            "subtask": True,
        }
        assert body == "body text"

    def test_boolean_parsing(self):
        text = "---\nopt_a: true\nopt_b: false\n---\nbody"
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {"opt_a": True, "opt_b": False}
        assert body == "body"

    def test_null_values(self):
        text = "---\nkey_a:\nkey_b: null\n---\nbody"
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {"key_a": None, "key_b": None}
        assert body == "body"

    def test_comment_lines_skipped(self):
        text = "---\n# comment\ndescription: real\n---\nbody"
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {"description": "real"}

    def test_no_colon_line_skipped(self):
        text = "---\nno-colon-line\ndescription: ok\n---\nbody"
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {"description": "ok"}

    def test_frontmatter_only_no_body(self):
        text = "---\nkey: val\n---"
        meta, body = _parse_yaml_frontmatter(text)
        assert meta == {"key": "val"}
        assert body == ""

    def test_multiline_body_trimmed(self):
        text = "---\nkey: val\n---\n  \nbody line 1\nbody line 2\n  "
        meta, body = _parse_yaml_frontmatter(text)
        assert body == "body line 1\nbody line 2"


# ──────────────────────────────────────────────
# _render_template
# ──────────────────────────────────────────────


class TestRenderTemplate:
    def test_arguments_substitution(self):
        result = _render_template("run $ARGUMENTS", ["--verbose", "--all"], "/tmp")
        assert result == "run --verbose --all"

    def test_positional_args(self):
        result = _render_template("$1 $2 $3", ["a", "b", "c"], "/tmp")
        assert result == "a b c"

    def test_positional_missing(self):
        result = _render_template("$1 $2 $3", ["hello"], "/tmp")
        assert result == "hello $2 $3"

    def test_mixed_args(self):
        result = _render_template("cmd: $1, all: $ARGUMENTS", ["x", "y"], "/tmp")
        assert result == "cmd: x, all: x y"

    @patch("apex.commands_manager.subprocess.run")
    def test_shell_execution(self, mock_run):
        mock_run.return_value = MagicMock(stdout="result output", stderr="")
        result = _render_template("output: !echo hello", [], "/tmp")
        assert "result output" in result

    @patch("apex.commands_manager.subprocess.run")
    def test_shell_timeout_returns_empty(self, mock_run):
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("cmd", 30)
        result = _render_template("out: !sleep 100", [], "/tmp")
        assert result == "out: "

    @patch("apex.commands_manager.subprocess.run")
    def test_shell_exception_returns_empty(self, mock_run):
        mock_run.side_effect = Exception("boom")
        result = _render_template("out: !badcommand", [], "/tmp")
        assert result == "out: "

    @patch("apex.commands_manager.subprocess.run")
    def test_shell_stderr_fallback(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="error msg")
        result = _render_template("err: !cmd", [], "/tmp")
        assert "error msg" in result

    def test_file_inclusion(self, tmp_path):
        d = tmp_path / "sub"
        d.mkdir()
        f = d / "data.txt"
        f.write_text("included content")
        result = _render_template("content: @{}".format(f), [], str(tmp_path))
        assert "included content" in result

    def test_file_inclusion_relative_path(self, tmp_path):
        (tmp_path / "notes.txt").write_text("relative content")
        result = _render_template("content: @notes.txt", [], str(tmp_path))
        assert "relative content" in result

    def test_file_missing_returns_empty(self):
        result = _render_template("content: @/nonexistent/file.txt", [], "/tmp")
        assert result == "content: "

    def test_no_substitutions(self):
        result = _render_template("plain text", [], "/tmp")
        assert result == "plain text"

    def test_empty_args(self):
        result = _render_template("run $ARGUMENTS", [], "/tmp")
        assert result == "run "


# ──────────────────────────────────────────────
# CustomCommandManager — constructor & builtins
# ──────────────────────────────────────────────


class TestCustomCommandManagerInit:
    def test_builtins_loaded(self):
        mgr = CustomCommandManager()
        for name in ("test", "review", "commit", "docs"):
            cmd = mgr.get(name)
            assert cmd is not None, f"Built-in '{name}' not found"
            assert cmd.name == name

    def test_builtins_count(self):
        mgr = CustomCommandManager()
        cmds = mgr.list()
        assert len(cmds) == 4

    def test_builtin_values(self):
        mgr = CustomCommandManager()
        test_cmd = mgr.get("test")
        assert test_cmd.description == "Run tests"
        assert test_cmd.agent == "build"


# ──────────────────────────────────────────────
# CustomCommandManager — load_all
# ──────────────────────────────────────────────


class TestLoadAll:
    def _mgr(self) -> CustomCommandManager:
        _pop_cfg()
        return CustomCommandManager()

    @patch("apex.commands_manager.Path.is_dir", return_value=False)
    def test_load_all_only_builtins(self, mock_isdir):
        _pop_cfg()
        mgr = self._mgr()
        mgr.load_all("/some/project")
        names = {c.name for c in mgr.list()}
        assert names == {"test", "review", "commit", "docs"}

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_load_all_global_dir(self, mock_glob, mock_isdir):
        _pop_cfg()
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "global-cmd"
        mock_file.read_text.return_value = (
            "---\ndescription: global\n---\ndo global stuff"
        )
        mock_glob.return_value = [mock_file]
        mgr = self._mgr()
        mgr.load_all("/some/project")
        cmd = mgr.get("global-cmd")
        assert cmd is not None
        assert cmd.description == "global"

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_load_all_project_dir(self, mock_glob, mock_isdir):
        _pop_cfg()
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "proj-cmd"
        mock_file.read_text.return_value = (
            "---\ndescription: project\n---\ndo project stuff"
        )
        mock_glob.return_value = [mock_file]
        mgr = self._mgr()
        mgr.load_all("/some/project")
        cmd = mgr.get("proj-cmd")
        assert cmd is not None
        assert cmd.description == "project"

    @patch("apex.commands_manager.Path.is_dir", return_value=False)
    def test_load_all_from_config(self, mock_isdir):
        mgr = self._mgr()
        _set_cfg({
            "mycmd": {
                "template": "run {{task}}",
                "description": "Config cmd",
                "agent": "coder",
                "model": "gpt-4",
                "subtask": True,
            }
        })
        mgr.load_all("/some/project")
        cmd = mgr.get("mycmd")
        assert cmd is not None
        assert cmd.description == "Config cmd"
        assert cmd.agent == "coder"
        assert cmd.model == "gpt-4"
        assert cmd.subtask is True

    @patch("apex.commands_manager.Path.is_dir", return_value=False)
    def test_load_from_config_minimal_dict(self, mock_isdir):
        mgr = self._mgr()
        _set_cfg({
            "minimal": {
                "template": "do it",
            }
        })
        mgr.load_all("/p")
        cmd = mgr.get("minimal")
        assert cmd is not None
        assert cmd.template == "do it"
        assert cmd.description == ""
        assert cmd.agent is None
        assert cmd.model is None
        assert cmd.subtask is False

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_override_hierarchy(self, mock_glob, mock_isdir):
        _pop_cfg()
        mock_global = MagicMock(spec=Path)
        mock_global.stem = "test"
        mock_global.read_text.return_value = (
            "---\ndescription: from global\n---\nglobal template"
        )
        mock_project = MagicMock(spec=Path)
        mock_project.stem = "test"
        mock_project.read_text.return_value = (
            "---\ndescription: from project\n---\nproject template"
        )
        call_count = 0

        def glob_side_effect(_pattern):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_global]
            return [mock_project]

        mock_glob.side_effect = glob_side_effect
        mgr = self._mgr()
        mgr.load_all("/some/project")
        cmd = mgr.get("test")
        assert cmd.description == "from project"

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_config_overrides_markdown(self, mock_glob, mock_isdir):
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "override-me"
        mock_file.read_text.return_value = (
            "---\ndescription: from md\n---\nmd template"
        )
        mock_glob.return_value = [mock_file]
        mgr = self._mgr()
        _set_cfg({
            "override-me": {
                "template": "from config",
                "description": "from config",
            }
        })
        mgr.load_all("/some/project")
        cmd = mgr.get("override-me")
        assert cmd.description == "from config"

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_load_from_dir_read_error_skipped(self, mock_glob, mock_isdir):
        _pop_cfg()
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "broken"
        mock_file.read_text.side_effect = OSError("permission denied")
        mock_glob.return_value = [mock_file]
        mgr = self._mgr()
        mgr.load_all("/some/project")
        assert mgr.get("broken") is None

    @patch("apex.commands_manager.Path.is_dir", return_value=True)
    @patch("apex.commands_manager.Path.glob")
    def test_load_from_dir_malformed_frontmatter(self, mock_glob, mock_isdir):
        _pop_cfg()
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "malformed"
        mock_file.read_text.return_value = "---\nunparseable!!!\n---\nbody"
        mock_glob.return_value = [mock_file]
        mgr = self._mgr()
        mgr.load_all("/some/project")
        cmd = mgr.get("malformed")
        assert cmd is not None
        assert cmd.template == "body"

    def test_load_all_defaults_to_cwd(self):
        _pop_cfg()
        mgr = self._mgr()
        mgr.load_all()
        names = {c.name for c in mgr.list()}
        assert names == {"test", "review", "commit", "docs"}


# ──────────────────────────────────────────────
# CustomCommandManager — get / list / add / remove
# ──────────────────────────────────────────────


class TestManagerCRUD:
    def test_get_existing(self):
        mgr = CustomCommandManager()
        cmd = mgr.get("test")
        assert cmd is not None
        assert cmd.name == "test"

    def test_get_missing(self):
        mgr = CustomCommandManager()
        assert mgr.get("nope") is None

    def test_list(self):
        mgr = CustomCommandManager()
        all_cmds = mgr.list()
        assert len(all_cmds) == 4
        assert all(isinstance(c, CommandConfig) for c in all_cmds)

    def test_add(self):
        mgr = CustomCommandManager()
        new_cmd = CommandConfig(name="custom", template="do stuff")
        mgr.add(new_cmd)
        assert mgr.get("custom") is new_cmd

    def test_remove_existing(self):
        mgr = CustomCommandManager()
        assert mgr.remove("test") is True
        assert mgr.get("test") is None

    def test_remove_missing(self):
        mgr = CustomCommandManager()
        assert mgr.remove("nonexistent") is False

    def test_add_overrides(self):
        mgr = CustomCommandManager()
        override = CommandConfig(
            name="test", template="overridden", description="overridden"
        )
        mgr.add(override)
        cmd = mgr.get("test")
        assert cmd.description == "overridden"


# ──────────────────────────────────────────────
# CustomCommandManager — render_template
# ──────────────────────────────────────────────


class TestManagerRenderTemplate:
    def test_delegates_to_module_function(self):
        mgr = CustomCommandManager()
        result = mgr.render_template("hello $1", ["world"], "/tmp")
        assert result == "hello world"


# ──────────────────────────────────────────────
# CustomCommandManager — execute
# ──────────────────────────────────────────────


class TestExecute:
    def test_unknown_command(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        result = mgr.execute("unknown", [], agent)
        assert "ERROR: Unknown command" in result

    def test_execute_calls_agent_chat(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        agent.chat.return_value = "chat result"
        agent.cwd = "/tmp"
        result = mgr.execute("test", ["--verbose"], agent)
        assert result == "chat result"

    def test_execute_template_renders_args(self):
        mgr = CustomCommandManager()
        mgr.add(
            CommandConfig(name="echo", template="say $1", description="Echo")
        )
        agent = MagicMock()
        agent.chat.return_value = "done"
        agent.cwd = "/tmp"
        mgr.execute("echo", ["fast"], agent)
        call_prompt = agent.chat.call_args[0][0]
        assert "say fast" in call_prompt

    def test_execute_switches_model(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        agent.switch_model = MagicMock()
        cmd = CommandConfig(
            name="modelcmd",
            template="use model",
            model="claude-sonnet-4-5",
        )
        mgr.add(cmd)
        mgr.execute("modelcmd", [], agent)
        agent.switch_model.assert_called_once_with("claude-sonnet-4-5")

    def test_execute_no_switch_model_when_no_model(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        agent.switch_model = MagicMock()
        mgr.execute("test", [], agent)
        agent.switch_model.assert_not_called()

    def test_execute_switches_agent(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        agent.switch_agent = MagicMock()
        cmd = CommandConfig(
            name="agentcmd",
            template="use agent",
            agent="reviewer",
        )
        mgr.add(cmd)
        mgr.execute("agentcmd", [], agent)
        agent.switch_agent.assert_called_once_with("reviewer")

    def test_execute_no_switch_agent_when_no_agent(self):
        mgr = CustomCommandManager()
        mgr.add(
            CommandConfig(
                name="noagent", template="just do it", description="no agent"
            )
        )
        agent = MagicMock()
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        agent.switch_agent = MagicMock()
        mgr.execute("noagent", [], agent)
        agent.switch_agent.assert_not_called()

    def test_execute_no_switch_model_if_no_attr(self):
        mgr = CustomCommandManager()
        mgr.add(CommandConfig(name="x", template="t", model="gpt-4"))
        agent = MagicMock(spec=["chat", "cwd"])
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        mgr.execute("x", [], agent)

    def test_execute_no_switch_agent_if_no_attr(self):
        mgr = CustomCommandManager()
        mgr.add(CommandConfig(name="y", template="t", agent="coder"))
        agent = MagicMock(spec=["chat", "cwd"])
        agent.chat.return_value = ""
        agent.cwd = "/tmp"
        mgr.execute("y", [], agent)

    def test_execute_agent_cwd_fallback(self):
        mgr = CustomCommandManager()
        agent = MagicMock()
        agent.chat.return_value = ""
        mgr.execute("test", [], agent)


# ──────────────────────────────────────────────
# commands_manager singleton
# ──────────────────────────────────────────────


class TestSingleton:
    def test_is_instance(self):
        assert isinstance(commands_manager, CustomCommandManager)

    def test_has_builtins(self):
        assert commands_manager.get("test") is not None
        assert commands_manager.get("review") is not None
        assert commands_manager.get("commit") is not None
        assert commands_manager.get("docs") is not None

    def test_singleton_identity(self):
        from apex.commands_manager import commands_manager as cm2

        assert commands_manager is cm2


# ──────────────────────────────────────────────
# Integration: load from real markdown files
# ──────────────────────────────────────────────


class TestLoadFromRealMarkdown:
    def test_load_from_global_dir(self, tmp_path):
        _pop_cfg()
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        global_dir = home_dir / ".config" / "apex" / "commands"
        global_dir.mkdir(parents=True)
        (global_dir / "greet.md").write_text(
            "---\ndescription: Say hello\nagent: general\n---\n"
            "Greet the user warmly. Say hello to $1."
        )
        mgr = CustomCommandManager()
        with patch.object(Path, "home", return_value=home_dir):
            mgr.load_all(str(tmp_path))
        cmd = mgr.get("greet")
        assert cmd is not None
        assert cmd.description == "Say hello"
        assert cmd.agent == "general"
        assert "$1" in cmd.template

    def test_load_from_project_dir(self, tmp_path):
        _pop_cfg()
        proj_dir = tmp_path / "myproject"
        proj_dir.mkdir()
        cmd_dir = proj_dir / ".apex" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "build.md").write_text(
            "---\ndescription: Build project\n---\n"
            "Build the project using $ARGUMENTS."
        )
        mgr = CustomCommandManager()
        mgr.load_all(str(proj_dir))
        cmd = mgr.get("build")
        assert cmd is not None
        assert cmd.description == "Build project"

    def test_both_global_and_project(self, tmp_path):
        _pop_cfg()
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        global_dir = home_dir / ".config" / "apex" / "commands"
        global_dir.mkdir(parents=True)
        (global_dir / "shared.md").write_text(
            "---\ndescription: Global cmd\n---\nglobal"
        )
        proj_dir = tmp_path / "proj"
        proj_dir.mkdir()
        proj_cmd_dir = proj_dir / ".apex" / "commands"
        proj_cmd_dir.mkdir(parents=True)
        (proj_cmd_dir / "shared.md").write_text(
            "---\ndescription: Project override\n---\nproject"
        )
        mgr = CustomCommandManager()
        with patch.object(Path, "home", return_value=home_dir):
            mgr.load_all(str(proj_dir))
        cmd = mgr.get("shared")
        assert cmd.description == "Project override"

    def test_load_from_dir_no_frontmatter(self, tmp_path):
        _pop_cfg()
        d = tmp_path / "cmds"
        d.mkdir()
        (d / "plain.md").write_text("this has no frontmatter")
        mgr = CustomCommandManager()
        mgr._load_from_dir(d)
        cmd = mgr.get("plain")
        assert cmd is not None
        assert cmd.template == "this has no frontmatter"

    def test_load_from_dir_empty_file(self, tmp_path):
        _pop_cfg()
        d = tmp_path / "cmds"
        d.mkdir()
        (d / "empty.md").write_text("")
        mgr = CustomCommandManager()
        mgr._load_from_dir(d)
        cmd = mgr.get("empty")
        assert cmd is not None
        assert cmd.template == ""


# ──────────────────────────────────────────────
# _load_builtins (reset behaviour)
# ──────────────────────────────────────────────


class TestLoadBuiltins:
    def test_load_builtins_clears_and_restores(self):
        mgr = CustomCommandManager()
        mgr.add(CommandConfig(name="extra", template="x"))
        assert len(mgr.list()) == 5
        mgr._load_builtins()
        assert len(mgr.list()) == 4
        assert mgr.get("extra") is None

    def test_load_builtins_after_override(self):
        mgr = CustomCommandManager()
        mgr.add(CommandConfig(name="test", template="override"))
        assert mgr.get("test").template == "override"
        mgr._load_builtins()
        assert mgr.get("test").template != "override"
