"""Ruleset-based permission system for APEX."""

import fnmatch
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PermissionAction(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    pattern: str
    action: PermissionAction
    reason: Optional[str] = None
    expires_at: Optional[float] = None
    remember: bool = False

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class PermissionRequest:
    request_id: str
    tool_name: str
    permission: str
    args: dict
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None


class PermissionManager:
    def __init__(self):
        self._rules: list[PermissionRule] = []
        self._requests: dict[str, PermissionRequest] = {}
        self._default_action = PermissionAction.ASK
        self._request_id_counter = 0
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        self._rules = [
            PermissionRule("read_file", PermissionAction.ALLOW, "Reading files is safe"),
            PermissionRule("glob", PermissionAction.ALLOW, "File searching is safe"),
            PermissionRule("grep", PermissionAction.ALLOW, "Search is safe"),
            PermissionRule("lsp_*", PermissionAction.ALLOW, "LSP operations are safe"),
            PermissionRule("*", PermissionAction.ASK, "Default: ask for permission"),
        ]

    def add_rule(
        self,
        pattern: str,
        action: PermissionAction,
        reason: Optional[str] = None,
        expires_in: Optional[int] = None,
        remember: bool = False,
    ) -> None:
        expires_at = time.time() + expires_in if expires_in else None
        rule = PermissionRule(pattern, action, reason, expires_at, remember)
        if remember and not expires_in:
            rule.expires_at = None
        self._rules.insert(0, rule)
        logger.debug(f"Added rule: {pattern} -> {action.value}")

    def remove_rule(self, pattern: str, action: PermissionAction) -> bool:
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if not (r.pattern == pattern and r.action == action)]
        return len(self._rules) < original_len

    def clear_rules(self) -> None:
        self._rules.clear()
        self._setup_default_rules()

    def can_execute_tool(
        self, tool_name: str, workspace_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> tuple[bool, str]:
        self.initialize()
        for rule in self._rules:
            if rule.is_expired():
                continue
            if self._match_pattern(tool_name, rule.pattern):
                if rule.action == PermissionAction.ALLOW:
                    return True, rule.reason or "Allowed by rule"
                elif rule.action == PermissionAction.DENY:
                    return False, rule.reason or "Denied by rule"
                else:
                    return False, f"Requires permission: {rule.reason or tool_name}"
        return False, f"No rule matched '{tool_name}', defaulting to ask"

    def request_permission(
        self,
        tool_name: str,
        args: dict,
        permission: str,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        self._request_id_counter += 1
        request_id = f"req_{self._request_id_counter}_{uuid.uuid4().hex[:8]}"
        request = PermissionRequest(
            request_id=request_id,
            tool_name=tool_name,
            permission=permission,
            args=args,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        self._requests[request_id] = request
        logger.info(f"Permission requested: {request_id} for {tool_name}")
        return request_id

    def approve_request(
        self, request_id: str, remember: bool = False, expires_in: Optional[int] = None
    ) -> bool:
        if request_id not in self._requests:
            logger.warning(f"Unknown request: {request_id}")
            return False
        request = self._requests[request_id]
        request.status = "approved"
        if remember:
            self.add_rule(
                request.tool_name,
                PermissionAction.ALLOW,
                f"Approved for {request.tool_name}",
                expires_in=expires_in,
                remember=True,
            )
        del self._requests[request_id]
        logger.info(f"Request approved: {request_id}")
        return True

    def deny_request(self, request_id: str, remember: bool = False) -> bool:
        if request_id not in self._requests:
            logger.warning(f"Unknown request: {request_id}")
            return False
        request = self._requests[request_id]
        request.status = "denied"
        if remember:
            self.add_rule(
                request.tool_name,
                PermissionAction.DENY,
                f"Denied for {request.tool_name}",
                remember=True,
            )
        del self._requests[request_id]
        logger.info(f"Request denied: {request_id}")
        return True

    def get_pending_requests(self) -> list[PermissionRequest]:
        return list(self._requests.values())

    def get_request(self, request_id: str) -> Optional[PermissionRequest]:
        return self._requests.get(request_id)

    def _match_pattern(self, tool_name: str, pattern: str) -> bool:
        return fnmatch.fnmatch(tool_name, pattern)


def get_tool_permission(tool_name: str) -> str:
    permission_map = {
        "read_file": "file:read",
        "write_file": "file:write",
        "edit_file": "file:edit",
        "delete_file": "file:delete",
        "run_command": "shell:execute",
        "bash": "shell:execute",
        "shell": "shell:execute",
        "search": "web:search",
        "fetch_url": "web:fetch",
        "mcp_*": "mcp:execute",
    }
    for pattern, permission in permission_map.items():
        if fnmatch.fnmatch(tool_name, pattern):
            return permission
    return "tool:execute"


permission_manager = PermissionManager()


class PermissionRequestDenied(Exception):
    def __init__(self, tool_name: str, permission: str, request_id: str):
        self.tool_name = tool_name
        self.permission = permission
        self.request_id = request_id
        super().__init__(f"Permission required for {tool_name}: {permission}")
