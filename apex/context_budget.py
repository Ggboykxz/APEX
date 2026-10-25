"""Context-window budgeting helpers for APEX prompts.

This module is intentionally pure and dependency-free beyond
:mod:`apex.repomap`: it never reads configuration, global state or the
environment. Callers resolve the settings and pass them in.

Two complementary mechanisms keep requests small:

* :func:`prune_tool_outputs` replaces old, oversized tool results with a
  deterministic marker. Recent results, system messages and conversation
  messages are never touched, and a second pass is a no-op.
* :func:`inject_repo_map` appends a token-budgeted symbol map to a system
  prompt exactly once, detected through the ``## Repository map`` marker.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .repomap import build_repo_map, estimate_tokens

__all__ = [
    "REPO_MAP_MARKER",
    "ContextStats",
    "count_message_tokens",
    "estimate_tokens",
    "inject_repo_map",
    "prune_tool_outputs",
]

REPO_MAP_MARKER = "## Repository map"

_PRUNED_RE = re.compile(r"^\[tool output pruned: \d+ chars, sha256:[0-9a-f]{8}\]$")
_DEFAULT_MAX_CHARS = 4000
_DEFAULT_KEEP_RECENT = 3


@dataclass
class ContextStats:
    """Measured effect of one context-budget pass.

    Attributes:
        tokens_before: Estimated tokens across all message contents before
            pruning (``0`` when no messages are provided).
        tokens_after: Estimated tokens after pruning.
        pruned_messages: Number of tool results replaced by a marker.
        pruned_chars: Number of characters removed from message contents.
        repo_map_tokens: Estimated tokens contributed by the repository map,
            filled in by the agent when it records the stats.
    """

    tokens_before: int = 0
    tokens_after: int = 0
    pruned_messages: int = 0
    pruned_chars: int = 0
    repo_map_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        """Return the stats as a JSON-serialisable dictionary."""
        return {
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "pruned_messages": self.pruned_messages,
            "pruned_chars": self.pruned_chars,
            "repo_map_tokens": self.repo_map_tokens,
        }


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        role = message.get("role")
    else:
        role = getattr(message, "role", None)
    return role if isinstance(role, str) else ""


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        return message.get("content")
    return getattr(message, "content", None)


def count_message_tokens(messages: list[Any]) -> int:
    """Estimate the token count of all textual message contents.

    Content that is not a string (for example multi-part image payloads or
    ``None`` on assistant tool-call messages) contributes nothing. Each
    message is estimated independently, matching the per-string estimate used
    by the repository map.
    """
    total = 0
    for message in messages:
        content = _message_content(message)
        if isinstance(content, str):
            total += estimate_tokens(content)
    return total


def _pruned_marker(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8", "surrogatepass")).hexdigest()[:8]
    return f"[tool output pruned: {len(content)} chars, sha256:{digest}]"


def _is_pruned_marker(content: str) -> bool:
    return bool(_PRUNED_RE.fullmatch(content))


def _replace_content(message: Any, content: str) -> Any | None:
    """Return a copy of *message* with new content, or ``None`` if unsupported."""
    if isinstance(message, dict):
        updated = dict(message)
        updated["content"] = content
        return updated
    try:
        updated = copy.copy(message)
        setattr(updated, "content", content)
    except (AttributeError, TypeError):
        return None
    return updated


def _coerce_non_negative_int(value: Any, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(0, value)


def prune_tool_outputs(
    messages: list[Any],
    max_chars_per_result: int = _DEFAULT_MAX_CHARS,
    keep_recent: int = _DEFAULT_KEEP_RECENT,
) -> tuple[list[Any], ContextStats]:
    """Prune old, oversized tool results without mutating *messages*.

    Only messages whose role is ``tool`` are candidates. The last
    *keep_recent* tool results are always preserved, as are system, user and
    assistant messages. Older tool results longer than
    *max_chars_per_result* are replaced with a deterministic marker of the
    form ``[tool output pruned: N chars, sha256:xxxxxxxx]``. Already marked
    results are left alone, so applying the function twice yields the same
    output and zero further pruning.

    Args:
        messages: OpenAI-style message dictionaries (``role``/``content``/
            ``tool_call_id``) or objects exposing ``role`` and ``content``.
        max_chars_per_result: Maximum content length kept for non-recent
            tool results. Negative values are treated as ``0``.
        keep_recent: Number of most recent tool results that are never
            pruned. Negative values are treated as ``0``.

    Returns:
        A new list and the :class:`ContextStats` for this pass. Unmodified
        messages may be shared with the input; modified messages are copied.
        The input list and its members are never written to.
    """
    limit = _coerce_non_negative_int(max_chars_per_result, _DEFAULT_MAX_CHARS)
    recent = _coerce_non_negative_int(keep_recent, _DEFAULT_KEEP_RECENT)

    tool_indexes = [
        index for index, message in enumerate(messages) if _message_role(message) == "tool"
    ]
    protected = set(tool_indexes[-recent:]) if recent else set()

    output: list[Any] = list(messages)
    pruned_messages = 0
    pruned_chars = 0
    tokens_before = 0
    tokens_after = 0

    for index, message in enumerate(messages):
        content = _message_content(message)
        if not isinstance(content, str):
            continue
        tokens_before += estimate_tokens(content)

        replacement = content
        if (
            index in tool_indexes
            and index not in protected
            and len(content) > limit
            and not _is_pruned_marker(content)
        ):
            replacement = _pruned_marker(content)
            updated = _replace_content(message, replacement)
            if updated is not None:
                output[index] = updated
                pruned_messages += 1
                pruned_chars += len(content) - len(replacement)
            else:  # pragma: no cover - defensive for immutable objects
                replacement = content

        tokens_after += estimate_tokens(replacement)

    stats = ContextStats(
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        pruned_messages=pruned_messages,
        pruned_chars=pruned_chars,
    )
    return output, stats


def _coerce_tokens(max_tokens: Any) -> int:
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
        return 0
    return max(0, max_tokens)


def inject_repo_map(system_prompt: str, root: Path | str, max_tokens: int) -> tuple[str, int]:
    """Append a budgeted repository symbol map to *system_prompt* once.

    The map is considered present when the prompt already contains the
    ``## Repository map`` marker, in which case the prompt is returned
    unchanged and zero tokens are reported. A missing, non-directory or empty
    repository produces an empty map and leaves the prompt unchanged.

    Args:
        system_prompt: Current system prompt. Non-string values are treated
            as an empty prompt.
        root: Repository root passed to :func:`apex.repomap.build_repo_map`.
        max_tokens: Token budget for the rendered symbol map. Values ``<= 0``
            disable injection.

    Returns:
        ``(prompt, tokens_used)`` where ``tokens_used`` is the estimated size
        of the appended symbol map (excluding the heading), or ``0`` when
        nothing was appended.
    """
    prompt = system_prompt if isinstance(system_prompt, str) else ""
    if REPO_MAP_MARKER in prompt:
        return prompt, 0

    budget = _coerce_tokens(max_tokens)
    if budget <= 0:
        return prompt, 0

    try:
        repo_map = build_repo_map(Path(root), max_tokens=budget)
    except Exception:
        return prompt, 0
    if not repo_map.strip():
        return prompt, 0

    block = f"{REPO_MAP_MARKER}\n\n{repo_map.rstrip()}"
    if prompt.strip():
        updated = f"{prompt.rstrip()}\n\n{block}"
    else:
        updated = block
    return updated, estimate_tokens(repo_map)
