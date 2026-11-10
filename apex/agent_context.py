"""Context-window management for the APEX agent.

Split out of ``apex.agent`` so that module keeps a single responsibility: the
chat loop itself. The mixin expects its host class to expose ``history``,
``_system_message`` and the repository-map cache attributes.
"""

from __future__ import annotations

from typing import Any

from . import config_v2
from .config_v2 import normalize_context_config
from .context_budget import (
    REPO_MAP_MARKER,
    ContextStats,
    count_message_tokens,
    inject_repo_map,
    prune_tool_outputs,
)

__all__ = ["ContextMixin"]


class ContextMixin:
    """Build model requests and keep them inside the context budget."""

    def get_context_stats(self) -> dict[str, int]:
        """Return the stats from the most recent context-budget pass."""
        return self.last_context_stats.to_dict()

    def _context_settings(self) -> dict[str, Any]:
        """Resolve validated ``context`` settings, tolerating older configs.

        The config singleton is read through the module so that a reloaded
        ``apex.config_v2`` is always honoured.
        """
        try:
            raw = config_v2.apex_config.context
        except Exception:  # noqa: BLE001
            raw = None
        return normalize_context_config(raw)

    def _ensure_repo_map_context(self) -> None:
        """Append the budgeted repository map once per session and root.

        Scanning is cached per ``(root, budget)`` so switching agents or
        starting another turn reuses the rendered map instead of rescanning.
        An empty repository or a disabled budget simply appends nothing.
        """
        content = self._system_message.get("content", "")
        if not isinstance(content, str):
            content = ""
        if REPO_MAP_MARKER in content:
            return

        settings = self._context_settings()
        budget = settings["max_repo_map_tokens"]
        if budget <= 0:
            return

        root = self.cwd
        cache_key = (str(root), budget)
        cached = self._repo_map_cache.get(cache_key)
        if cached is None:
            cached = inject_repo_map("", root, budget)
            self._repo_map_cache[cache_key] = cached
        block, tokens = cached
        if not block:
            return

        injected = f"{content.rstrip()}\n\n{block}" if content.strip() else block
        self._system_message = {**self._system_message, "content": injected}
        self._repo_map_tokens = tokens

    def _request_messages(self, user_input: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build the message list for a model request, repo map included.

        *user_input* may be multi-part (text + image_url parts) for vision.
        """
        self._ensure_repo_map_context()
        return [self._system_message, *self.history, {"role": "user", "content": user_input}]

    def _apply_context_budget(self, messages: list[Any]) -> list[Any]:
        """Prune old tool results from a request and record the stats."""
        settings = self._context_settings()
        if settings["prune_tool_outputs"]:
            try:
                pruned, stats = prune_tool_outputs(
                    messages,
                    max_chars_per_result=settings["tool_output_max_chars"],
                    keep_recent=settings["keep_recent_tool_results"],
                )
            except Exception:  # noqa: BLE001
                pruned = messages
                tokens = count_message_tokens(messages)
                stats = ContextStats(tokens_before=tokens, tokens_after=tokens)
        else:
            pruned = messages
            tokens = count_message_tokens(messages)
            stats = ContextStats(tokens_before=tokens, tokens_after=tokens)
        stats.repo_map_tokens = self._repo_map_tokens
        self.last_context_stats = stats
        return pruned
