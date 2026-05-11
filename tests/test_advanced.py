"""Tests for apex/advanced.py — RetryHandler, BatchOperation, StreamingOutput, ToolTimeout, ContextOptimizer, FileOperationCache."""

import pytest
import asyncio
import time
from apex.advanced import (
    RetryConfig,
    RetryHandler,
    BatchOperation,
    StreamingOutput,
    ToolTimeout,
    ContextOptimizer,
    FileOperationCache,
    get_retry_handler,
    get_file_cache,
)


class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.initial_delay == 1.0
        assert cfg.backoff_factor == 2.0
        assert cfg.max_delay == 30.0

    def test_custom(self):
        cfg = RetryConfig(max_retries=5, initial_delay=0.1, backoff_factor=3.0, max_delay=60.0)
        assert cfg.max_retries == 5
        assert cfg.initial_delay == 0.1


class TestRetryHandler:
    def test_execute_success(self):
        handler = RetryHandler(RetryConfig(max_retries=0))
        result = handler.execute(lambda: 42)
        assert result == 42

    def test_execute_retry_then_succeed(self):
        attempts = [0]

        def flaky():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("not yet")
            return "success"

        handler = RetryHandler(
            RetryConfig(max_retries=3, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1)
        )
        result = handler.execute(flaky)
        assert result == "success"
        assert attempts[0] == 3

    def test_execute_all_fail(self):
        def always_fail():
            raise ValueError("fail")

        handler = RetryHandler(
            RetryConfig(max_retries=2, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1)
        )
        with pytest.raises(ValueError, match="fail"):
            handler.execute(always_fail)

    def test_execute_with_args(self):
        def add(a, b):
            return a + b

        handler = RetryHandler()
        result = handler.execute(add, 3, 4)
        assert result == 7

    def test_execute_async(self):
        async def async_func():
            return "async_result"

        handler = RetryHandler(RetryConfig(max_retries=0))

        async def _test():
            result = await handler.execute_async(async_func)
            assert result == "async_result"

        asyncio.run(_test())

    def test_execute_async_sync_func(self):
        handler = RetryHandler(RetryConfig(max_retries=0))

        async def _test():
            result = await handler.execute_async(lambda: "sync_result")
            assert result == "sync_result"

        asyncio.run(_test())

    def test_execute_async_retry(self):
        attempts = [0]

        async def async_flaky():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("not yet")
            return "ok"

        handler = RetryHandler(
            RetryConfig(max_retries=2, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1)
        )

        async def _test():
            result = await handler.execute_async(async_flaky)
            assert result == "ok"

        asyncio.run(_test())

    def test_execute_async_all_fail(self):
        async def always_fail():
            raise ValueError("fail")

        handler = RetryHandler(
            RetryConfig(max_retries=1, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1)
        )

        async def _test():
            with pytest.raises(ValueError):
                await handler.execute_async(always_fail)

        asyncio.run(_test())


class TestBatchOperation:
    def test_batch_read(self, tmp_path):
        (tmp_path / "a.txt").write_text("content_a")
        (tmp_path / "b.txt").write_text("content_b")
        results = BatchOperation.batch_read(["a.txt", "b.txt", "c.txt"], str(tmp_path))
        assert results["a.txt"] == "content_a"
        assert results["b.txt"] == "content_b"
        assert "c.txt" not in results

    def test_batch_read_error(self, tmp_path):
        # Create a file we can't read (might not work on all systems)
        results = BatchOperation.batch_read(["nonexistent.txt"], str(tmp_path))
        assert "nonexistent.txt" not in results

    def test_batch_write(self, tmp_path):
        operations = [
            {"path": "new1.txt", "content": "hello"},
            {"path": "sub/new2.txt", "content": "world"},
        ]
        results = BatchOperation.batch_write(operations, str(tmp_path))
        assert "new1.txt" in results["success"]
        assert "sub/new2.txt" in results["success"]
        assert (tmp_path / "new1.txt").read_text() == "hello"
        assert (tmp_path / "sub" / "new2.txt").read_text() == "world"

    def test_batch_write_empty(self, tmp_path):
        results = BatchOperation.batch_write([], str(tmp_path))
        assert results["success"] == []
        assert results["failed"] == []


class TestStreamingOutput:
    def test_init(self):
        so = StreamingOutput(chunk_size=5)
        assert so.chunk_size == 5
        assert so._buffer == ""

    def test_add_and_get_chunks(self):
        so = StreamingOutput(chunk_size=5)
        so.add("hello world!")
        chunks = so.get_chunks()
        assert len(chunks) == 3  # "hello", " worl", "d!"
        assert chunks[0] == "hello"
        assert chunks[1] == " worl"
        assert chunks[2] == "d!"

    def test_get_chunks_small(self):
        so = StreamingOutput(chunk_size=100)
        so.add("short")
        chunks = so.get_chunks()
        assert len(chunks) == 1
        assert chunks[0] == "short"

    def test_get_chunks_empty(self):
        so = StreamingOutput()
        chunks = so.get_chunks()
        assert chunks == []

    def test_flush(self):
        so = StreamingOutput()
        so.add("data to flush")
        result = so.flush()
        assert result == "data to flush"
        assert so._buffer == ""

    def test_flush_empty(self):
        so = StreamingOutput()
        assert so.flush() == ""


class TestToolTimeout:
    def test_default_timeout(self):
        assert ToolTimeout.DEFAULT_TIMEOUT == 30

    def test_get_timeout_known(self):
        assert ToolTimeout.get_timeout("run_command") == 300
        assert ToolTimeout.get_timeout("web_search") == 15

    def test_get_timeout_unknown(self):
        assert ToolTimeout.get_timeout("unknown_tool") == 30

    def test_set_timeout(self):
        ToolTimeout.set_timeout("custom_tool", 60)
        assert ToolTimeout.get_timeout("custom_tool") == 60
        # Clean up
        del ToolTimeout.TIMEOUTS["custom_tool"]


class TestContextOptimizer:
    def test_prioritize_messages(self):
        messages = [
            {"content": "normal message"},
            {"content": "fix this error now"},
            {"content": "another normal"},
            {"content": "critical bug found"},
        ]
        result = ContextOptimizer.prioritize_messages(messages)
        assert "fix this error now" in result[0]["content"]
        assert "critical bug found" in result[1]["content"]

    def test_prioritize_messages_custom_keywords(self):
        messages = [
            {"content": "urgent task"},
            {"content": "normal message"},
        ]
        result = ContextOptimizer.prioritize_messages(messages, ["urgent"])
        assert result[0]["content"] == "urgent task"

    def test_extract_key_info(self):
        messages = [
            {"content": "Check main.py for errors", "tool_calls": [{"name": "read_file"}]},
            {"content": "Everything looks fine"},
        ]
        info = ContextOptimizer.extract_key_info(messages)
        assert "main.py" in info["files_mentioned"]
        assert "read_file" in info["tools_used"]
        assert len(info["errors"]) == 1  # "errors" matches in first message

    def test_smart_truncate_short(self):
        text = "short text"
        assert ContextOptimizer.smart_truncate(text, 100) == "short text"

    def test_smart_truncate_long_single_line(self):
        text = "x" * 5000
        result = ContextOptimizer.smart_truncate(text, 100)
        assert "truncated" in result
        assert len(result) < len(text)

    def test_smart_truncate_long_multiline(self):
        lines = [f"line {i} " * 50 for i in range(200)]
        text = "\n".join(lines)
        result = ContextOptimizer.smart_truncate(text, 4000)
        assert "truncated" in result


class TestFileOperationCache:
    def test_init(self):
        cache = FileOperationCache(max_size=10)
        assert cache._cache == {}
        assert cache._max_size == 10

    def test_set_and_get(self):
        cache = FileOperationCache()
        cache.set("file.py", "content")
        assert cache.get("file.py") == "content"

    def test_get_nonexistent(self):
        cache = FileOperationCache()
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = FileOperationCache()
        cache.set("file.py", "content")
        cache.invalidate("file.py")
        assert cache.get("file.py") is None

    def test_invalidate_nonexistent(self):
        cache = FileOperationCache()
        cache.invalidate("nonexistent")  # Should not raise

    def test_clear(self):
        cache = FileOperationCache()
        cache.set("a", "1")
        cache.set("b", "2")
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_eviction(self):
        cache = FileOperationCache(max_size=2)
        cache.set("a", "1")
        time.sleep(0.01)
        cache.set("b", "2")
        time.sleep(0.01)
        cache.set("c", "3")  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"


class TestGlobalFunctions:
    def test_get_retry_handler(self):
        import apex.advanced as adv

        adv._retry_handler = None
        handler = get_retry_handler()
        assert isinstance(handler, RetryHandler)

    def test_get_file_cache(self):
        import apex.advanced as adv

        adv._file_cache = None
        cache = get_file_cache()
        assert isinstance(cache, FileOperationCache)
