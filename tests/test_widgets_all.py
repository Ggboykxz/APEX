"""Tests for all TUI widgets using Textual testing framework."""

import pytest
from textual.app import App
from apex.widgets import SidebarPane, ChatPane, InputBar, StatusBar


class SidebarTestApp(App):
    """Test app for sidebar."""

    def compose(self):
        yield SidebarPane(".")


class ChatTestApp(App):
    """Test app for chat."""

    def compose(self):
        yield ChatPane()


class InputTestApp(App):
    """Test app for input."""

    def compose(self):
        yield InputBar()


class StatusTestApp(App):
    """Test app for status."""

    def compose(self):
        yield StatusBar()


# ===== SidebarPane Tests =====
@pytest.mark.asyncio
async def test_sidebar_pane_init():
    """Test SidebarPane initializes."""
    app = SidebarTestApp()
    async with app.run_test() as _:
        sidebar = app.query_one(SidebarPane)
        assert sidebar is not None
        assert sidebar.cwd == "."


@pytest.mark.asyncio
async def test_sidebar_pane_update_cwd():
    """Test SidebarPane update_cwd method."""
    app = SidebarTestApp()
    async with app.run_test() as _:
        sidebar = app.query_one(SidebarPane)
        sidebar.update_cwd("/new/path")
        assert sidebar.cwd == "/new/path"


# ===== ChatPane Tests =====
@pytest.mark.asyncio
async def test_chat_pane_init():
    """Test ChatPane initializes."""
    app = ChatTestApp()
    async with app.run_test() as _:
        chat = app.query_one(ChatPane)
        assert chat is not None
        assert chat.messages == []


@pytest.mark.asyncio
async def test_chat_pane_add_user_message():
    """Test adding user message (does not raise)."""
    app = ChatTestApp()
    async with app.run_test() as _:
        chat = app.query_one(ChatPane)
        chat.add_user_message("Hello")


@pytest.mark.asyncio
async def test_chat_pane_add_ai_message():
    """Test adding AI message (does not raise)."""
    app = ChatTestApp()
    async with app.run_test() as _:
        chat = app.query_one(ChatPane)
        chat.add_ai_message("Hi there", "gpt-4o")


@pytest.mark.asyncio
async def test_chat_pane_clear():
    """Test clearing chat."""
    app = ChatTestApp()
    async with app.run_test() as _:
        chat = app.query_one(ChatPane)
        chat.add_user_message("Hello")
        chat.clear()
        assert chat.messages == []


@pytest.mark.asyncio
async def test_chat_pane_scroll_end():
    """Test scroll_end method."""
    app = ChatTestApp()
    async with app.run_test() as _:
        chat = app.query_one(ChatPane)
        chat.scroll_end()


# ===== InputBar Tests =====
@pytest.mark.asyncio
async def test_input_bar_init():
    """Test InputBar initializes."""
    app = InputTestApp()
    async with app.run_test() as _:
        input_bar = app.query_one(InputBar)
        assert input_bar is not None
        assert input_bar.is_thinking is False
        assert input_bar.current_input == ""


@pytest.mark.asyncio
async def test_input_bar_set_thinking():
    """Test set_thinking method."""
    app = InputTestApp()
    async with app.run_test() as _:
        input_bar = app.query_one(InputBar)
        input_bar.set_thinking(True)
        assert input_bar.is_thinking is True


# ===== StatusBar Tests =====
@pytest.mark.asyncio
async def test_status_bar_init():
    """Test StatusBar initializes."""
    app = StatusTestApp()
    async with app.run_test() as _:
        status = app.query_one(StatusBar)
        assert status is not None


@pytest.mark.asyncio
async def test_status_bar_update_status():
    """Test update_status method."""
    app = StatusTestApp()
    async with app.run_test() as _:
        status = app.query_one(StatusBar)
        status.update_status(True, "gpt-4o")
        assert status.is_thinking is True
        assert status.model == "gpt-4o"