"""Tests for tui.py main app."""

import pytest
from apex.tui import ApexApp


@pytest.mark.asyncio
async def test_apex_app_init():
    """Test ApexApp initializes."""
    app = ApexApp()
    assert app.model == "or-gpt4o-mini"
    assert app.cwd == "."
    assert app.sidebar_visible is True


@pytest.mark.asyncio
async def test_apex_app_init_custom():
    """Test ApexApp with custom parameters."""
    app = ApexApp(model="claude-sonnet", cwd="/home/user")
    assert app.model == "claude-sonnet"
    assert app.cwd == "/home/user"


@pytest.mark.asyncio
async def test_apex_app_theme_manager():
    """Test theme manager exists."""
    app = ApexApp()
    assert hasattr(app, 'current_theme_idx')
    assert app.current_theme_idx == 0


@pytest.mark.asyncio
async def test_apex_app_history():
    """Test message history exists."""
    app = ApexApp()
    assert hasattr(app, 'message_history')
    assert app.message_history == []
    assert app.history_index == -1


@pytest.mark.asyncio
async def test_apex_app_bindings():
    """Test app bindings exist."""
    app = ApexApp()
    bindings = [b.key for b in app.BINDINGS]
    assert "ctrl+k" in bindings
    assert "ctrl+l" in bindings
    assert "ctrl+t" in bindings


@pytest.mark.asyncio
async def test_apex_app_actions_exist():
    """Test action methods exist."""
    app = ApexApp()
    assert hasattr(app, 'action_clear_chat')
    assert hasattr(app, 'action_toggle_sidebar')
    assert hasattr(app, 'action_toggle_theme')
    assert hasattr(app, 'action_command_palette')
    assert hasattr(app, 'action_show_help')


@pytest.mark.asyncio
async def test_apex_app_message_handlers():
    """Test message handlers exist."""
    app = ApexApp()
    assert hasattr(app, 'on_input_bar_message')
    assert hasattr(app, 'on_palette_command')
    assert hasattr(app, 'onToggleSidebar')
    assert hasattr(app, 'onModelChanged')
    assert hasattr(app, 'onCwdChanged')