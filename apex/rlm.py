"""Native RLM (Remote Language Model) query - batched analysis through cheap models."""

import asyncio
import time
from dataclasses import asdict, dataclass
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor

import litellm

from .config import MODELS


@dataclass
class RLMConfig:
    """Configuration for the Rate Limit Manager."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000


class RLM:
    """Rate Limit Manager - tracks and enforces per-key rate limits."""

    WINDOWS = {
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    def __init__(self, config: Optional[RLMConfig] = None):
        self.config = config or RLMConfig()
        self._counts: dict[str, dict[str, tuple[int, float]]] = {}

    def _ensure_key(self, key: str) -> dict[str, tuple[int, float]]:
        if key not in self._counts:
            self._counts[key] = {w: (0, 0.0) for w in self.WINDOWS}
        return self._counts[key]

    def check_rate_limit(self, key: str) -> dict:
        windows = self._ensure_key(key)
        now = time.time()
        result: dict = {"allowed": True, "retry_after": 0}

        for window, window_secs in self.WINDOWS.items():
            count, timestamp = windows[window]
            limit = getattr(self.config, f"requests_per_{window}")

            if now - timestamp < window_secs:
                remaining = limit - count
                if remaining <= 0:
                    result["allowed"] = False
                    retry = int(window_secs - (now - timestamp))
                    result["retry_after"] = max(result["retry_after"], retry)
            else:
                remaining = limit

            result[f"remaining_{window}"] = max(0, remaining)

        return result

    def increment(self, key: str) -> dict:
        windows = self._ensure_key(key)
        now = time.time()

        for window, window_secs in self.WINDOWS.items():
            count, timestamp = windows[window]
            if now - timestamp >= window_secs:
                windows[window] = (1, now)
            else:
                windows[window] = (count + 1, timestamp)

        return self.check_rate_limit(key)

    def reset(self, key: str) -> None:
        self._counts.pop(key, None)

    def to_dict(self) -> dict:
        return {
            "config": asdict(self.config),
            "counts": {
                k: {w: list(v) for w, v in wins.items()}
                for k, wins in self._counts.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RLM":
        config = RLMConfig(**data["config"])
        rlm = cls(config=config)
        rlm._counts = {
            k: {w: tuple(v) for w, v in wins.items()}
            for k, wins in data.get("counts", {}).items()
        }
        return rlm


class RLMQuery:
    """Remote Language Model query for batched cheap analysis."""

    def __init__(
        self,
        cheap_model: str = "gpt-4o-mini",
        expensive_model: str = "gpt-4o",
        max_parallel: int = 10,
    ):
        self.cheap_model = cheap_model
        self.expensive_model = expensive_model
        self.max_parallel = max_parallel
        self._executor = ThreadPoolExecutor(max_workers=max_parallel)

    def query(self, prompt: str, use_cheap: bool = True, **kwargs) -> str:
        """Query a single prompt."""
        model = self.cheap_model if use_cheap else self.expensive_model
        model_str = MODELS.get(model, model)

        try:
            response = litellm.completion(
                model=model_str, messages=[{"role": "user", "content": prompt}], **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"ERROR: {e}"

    def batch_query(
        self,
        prompts: list[str],
        use_cheap: bool = True,
        callback: Callable[[int, str], None] | None = None,
    ) -> list[str]:
        """Batch query multiple prompts in parallel."""
        model = self.cheap_model if use_cheap else self.expensive_model

        def query_single(idx_prompt):
            idx, prompt = idx_prompt
            model_str = MODELS.get(model, model)

            try:
                response = litellm.completion(
                    model=model_str, messages=[{"role": "user", "content": prompt}], timeout=30
                )
                result = response.choices[0].message.content or ""
            except Exception as e:
                result = f"ERROR: {e}"

            if callback:
                callback(idx, result)

            return result

        results = list(self._executor.map(query_single, enumerate(prompts)))
        return results

    async def async_query(self, prompt: str, use_cheap: bool = True, **kwargs) -> str:
        """Async query a single prompt."""
        model = self.cheap_model if use_cheap else self.expensive_model
        model_str = MODELS.get(model, model)

        try:
            response = await litellm.acompletion(
                model=model_str, messages=[{"role": "user", "content": prompt}], **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"ERROR: {e}"

    async def async_batch_query(
        self, prompts: list[str], use_cheap: bool = True, **kwargs
    ) -> list[str]:
        """Async batch query multiple prompts."""
        model = self.cheap_model if use_cheap else self.expensive_model
        model_str = MODELS.get(model, model)

        async def query_single(prompt):
            try:
                response = await litellm.acompletion(
                    model=model_str, messages=[{"role": "user", "content": prompt}], **kwargs
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                return f"ERROR: {e}"

        tasks = [query_single(p) for p in prompts]
        results = await asyncio.gather(*tasks)
        return list(results)

    def classify_batch(
        self, items: list[str], criteria: str, categories: list[str]
    ) -> dict[str, list[int]]:
        """Classify a batch of items into categories."""
        prompt = f"""Classify each item into one of these categories: {", ".join(categories)}

Criteria: {criteria}

Items:
""" + "\n".join(f"{i}. {item}" for i, item in enumerate(items))

        response = self.query(prompt, use_cheap=True)

        result = {cat: [] for cat in categories}

        for i, line in enumerate(response.split("\n")):
            line = line.strip()
            for cat in categories:
                if cat.lower() in line.lower():
                    result[cat].append(i)

        return result

    def summarize_batch(self, items: list[str], max_length: int = 100) -> list[str]:
        """Summarize each item in a batch using cheap model."""

        def summarize(idx_prompt):
            idx, item = idx_prompt
            prompt = f"Summarize this in max {max_length} chars: {item}"
            return self.query(prompt, use_cheap=True)

        return list(self._executor.map(summarize, enumerate(items)))

    def extract_batch(self, items: list[str], extract_pattern: str) -> list[list[str]]:
        """Extract information from a batch using a pattern."""

        def extract(idx_item):
            idx, item = idx_item
            prompt = f"Extract {extract_pattern} from: {item}"
            result = self.query(prompt, use_cheap=True)
            return [x.strip() for x in result.split("\n") if x.strip()]

        return list(self._executor.map(extract, enumerate(items)))

    def route_query(self, prompt: str, complexity_hint: str = "auto") -> str:
        """Route query to appropriate model based on complexity."""
        if complexity_hint == "simple":
            return self.query(prompt, use_cheap=True)
        elif complexity_hint == "complex":
            return self.query(prompt, use_cheap=False)
        else:
            complexity_prompt = f"""Is this query simple or complex? 
Reply with just "simple" or "complex".

Query: {prompt}"""

            result = self.query(complexity_prompt, use_cheap=True)

            if "simple" in result.lower():
                return self.query(prompt, use_cheap=True)
            else:
                return self.query(prompt, use_cheap=False)


rlm_query = RLMQuery()
