"""Permission gating for the APEX agent.

Split out of ``apex.agent`` so that module keeps a single responsibility: the
chat loop itself. The mixin expects its host class to expose
``_current_agent`` and ``_pending_permissions``.
"""

from __future__ import annotations

from typing import Any

from .agents import agent_manager
from .permission import get_tool_permission, permission_manager

__all__ = ["PermissionsMixin"]


class PermissionsMixin:
    """Decide whether a tool may run, and track the pending requests."""

    def _check_tool_permission(
        self, tool_name: str, tool_args: dict | None = None
    ) -> tuple[bool, str]:
        can_execute, reason = permission_manager.can_execute_tool(tool_name)
        if not can_execute:
            return can_execute, reason
        agent_cfg = agent_manager.get(self._current_agent)
        if agent_cfg and tool_name in ("run_command", "bash"):
            command = ""
            if tool_args:
                command = tool_args.get("command", "")
            bash_perm = agent_cfg.check_bash_permission(command)
            if bash_perm == "deny":
                return False, f"Agent '{self._current_agent}' denies this bash command"
            if bash_perm == "ask":
                return (
                    False,
                    f"Agent '{self._current_agent}' requires approval for this bash command",
                )
        return True, reason

    def _request_permission(self, tool_name: str, tool_args: dict, tc_id: str) -> str:
        """Request permission for a tool."""
        permission = get_tool_permission(tool_name)
        request_id = permission_manager.request_permission(
            tool_name=tool_name,
            args=tool_args,
            permission=permission,
        )
        self._pending_permissions[request_id] = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tc_id": tc_id,
        }
        return request_id

    def approve_permission(
        self, request_id: str, remember: bool = False, expires_in: int | None = None
    ) -> bool:
        """Approve a pending permission request."""
        if request_id not in self._pending_permissions:
            return False
        result = permission_manager.approve_request(
            request_id, remember=remember, expires_in=expires_in
        )
        if result:
            del self._pending_permissions[request_id]
        return result

    def deny_permission(self, request_id: str) -> bool:
        """Deny a pending permission request."""
        if request_id not in self._pending_permissions:
            return False
        result = permission_manager.deny_request(request_id)
        if result:
            del self._pending_permissions[request_id]
        return result

    def get_pending_permissions(self) -> list[dict]:
        """Get all pending permission requests."""
        pending = permission_manager.get_pending_requests()
        return [self._describe_pending_request(req) for req in pending]

    def _describe_pending_request(self, request: Any) -> dict:
        """Render one pending permission request for the UI.

        The arguments come from the agent's own record when it created the
        request, and from the permission manager otherwise.
        """
        tracked = self._pending_permissions.get(request.request_id, {})
        return {
            "request_id": request.request_id,
            "tool_name": request.tool_name,
            "permission": request.permission,
            "args": tracked.get("tool_args", request.args),
            "timestamp": request.timestamp,
        }
