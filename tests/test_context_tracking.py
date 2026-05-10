"""Tests for context_tracking module."""

import pytest
from apex.context_tracking import ContextManager


class TestContextManager:
    """Test ContextManager class."""

    @pytest.fixture
    def ctx(self):
        """Create ContextManager instance."""
        return ContextManager(max_tokens=1000, compaction_threshold=0.9)

    def test_init_default(self):
        """Test default initialization."""
        ctx = ContextManager()
        assert ctx.max_tokens == 1000000
        assert ctx.compaction_threshold == 0.9
        assert ctx._messages == []

    def test_init_custom(self):
        """Test custom initialization."""
        ctx = ContextManager(max_tokens=500, compaction_threshold=0.5)
        assert ctx.max_tokens == 500
        assert ctx.compaction_threshold == 0.5

    def test_estimate_tokens(self, ctx):
        """Test token estimation."""
        tokens = ctx.estimate_tokens("hello world")
        assert tokens >= 0

    def test_estimate_tokens_long(self, ctx):
        """Test token estimation for long text."""
        text = "a" * 1000
        tokens = ctx.estimate_tokens(text)
        assert tokens == 250

    def test_add_message(self, ctx):
        """Test add_message method."""
        tokens = ctx.add_message("user", "hello")
        assert tokens > 0
        assert len(ctx._messages) == 1

    def test_get_messages(self, ctx):
        """Test get_messages method."""
        ctx.add_message("user", "hello")
        messages = ctx.get_messages()
        assert len(messages) == 1

    def test_token_count(self, ctx):
        """Test token_count property."""
        ctx.add_message("user", "hello")
        assert ctx.token_count > 0

    def test_utilization(self, ctx):
        """Test utilization property."""
        ctx.add_message("user", "hello world test message")
        util = ctx.utilization
        assert 0 <= util <= 1

    def test_should_compact_false(self, ctx):
        """Test should_compact when not needed."""
        result = ctx.should_compact()
        assert result is False

    def test_should_compact_true(self, ctx):
        """Test should_compact when needed."""
        ctx.max_tokens = 10
        ctx.add_message("user", "a" * 100)  # Add lots of tokens
        result = ctx.should_compact()
        assert result is True

    def test_compact_no_messages(self, ctx):
        """Test compact with no messages."""
        result = ctx.compact()
        assert result == 0

    def test_compact_summarize(self, ctx):
        """Test compact with summarize strategy."""
        for i in range(5):
            ctx.add_message("user", f"message {i}")

        result = ctx.compact(strategy="summarize")
        assert isinstance(result, int)

    def test_compact_prune(self, ctx):
        """Test compact with prune strategy."""
        for i in range(5):
            ctx.add_message("user", f"message {i}")

        result = ctx.compact(strategy="prune")
        assert isinstance(result, int)

    def test_compact_merge(self, ctx):
        """Test compact with merge strategy."""
        ctx.add_message("user", "message 1")
        ctx.add_message("user", "message 2")
        ctx.add_message("assistant", "response")

        result = ctx.compact(strategy="merge")
        assert result >= 0

    def test_compact_invalid_strategy(self, ctx):
        """Test compact with invalid strategy."""
        ctx.add_message("user", "test")
        result = ctx.compact(strategy="invalid")
        assert result == 0

    def test_record_cache_hit(self, ctx):
        """Test cache hit recording."""
        ctx.record_cache_hit()
        assert ctx._cache_hits == 1

    def test_record_cache_miss(self, ctx):
        """Test cache miss recording."""
        ctx.record_cache_miss()
        assert ctx._cache_misses == 1

    def test_cache_stats_empty(self, ctx):
        """Test cache_stats with no data."""
        stats = ctx.cache_stats
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate"] == 0

    def test_cache_stats_with_data(self, ctx):
        """Test cache_stats with data."""
        ctx.record_cache_hit()
        ctx.record_cache_hit()
        ctx.record_cache_miss()

        stats = ctx.cache_stats
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["hit_rate"] == 2/3

    def test_compaction_stats_empty(self, ctx):
        """Test compaction_stats when empty."""
        stats = ctx.compaction_stats
        assert stats == []

    def test_compaction_stats_with_data(self, ctx):
        """Test compaction_stats with data."""
        for i in range(3):
            ctx.add_message("user", f"message {i}")

        ctx.compact(strategy="summarize")
        stats = ctx.compaction_stats
        assert len(stats) == 1
        assert "timestamp" in stats[0]

    def test_reset(self, ctx):
        """Test reset method."""
        ctx.add_message("user", "test")
        ctx.reset()
        assert ctx._messages == []
        assert ctx._token_count == 0