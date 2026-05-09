"""Tests for widgets using Textual app testing."""

import pytest
from textual.app import App
from textual.widgets import Static, Button
from apex.widgets import HeaderBar


class HeaderTestApp(App):
    """Test app for header."""

    def compose(self):
        yield HeaderBar()


@pytest.mark.asyncio
async def test_header_bar_init():
    """Test HeaderBar initializes."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        assert header is not None


@pytest.mark.asyncio
async def test_header_model_alias_reactive():
    """Test model_alias reactive property."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        header.model_alias = "claude-sonnet"
        assert header.model_alias == "claude-sonnet"


@pytest.mark.asyncio
async def test_header_cwd_reactive():
    """Test cwd reactive property."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        header.cwd = "/home/user"
        assert header.cwd == "/home/user"


@pytest.mark.asyncio
async def test_header_token_count_reactive():
    """Test token_count reactive property."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        header.token_count = 1500
        assert header.token_count == 1500


@pytest.mark.asyncio
async def test_header_cost_usd_reactive():
    """Test cost_usd reactive property."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        header.cost_usd = 0.05
        assert header.cost_usd == 0.05


@pytest.mark.asyncio
async def test_header_update_tokens():
    """Test update_tokens method."""
    app = HeaderTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(HeaderBar)
        header.update_tokens(2000, 0.1)
        assert header.token_count == 2000
        assert header.cost_usd == 0.1