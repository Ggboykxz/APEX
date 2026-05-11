"""Tests for refactored plugins module — no mocks, real objects."""

from pathlib import Path

from apex.refactored_plugins import (
    PluginInfo,
    PluginHook,
    PluginRegistry,
    PluginHookManager,
    PluginManager,
    BuiltInPlugins,
    create_plugin_manager,
)


class TestPluginInfo:
    def test_create_minimal(self):
        info = PluginInfo(name="test", version="1.0", description="Test plugin")
        assert info.name == "test"
        assert info.version == "1.0"
        assert info.description == "Test plugin"
        assert info.author == ""
        assert info.homepage == ""

    def test_create_full(self):
        info = PluginInfo(
            name="test",
            version="1.0",
            description="Test",
            author="Author",
            homepage="http://example.com",
        )
        assert info.author == "Author"
        assert info.homepage == "http://example.com"


class TestPluginHook:
    def test_create_default_priority(self):
        hook = PluginHook(name="test", callback=lambda: None)
        assert hook.name == "test"
        assert hook.priority == 0

    def test_create_with_priority(self):
        hook = PluginHook(name="test", callback=lambda: None, priority=5)
        assert hook.priority == 5


class TestPluginRegistry:
    def test_init(self):
        reg = PluginRegistry()
        assert reg._plugins == {}
        assert reg._enabled == {}

    def test_register(self):
        reg = PluginRegistry()
        reg.register("test", {"type": "plugin_obj"})
        assert "test" in reg._plugins
        assert reg._enabled["test"] is True

    def test_unregister(self):
        reg = PluginRegistry()
        reg.register("test", {"type": "plugin_obj"})
        reg.unregister("test")
        assert "test" not in reg._plugins
        assert "test" not in reg._enabled

    def test_unregister_not_exists(self):
        reg = PluginRegistry()
        reg.unregister("nonexistent")  # Should not raise

    def test_get_exists(self):
        reg = PluginRegistry()
        obj = {"type": "plugin_obj"}
        reg.register("test", obj)
        assert reg.get("test") is obj

    def test_get_not_exists(self):
        reg = PluginRegistry()
        assert reg.get("nonexistent") is None

    def test_is_enabled(self):
        reg = PluginRegistry()
        reg.register("test", {})
        assert reg.is_enabled("test") is True

    def test_is_enabled_not_registered(self):
        reg = PluginRegistry()
        assert reg.is_enabled("nonexistent") is False

    def test_enable(self):
        reg = PluginRegistry()
        reg.register("test", {})
        reg.disable("test")
        reg.enable("test")
        assert reg.is_enabled("test") is True

    def test_enable_not_registered(self):
        reg = PluginRegistry()
        reg.enable("nonexistent")  # Should not raise

    def test_disable(self):
        reg = PluginRegistry()
        reg.register("test", {})
        reg.disable("test")
        assert reg.is_enabled("test") is False

    def test_list_plugins(self):
        reg = PluginRegistry()
        reg.register("a", {})
        reg.register("b", {})
        assert sorted(reg.list_plugins()) == ["a", "b"]

    def test_list_enabled(self):
        reg = PluginRegistry()
        reg.register("a", {})
        reg.register("b", {})
        reg.disable("a")
        assert reg.list_enabled() == ["b"]


class TestPluginHookManager:
    def test_init(self):
        mgr = PluginHookManager()
        assert mgr._hooks == {}

    def test_register_hook(self):
        mgr = PluginHookManager()
        hook = PluginHook(name="test", callback=lambda: None)
        mgr.register_hook("event1", hook)
        assert "event1" in mgr._hooks
        assert len(mgr._hooks["event1"]) == 1

    def test_trigger_hook(self):
        mgr = PluginHookManager()
        called = []
        hook = PluginHook(name="test", callback=lambda: called.append(True))
        mgr.register_hook("event1", hook)
        mgr.trigger_hook("event1")
        assert len(called) == 1

    def test_trigger_hook_returns_results(self):
        mgr = PluginHookManager()
        hook = PluginHook(name="test", callback=lambda: 42)
        mgr.register_hook("event1", hook)
        results = mgr.trigger_hook("event1")
        assert results == [42]

    def test_trigger_hook_nonexistent_event(self):
        mgr = PluginHookManager()
        results = mgr.trigger_hook("nonexistent")
        assert results == []

    def test_trigger_hook_with_exception(self):
        mgr = PluginHookManager()

        def bad_callback():
            raise ValueError("oops")

        hook = PluginHook(name="bad", callback=bad_callback)
        mgr.register_hook("event1", hook)
        results = mgr.trigger_hook("event1")
        assert results == []

    def test_trigger_hook_multiple(self):
        mgr = PluginHookManager()
        results = []
        mgr.register_hook(
            "event1", PluginHook(name="h1", callback=lambda: results.append(1), priority=1)
        )
        mgr.register_hook(
            "event1", PluginHook(name="h2", callback=lambda: results.append(2), priority=0)
        )
        mgr.trigger_hook("event1")
        assert results == [1, 2]  # Higher priority first

    def test_trigger_hook_with_args(self):
        mgr = PluginHookManager()
        collected = []
        hook = PluginHook(name="test", callback=lambda x, y: collected.append((x, y)))
        mgr.register_hook("event1", hook)
        mgr.trigger_hook("event1", "a", "b")
        assert collected == [("a", "b")]

    def test_clear_hooks_specific(self):
        mgr = PluginHookManager()
        mgr.register_hook("event1", PluginHook(name="test", callback=lambda: None))
        mgr.clear_hooks("event1")
        assert mgr._hooks.get("event1") is None

    def test_clear_hooks_all(self):
        mgr = PluginHookManager()
        mgr.register_hook("event1", PluginHook(name="test", callback=lambda: None))
        mgr.register_hook("event2", PluginHook(name="test", callback=lambda: None))
        mgr.clear_hooks()
        assert mgr._hooks == {}

    def test_clear_hooks_nonexistent_event(self):
        mgr = PluginHookManager()
        mgr.clear_hooks("nonexistent")  # Should not raise


class TestPluginManager:
    def test_init(self):
        mgr = PluginManager()
        assert mgr._app is None
        assert mgr._plugin_dirs == []

    def test_init_with_dirs(self):
        mgr = PluginManager([Path("/plugins")])
        assert len(mgr._plugin_dirs) == 1

    def test_set_app(self):
        mgr = PluginManager()
        app = {"name": "test_app"}
        mgr.set_app(app)
        assert mgr.get_app() is app

    def test_load_plugins_from_directory_empty(self, tmp_path):
        mgr = PluginManager()
        result = mgr.load_plugins_from_directory(tmp_path)
        assert result == []

    def test_load_plugins_from_directory_not_exists(self, tmp_path):
        mgr = PluginManager()
        result = mgr.load_plugins_from_directory(tmp_path / "nonexistent")
        assert result == []

    def test_load_plugins_from_directory_with_files(self, tmp_path):
        (tmp_path / "test_plugin.py").write_text("# test")
        (tmp_path / "_private.py").write_text("# private")
        mgr = PluginManager()
        result = mgr.load_plugins_from_directory(tmp_path)
        assert "test_plugin" in result
        assert "_private" not in result

    def test_get_all_tools_empty(self):
        mgr = PluginManager()
        tools = mgr.get_all_tools()
        assert tools == []

    def test_get_all_tools_enabled_plugin(self):
        mgr = PluginManager()

        class ToolPlugin:
            def get_tools(self):
                return [{"name": "tool1"}]

        mgr.register("tool_plugin", ToolPlugin())
        tools = mgr.get_all_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "tool1"

    def test_get_all_tools_disabled_plugin(self):
        mgr = PluginManager()

        class ToolPlugin:
            def get_tools(self):
                return [{"name": "tool1"}]

        mgr.register("tool_plugin", ToolPlugin())
        mgr.disable("tool_plugin")
        tools = mgr.get_all_tools()
        assert tools == []

    def test_get_all_tools_no_get_tools(self):
        mgr = PluginManager()
        mgr.register("simple", {"just": "data"})
        tools = mgr.get_all_tools()
        assert tools == []

    def test_get_all_tools_get_tools_exception(self):
        mgr = PluginManager()

        class BadPlugin:
            def get_tools(self):
                raise RuntimeError("plugin error")

        mgr.register("bad", BadPlugin())
        tools = mgr.get_all_tools()
        assert tools == []

    def test_cleanup(self):
        cleaned = []

        class CleanPlugin:
            def cleanup(self):
                cleaned.append(True)

        mgr = PluginManager()
        mgr.register("test", CleanPlugin())
        mgr.cleanup("test")
        assert len(cleaned) == 1
        assert "test" not in mgr._plugins

    def test_cleanup_no_cleanup_method(self):
        mgr = PluginManager()
        mgr.register("test", {"just": "data"})
        mgr.cleanup("test")
        assert "test" not in mgr._plugins

    def test_cleanup_cleanup_exception(self):
        class BadPlugin:
            def cleanup(self):
                raise RuntimeError("cleanup error")

        mgr = PluginManager()
        mgr.register("test", BadPlugin())
        mgr.cleanup("test")  # Should not raise
        assert "test" not in mgr._plugins


class TestBuiltInPlugins:
    def test_create_logger_plugin(self):
        cls = BuiltInPlugins.create_logger_plugin()
        assert cls.info.name == "logger"
        plugin = cls()
        plugin.log("event", {"data": "test"})
        assert len(plugin.get_logs()) == 1
        assert plugin.get_logs()[0]["event"] == "event"

    def test_logger_plugin_initialize(self):
        cls = BuiltInPlugins.create_logger_plugin()
        plugin = cls()
        plugin.initialize({"app": "test"})  # Should not raise

    def test_logger_plugin_cleanup(self):
        cls = BuiltInPlugins.create_logger_plugin()
        plugin = cls()
        plugin.cleanup()  # Should not raise

    def test_logger_plugin_get_tools(self):
        cls = BuiltInPlugins.create_logger_plugin()
        plugin = cls()
        tools = plugin.get_tools()
        assert tools == []

    def test_create_telemetry_plugin(self):
        cls = BuiltInPlugins.create_telemetry_plugin()
        assert cls.info.name == "telemetry"
        plugin = cls()
        plugin.track_event("page_view", {"page": "/home"})
        assert len(plugin.get_events()) == 1
        assert plugin.get_events()[0]["event"] == "page_view"

    def test_telemetry_plugin_track_event_no_properties(self):
        cls = BuiltInPlugins.create_telemetry_plugin()
        plugin = cls()
        plugin.track_event("click")
        assert plugin.get_events()[0]["properties"] == {}

    def test_telemetry_plugin_initialize(self):
        cls = BuiltInPlugins.create_telemetry_plugin()
        plugin = cls()
        plugin.initialize({"app": "test"})  # Should not raise

    def test_telemetry_plugin_cleanup(self):
        cls = BuiltInPlugins.create_telemetry_plugin()
        plugin = cls()
        plugin.cleanup()  # Should not raise


class TestFactoryFunction:
    def test_create_plugin_manager(self):
        mgr = create_plugin_manager(["/plugins"])
        assert isinstance(mgr, PluginManager)
        assert len(mgr._plugin_dirs) == 1

    def test_create_plugin_manager_no_dirs(self):
        mgr = create_plugin_manager()
        assert isinstance(mgr, PluginManager)
        assert mgr._plugin_dirs == []
