"""Tests for plugins module."""

import pytest
from apex.plugins import PluginManager, PluginInfo


class TestPluginInfo:
    """Test PluginInfo."""

    def test_init(self):
        info = PluginInfo(name="test", version="1.0", description="A test")
        assert info.name == "test"


class TestPluginManager:
    """Test PluginManager."""

    @pytest.fixture
    def mgr(self):
        return PluginManager()

    def test_init(self, mgr):
        assert hasattr(mgr, "_plugins")

    def test_list_plugins(self, mgr):
        result = mgr.list_plugins()
        assert isinstance(result, list)
