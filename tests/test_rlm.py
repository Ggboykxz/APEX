"""Tests for rlm module."""

import pytest
from unittest.mock import patch, MagicMock
from apex.rlm import RLMQuery, rlm_query


class TestRLMQuery:
    """Test RLMQuery class."""

    @pytest.fixture
    def rlm(self):
        """Create RLMQuery instance."""
        return RLMQuery(
            cheap_model="gpt-4o-mini",
            expensive_model="gpt-4o",
            max_parallel=2
        )

    def test_init_default(self):
        """Test initialization with defaults."""
        rlm = RLMQuery()
        assert rlm.cheap_model == "gpt-4o-mini"
        assert rlm.expensive_model == "gpt-4o"
        assert rlm.max_parallel == 10

    def test_init_custom(self, rlm):
        """Test initialization with custom values."""
        assert rlm.cheap_model == "gpt-4o-mini"
        assert rlm.expensive_model == "gpt-4o"
        assert rlm.max_parallel == 2

    @patch('apex.rlm.litellm.completion')
    def test_query_cheap(self, mock_completion, rlm):
        """Test query with cheap model."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]
        mock_completion.return_value = mock_response

        result = rlm.query("test prompt", use_cheap=True)
        assert result == "test response"
        mock_completion.assert_called_once()

    @patch('apex.rlm.litellm.completion')
    def test_query_expensive(self, mock_completion, rlm):
        """Test query with expensive model."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="expensive response"))]
        mock_completion.return_value = mock_response

        result = rlm.query("test prompt", use_cheap=False)
        assert result == "expensive response"

    @patch('apex.rlm.litellm.completion')
    def test_query_error(self, mock_completion, rlm):
        """Test query with error."""
        mock_completion.side_effect = Exception("API Error")

        result = rlm.query("test prompt", use_cheap=True)
        assert "ERROR" in result

    @patch('apex.rlm.litellm.completion')
    def test_batch_query(self, mock_completion, rlm):
        """Test batch query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_completion.return_value = mock_response

        prompts = ["prompt1", "prompt2", "prompt3"]
        results = rlm.batch_query(prompts, use_cheap=True)
        assert len(results) == 3

    @patch('apex.rlm.litellm.completion')
    def test_batch_query_with_callback(self, mock_completion, rlm):
        """Test batch query with callback."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_completion.return_value = mock_response

        callback_results = []
        def callback(idx, result):
            callback_results.append((idx, result))

        prompts = ["prompt1", "prompt2"]
        results = rlm.batch_query(prompts, use_cheap=True, callback=callback)
        assert len(callback_results) == 2

    @pytest.mark.asyncio
    @patch('apex.rlm.litellm.acompletion')
    async def test_async_query(self, mock_completion, rlm):
        """Test async query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="async response"))]
        mock_completion.return_value = mock_response

        result = await rlm.async_query("test prompt", use_cheap=True)
        assert result == "async response"

    @pytest.mark.asyncio
    @patch('apex.rlm.litellm.acompletion')
    async def test_async_batch_query(self, mock_completion, rlm):
        """Test async batch query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_completion.return_value = mock_response

        prompts = ["prompt1", "prompt2", "prompt3"]
        results = await rlm.async_batch_query(prompts, use_cheap=True)
        assert len(results) == 3

    @patch('apex.rlm.litellm.completion')
    def test_classify_batch(self, mock_completion, rlm):
        """Test classify batch."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="simple"))]
        mock_completion.return_value = mock_response

        items = ["item1", "item2"]
        result = rlm.classify_batch(items, "is it simple", ["simple", "complex"])
        assert "simple" in result or "complex" in result

    @patch('apex.rlm.litellm.completion')
    def test_summarize_batch(self, mock_completion, rlm):
        """Test summarize batch."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="summary"))]
        mock_completion.return_value = mock_response

        items = ["item1", "item2"]
        results = rlm.summarize_batch(items, max_length=50)
        assert len(results) == 2

    @patch('apex.rlm.litellm.completion')
    def test_extract_batch(self, mock_completion, rlm):
        """Test extract batch."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="extracted1\nextracted2"))]
        mock_completion.return_value = mock_response

        items = ["item1", "item2"]
        results = rlm.extract_batch(items, "extract numbers")
        assert len(results) == 2

    @patch('apex.rlm.litellm.completion')
    def test_route_query_simple(self, mock_completion, rlm):
        """Test route query with simple hint."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="result"))]
        mock_completion.return_value = mock_response

        result = rlm.route_query("test prompt", complexity_hint="simple")
        assert "result" in result

    @patch('apex.rlm.litellm.completion')
    def test_route_query_auto(self, mock_completion, rlm):
        """Test route query with auto complexity."""
        responses = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="simple"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="result"))])
        ]
        mock_completion.side_effect = responses

        result = rlm.route_query("test prompt", complexity_hint="auto")
        assert "result" in result


class TestRLMQueryGlobal:
    """Test global rlm_query instance."""

    def test_global_instance(self):
        """Test global instance exists."""
        assert rlm_query is not None
        assert isinstance(rlm_query, RLMQuery)