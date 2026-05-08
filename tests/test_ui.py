"""Tests for APEX UI."""

import pytest
from io import StringIO
from apex.ui import UI


@pytest.fixture
def ui():
    return UI()


def test_ui_init(ui):
    assert ui.console is not None


def test_show_banner(ui, capsys):
    ui.show_banner("gpt-4o", "/home/user/project")
    captured = capsys.readouterr()
    assert "APEX" in captured.out


def test_show_help(ui, capsys):
    ui.show_help()
    captured = capsys.readouterr()
    assert "/model" in captured.out
    assert "/help" in captured.out


def test_show_models(ui, capsys):
    from apex.config import MODELS
    ui.show_models("claude-sonnet")
    captured = capsys.readouterr()
    assert "Available Models" in captured.out
    assert "claude-sonnet" in captured.out


def test_print_user(ui, capsys):
    ui.print_user("Hello world")
    captured = capsys.readouterr()
    assert "Hello world" in captured.out


def test_print_response_plain(ui, capsys):
    ui.print_response("Plain text response")
    captured = capsys.readouterr()
    assert "Plain text response" in captured.out


def test_print_response_with_code(ui, capsys):
    ui.print_response("Here is code:\n```python\nprint('hello')\n```")
    captured = capsys.readouterr()
    assert "print('hello')" in captured.out


def test_print_tool_call(ui, capsys):
    ui.print_tool_call("read_file", {"path": "/test.txt"})
    captured = capsys.readouterr()
    assert "read_file" in captured.out


def test_print_tool_result_error(ui, capsys):
    ui.print_tool_result("read_file", "ERROR: File not found")
    captured = capsys.readouterr()
    assert "ERROR" in captured.out


def test_print_tool_result_success(ui, capsys):
    ui.print_tool_result("write_file", "SUCCESS: File written")
    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out


def test_print_error(ui, capsys):
    ui.print_error("Something went wrong")
    captured = capsys.readouterr()
    assert "Error" in captured.out or "wrong" in captured.out


def test_print_success(ui, capsys):
    ui.print_success("Operation completed")
    captured = capsys.readouterr()
    assert "completed" in captured.out


def test_print_info(ui, capsys):
    ui.print_info("Informational message")
    captured = capsys.readouterr()
    assert "Informational" in captured.out


def test_print_cost(ui, capsys):
    ui.print_cost({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
    captured = capsys.readouterr()
    assert "100" in captured.out or "150" in captured.out