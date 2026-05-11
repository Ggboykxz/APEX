"""Tests for apex/plugins.py — PluginManager, PluginBase, BuiltInPlugins, _check_code_safety."""

import pytest
import tempfile
import os
from pathlib import Path
from apex.plugins import (
    _check_code_safety,
    PluginInfo,
    PluginBase,
    PluginHook,
    PluginManager,
    BuiltInPlugins,
    plugin_manager,
    load_plugins_from_config,
)


# ---------------------------------------------------------------------------
# _check_code_safety
# ---------------------------------------------------------------------------


class TestCheckCodeSafety:
    def test_clean_code(self):
        issues = _check_code_safety("x = 1 + 2")
        assert issues == []

    def test_eval(self):
        issues = _check_code_safety("eval('1+1')")
        assert any("eval" in i for i in issues)

    def test_exec(self):
        issues = _check_code_safety("exec('code')")
        assert any("exec" in i for i in issues)

    def test_import(self):
        issues = _check_code_safety("__import__('os')")
        assert any("__import__" in i for i in issues)

    def test_shell_true(self):
        issues = _check_code_safety("subprocess.run(cmd, shell=True)")
        assert any("shell=True" in i for i in issues)

    def test_os_system(self):
        issues = _check_code_safety("os.system('rm -rf /')")
        assert any("os.system" in i for i in issues)

    def test_os_popen(self):
        issues = _check_code_safety("os.popen('ls')")
        assert any("os.popen" in i for i in issues)

    def test_pickle_load(self):
        issues = _check_code_safety("pickle.load(f)")
        assert any("pickle" in i for i in issues)

    def test_marshal_load(self):
        issues = _check_code_safety("marshal.load(f)")
        assert any("marshal" in i for i in issues)

    def test_tempfile_mktemp(self):
        issues = _check_code_safety("tempfile.mktemp()")
        assert any("tempfile" in i for i in issues)

    def test_read_text(self):
        issues = _check_code_safety("file.read_text()")
        assert any("file read" in i for i in issues)

    def test_write_text(self):
        issues = _check_code_safety("file.write_text('data')")
        assert any("file write" in i for i in issues)

    def test_multiple_issues(self):
        code = "eval('1')\nexec('2')\n__import__('os')"
        issues = _check_code_safety(code)
        assert len(issues) >= 3


# ---------------------------------------------------------------------------
# PluginInfo
# ---------------------------------------------------------------------------


class TestPluginInfo:
    def test_creation(self):
        info = PluginInfo(name="test", version="1.0", description="Test plugin")
        assert info.name == "test"
        assert info.version == "1.0"
        assert info.description == "Test plugin"
        assert info.author == ""
        assert info.dependencies == []

    def test_with_all_fields(self):
        info = PluginInfo(
            name="test",
            version="2.0",
            description="desc",
            author="me",
            dependencies=["dep1", "dep2"],
        )
        assert info.author == "me"
        assert info.dependencies == ["dep1", "dep2"]


# ---------------------------------------------------------------------------
# PluginBase
# ---------------------------------------------------------------------------


class TestPluginBase:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            PluginBase()

    def test_concrete_subclass(self):
        class MyPlugin(PluginBase):
            info = PluginInfo(name="my", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        plugin = MyPlugin()
        assert plugin.info.name == "my"
        plugin.initialize(None)
        plugin.cleanup()


# ---------------------------------------------------------------------------
# PluginHook
# ---------------------------------------------------------------------------


class TestPluginHook:
    def test_creation(self):
        hook = PluginHook(name="test", callback=lambda: None, priority=5)
        assert hook.name == "test"
        assert hook.priority == 5

    def test_default_priority(self):
        hook = PluginHook(name="test", callback=lambda: None)
        assert hook.priority == 0


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------


class TestPluginManager:
    def test_init(self):
        pm = PluginManager()
        assert pm._plugins == {}
        assert pm._hooks == {}
        assert pm._plugin_dirs == []
        assert pm._app is None
        assert pm._enabled == {}

    def test_init_with_dirs(self):
        pm = PluginManager(plugin_dirs=[Path("/tmp")])
        assert Path("/tmp") in pm._plugin_dirs

    def test_set_app(self):
        pm = PluginManager()
        pm.set_app("myapp")
        assert pm._app == "myapp"

    def test_add_plugin_dir(self):
        pm = PluginManager()
        pm.add_plugin_dir(Path("/tmp/test"))
        assert Path("/tmp/test") in pm._plugin_dirs

    def test_add_plugin_dir_no_duplicate(self):
        pm = PluginManager()
        p = Path("/tmp/test")
        pm.add_plugin_dir(p)
        pm.add_plugin_dir(p)
        assert pm._plugin_dirs.count(p) == 1

    def test_register_hook(self):
        pm = PluginManager()
        pm.register_hook("test_hook", lambda: "result")
        assert "test_hook" in pm._hooks
        assert len(pm._hooks["test_hook"]) == 1

    def test_register_hook_priority(self):
        pm = PluginManager()
        pm.register_hook("test", lambda: "low", priority=10)
        pm.register_hook("test", lambda: "high", priority=1)
        assert pm._hooks["test"][0].priority == 1
        assert pm._hooks["test"][1].priority == 10

    def test_trigger_hook(self):
        pm = PluginManager()
        pm.register_hook("test", lambda x: x * 2)
        results = pm.trigger_hook("test", 5)
        assert results == [10]

    def test_trigger_hook_no_hooks(self):
        pm = PluginManager()
        results = pm.trigger_hook("nonexistent")
        assert results == []

    def test_trigger_hook_exception(self):
        pm = PluginManager()

        def bad_hook():
            raise RuntimeError("fail")

        pm.register_hook("test", bad_hook)
        # Should catch exception and continue
        pm.register_hook("test", lambda: "ok")
        results = pm.trigger_hook("test")
        assert "ok" in results

    def test_discover_plugins_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            discovered = asyncio_run(pm.discover_plugins())
            assert discovered == []

    def test_discover_plugins_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "my_plugin.py"
            plugin_file.write_text("# test plugin")
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            discovered = asyncio_run(pm.discover_plugins())
            assert "my_plugin" in discovered

    def test_discover_plugins_with_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "my_plugin_dir"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.py").write_text("# plugin")
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            discovered = asyncio_run(pm.discover_plugins())
            assert "my_plugin_dir" in discovered

    def test_discover_plugins_skips_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "__init__.py").write_text("# init")
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            discovered = asyncio_run(pm.discover_plugins())
            assert "__init__" not in discovered

    def test_discover_plugins_nonexistent_dir(self):
        pm = PluginManager(plugin_dirs=[Path("/nonexistent/path")])
        discovered = asyncio_run(pm.discover_plugins())
        assert discovered == []

    def test_load_plugin_nonexistent(self):
        pm = PluginManager()
        assert pm.load_plugin("nonexistent") is False

    def test_load_plugin_dangerous_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "dangerous.py"
            plugin_file.write_text("eval('1+1')")
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            # Without APEX_ALLOW_DANGEROUS_PLUGINS, should be blocked
            os.environ.pop("APEX_ALLOW_DANGEROUS_PLUGINS", None)
            result = pm.load_plugin("dangerous")
            assert result is False

    def test_load_plugin_with_dangerous_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "dangerous.py"
            plugin_file.write_text(
                "from apex.plugins import PluginBase, PluginInfo\n"
                "class Plugin(PluginBase):\n"
                "    info = PluginInfo(name='dangerous', version='1.0')\n"
                "    def initialize(self, app): pass\n"
                "    def cleanup(self): pass\n"
            )
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            pm.set_app("test_app")
            os.environ["APEX_ALLOW_DANGEROUS_PLUGINS"] = "true"
            try:
                result = pm.load_plugin("dangerous")
                assert result is True
            finally:
                del os.environ["APEX_ALLOW_DANGEROUS_PLUGINS"]

    def test_unload_plugin(self):
        pm = PluginManager()

        # Manually add a plugin
        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        plugin = TestPlugin()
        pm._plugins["test"] = plugin
        pm._enabled["test"] = True
        result = pm.unload_plugin("test")
        assert result is True
        assert "test" not in pm._plugins
        assert "test" not in pm._enabled

    def test_unload_nonexistent(self):
        pm = PluginManager()
        assert pm.unload_plugin("nonexistent") is False

    def test_enable_plugin(self):
        pm = PluginManager()

        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        pm._plugins["test"] = TestPlugin()
        result = pm.enable_plugin("test")
        assert result is True
        assert pm._enabled["test"] is True

    def test_enable_plugin_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PluginManager(plugin_dirs=[Path(tmpdir)])
            # load_plugin will fail since file doesn't exist
            result = pm.enable_plugin("nonexistent")
            assert result is False

    def test_disable_plugin(self):
        pm = PluginManager()

        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        pm._plugins["test"] = TestPlugin()
        pm._enabled["test"] = True
        result = pm.disable_plugin("test")
        assert result is True
        assert pm._enabled["test"] is False

    def test_disable_nonexistent(self):
        pm = PluginManager()
        assert pm.disable_plugin("nonexistent") is False

    def test_get_plugin(self):
        pm = PluginManager()

        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        plugin = TestPlugin()
        pm._plugins["test"] = plugin
        assert pm.get_plugin("test") is plugin
        assert pm.get_plugin("nonexistent") is None

    def test_list_plugins(self):
        pm = PluginManager()

        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        pm._plugins["test"] = TestPlugin()
        pm._enabled["test"] = True
        result = pm.list_plugins()
        assert len(result) == 1
        assert result[0]["name"] == "test"
        assert result[0]["enabled"] is True

    def test_get_tools_no_tools(self):
        pm = PluginManager()

        class TestPlugin(PluginBase):
            info = PluginInfo(name="test", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

        pm._plugins["test"] = TestPlugin()
        pm._enabled["test"] = True
        tools = pm.get_tools()
        assert tools == []

    def test_get_tools_with_tools(self):
        pm = PluginManager()

        class ToolPlugin(PluginBase):
            info = PluginInfo(name="tool", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

            def get_tools(self):
                return [{"name": "my_tool"}]

        pm._plugins["tool"] = ToolPlugin()
        pm._enabled["tool"] = True
        tools = pm.get_tools()
        assert len(tools) == 1

    def test_get_tools_disabled(self):
        pm = PluginManager()

        class ToolPlugin(PluginBase):
            info = PluginInfo(name="tool", version="1.0")

            def initialize(self, app):
                pass

            def cleanup(self):
                pass

            def get_tools(self):
                return [{"name": "my_tool"}]

        pm._plugins["tool"] = ToolPlugin()
        pm._enabled["tool"] = False
        tools = pm.get_tools()
        assert tools == []


# ---------------------------------------------------------------------------
# BuiltInPlugins
# ---------------------------------------------------------------------------


class TestBuiltInPlugins:
    def test_create_logger_plugin(self):
        cls = BuiltInPlugins.create_logger_plugin()
        assert issubclass(cls, PluginBase)
        assert cls.info.name == "logger"

    def test_create_security_scanner_plugin(self):
        cls = BuiltInPlugins.create_security_scanner_plugin()
        assert issubclass(cls, PluginBase)
        assert cls.info.name == "security_scanner"

    def test_logger_plugin_methods(self):
        cls = BuiltInPlugins.create_logger_plugin()
        plugin = cls()

        # Create a simple app-like object with plugin_manager
        class FakeApp:
            def __init__(self):
                self.plugin_manager = PluginManager()

        app = FakeApp()
        plugin.initialize(app)
        # on_tool_call and on_agent_message should not crash
        plugin.on_tool_call("test_tool", {"arg": "value"})
        plugin.on_agent_message("test message")
        plugin.cleanup()

    def test_security_scanner_methods(self):
        cls = BuiltInPlugins.create_security_scanner_plugin()
        plugin = cls()

        class FakeApp:
            def __init__(self):
                self.plugin_manager = PluginManager()

        app = FakeApp()
        plugin.initialize(app)

        # scan_tool should return True
        assert plugin.scan_tool("write_file", {"content": "clean code"}) is True

        # Scan code with dangerous patterns
        issues = plugin._scan_code("eval('1+1')")
        assert len(issues) > 0

        # get_tools
        tools = plugin.get_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "security_scan"

        plugin.cleanup()


# ---------------------------------------------------------------------------
# load_plugins_from_config
# ---------------------------------------------------------------------------


class TestLoadPluginsFromConfig:
    def test_nonexistent_file(self):
        load_plugins_from_config(Path("/nonexistent/config.yaml"), app=None)

    def test_empty_file(self, tmp_path):
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")
        try:
            load_plugins_from_config(config_path, app=None)
        except ImportError:
            pass

    def test_no_plugins_key(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_key: value\n")
        try:
            load_plugins_from_config(config_path, app=None)
        except ImportError:
            pass


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------


class TestGlobalInstance:
    def test_plugin_manager_global(self):
        assert isinstance(plugin_manager, PluginManager)


# Helper
def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
