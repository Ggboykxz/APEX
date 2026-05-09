"""Core agent loop for APEX - litellm integration and tool orchestration with multi-agent support."""

import json
import re
from pathlib import Path
from typing import Any, AsyncGenerator

import litellm
from litellm import BadRequestError, RateLimitError, AuthenticationError

from .config import Config, MODELS
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI
from .agents import agent_manager
from .permission import permission_manager, get_tool_permission

from .permission import PermissionRequestDenied


class PermissionRequestDenied(Exception):
    def __init__(self, tool_name: str, permission: str, request_id: str):
        self.tool_name = tool_name
        self.permission = permission
        self.request_id = request_id
        super().__init__(f"Permission required for {tool_name}: {permission}")


class Agent:
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
        permission_manager.initialize()

    def _set_agent_system_prompt(self) -> None:
        agent_config = agent_manager.get(self._current_agent)
        self._system_message = {
            "role": "system",
            "content": agent_config.system_prompt if agent_config else ""
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

    @property
    def usage(self) -> dict[str, int]:
        return self._usage.copy()

    def switch_model(self, alias: str) -> bool:
        if alias not in MODELS:
            return False
        self.model = alias
        self.config.model = alias
        return True

    def switch_agent(self, agent_name: str) -> bool:
        if agent_name not in agent_manager.agents:
            return False
        self._current_agent = agent_name
        self._set_agent_system_prompt()
        return True

    def cycle_agent(self) -> str:
        primary_agents = agent_manager.list_agents("primary")
        if not primary_agents:
            return self._current_agent
        names = [a.name for a in primary_agents]
        current_idx = names.index(self._current_agent) if self._current_agent in names else 0
        next_idx = (current_idx + 1) % len(names)
        self._current_agent = names[next_idx]
        self._set_agent_system_prompt()
        return self._current_agent

    def reset_history(self) -> None:
        self.history = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _check_tool_permission(self, tool_name: str) -> tuple[bool, str]:
        permission = get_tool_permission(tool_name)
        can_execute, reason = permission_manager.can_execute_tool(tool_name)
        return can_execute, reason

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

    def approve_permission(self, request_id: str, remember: bool = False, expires_in: int | None = None) -> bool:
        """Approve a pending permission request."""
        if request_id not in self._pending_permissions:
            return False
        result = permission_manager.approve_request(request_id, remember=remember, expires_in=expires_in)
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
        return [
            {
                "request_id": req.request_id,
                "tool_name": req.tool_name,
                "permission": req.permission,
                "args": req.args,
                "timestamp": req.timestamp,
            }
            for req in pending
        ]

    def _parse_subagent_invocation(self, user_input: str) -> tuple[str | None, str]:
        match = re.match(r"^@(\w+)\s+(.+)$", user_input.strip())
        if match:
            subagent_name = match.group(1)
            task = match.group(2)
            if subagent_name in agent_manager.agents:
                agent = agent_manager.get(subagent_name)
                if agent and (agent.mode == "subagent" or agent.mode == "all"):
                    return subagent_name, task
        return None, user_input

    def chat(self, user_input: str, max_rounds: int | None = None) -> str:
        subagent_name, actual_input = self._parse_subagent_invocation(user_input)

        if subagent_name:
            return self._chat_as_subagent(subagent_name, actual_input, max_rounds)

        return self._chat_internal(actual_input, max_rounds)

    def _chat_as_subagent(self, subagent_name: str, task: str, max_rounds: int | None = None) -> str:
        original_agent = self._current_agent
        self._current_agent = subagent_name
        self._set_agent_system_prompt()

        try:
            result = self._chat_internal(task, max_rounds)
            return f"[@{subagent_name}]: {result}"
        finally:
            self._current_agent = original_agent
            self._set_agent_system_prompt()

    def _chat_internal(self, user_input: str, max_rounds: int | None = None) -> str:
        max_rounds = max_rounds or self.config.max_tool_rounds
        messages = [self._system_message] + self.history + [{"role": "user", "content": user_input}]
        model_str = MODELS.get(self.model, self.model)

        for round_num in range(max_rounds):
            try:
                response = litellm.completion(
                    model=model_str,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    timeout=120
                )
                self._update_usage(response.usage)
                if not response.choices[0].message.tool_calls:
                    assistant_text = response.choices[0].message.content or ""
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": assistant_text})
                    return assistant_text

                tool_calls = response.choices[0].message.tool_calls
                tool_calls_data = []
                for tc in tool_calls:
                    tool_name = tc.function.name
                    tool_args = tc.function.arguments
                    if isinstance(tool_args, str):
                        tool_args = json.loads(tool_args)

                    allowed, message = self._check_tool_permission(tool_name)
                    if not allowed:
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"ERROR: {message}"
                        })
                        continue

                    tool_calls_data.append((tc.id, tool_name, tool_args))
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }]
                    })

                results = self._execute_tools_parallel(tool_calls_data)
                for tc_id, result in results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result
                    })
            except AuthenticationError as e:
                return f"ERROR: Authentication failed. Check your API key for {self.model}. Details: {e}"
            except RateLimitError as e:
                return f"ERROR: Rate limit exceeded. Please wait and try again. Details: {e}"
            except BadRequestError as e:
                return f"ERROR: Bad request. The model may not support tools. Details: {e}"
            except Exception as e:
                return f"ERROR: {type(e).__name__}: {e}"

        return "ERROR: Max tool rounds reached. The conversation was terminated due to too many tool calls."

    async def chat_streaming(self, user_input: str, max_rounds: int | None = None) -> AsyncGenerator[str, None]:
        subagent_name, actual_input = self._parse_subagent_invocation(user_input)

        if subagent_name:
            original_agent = self._current_agent
            self._current_agent = subagent_name
            self._set_agent_prompt()

            try:
                async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
                    yield f"[@{subagent_name}]: {chunk}"
            finally:
                self._current_agent = original_agent
                self._set_agent_system_prompt()
        else:
            async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
                yield chunk

    def _set_agent_prompt(self) -> None:
        agent_config = agent_manager.get(self._current_agent)
        self._system_message = {
            "role": "system",
            "content": agent_config.system_prompt if agent_config else ""
        }

    async def _chat_internal_streaming(self, user_input: str, max_rounds: int | None = None) -> AsyncGenerator[str, None]:
        max_rounds = max_rounds or self.config.max_tool_rounds
        messages = [self._system_message] + self.history + [{"role": "user", "content": user_input}]
        model_str = MODELS.get(self.model, self.model)

        for round_num in range(max_rounds):
            try:
                response = litellm.completion(
                    model=model_str,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    stream=True,
                    timeout=120
                )

                full_content = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield content

                    if chunk.choices[0].delta.tool_calls:
                        break

                self._update_usage(chunk.usage if hasattr(chunk, 'usage') else None)

                if not full_content and chunk.choices[0].delta.tool_calls:
                    tool_calls_data = []
                    for tc in chunk.choices[0].delta.tool_calls:
                        tool_args = tc.function.arguments
                        if isinstance(tool_args, str):
                            tool_args = json.loads(tool_args)

                        allowed, message = self._check_tool_permission(tc.function.name)
                        if not allowed:
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": f"ERROR: {message}"
                            })
                            continue

                        tool_calls_data.append((tc.id, tc.function.name, tool_args))
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }]
                        })

                    results = self._execute_tools_parallel(tool_calls_data)
                    for tc_id, result in results:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result
                        })

                    response = litellm.completion(
                        model=model_str,
                        messages=messages,
                        tools=TOOL_SCHEMAS,
                        timeout=120
                    )
                    self._update_usage(response.usage)

                    if not response.choices[0].message.tool_calls:
                        assistant_text = response.choices[0].message.content or ""
                        self.history.append({"role": "user", "content": user_input})
                        self.history.append({"role": "assistant", "content": assistant_text})
                        yield assistant_text
                        return
                else:
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": full_content})
                    return

            except AuthenticationError as e:
                yield f"ERROR: Authentication failed. Check your API key for {self.model}. Details: {e}"
                return
            except RateLimitError as e:
                yield f"ERROR: Rate limit exceeded. Please wait and try again. Details: {e}"
                return
            except BadRequestError as e:
                yield f"ERROR: Bad request. The model may not support tools. Details: {e}"
                return
            except Exception as e:
                yield f"ERROR: {type(e).__name__}: {e}"
                return

        yield "ERROR: Max tool rounds reached."

    def _execute_tools_parallel(self, tool_calls_data: list[tuple[str, str, dict]]) -> list[tuple[str, str]]:
        results = []
        for tc_id, tool_name, tool_args in tool_calls_data:
            result = self._executor.execute(tool_name, tool_args)
            results.append((tc_id, result))
        return results

    async def _execute_tools_parallel_async(self, tool_calls_data: list[tuple[str, str, dict]]) -> list[tuple[str, str]]:
        tool_calls_list = [(name, args) for _, name, args in tool_calls_data]
        results = await self._async_executor.execute_all_parallel(tool_calls_list)
        return [(tc_id, result) for (tc_id, _, _), result in zip(tool_calls_data, results)]

    def _update_usage(self, usage: Any) -> None:
        if usage:
            self._usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            self._usage["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            self._usage["total_tokens"] += getattr(usage, "total_tokens", 0) or 0