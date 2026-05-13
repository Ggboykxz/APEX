"""Tests for context_tracking module — no mocks, real objects only."""

from apex.context_tracking import ContextManager


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestContextManagerInit:
    def test_default_initialization(self):
        ctx = ContextManager()
        assert ctx.max_tokens == 1000000
        assert ctx.compaction_threshold == 0.9
        assert ctx._messages == []
        assert ctx._token_count == 0
        assert ctx._cache_hits == 0
        assert ctx._cache_misses == 0
        assert ctx._compaction_history == []

    def test_custom_initialization(self):
        ctx = ContextManager(max_tokens=500, compaction_threshold=0.5)
        assert ctx.max_tokens == 500
        assert ctx.compaction_threshold == 0.5


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_empty_string(self):
        ctx = ContextManager()
        assert ctx.estimate_tokens("") == 0

    def test_short_string(self):
        ctx = ContextManager()
        assert ctx.estimate_tokens("hello") == 1  # 5 // 4

    def test_long_string(self):
        ctx = ContextManager()
        text = "a" * 1000
        assert ctx.estimate_tokens(text) == 250

    def test_exactly_four_chars(self):
        ctx = ContextManager()
        assert ctx.estimate_tokens("abcd") == 1


# ---------------------------------------------------------------------------
# add_message
# ---------------------------------------------------------------------------


class TestAddMessage:
    def test_add_single_message(self):
        ctx = ContextManager(max_tokens=1000)
        tokens = ctx.add_message("user", "hello")
        assert tokens > 0
        assert len(ctx._messages) == 1
        assert ctx._messages[0]["role"] == "user"
        assert ctx._messages[0]["content"] == "hello"

    def test_add_multiple_messages(self):
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "hello")
        ctx.add_message("assistant", "hi there")
        assert len(ctx._messages) == 2

    def test_add_updates_token_count(self):
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "hello world test")
        assert ctx._token_count > 0


# ---------------------------------------------------------------------------
# get_messages
# ---------------------------------------------------------------------------


class TestGetMessages:
    def test_returns_copy(self):
        ctx = ContextManager()
        ctx.add_message("user", "hello")
        msgs = ctx.get_messages()
        msgs.append({"role": "test", "content": "extra"})
        assert len(ctx._messages) == 1  # original unchanged

    def test_empty(self):
        ctx = ContextManager()
        assert ctx.get_messages() == []


# ---------------------------------------------------------------------------
# token_count property
# ---------------------------------------------------------------------------


class TestTokenCount:
    def test_initial_zero(self):
        ctx = ContextManager()
        assert ctx.token_count == 0

    def test_after_add(self):
        ctx = ContextManager()
        ctx.add_message("user", "hello")
        assert ctx.token_count > 0


# ---------------------------------------------------------------------------
# utilization property
# ---------------------------------------------------------------------------


class TestUtilization:
    def test_initial_zero(self):
        ctx = ContextManager(max_tokens=1000)
        assert ctx.utilization == 0.0

    def test_after_add(self):
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "hello world test message")
        util = ctx.utilization
        assert 0 < util <= 1


# ---------------------------------------------------------------------------
# should_compact
# ---------------------------------------------------------------------------


class TestShouldCompact:
    def test_false_when_below_threshold(self):
        ctx = ContextManager(max_tokens=1000, compaction_threshold=0.9)
        assert ctx.should_compact() is False

    def test_true_when_above_threshold(self):
        ctx = ContextManager(max_tokens=10, compaction_threshold=0.9)
        ctx.add_message("user", "a" * 100)
        assert ctx.should_compact() is True

    def test_at_exact_threshold(self):
        ctx = ContextManager(max_tokens=100, compaction_threshold=0.5)
        # Add exactly 50 tokens worth of text (200 chars)
        ctx.add_message("user", "a" * 200)
        assert ctx.should_compact() is True


# ---------------------------------------------------------------------------
# compact
# ---------------------------------------------------------------------------


class TestCompact:
    def test_compact_no_messages(self):
        ctx = ContextManager()
        result = ctx.compact()
        assert result == 0

    def test_compact_summarize(self):
        ctx = ContextManager(max_tokens=1000)
        for i in range(10):
            ctx.add_message("user", f"message {i}")
        result = ctx.compact(strategy="summarize")
        assert isinstance(result, int)

    def test_compact_summarize_few_messages(self):
        """Summarize with <4 messages does nothing special."""
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "hi")
        ctx.add_message("assistant", "hello")
        result = ctx.compact(strategy="summarize")
        assert isinstance(result, int)

    def test_compact_prune(self):
        ctx = ContextManager(max_tokens=1000)
        for i in range(10):
            ctx.add_message("user", f"message {i}")
        result = ctx.compact(strategy="prune")
        assert isinstance(result, int)
        # After prune, system messages should still be present if any
        # and message count should be reduced
        assert len(ctx._messages) < 10

    def test_compact_prune_preserves_system(self):
        """Prune keeps system messages."""
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("system", "system prompt")
        for i in range(10):
            ctx.add_message("user", f"message {i}")
        ctx.compact(strategy="prune")
        system_msgs = [m for m in ctx._messages if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_compact_merge(self):
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "message 1")
        ctx.add_message("user", "message 2")
        ctx.add_message("assistant", "response")
        result = ctx.compact(strategy="merge")
        assert result >= 0

    def test_compact_merge_few_messages(self):
        """Merge with <3 messages does nothing."""
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "only one")
        result = ctx.compact(strategy="merge")
        assert isinstance(result, int)

    def test_compact_merge_consecutive_same_role(self):
        """Merging consecutive same-role messages."""
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "msg 1")
        ctx.add_message("user", "msg 2")
        ctx.add_message("user", "msg 3")
        ctx.add_message("assistant", "reply")
        ctx.compact(strategy="merge")
        # Should have merged the 3 user messages into 1
        user_msgs = [m for m in ctx._messages if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert "msg 1" in user_msgs[0]["content"]
        assert "msg 3" in user_msgs[0]["content"]

    def test_compact_invalid_strategy(self):
        ctx = ContextManager(max_tokens=1000)
        ctx.add_message("user", "test")
        result = ctx.compact(strategy="invalid")
        assert result == 0  # No change

    def test_compact_records_history(self):
        ctx = ContextManager(max_tokens=1000)
        for i in range(5):
            ctx.add_message("user", f"message {i}")
        ctx.compact(strategy="summarize")
        assert len(ctx._compaction_history) == 1
        hist = ctx._compaction_history[0]
        assert "timestamp" in hist
        assert "strategy" in hist
        assert "before_tokens" in hist
        assert "after_tokens" in hist


# ---------------------------------------------------------------------------
# _create_summary
# ---------------------------------------------------------------------------


class TestCreateSummary:
    def test_empty_messages(self):
        ctx = ContextManager()
        result = ctx._create_summary([])
        assert result == "No previous messages"

    def test_with_messages(self):
        ctx = ContextManager()
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = ctx._create_summary(msgs)
        assert "user" in result
        assert "assistant" in result

    def test_with_empty_content(self):
        ctx = ContextManager()
        msgs = [{"role": "user", "content": ""}]
        result = ctx._create_summary(msgs)
        # Empty content messages are skipped in the summary
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _recalc_tokens
# ---------------------------------------------------------------------------


class TestRecalcTokens:
    def test_recalc(self):
        ctx = ContextManager()
        ctx.add_message("user", "hello")
        ctx.add_message("assistant", "world")
        # Manually corrupt token count
        ctx._token_count = 99999
        ctx._recalc_tokens()
        # Should be recalculated based on actual messages
        expected = sum(ctx.estimate_tokens(m.get("content", "")) for m in ctx._messages)
        assert ctx._token_count == expected


# ---------------------------------------------------------------------------
# Cache stats
# ---------------------------------------------------------------------------


class TestCacheStats:
    def test_initial_empty(self):
        ctx = ContextManager()
        stats = ctx.cache_stats
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate"] == 0
        assert stats["total_requests"] == 0

    def test_with_hits_and_misses(self):
        ctx = ContextManager()
        ctx.record_cache_hit()
        ctx.record_cache_hit()
        ctx.record_cache_miss()
        stats = ctx.cache_stats
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert abs(stats["hit_rate"] - 2 / 3) < 0.001
        assert stats["total_requests"] == 3

    def test_only_hits(self):
        ctx = ContextManager()
        ctx.record_cache_hit()
        stats = ctx.cache_stats
        assert stats["hit_rate"] == 1.0

    def test_only_misses(self):
        ctx = ContextManager()
        ctx.record_cache_miss()
        stats = ctx.cache_stats
        assert stats["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Compaction stats
# ---------------------------------------------------------------------------


class TestCompactionStats:
    def test_empty(self):
        ctx = ContextManager()
        assert ctx.compaction_stats == []

    def test_with_data(self):
        ctx = ContextManager()
        for i in range(5):
            ctx.add_message("user", f"message {i}")
        ctx.compact(strategy="summarize")
        stats = ctx.compaction_stats
        assert len(stats) == 1
        assert "timestamp" in stats[0]
        assert "strategy" in stats[0]

    def test_returns_copy(self):
        ctx = ContextManager()
        for i in range(5):
            ctx.add_message("user", f"message {i}")
        ctx.compact(strategy="summarize")
        stats = ctx.compaction_stats
        stats.append({"extra": True})
        assert len(ctx._compaction_history) == 1  # original unchanged


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_messages(self):
        ctx = ContextManager()
        ctx.add_message("user", "test")
        ctx.reset()
        assert ctx._messages == []
        assert ctx._token_count == 0

    def test_reset_clears_tokens(self):
        ctx = ContextManager()
        ctx.add_message("user", "a" * 1000)
        assert ctx._token_count > 0
        ctx.reset()
        assert ctx._token_count == 0
