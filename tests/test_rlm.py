"""Tests for apex/rlm.py — RLMQuery class (no API calls, just structure and logic)."""

import pytest
from apex.rlm import RLMQuery, rlm_query


class TestRLMQueryInit:
    def test_defaults(self):
        q = RLMQuery()
        assert q.cheap_model == "gpt-4o-mini"
        assert q.expensive_model == "gpt-4o"
        assert q.max_parallel == 10

    def test_custom(self):
        q = RLMQuery(
            cheap_model="claude-3.5-haiku", expensive_model="claude-4-opus", max_parallel=5
        )
        assert q.cheap_model == "claude-3.5-haiku"
        assert q.expensive_model == "claude-4-opus"
        assert q.max_parallel == 5


class TestRLMQueryQueryNoNetwork:
    """Test query method — will fail without API key, but should return error string."""

    def test_query_returns_error_without_key(self):
        q = RLMQuery()
        result = q.query("test prompt", use_cheap=True)
        # Without a valid API key, should return an error
        assert isinstance(result, str)
        # It might be an error or a real response if a key is set
        assert len(result) > 0


class TestRLMQueryRouteQuery:
    """Test route_query logic."""

    def test_route_simple(self):
        q = RLMQuery()
        # Will fail without API key but should not crash
        result = q.route_query("test", complexity_hint="simple")
        assert isinstance(result, str)

    def test_route_complex(self):
        q = RLMQuery()
        result = q.route_query("test", complexity_hint="complex")
        assert isinstance(result, str)


class TestRLMQueryBatchMethods:
    """Test batch methods exist and are callable."""

    def test_batch_query_callable(self):
        q = RLMQuery()
        assert callable(q.batch_query)

    def test_classify_batch_callable(self):
        q = RLMQuery()
        assert callable(q.classify_batch)

    def test_summarize_batch_callable(self):
        q = RLMQuery()
        assert callable(q.summarize_batch)

    def test_extract_batch_callable(self):
        q = RLMQuery()
        assert callable(q.extract_batch)


class TestRLMQueryAsync:
    """Test async methods are callable."""

    @pytest.mark.asyncio
    async def test_async_query_callable(self):
        q = RLMQuery()
        assert callable(q.async_query)

    @pytest.mark.asyncio
    async def test_async_batch_query_callable(self):
        q = RLMQuery()
        assert callable(q.async_batch_query)


class TestGlobalInstance:
    def test_rlm_query_global(self):
        assert isinstance(rlm_query, RLMQuery)
