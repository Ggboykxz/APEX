"""Context Manager for APEX - Handle long conversations with summarization."""

import json
from typing import Any
from dataclasses import dataclass, field


@dataclass
class MessageSummary:
    summary: str
    message_count: int
    token_estimate: int


@dataclass
class ContextWindow:
    max_tokens: int = 100000
    compress_threshold: float = 0.8
    summary_messages: int = 50

    _last_summary: MessageSummary | None = field(default=None, init=False)

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        total_text = ""
        for m in messages:
            content = m.get("content", "")
            if content:
                total_text += " " + content
        return self.estimate_tokens(total_text) > self.max_tokens * self.compress_threshold

    def compress_messages(self, messages: list[dict[str, Any]], summary_prompt: str = "") -> list[dict[str, Any]]:
        if len(messages) < self.summary_messages:
            return messages

        recent = messages[-20:] if len(messages) > 20 else messages
        older = messages[:-20] if len(messages) > 20 else []

        summary_text = f"Previous {len(older)} messages summary:\n"
        for msg in older:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                summary_text += f"[{role}]: {content[:200]}...\n"

        summary = MessageSummary(
            summary=f"Conversation had {len(older)} messages. Key points: [see summary]",
            message_count=len(older),
            token_estimate=self.estimate_tokens(summary_text)
        )
        self._last_summary = summary

        return [
            {"role": "system", "content": f"Context summary: {len(older)} previous messages compressed. {summary_prompt}"},
            {"role": "system", "content": summary_text[:2000]},
        ] + recent


class ConversationManager:
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: list[dict[str, Any]] = []
        self._bookmarks: dict[str, int] = {}

    def add_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        msg = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata
        self._history.append(msg)

        if len(self._history) > self.max_history:
            self._trim_history()

    def get_messages(self) -> list[dict[str, Any]]:
        return self._history.copy()

    def set_messages(self, messages: list[dict[str, Any]]) -> None:
        self._history = messages[:self.max_history]

    def _trim_history(self) -> None:
        keep = self.max_history // 2
        summary = f"[Previous {len(self._history) - keep} messages trimmed]"
        self._history = [{"role": "system", "content": summary}] + self._history[-keep:]

    def bookmark(self, name: str) -> None:
        self._bookmarks[name] = len(self._history)

    def restore_bookmark(self, name: str) -> list[dict[str, Any]] | None:
        if name not in self._bookmarks:
            return None
        return self._history[self._bookmarks[name]:]

    def search(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for i, msg in enumerate(self._history):
            content = msg.get("content", "")
            if query_lower in content.lower():
                results.append({"index": i, "message": msg})
        return results

    def clear(self) -> None:
        self._history = []
        self._bookmarks = {}

    def get_stats(self) -> dict[str, Any]:
        return {
            "message_count": len(self._history),
            "bookmarks": len(self._bookmarks),
            "roles": self._count_roles()
        }

    def _count_roles(self) -> dict[str, int]:
        counts = {}
        for msg in self._history:
            role = msg.get("role", "unknown")
            counts[role] = counts.get(role, 0) + 1
        return counts


class AutoSaveManager:
    def __init__(self, save_dir: str | None = None):
        from pathlib import Path
        self._save_dir = Path(save_dir) if save_dir else Path.home() / ".apex" / "autosave"
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = self._save_dir / "current.json"
        self._last_save = 0

    def save_state(self, state: dict[str, Any]) -> None:
        import time
        import json

        state["timestamp"] = time.time()
        state["version"] = "0.3.0"

        with open(self._current_file, "w") as f:
            json.dump(state, f, indent=2)

        self._last_save = time.time()

    def load_state(self) -> dict[str, Any] | None:
        import json
        if not self._current_file.exists():
            return None

        try:
            with open(self._current_file) as f:
                return json.load(f)
        except:
            return None

    def clear(self) -> None:
        if self._current_file.exists():
            self._current_file.unlink()

    def list_saves(self) -> list[dict[str, Any]]:
        import os
        saves = []
        for f in self._save_dir.glob("*.json"):
            stat = f.stat()
            saves.append({
                "name": f.stem,
                "path": str(f),
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        return sorted(saves, key=lambda x: x["modified"], reverse=True)