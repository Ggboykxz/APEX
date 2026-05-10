"""Advanced features for APEX - streaming, batching, retry, timeouts."""

import asyncio
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0


class RetryHandler:
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        delay = self.config.initial_delay
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(delay)
                    delay = min(delay * self.config.backoff_factor, self.config.max_delay)

        raise last_error

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        delay = self.config.initial_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * self.config.backoff_factor, self.config.max_delay)
                else:
                    raise


class BatchOperation:
    @staticmethod
    def batch_read(paths: list[str], cwd: str) -> dict[str, str]:
        from pathlib import Path
        results = {}
        cwd_path = Path(cwd)

        for path in paths:
            full_path = cwd_path / path
            try:
                if full_path.exists():
                    results[path] = full_path.read_text()
            except Exception:
                results[path] = f"ERROR: Cannot read {path}"

        return results

    @staticmethod
    def batch_write(operations: list[dict[str, str]], cwd: str) -> dict[str, Any]:
        from pathlib import Path
        cwd_path = Path(cwd)
        results = {"success": [], "failed": []}

        for op in operations:
            path = op.get("path", "")
            content = op.get("content", "")
            full_path = cwd_path / path

            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                results["success"].append(path)
            except Exception as e:
                results["failed"].append({"path": path, "error": str(e)})

        return results


class StreamingOutput:
    def __init__(self, chunk_size: int = 10):
        self.chunk_size = chunk_size
        self._buffer = ""

    def add(self, text: str):
        self._buffer += text

    def get_chunks(self) -> list[str]:
        chunks = []
        while len(self._buffer) > self.chunk_size:
            chunks.append(self._buffer[:self.chunk_size])
            self._buffer = self._buffer[self.chunk_size:]
        if self._buffer:
            chunks.append(self._buffer)
            self._buffer = ""
        return chunks

    def flush(self) -> str:
        result = self._buffer
        self._buffer = ""
        return result


class ToolTimeout:
    DEFAULT_TIMEOUT = 30

    TIMEOUTS = {
        "run_command": 300,
        "run_test": 120,
        "install_package": 180,
        "format_file": 60,
        "run_code": 30,
        "web_search": 15,
        "fetch_url": 15,
    }

    @classmethod
    def get_timeout(cls, tool_name: str) -> int:
        return cls.TIMEOUTS.get(tool_name, cls.DEFAULT_TIMEOUT)

    @classmethod
    def set_timeout(cls, tool_name: str, timeout: int):
        cls.TIMEOUTS[tool_name] = timeout


class ContextOptimizer:
    @staticmethod
    def prioritize_messages(messages: list[dict[str, Any]], priority_keywords: list[str] = None) -> list[dict[str, Any]]:
        priority_keywords = priority_keywords or ["error", "fix", "bug", "important", "critical"]
        high_priority = []
        low_priority = []

        for msg in messages:
            content = msg.get("content", "").lower()
            is_priority = any(kw in content for kw in priority_keywords)

            if is_priority:
                high_priority.append(msg)
            else:
                low_priority.append(msg)

        return high_priority + low_priority

    @staticmethod
    def extract_key_info(messages: list[dict[str, Any]]) -> dict[str, Any]:
        key_info = {
            "files_mentioned": set(),
            "functions_called": set(),
            "errors": [],
            "tools_used": set(),
        }

        for msg in messages:
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        key_info["tools_used"].add(tc.get("name", ""))

            if "error" in content.lower():
                key_info["errors"].append(content[:200])

            import re
            key_info["files_mentioned"].update(re.findall(r'[a-zA-Z_]+\.[a-zA-Z]+', content))

        return {
            "files_mentioned": list(key_info["files_mentioned"])[:20],
            "functions_called": list(key_info["functions_called"])[:10],
            "errors": key_info["errors"][:5],
            "tools_used": list(key_info["tools_used"]),
        }

    @staticmethod
    def smart_truncate(content: str, max_length: int = 4000) -> str:
        if len(content) <= max_length:
            return content

        lines = content.split("\n")
        if len(lines) > 1:
            first_half = lines[:len(lines)//2]
            second_half = lines[len(lines)//2:]
            return "\n".join(first_half) + "\n... [truncated] ...\n" + "\n".join(second_half[-20:])

        return content[:max_length-100] + "\n... [truncated]"


class FileOperationCache:
    def __init__(self, max_size: int = 100):
        self._cache = {}
        self._max_size = max_size
        self._access_times = {}

    def get(self, path: str) -> Optional[str]:
        if path in self._cache:
            self._access_times[path] = time.time()
            return self._cache[path]
        return None

    def set(self, path: str, content: str):
        if len(self._cache) >= self._max_size:
            oldest = min(self._access_times.items(), key=lambda x: x[1])[0]
            del self._cache[oldest]
            del self._access_times[oldest]

        self._cache[path] = content
        self._access_times[path] = time.time()

    def invalidate(self, path: str):
        if path in self._cache:
            del self._cache[path]
            del self._access_times[path]

    def clear(self):
        self._cache.clear()
        self._access_times.clear()


_retry_handler: Optional[RetryHandler] = None
_file_cache: Optional[FileOperationCache] = None


def get_retry_handler() -> RetryHandler:
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = RetryHandler()
    return _retry_handler


def get_file_cache() -> FileOperationCache:
    global _file_cache
    if _file_cache is None:
        _file_cache = FileOperationCache()
    return _file_cache