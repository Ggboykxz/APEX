"""Session tools: bookmarks, undo/redo, sharing and history search.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "SessionToolsMixin",
]


class SessionToolsMixin:
    def _execute_task(self, args: dict[str, Any]) -> str:
        agent_name = args["agent"]
        task = args["task"]
        from .agents import agent_manager

        if agent_name not in agent_manager.agents:
            return f"ERROR: Unknown agent: {agent_name}"
        return f"[Delegated to @{agent_name}]: {task}"

    def _execute_bookmark_session(self, args: dict[str, Any]) -> str:
        from .context_manager import ConversationManager

        name = args["name"]
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            conv_manager = ConversationManager()
            self._conv_manager = conv_manager

        conv_manager.bookmark(name)
        return f"SUCCESS: Bookmarked current position as '{name}'"

    def _execute_restore_bookmark(self, args: dict[str, Any]) -> str:
        name = args["name"]
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            return "ERROR: No bookmarks exist"

        restored = conv_manager.restore_bookmark(name)
        if restored is None:
            return f"ERROR: Bookmark '{name}' not found"
        return f"[RESTORED from bookmark '{name}']\nMessages: {len(restored)}"

    def _execute_get_conversation_stats(self, args: dict[str, Any]) -> str:
        conv_manager = getattr(self, "_conv_manager", None)
        if conv_manager is None:
            return "No conversation statistics available"

        stats = conv_manager.get_stats()
        return f"Conversation stats:\n  Messages: {stats['message_count']}\n  Bookmarks: {stats['bookmarks']}\n  Roles: {stats['roles']}"

    def _execute_undo(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "ERROR: Undo manager not available"
        action = undo_manager.undo()
        if action is None:
            return "Nothing to undo"
        return f"UNDONE: {action.get('type', 'action')}\n{action.get('details', {})}"

    def _execute_redo(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "ERROR: Undo manager not available"
        action = undo_manager.redo()
        if action is None:
            return "Nothing to redo"
        return f"REDONE: {action.get('type', 'action')}\n{action.get('details', {})}"

    def _execute_undo_info(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "Undo: Not available"
        can_undo = undo_manager.can_undo()
        desc = undo_manager.get_undo_description()
        return f"Can undo: {can_undo}\nLast action: {desc}"

    def _execute_redo_info(self, args: dict[str, Any]) -> str:
        undo_manager = getattr(self, "_undo_manager", None)
        if undo_manager is None:
            return "Redo: Not available"
        can_redo = undo_manager.can_redo()
        desc = undo_manager.get_redo_description()
        return f"Can redo: {can_redo}\nNext action: {desc}"

    def _execute_share_session(self, args: dict[str, Any]) -> str:
        from .session import SessionManager

        agent = getattr(self, "_agent", None)
        if agent is None:
            return "ERROR: Session sharing not available in this context"
        session_manager = SessionManager()
        share_link = session_manager.share(agent)
        return f"Session shared: {share_link}\nShare this link with others to collaborate."

    def _execute_search_history(self, args: dict[str, Any]) -> str:
        from .extras import get_history_search

        query = args["query"]
        fuzzy = args.get("fuzzy", True)
        hs = get_history_search()
        results = hs.search(query, fuzzy) if fuzzy else hs.fuzzy_match(query)
        if not results:
            return "No results found"
        lines = [f"Found {len(results)} results:", "=" * 40]
        for r in results[:5]:
            sim = r.get("similarity", 1.0)
            lines.append(f"  - {r['query'][:50]} (sim: {sim:.2f})")
        return "\n".join(lines)
