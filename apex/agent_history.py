"""Conversation history and compaction for the APEX agent.

Split out of ``apex.agent`` so that module keeps a single responsibility: the
chat loop itself. The mixin expects its host class to expose ``history`` and
``_usage``.
"""

from __future__ import annotations

from typing import Any

from . import config_v2

__all__ = ["HistoryMixin"]


class HistoryMixin:
    """Own the conversation history and shrink it when it grows too large."""

    def reset_history(self) -> None:
        self.history = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def compact_context(self, strategy: str = "summarize") -> int:
        """Compact conversation history to reduce context size.

        Supports ``summarize`` (default), ``prune`` and ``merge`` strategies,
        mirroring :class:`apex.context_tracking.ContextManager`. Returns the
        number of messages removed.
        """
        if not self.history:
            return 0

        original_count = len(self.history)

        if strategy == "summarize":
            self._compact_history_summarize()
        elif strategy == "prune":
            self._compact_history_prune()
        elif strategy == "merge":
            self._compact_history_merge()
        # Unknown strategy: leave history untouched.

        return original_count - len(self.history)

    def _maybe_auto_compact(self) -> None:
        """Compact the history when auto-compaction is enabled and it grew large.

        Failures are swallowed: compaction is an optimisation and must never
        break the conversation. The config singleton is read through the
        module so that a reloaded ``apex.config_v2`` is always honoured.
        """
        try:
            ccfg = config_v2.apex_config.compaction
            if ccfg.get("auto") and len(self.history) > 20:
                strategy = "prune" if ccfg.get("prune") else "summarize"
                self.compact_context(strategy=strategy)
        except Exception:  # noqa: BLE001, S110
            pass

    def _compact_history_summarize(self) -> None:
        if len(self.history) < 4:
            return
        system_messages = [m for m in self.history if m.get("role") == "system"]
        recent = self.history[-6:]
        old = self.history[:-6]

        summary_parts = []
        for msg in old:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            if content:
                summary_parts.append(f"{role}: {content}...")
        summary = "; ".join(summary_parts[:5]) if summary_parts else "No previous messages"

        self.history = (
            system_messages
            + [{"role": "system", "content": f"[Previous conversation summary: {summary}]"}]
            + recent
        )

    def _compact_history_prune(self) -> None:
        keep_count = len(self.history) // 2
        system_messages = [m for m in self.history if m.get("role") == "system"]
        others = [m for m in self.history if m.get("role") != "system"]
        self.history = system_messages + others[-keep_count:]

    def _compact_history_merge(self) -> None:
        if len(self.history) < 3:
            return
        self.history = self._merge_consecutive_messages(self.history)

    @staticmethod
    def _merge_consecutive_messages(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Collapse consecutive messages sharing the same role into one."""
        merged: list[dict[str, Any]] = []
        for msg in history:
            if merged and msg.get("role") == merged[-1].get("role"):
                previous = merged[-1]
                previous["content"] = f"{previous.get('content', '')}\n{msg.get('content', '')}"
                continue
            merged.append(dict(msg))
        return merged
