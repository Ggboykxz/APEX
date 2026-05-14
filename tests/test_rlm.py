"""Comprehensive tests for apex/rlm.py — RLMQuery, RLMConfig, RLM (Rate Limit Manager)."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from apex.rlm import RLM, RLMConfig, RLMQuery, rlm_query


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def mock_completion():
    with patch("apex.rlm.litellm.completion") as mock:
        response = MagicMock()
        response.choices[0].message.content = "mocked response"
        mock.return_value = response
        yield mock


@pytest.fixture
def mock_acompletion():
    with patch("apex.rlm.litellm.acompletion") as mock:
        response = MagicMock()
        response.choices[0].message.content = "mocked async response"
        mock.return_value = response
        yield mock


@pytest.fixture
def mock_completion_error():
    with patch("apex.rlm.litellm.completion") as mock:
        mock.side_effect = Exception("API error")
        yield mock


@pytest.fixture
def mock_acompletion_error():
    with patch("apex.rlm.litellm.acompletion") as mock:
        mock.side_effect = Exception("Async error")
        yield mock


# ===========================================================================
# RLMConfig
# ===========================================================================


class TestRLMConfig:
    """Test RLMConfig dataclass."""

    def test_default_values(self):
        config = RLMConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000

    def test_custom_values(self):
        config = RLMConfig(
            requests_per_minute=10,
            requests_per_hour=50,
            requests_per_day=200,
        )
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 50
        assert config.requests_per_day == 200

    def test_partial_custom(self):
        config = RLMConfig(requests_per_minute=30)
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000


# ===========================================================================
# RLM (Rate Limit Manager)
# ===========================================================================


class TestRLMInit:
    """Test RLM initialization."""

    def test_default_config(self):
        rlm = RLM()
        assert rlm.config.requests_per_minute == 60
        assert rlm.config.requests_per_hour == 1000
        assert rlm.config.requests_per_day == 10000
        assert rlm._counts == {}

    def test_custom_config(self):
        config = RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        rlm = RLM(config=config)
        assert rlm.config is config


class TestRLMCheckRateLimit:
    """Test rate limit checking."""

    def test_first_request_allowed(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is True
        assert result["remaining_minute"] == 5
        assert result["remaining_hour"] == 20
        assert result["remaining_day"] == 100

    def test_after_increments(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        rlm.increment("user1")
        rlm.increment("user1")
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is True
        assert result["remaining_minute"] == 3

    def test_minute_limit_exceeded(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=2, requests_per_hour=100, requests_per_day=500)
        )
        rlm.increment("user1")
        rlm.increment("user1")
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is False
        assert result["remaining_minute"] == 0
        assert result["retry_after"] > 0

    def test_hour_limit_exceeded(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=100, requests_per_hour=2, requests_per_day=500)
        )
        now = time.time()
        rlm._counts["user1"] = {
            "minute": (1, now),
            "hour": (2, now),
            "day": (1, now),
        }
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is False
        assert result["remaining_hour"] == 0
        assert result["remaining_minute"] == 99

    def test_day_limit_exceeded(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=100, requests_per_hour=100, requests_per_day=2)
        )
        now = time.time()
        rlm._counts["user1"] = {
            "minute": (1, now),
            "hour": (1, now),
            "day": (2, now),
        }
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is False
        assert result["remaining_day"] == 0
        assert result["retry_after"] > 0

    def test_different_keys_independent(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        rlm.increment("user1")
        r1 = rlm.check_rate_limit("user1")
        r2 = rlm.check_rate_limit("user2")
        assert r1["remaining_minute"] == 4
        assert r2["remaining_minute"] == 5

    def test_expired_window_returns_full_limit(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        old_time = time.time() - 120
        rlm._counts["user1"] = {
            "minute": (5, old_time),
            "hour": (1, time.time()),
            "day": (1, time.time()),
        }
        result = rlm.check_rate_limit("user1")
        assert result["remaining_minute"] == 5
        assert result["allowed"] is True


class TestRLMIncrement:
    """Test rate limit incrementing."""

    def test_increment_increases_count(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        r1 = rlm.increment("user1")
        assert r1["remaining_minute"] == 4
        r2 = rlm.increment("user1")
        assert r2["remaining_minute"] == 3

    def test_increment_updates_all_windows(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        result = rlm.increment("user1")
        assert result["remaining_minute"] == 4
        assert result["remaining_hour"] == 19
        assert result["remaining_day"] == 99

    def test_increment_resets_expired_window(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        old_time = time.time() - 120
        rlm._counts["user1"] = {
            "minute": (5, old_time),
            "hour": (0, 0.0),
            "day": (0, 0.0),
        }
        result = rlm.increment("user1")
        assert result["remaining_minute"] == 4

    def test_increment_creates_entry_for_new_key(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        result = rlm.increment("new_user")
        assert result["allowed"] is True
        assert "new_user" in rlm._counts
        assert rlm._counts["new_user"]["minute"][0] == 1


class TestRLMReset:
    """Test rate limit reset."""

    def test_reset_clears_existing_key(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100)
        )
        rlm.increment("user1")
        assert "user1" in rlm._counts
        rlm.reset("user1")
        assert "user1" not in rlm._counts

    def test_reset_nonexistent_key_does_nothing(self):
        rlm = RLM()
        rlm.reset("nonexistent")
        assert "nonexistent" not in rlm._counts


class TestRLMTimeWindows:
    """Test different time windows (minute, hour, day) expiry."""

    def test_minute_window_expiry(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=2, requests_per_hour=100, requests_per_day=500)
        )
        with patch.object(time, "time") as mock_time:
            mock_time.return_value = 1000.0
            rlm.increment("user1")
            rlm.increment("user1")
            assert rlm.check_rate_limit("user1")["allowed"] is False

            mock_time.return_value = 1061.0
            result = rlm.check_rate_limit("user1")
            assert result["allowed"] is True
            assert result["remaining_minute"] == 2

    def test_hour_window_expiry(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=100, requests_per_hour=2, requests_per_day=500)
        )
        with patch.object(time, "time") as mock_time:
            mock_time.return_value = 1000.0
            rlm.increment("user1")
            rlm.increment("user1")
            assert rlm.check_rate_limit("user1")["allowed"] is False

            mock_time.return_value = 5000.0
            result = rlm.check_rate_limit("user1")
            assert result["remaining_hour"] == 2

    def test_day_window_expiry(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=100, requests_per_hour=100, requests_per_day=2)
        )
        with patch.object(time, "time") as mock_time:
            mock_time.return_value = 1000.0
            rlm.increment("user1")
            rlm.increment("user1")
            assert rlm.check_rate_limit("user1")["allowed"] is False

            mock_time.return_value = 90000.0
            result = rlm.check_rate_limit("user1")
            assert result["remaining_day"] == 2

    def test_all_windows_exceeded_simultaneously(self):
        rlm = RLM(config=RLMConfig(requests_per_minute=1, requests_per_hour=1, requests_per_day=1))
        now = time.time()
        rlm._counts["user1"] = {
            "minute": (1, now),
            "hour": (1, now),
            "day": (1, now),
        }
        result = rlm.check_rate_limit("user1")
        assert result["allowed"] is False
        assert result["remaining_minute"] == 0
        assert result["remaining_hour"] == 0
        assert result["remaining_day"] == 0

    def test_mixed_windows_partial_exceeded(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=3, requests_per_hour=100, requests_per_day=500)
        )
        with patch.object(time, "time") as mock_time:
            mock_time.return_value = 1000.0
            rlm.increment("user1")
            rlm.increment("user1")
            rlm.increment("user1")
            result = rlm.check_rate_limit("user1")
            assert result["allowed"] is False
            assert result["remaining_minute"] == 0
            assert result["remaining_hour"] == 97
            assert result["remaining_day"] == 497


class TestRLMSerialization:
    """Test serialization and deserialization (to_dict / from_dict)."""

    def test_to_dict(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=10, requests_per_hour=50, requests_per_day=200)
        )
        rlm.increment("user1")
        data = rlm.to_dict()
        assert data["config"]["requests_per_minute"] == 10
        assert data["config"]["requests_per_hour"] == 50
        assert data["config"]["requests_per_day"] == 200
        assert "user1" in data["counts"]
        assert data["counts"]["user1"]["minute"][0] == 1

    def test_from_dict(self):
        data = {
            "config": {
                "requests_per_minute": 5,
                "requests_per_hour": 25,
                "requests_per_day": 100,
            },
            "counts": {
                "user1": {
                    "minute": [3, 1000.0],
                    "hour": [5, 1000.0],
                    "day": [10, 1000.0],
                }
            },
        }
        rlm = RLM.from_dict(data)
        assert rlm.config.requests_per_minute == 5
        assert rlm.config.requests_per_hour == 25
        assert rlm.config.requests_per_day == 100
        assert rlm._counts["user1"]["minute"] == (3, 1000.0)

    def test_from_dict_empty_counts(self):
        data = {
            "config": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
            },
        }
        rlm = RLM.from_dict(data)
        assert rlm._counts == {}

    def test_roundtrip_json(self):
        rlm = RLM(
            config=RLMConfig(requests_per_minute=10, requests_per_hour=50, requests_per_day=200)
        )
        rlm.increment("user1")
        rlm.increment("user1")
        rlm.increment("user1")
        data = rlm.to_dict()
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        rlm2 = RLM.from_dict(restored)
        assert rlm2.config.requests_per_minute == 10
        assert rlm2._counts["user1"]["minute"][0] == 3
        assert rlm2._counts["user1"]["minute"][1] > 0


# ===========================================================================
# RLMQuery
# ===========================================================================


class TestRLMQueryInit:
    def test_defaults(self):
        q = RLMQuery()
        assert q.cheap_model == "gpt-4o-mini"
        assert q.expensive_model == "gpt-4o"
        assert q.max_parallel == 10

    def test_custom(self):
        q = RLMQuery(
            cheap_model="claude-3.5-haiku",
            expensive_model="claude-4-opus",
            max_parallel=5,
        )
        assert q.cheap_model == "claude-3.5-haiku"
        assert q.expensive_model == "claude-4-opus"
        assert q.max_parallel == 5


class TestRLMQueryQuery:
    def test_query_cheap(self, mock_completion):
        q = RLMQuery()
        result = q.query("test prompt", use_cheap=True)
        assert result == "mocked response"

    def test_query_expensive(self, mock_completion):
        q = RLMQuery()
        result = q.query("test prompt", use_cheap=False)
        assert result == "mocked response"

    def test_query_with_kwargs(self, mock_completion):
        q = RLMQuery()
        result = q.query("test", temperature=0.5, max_tokens=100)
        assert result == "mocked response"
        _, kwargs = mock_completion.call_args
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 100

    def test_query_error(self, mock_completion_error):
        q = RLMQuery()
        result = q.query("test prompt")
        assert result == "ERROR: API error"

    def test_query_empty_response(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            response = MagicMock()
            response.choices[0].message.content = None
            mock.return_value = response
            result = q.query("test")
            assert result == ""


class TestRLMQueryBatch:
    def test_batch_query(self, mock_completion):
        q = RLMQuery()
        results = q.batch_query(["prompt1", "prompt2"])
        assert len(results) == 2
        assert all(r == "mocked response" for r in results)

    def test_batch_query_with_callback(self, mock_completion):
        q = RLMQuery()
        collected = []

        def callback(idx, result):
            collected.append((idx, result))

        results = q.batch_query(["p1", "p2"], callback=callback)
        assert len(results) == 2
        assert len(collected) == 2
        assert collected[0] == (0, "mocked response")

    def test_batch_query_error(self, mock_completion_error):
        q = RLMQuery()
        results = q.batch_query(["p1"])
        assert results == ["ERROR: API error"]

    def test_batch_query_expensive(self, mock_completion):
        q = RLMQuery()
        results = q.batch_query(["p1"], use_cheap=False)
        assert results == ["mocked response"]


class TestRLMQueryAsync:
    @pytest.mark.asyncio
    async def test_async_query(self, mock_acompletion):
        q = RLMQuery()
        result = await q.async_query("test prompt")
        assert result == "mocked async response"

    @pytest.mark.asyncio
    async def test_async_query_expensive(self, mock_acompletion):
        q = RLMQuery()
        result = await q.async_query("test prompt", use_cheap=False)
        assert result == "mocked async response"

    @pytest.mark.asyncio
    async def test_async_query_with_kwargs(self, mock_acompletion):
        q = RLMQuery()
        result = await q.async_query("test", temperature=0.7)
        assert result == "mocked async response"
        _, kwargs = mock_acompletion.call_args
        assert kwargs["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_async_query_error(self, mock_acompletion_error):
        q = RLMQuery()
        result = await q.async_query("test")
        assert result == "ERROR: Async error"

    @pytest.mark.asyncio
    async def test_async_batch_query(self, mock_acompletion):
        q = RLMQuery()
        results = await q.async_batch_query(["p1", "p2"])
        assert len(results) == 2
        assert all(r == "mocked async response" for r in results)

    @pytest.mark.asyncio
    async def test_async_batch_query_expensive(self, mock_acompletion):
        q = RLMQuery()
        results = await q.async_batch_query(["p1"], use_cheap=False)
        assert results == ["mocked async response"]

    @pytest.mark.asyncio
    async def test_async_batch_query_error(self, mock_acompletion_error):
        q = RLMQuery()
        results = await q.async_batch_query(["p1"])
        assert results == ["ERROR: Async error"]

    @pytest.mark.asyncio
    async def test_async_batch_query_empty_response(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.acompletion") as mock:
            response = MagicMock()
            response.choices[0].message.content = None
            mock.return_value = response
            results = await q.async_batch_query(["p1"])
            assert results == [""]


class TestRLMQueryClassify:
    def test_classify_batch_no_matches(self, mock_completion):
        q = RLMQuery()
        result = q.classify_batch(
            ["item A", "item B"],
            criteria="topic",
            categories=["bug", "feature"],
        )
        assert result == {"bug": [], "feature": []}

    def test_classify_batch_with_matches(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            response = MagicMock()
            response.choices[0].message.content = "bug\nfeature\n"
            mock.return_value = response
            result = q.classify_batch(
                ["item A", "item B"],
                criteria="topic",
                categories=["bug", "feature"],
            )
            assert 0 in result["bug"]
            assert 1 in result["feature"]

    def test_classify_batch_case_insensitive(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            response = MagicMock()
            response.choices[0].message.content = "BUG\nFEATURE\n"
            mock.return_value = response
            result = q.classify_batch(
                ["item A", "item B"],
                criteria="topic",
                categories=["bug", "feature"],
            )
            assert 0 in result["bug"]
            assert 1 in result["feature"]


class TestRLMQuerySummarize:
    def test_summarize_batch(self, mock_completion):
        q = RLMQuery()
        results = q.summarize_batch(["long text one", "long text two"], max_length=50)
        assert len(results) == 2
        assert all(r == "mocked response" for r in results)


class TestRLMQueryExtract:
    def test_extract_batch(self, mock_completion):
        q = RLMQuery()
        results = q.extract_batch(["item1", "item2"], "emails")
        assert len(results) == 2
        assert results[0] == ["mocked response"]

    def test_extract_batch_multiple_lines(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            response = MagicMock()
            response.choices[0].message.content = "alice@test.com\nbob@test.com\n"
            mock.return_value = response
            results = q.extract_batch(["text with emails"], "emails")
            assert results[0] == ["alice@test.com", "bob@test.com"]


class TestRLMQueryRoute:
    def test_route_simple_hint(self, mock_completion):
        q = RLMQuery()
        result = q.route_query("test", complexity_hint="simple")
        assert result == "mocked response"

    def test_route_complex_hint(self, mock_completion):
        q = RLMQuery()
        result = q.route_query("test", complexity_hint="complex")
        assert result == "mocked response"

    def test_route_auto_simple_detected(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            r1 = MagicMock()
            r1.choices[0].message.content = "simple"
            r2 = MagicMock()
            r2.choices[0].message.content = "cheap result"
            mock.side_effect = [r1, r2]
            result = q.route_query("test", complexity_hint="auto")
            assert result == "cheap result"

    def test_route_auto_complex_detected(self):
        q = RLMQuery()
        with patch("apex.rlm.litellm.completion") as mock:
            r1 = MagicMock()
            r1.choices[0].message.content = "complex task"
            r2 = MagicMock()
            r2.choices[0].message.content = "expensive result"
            mock.side_effect = [r1, r2]
            result = q.route_query("test", complexity_hint="auto")
            assert result == "expensive result"


class TestGlobalInstance:
    def test_rlm_query_global_instance(self):
        assert isinstance(rlm_query, RLMQuery)
        assert rlm_query.cheap_model == "gpt-4o-mini"
        assert rlm_query.expensive_model == "gpt-4o"
