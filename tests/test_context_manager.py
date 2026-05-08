"""Tests for APEX context manager and sandbox."""

import pytest
from apex.context_manager import ContextWindow, ConversationManager, AutoSaveManager
from apex.sandbox import CodeSandbox, ShellSession


def test_context_window_estimate_tokens():
    cw = ContextWindow(max_tokens=1000)
    assert cw.estimate_tokens("hello world") > 0


def test_context_window_should_compress():
    cw = ContextWindow(max_tokens=100, compress_threshold=0.5)
    messages = [{"role": "user", "content": "x" * 500}] * 10
    assert cw.should_compress(messages) is True


def test_context_window_compress_messages():
    cw = ContextWindow(max_tokens=1000)
    messages = [
        {"role": "user", "content": f"message {i}"}
        for i in range(60)
    ]
    compressed = cw.compress_messages(messages)
    assert len(compressed) < len(messages)


def test_conversation_manager_add_message():
    cm = ConversationManager()
    cm.add_message("user", "Hello")
    cm.add_message("assistant", "Hi there")
    assert len(cm.get_messages()) == 2


def test_conversation_manager_search():
    cm = ConversationManager()
    cm.add_message("user", "How to use Python?")
    cm.add_message("assistant", "Python is great")
    results = cm.search("Python")
    assert len(results) == 2


def test_conversation_manager_bookmark():
    cm = ConversationManager()
    for i in range(10):
        cm.add_message("user", f"message {i}")
    cm.bookmark("important")
    restored = cm.restore_bookmark("important")
    assert len(restored) >= 0


def test_conversation_manager_stats():
    cm = ConversationManager()
    cm.add_message("user", "Hello")
    cm.add_message("assistant", "Hi")
    stats = cm.get_stats()
    assert stats["message_count"] == 2
    assert stats["roles"]["user"] == 1
    assert stats["roles"]["assistant"] == 1


def test_code_sandbox_python():
    sb = CodeSandbox(timeout=10)
    result = sb.run_code("print('Hello from sandbox')", "python")
    assert "Hello from sandbox" in result


def test_code_sandbox_unsupported_language():
    sb = CodeSandbox()
    result = sb.run_code("code", "unsupported")
    assert "ERROR: Unsupported language" in result


def test_code_sandbox_timeout():
    sb = CodeSandbox(timeout=1)
    result = sb.run_code("import time; time.sleep(10)", "python")
    assert "timed out" in result.lower()


def test_shell_session_start():
    shell = ShellSession()
    assert shell.start() is True
    shell.close()


def test_autosave_manager(tmp_path):
    asm = AutoSaveManager(save_dir=str(tmp_path))
    asm.save_state({"test": "data", "messages": []})
    state = asm.load_state()
    assert state is not None
    assert state["test"] == "data"


def test_autosave_manager_clear(tmp_path):
    asm = AutoSaveManager(save_dir=str(tmp_path))
    asm.save_state({"test": "data"})
    asm.clear()
    state = asm.load_state()
    assert state is None