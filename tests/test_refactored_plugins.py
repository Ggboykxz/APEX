"""Tests for refactored plugins module."""

from unittest.mock import Mock

from apex.refactored_plugins import (
    PluginInfo, PluginHook, PluginRegistry, PluginHookManager, PluginManager,
    BuiltInPlugins, create_plugin_manager
)


class TestPluginInfo:
    def test_create_minimal(self):
        info = PluginInfo(name="test", version="1.0", description="Test plugin")
        assert info.name == "test"
        assert info.version == "1.0"
        assert info.description == "Test plugin"
    
    def test_create_full(self):
        info = PluginInfo(
            name="test", version="1.0", description="Test",
            author="Author", homepage="http://example.com"
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
        reg.register("test", Mock())
        assert "test" in reg._plugins
    
    def test_unregister(self):
        reg = PluginRegistry()
        reg.register("test", Mock())
        reg.unregister("test")
        assert "test" not in reg._plugins
    
    def test_get_exists(self):
        reg = PluginRegistry()
        plugin = Mock()
        reg.register("test", plugin)
        assert reg.get("test") is plugin
    
    def test_get_not_exists(self):
        reg = PluginRegistry()
        assert reg.get("nonexistent") is None
    
    def test_is_enabled(self):
        reg = PluginRegistry()
        reg.register("test", Mock())
        assert reg.is_enabled("test") is True
    
    def test_enable(self):
        reg = PluginRegistry()
        reg.register("test", Mock())
        reg.disable("test")
        reg.enable("test")
        assert reg.is_enabled("test") is True
    
    def test_disable(self):
        reg = PluginRegistry()
        reg.register("test", Mock())
        reg.disable("test")
        assert reg.is_enabled("test") is False
    
    def test_list_plugins(self):
        reg = PluginRegistry()
        reg.register("a", Mock())
        reg.register("b", Mock())
        assert sorted(reg.list_plugins()) == ["a", "b"]
    
    def test_list_enabled(self):
        reg = PluginRegistry()
        reg.register("a", Mock())
        reg.register("b", Mock())
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
    
    def test_trigger_hook(self):
        mgr = PluginHookManager()
        called = []
        hook = PluginHook(name="test", callback=lambda: called.append(True))
        mgr.register_hook("event1", hook)
        mgr.trigger_hook("event1")
        assert len(called) == 1
    
    def test_trigger_hook_multiple(self):
        mgr = PluginHookManager()
        results = []
        mgr.register_hook("event1", PluginHook(name="h1", callback=lambda: results.append(1), priority=1))
        mgr.register_hook("event1", PluginHook(name="h2", callback=lambda: results.append(2), priority=0))
        mgr.trigger_hook("event1")
        assert results == [1, 2]  # Higher priority first
    
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


class TestPluginManager:
    def test_init(self):
        mgr = PluginManager()
        assert mgr._app is None
    
    def test_set_app(self):
        mgr = PluginManager()
        app = Mock()
        mgr.set_app(app)
        assert mgr.get_app() is app
    
    def test_load_plugins_from_directory_empty(self, tmp_path):
        mgr = PluginManager()
        result = mgr.load_plugins_from_directory(tmp_path)
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
    
    def test_cleanup(self):
        mgr = PluginManager()
        plugin = Mock()
        mgr.register("test", plugin)
        mgr.cleanup("test")
        plugin.cleanup.assert_called_once()
        assert "test" not in mgr._plugins


class TestBuiltInPlugins:
    def test_create_logger_plugin(self):
        cls = BuiltInPlugins.create_logger_plugin()
        assert cls.info.name == "logger"
        plugin = cls()
        plugin.log("event", {"data": "test"})
        assert len(plugin.get_logs()) == 1
    
    def test_create_telemetry_plugin(self):
        cls = BuiltInPlugins.create_telemetry_plugin()
        assert cls.info.name == "telemetry"
        plugin = cls()
        plugin.track_event("page_view", {"page": "/home"})
        assert len(plugin.get_events()) == 1


class TestFactoryFunction:
    def test_create_plugin_manager(self):
        mgr = create_plugin_manager(["/plugins"])
        assert isinstance(mgr, PluginManager)
        assert len(mgr._plugin_dirs) == 1