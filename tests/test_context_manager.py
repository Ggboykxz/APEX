"""Tests for APEX context manager — no mocks, real file system."""

from apex.context_manager import ContextWindow, MessageSummary, ConversationManager, AutoSaveManager


# ---------------------------------------------------------------------------
# MessageSummary
# ---------------------------------------------------------------------------


class TestMessageSummary:
    def test_creation(self):
        ms = MessageSummary(summary="test summary", message_count=5, token_estimate=100)
        assert ms.summary == "test summary"
        assert ms.message_count == 5
        assert ms.token_estimate == 100


# ---------------------------------------------------------------------------
# ContextWindow
# ---------------------------------------------------------------------------


class TestContextWindowInit:
    def test_default_values(self):
        cw = ContextWindow()
        assert cw.max_tokens == 100000
        assert cw.compress_threshold == 0.8
        assert cw.summary_messages == 50
        assert cw._last_summary is None

    def test_custom_values(self):
        cw = ContextWindow(max_tokens=500, compress_threshold=0.5, summary_messages=10)
        assert cw.max_tokens == 500
        assert cw.compress_threshold == 0.5
        assert cw.summary_messages == 10


class TestContextWindowEstimateTokens:
    def test_empty_string(self):
        cw = ContextWindow()
        assert cw.estimate_tokens("") == 0

    def test_short_string(self):
        cw = ContextWindow()
        assert cw.estimate_tokens("hello") == 1  # 5 // 4

    def test_long_string(self):
        cw = ContextWindow()
        text = "a" * 400
        assert cw.estimate_tokens(text) == 100


class TestContextWindowShouldCompress:
    def test_below_threshold(self):
        cw = ContextWindow(max_tokens=1000, compress_threshold=0.8)
        messages = [{"role": "user", "content": "short"}]
        assert cw.should_compress(messages) is False

    def test_above_threshold(self):
        cw = ContextWindow(max_tokens=100, compress_threshold=0.5)
        messages = [{"role": "user", "content": "x" * 500}] * 10
        assert cw.should_compress(messages) is True

    def test_empty_messages(self):
        cw = ContextWindow(max_tokens=100, compress_threshold=0.8)
        assert cw.should_compress([]) is False

    def test_messages_with_empty_content(self):
        cw = ContextWindow(max_tokens=10, compress_threshold=0.5)
        messages = [{"role": "user", "content": ""}] * 5
        assert cw.should_compress(messages) is False


class TestContextWindowCompressMessages:
    def test_below_threshold_messages(self):
        """Messages below summary_messages are returned unchanged."""
        cw = ContextWindow(summary_messages=100)
        messages = [{"role": "user", "content": "hi"}]
        result = cw.compress_messages(messages)
        assert result == messages

    def test_compress_creates_summary(self):
        """Compressing many messages creates a summary."""
        cw = ContextWindow(max_tokens=100000, summary_messages=5)
        messages = [{"role": "user", "content": f"message {i}"} for i in range(30)]
        compressed = cw.compress_messages(messages)
        assert len(compressed) < len(messages)
        # Should have system messages at the start
        assert compressed[0]["role"] == "system"

    def test_compress_with_summary_prompt(self):
        """Compress passes summary_prompt to the compressed output."""
        cw = ContextWindow(summary_messages=5)
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        compressed = cw.compress_messages(messages, summary_prompt="Custom prompt")
        assert any("Custom prompt" in m.get("content", "") for m in compressed)

    def test_compress_sets_last_summary(self):
        """Compress sets _last_summary."""
        cw = ContextWindow(summary_messages=5)
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        cw.compress_messages(messages)
        assert cw._last_summary is not None
        assert isinstance(cw._last_summary, MessageSummary)
        assert cw._last_summary.message_count > 0


# ---------------------------------------------------------------------------
# ConversationManager
# ---------------------------------------------------------------------------


class TestConversationManagerInit:
    def test_default_max_history(self):
        cm = ConversationManager()
        assert cm.max_history == 1000
        assert cm._history == []
        assert cm._bookmarks == {}


class TestConversationManagerAddMessage:
    def test_add_message(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        assert len(cm._history) == 1
        assert cm._history[0]["role"] == "user"
        assert cm._history[0]["content"] == "Hello"

    def test_add_message_with_metadata(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello", metadata={"key": "value"})
        assert cm._history[0]["metadata"] == {"key": "value"}

    def test_add_message_without_metadata(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        assert "metadata" not in cm._history[0]

    def test_add_many_messages_trims(self):
        cm = ConversationManager(max_history=10)
        for i in range(20):
            cm.add_message("user", f"msg {i}")
        assert len(cm._history) <= 10


class TestConversationManagerGetMessages:
    def test_get_messages_returns_copy(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        msgs = cm.get_messages()
        msgs.append({"role": "test", "content": "extra"})
        assert len(cm._history) == 1  # original unchanged


class TestConversationManagerSetMessages:
    def test_set_messages(self):
        cm = ConversationManager()
        msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        cm.set_messages(msgs)
        assert len(cm._history) == 2

    def test_set_messages_truncates_to_max(self):
        cm = ConversationManager(max_history=5)
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        cm.set_messages(msgs)
        assert len(cm._history) == 5


class TestConversationManagerTrimHistory:
    def test_trim_produces_summary(self):
        cm = ConversationManager(max_history=10)
        for i in range(20):
            cm.add_message("user", f"msg {i}")
        # After trimming, first message should be a summary
        assert cm._history[0]["role"] == "system"
        assert "trimmed" in cm._history[0]["content"]


class TestConversationManagerBookmark:
    def test_bookmark_and_restore(self):
        cm = ConversationManager()
        for i in range(5):
            cm.add_message("user", f"before {i}")
        cm.bookmark("checkpoint")
        cm.add_message("user", "after checkpoint")
        restored = cm.restore_bookmark("checkpoint")
        assert len(restored) == 1
        assert "after checkpoint" in restored[0]["content"]

    def test_restore_nonexistent_bookmark(self):
        cm = ConversationManager()
        result = cm.restore_bookmark("nonexistent")
        assert result is None


class TestConversationManagerSearch:
    def test_search_finds_matching(self):
        cm = ConversationManager()
        cm.add_message("user", "How to use Python?")
        cm.add_message("assistant", "Python is great")
        cm.add_message("user", "What about Rust?")
        results = cm.search("Python")
        assert len(results) == 2

    def test_search_case_insensitive(self):
        cm = ConversationManager()
        cm.add_message("user", "PYTHON is fun")
        results = cm.search("python")
        assert len(results) == 1

    def test_search_no_results(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        results = cm.search("xyz")
        assert len(results) == 0


class TestConversationManagerClear:
    def test_clear(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        cm.bookmark("test")
        cm.clear()
        assert len(cm._history) == 0
        assert len(cm._bookmarks) == 0


class TestConversationManagerStats:
    def test_get_stats(self):
        cm = ConversationManager()
        cm.add_message("user", "Hello")
        cm.add_message("assistant", "Hi")
        cm.add_message("user", "How are you?")
        stats = cm.get_stats()
        assert stats["message_count"] == 3
        assert stats["bookmarks"] == 0
        assert stats["roles"]["user"] == 2
        assert stats["roles"]["assistant"] == 1


class TestConversationManagerCountRoles:
    def test_count_roles(self):
        cm = ConversationManager()
        cm.add_message("user", "a")
        cm.add_message("assistant", "b")
        cm.add_message("system", "c")
        cm.add_message("user", "d")
        counts = cm._count_roles()
        assert counts["user"] == 2
        assert counts["assistant"] == 1
        assert counts["system"] == 1


# ---------------------------------------------------------------------------
# AutoSaveManager
# ---------------------------------------------------------------------------


class TestAutoSaveManager:
    def test_init_creates_dir(self, tmp_path):
        save_dir = tmp_path / "saves"
        AutoSaveManager(save_dir=str(save_dir))
        assert save_dir.exists()

    def test_save_and_load_state(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        asm.save_state({"test": "data", "messages": []})
        state = asm.load_state()
        assert state is not None
        assert state["test"] == "data"
        assert "timestamp" in state
        assert "version" in state
        assert state["version"] == "0.3.0"

    def test_load_state_no_file(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        state = asm.load_state()
        assert state is None

    def test_load_state_corrupt_json(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        asm._current_file.write_text("{invalid json")
        state = asm.load_state()
        assert state is None

    def test_clear(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        asm.save_state({"test": "data"})
        asm.clear()
        state = asm.load_state()
        assert state is None

    def test_clear_no_file(self, tmp_path):
        """Clearing when no file exists doesn't raise."""
        asm = AutoSaveManager(save_dir=str(tmp_path))
        asm.clear()  # should not raise

    def test_list_saves(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        asm.save_state({"save1": True})
        saves = asm.list_saves()
        assert len(saves) >= 1
        assert saves[0]["name"] == "current"
        assert saves[0]["size"] > 0

    def test_list_saves_empty(self, tmp_path):
        asm = AutoSaveManager(save_dir=str(tmp_path))
        saves = asm.list_saves()
        assert saves == []
