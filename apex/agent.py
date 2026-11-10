"""Core agent loop for APEX - litellm integration and tool orchestration with multi-agent support."""

import logging
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

try:
    import litellm
    from litellm import AuthenticationError, BadRequestError, RateLimitError

    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    BadRequestError = RateLimitError = AuthenticationError = Exception

# A subagent name is a run of word characters; the pattern is unambiguous,
# so it cannot backtrack.
_AGENT_NAME_RE = re.compile(r"\w+")


def _split_invocation(body: str) -> tuple[str | None, str]:
    """Split the text after ``@`` into a subagent name and its task."""
    match = _AGENT_NAME_RE.match(body)
    if not match:
        return None, ""
    rest = body[match.end() :]
    if not rest or not rest[0].isspace():
        return None, ""
    task = rest.lstrip()
    if not task or "\n" in task:
        return None, ""
    return match.group(0), task


def _is_invocable_subagent(subagent_name: str) -> bool:
    """Whether a name designates a subagent that may be invoked."""
    if subagent_name not in agent_manager.agents:
        return False
    agent = agent_manager.get(subagent_name)
    return agent is not None and agent.mode in ("subagent", "all")


from .agent_context import ContextMixin
from .agent_history import HistoryMixin
from .agent_messages import (
    assistant_tool_call_message,
    merge_tool_call_delta,
    parse_tool_args,
    tool_result_message,
)
from .agent_models import ModelSelectionMixin
from .agent_permissions import PermissionsMixin
from .agent_rules import RulesMixin
from .agent_types import CompletionParams, StreamState
from .agents import agent_manager
from .config import MODELS, Config
from .context_budget import (
    ContextStats,
)
from .permission import permission_manager
from .tools import AsyncToolExecutor, ToolExecutor, get_all_tool_schemas
from .ui import UI
from .vision import VisionNotSupportedError, check_vision_support, prepare_vision_input


class Agent(RulesMixin, ContextMixin, HistoryMixin, PermissionsMixin, ModelSelectionMixin):
    """The APEX agent: chat loop, tool orchestration and subagent dispatch.

    The supporting responsibilities live in sibling mixins:
    :class:`~apex.agent_rules.RulesMixin`,
    :class:`~apex.agent_context.ContextMixin`,
    :class:`~apex.agent_history.HistoryMixin`,
    :class:`~apex.agent_permissions.PermissionsMixin` and
    :class:`~apex.agent_models.ModelSelectionMixin`.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.model = self.config.model
        self._executor = ToolExecutor(cwd=self.config.cwd)
        self._async_executor = AsyncToolExecutor(cwd=self.config.cwd)
        self._ui = UI()
        self.history: list[dict[str, Any]] = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._pending_permissions: dict[str, dict] = {}

        self._current_agent = "build"
        self._set_agent_system_prompt()
        self.last_context_stats = ContextStats()
        self._repo_map_tokens = 0
        self._repo_map_cache: dict[tuple[str, int], tuple[str, int]] = {}
        permission_manager.initialize()

    def _set_agent_system_prompt(self) -> None:
        agent_config = agent_manager.get(self._current_agent)
        base_prompt = agent_config.system_prompt if agent_config else ""
        rules = self._load_rules()
        if rules:
            base_prompt += f"\n\n---\n## Project Rules\n\n{rules}"
        self._system_message = {
            "role": "system",
            "content": base_prompt,
        }

    @property
    def current_agent(self) -> str:
        return self._current_agent

    @property
    def cwd(self) -> Path:
        return self._executor.cwd

    @cwd.setter
    def cwd(self, value: Path) -> None:
        self._executor.cwd = value
        self._async_executor.cwd = value
        self.config.cwd = value
        self._set_agent_system_prompt()

    @property
    def usage(self) -> dict[str, int]:
        return self._usage.copy()

    def _parse_subagent_invocation(self, user_input: str) -> tuple[str | None, str]:
        """Split an ``@agent task`` invocation into its agent name and task.

        Returns ``(None, user_input)`` when the input is not an invocation
        of a known subagent.
        """
        stripped = user_input.strip()
        if not stripped.startswith("@"):
            return None, user_input

        subagent_name, task = _split_invocation(stripped[1:])
        if subagent_name is None:
            return None, user_input
        if not _is_invocable_subagent(subagent_name):
            return None, user_input

        return subagent_name, task

    def chat(
        self,
        user_input: str,
        max_rounds: int | None = None,
        images: list[str] | None = None,
    ) -> str:
        subagent_name, actual_input = self._parse_subagent_invocation(user_input)

        if subagent_name:
            return self._chat_as_subagent(subagent_name, actual_input, max_rounds, images)

        return self._chat_internal(actual_input, max_rounds, images)

    def _chat_as_subagent(
        self,
        subagent_name: str,
        task: str,
        max_rounds: int | None = None,
        images: list[str] | None = None,
    ) -> str:
        original_agent = self._current_agent
        self._current_agent = subagent_name
        self._set_agent_system_prompt()

        try:
            result = self._chat_internal(task, max_rounds, images)
            return f"[@{subagent_name}]: {result}"
        finally:
            self._current_agent = original_agent
            self._set_agent_system_prompt()

    def _format_api_error(self, exc: Exception) -> str:
        """Render an LLM-provider exception as a user-facing error line."""
        if isinstance(exc, AuthenticationError):
            return (
                f"ERROR: Authentication failed. Check your API key for {self.model}. Details: {exc}"
            )
        if isinstance(exc, RateLimitError):
            return f"ERROR: Rate limit exceeded. Please wait and try again. Details: {exc}"
        if isinstance(exc, BadRequestError):
            logging.getLogger(__name__).error(f"BadRequestError: {exc}")
            return f"ERROR: Bad request. The model may not support tools. Details: {exc}"
        logging.getLogger(__name__).error(f"Unexpected error in chat: {type(exc).__name__}: {exc}")
        return f"ERROR: {type(exc).__name__}: {exc}"

    @staticmethod
    def _resolve_max_rounds(max_rounds: int | None) -> int:
        """Return the tool-round budget, defaulting to 10."""
        return max_rounds if max_rounds else 10

    def _prepare_vision_content(
        self,
        user_input: str,
        images: list[str] | None,
        model_str: str,
    ) -> tuple[str | list[dict[str, Any]] | None, str | None]:
        """Validate vision support and build the user content blocks.

        Returns ``(content, error)``. When the model cannot handle the
        attached images, ``content`` is ``None`` and ``error`` holds the
        message to return to the caller.
        """
        try:
            check_vision_support(model_str, len(images or []))
        except VisionNotSupportedError as exc:
            return None, f"ERROR: {exc}"
        return prepare_vision_input(user_input, images), None

    def _chat_internal(
        self,
        user_input: str,
        max_rounds: int | None = None,
        images: list[str] | None = None,
    ) -> str:
        if not _LITELLM_AVAILABLE:
            return "ERROR: litellm is not installed. Run: pip install litellm"
        self._maybe_auto_compact()
        model_str = MODELS.get(self._resolve_model_alias(), self._resolve_model_alias())

        # Fail fast, before any LLM call, when images outpace model capability.
        user_content, vision_error = self._prepare_vision_content(user_input, images, model_str)
        if vision_error is not None:
            return vision_error

        messages = self._request_messages(user_content)
        completion = CompletionParams(model=model_str, extra=self._completion_kwargs())

        for round_num in range(self._resolve_max_rounds(max_rounds)):
            try:
                messages = self._apply_context_budget(messages)
                response = litellm.completion(
                    model=completion.model,
                    messages=messages,
                    tools=get_all_tool_schemas(),
                    timeout=120,
                    **completion.extra,
                )
                self._update_usage(response.usage)

                tool_calls = response.choices[0].message.tool_calls
                if not tool_calls:
                    return self._record_turn(
                        user_content, response.choices[0].message.content or ""
                    )

                tool_calls_data = self._collect_tool_calls(tool_calls, messages)
                results = self._execute_tools(tool_calls_data)
                for tc_id, result in results:
                    messages.append(tool_result_message(tc_id, result))
            except Exception as e:  # noqa: BLE001
                return self._format_api_error(e)

        return "ERROR: Max tool rounds reached. The conversation was terminated due to too many tool calls."

    def _record_turn(self, user_content: Any, assistant_text: str) -> str:
        """Persist a finished turn in the history and return the assistant text."""
        self.history.append({"role": "user", "content": user_content})
        self.history.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    async def chat_streaming(
        self, user_input: str, max_rounds: int | None = None
    ) -> AsyncGenerator[str, None]:
        subagent_name, actual_input = self._parse_subagent_invocation(user_input)

        if subagent_name:
            async for chunk in self._chat_as_subagent_streaming(
                subagent_name, actual_input, max_rounds
            ):
                yield chunk
            return

        async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
            yield chunk

    async def _chat_as_subagent_streaming(
        self, subagent_name: str, actual_input: str, max_rounds: int | None
    ) -> AsyncGenerator[str, None]:
        """Stream a turn under a subagent, tagging every chunk with its name."""
        original_agent = self._current_agent
        self._current_agent = subagent_name
        self._set_agent_system_prompt()

        try:
            async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
                yield f"[@{subagent_name}]: {chunk}"
        finally:
            self._current_agent = original_agent
            self._set_agent_system_prompt()

    async def _chat_internal_streaming(
        self, user_input: str, max_rounds: int | None = None
    ) -> AsyncGenerator[str, None]:
        if not _LITELLM_AVAILABLE:
            yield "ERROR: litellm is not installed. Run: pip install litellm"
            return
        self._maybe_auto_compact()
        messages = self._request_messages(user_input)
        completion = CompletionParams(
            model=MODELS.get(self._resolve_model_alias(), self._resolve_model_alias()),
            extra=self._completion_kwargs(),
        )

        try:
            async for chunk in self._stream_conversation(
                messages, completion, user_input, max_rounds
            ):
                yield chunk
        except Exception as e:  # noqa: BLE001
            yield self._format_api_error(e)
            return

    async def _stream_conversation(
        self,
        messages: list[Any],
        completion: CompletionParams,
        user_input: str,
        max_rounds: int | None,
    ) -> AsyncGenerator[str, None]:
        """Run the streaming tool rounds until the model answers for good."""
        for round_num in range(self._resolve_max_rounds(max_rounds)):
            messages = self._apply_context_budget(messages)
            state = StreamState()
            async for chunk in self._stream_round(messages, completion, state):
                yield chunk
            self._update_usage(state.usage)

            async for chunk in self._continue_after_stream(state, messages, completion, user_input):
                yield chunk
            if state.turn_complete:
                return

        yield "ERROR: Max tool rounds reached."

    async def _continue_after_stream(
        self,
        state: StreamState,
        messages: list[Any],
        completion: CompletionParams,
        user_input: str,
    ) -> AsyncGenerator[str, None]:
        """Yield the final assistant text and flag whether the turn is over.

        When the model asks for more tools, ``state.turn_complete`` stays
        ``False`` and the caller starts another round.
        """
        if not state.tool_call_deltas or state.content:
            self._record_turn(user_input, state.content)
            state.turn_complete = True
            return

        text = await self._run_streamed_tool_round(
            state.tool_call_deltas, messages, completion, user_input
        )
        if text is None:
            return

        state.turn_complete = True
        yield text

    async def _stream_round(
        self,
        messages: list[Any],
        completion: CompletionParams,
        state: StreamState,
    ) -> AsyncGenerator[str, None]:
        """Stream one completion and fill ``state`` with what it produced."""
        response = await litellm.acompletion(
            model=completion.model,
            messages=messages,
            tools=get_all_tool_schemas(),
            stream=True,
            timeout=120,
            **completion.extra,
        )
        async for chunk in self._stream_completion(response, state):
            yield chunk

    async def _run_streamed_tool_round(
        self,
        tool_call_deltas: dict[int, dict[str, Any]],
        messages: list[Any],
        completion: CompletionParams,
        user_input: str,
    ) -> str | None:
        """Execute the streamed tool calls and ask the model for a follow-up.

        Returns the final assistant text when the model answered without
        requesting more tools, ``None`` when another tool round is needed.
        """
        tool_calls_data = self._collect_streamed_tool_calls(tool_call_deltas, messages)

        results = await self._execute_tools_parallel_async(tool_calls_data)
        for tc_id, result in results:
            messages.append(tool_result_message(tc_id, result))

        messages = self._apply_context_budget(messages)
        follow_up = await litellm.acompletion(
            model=completion.model,
            messages=messages,
            tools=get_all_tool_schemas(),
            timeout=120,
            **completion.extra,
        )
        self._update_usage(follow_up.usage)

        if follow_up.choices[0].message.tool_calls:
            return None

        return self._record_turn(user_input, follow_up.choices[0].message.content or "")

    def _collect_tool_calls(
        self,
        tool_calls: list[Any],
        messages: list[Any],
    ) -> list[tuple[str, str, dict]]:
        """Validate a batch of tool calls and return the executable ones.

        For every call the assistant message is appended to ``messages``. When
        the arguments are malformed or the tool is not permitted, an error is
        sent back to the model as a tool result instead of executing anything,
        so the model can recover on the next round.
        """
        tool_calls_data: list[tuple[str, str, dict]] = []
        for tc in tool_calls:
            tool_name = tc.function.name
            raw_args = tc.function.arguments

            tool_args, args_error = parse_tool_args(raw_args)
            if args_error:
                messages.append(assistant_tool_call_message(tc.id, tool_name, raw_args))
                messages.append(tool_result_message(tc.id, args_error))
                continue

            allowed, message = self._check_tool_permission(tool_name, tool_args)
            if not allowed:
                messages.append(assistant_tool_call_message(tc.id, tool_name, raw_args))
                messages.append(tool_result_message(tc.id, f"ERROR: {message}"))
                continue

            tool_calls_data.append((tc.id, tool_name, tool_args))
            messages.append(assistant_tool_call_message(tc.id, tool_name, raw_args))
        return tool_calls_data

    async def _stream_completion(
        self,
        response: Any,
        state: StreamState,
    ) -> AsyncGenerator[str, None]:
        """Yield the text chunks of a streamed completion.

        Tool-call deltas and the usage payload are accumulated in ``state``
        while the text is yielded to the caller.
        """
        async for chunk in response:
            if chunk.usage:
                state.usage = chunk.usage
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                state.content += delta.content
                yield delta.content

            for tc_delta in delta.tool_calls or []:
                merge_tool_call_delta(state.tool_call_deltas, tc_delta)

    def _collect_streamed_tool_calls(
        self,
        tool_call_deltas: dict[int, dict[str, Any]],
        messages: list[Any],
    ) -> list[tuple[str, str, dict]]:
        """Turn accumulated stream deltas into executable tool calls.

        For every streamed tool call, the assistant message is appended to
        ``messages`` and the arguments are validated. When the arguments are
        malformed or the tool is not permitted, an error is sent back to the
        model as a tool result instead of executing anything, so the model
        can recover on the next round.
        """
        tool_calls_data: list[tuple[str, str, dict]] = []
        for idx in sorted(tool_call_deltas.keys()):
            tc_info = tool_call_deltas[idx]
            tc_id = tc_info["id"]
            tool_name = tc_info["name"]
            raw_args = tc_info["arguments"]

            tool_args, args_error = parse_tool_args(raw_args)
            if args_error:
                messages.append(assistant_tool_call_message(tc_id, tool_name, raw_args))
                messages.append(tool_result_message(tc_id, args_error))
                continue

            allowed, message = self._check_tool_permission(tool_name, tool_args)
            if not allowed:
                messages.append(assistant_tool_call_message(tc_id, tool_name, raw_args))
                messages.append(tool_result_message(tc_id, f"ERROR: {message}"))
                continue

            tool_calls_data.append((tc_id, tool_name, tool_args))
            messages.append(assistant_tool_call_message(tc_id, tool_name, raw_args))
        return tool_calls_data

    def _execute_tools(self, tool_calls_data: list[tuple[str, str, dict]]) -> list[tuple[str, str]]:
        results = []
        for tc_id, tool_name, tool_args in tool_calls_data:
            result = self._executor.execute(tool_name, tool_args)
            results.append((tc_id, result))
        return results

    async def _execute_tools_parallel_async(
        self, tool_calls_data: list[tuple[str, str, dict]]
    ) -> list[tuple[str, str]]:
        tool_calls_list = [(name, args) for _, name, args in tool_calls_data]
        results = await self._async_executor.execute_all_parallel(tool_calls_list)
        return [
            (tc_id, result) for (tc_id, _, _), result in zip(tool_calls_data, results, strict=False)
        ]

    def _update_usage(self, usage: Any) -> None:
        if usage:
            self._usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            self._usage["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            self._usage["total_tokens"] += getattr(usage, "total_tokens", 0) or 0
