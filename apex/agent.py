"""Core agent loop for APEX - litellm integration and tool orchestration with multi-agent support."""

import json
import re
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

try:
    import litellm
    from litellm import BadRequestError, RateLimitError, AuthenticationError
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    BadRequestError = RateLimitError = AuthenticationError = Exception

from .config import Config, MODELS
from .tools import ToolExecutor, AsyncToolExecutor, get_all_tool_schemas
from .ui import UI
from .agents import agent_manager
from .permission import permission_manager, get_tool_permission
from .config_v2 import apex_config


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

    def _load_rules(self) -> str:
        parts = []
        project_dir = self.cwd

        # 1. Project AGENTS.md
        for name in ("AGENTS.md", "CLAUDE.md"):
            f = project_dir / name
            if f.is_file():
                content = f.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    parts.append(f"## {name} (project rules)\n{content}")
                break

        # 2. Global AGENTS.md (~/.config/apex/AGENTS.md)
        global_rules = Path.home() / ".config" / "apex" / "AGENTS.md"
        if not global_rules.is_file():
            global_rules = Path.home() / ".claude" / "CLAUDE.md"
        if global_rules.is_file():
            content = global_rules.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                parts.append(f"## {global_rules.name} (global rules)\n{content}")

        # 3. Custom instructions from config (glob patterns + URLs)
        for instr in apex_config.instructions:
            # Remote URL
            if instr.startswith(("http://", "https://")):
                try:
                    import ssl
                    import urllib.request
                    ctx = ssl.create_default_context()
                    req = urllib.request.Request(instr, headers={"User-Agent": "APEX/1.0"})
                    resp = urllib.request.urlopen(req, timeout=5, context=ctx)
                    content = resp.read().decode("utf-8", errors="replace").strip()
                    if content:
                        parts.append(f"## Instructions from {instr}\n{content}")
                except Exception:
                    pass
                continue
            # Local glob pattern
            matches = []
            p = Path(instr)
            if p.is_absolute():
                parent = p.parent
                pattern = p.name
                if parent.is_dir():
                    matches = list(parent.glob(pattern))
            else:
                pattern = instr
                matches = list(project_dir.glob(pattern))
                if not matches:
                    matches = list(Path.cwd().glob(pattern))
            for m in matches:
                if m.is_file():
                    content = m.read_text(encoding="utf-8", errors="replace").strip()
                    if content:
                        parts.append(f"## Instructions from {m}\n{content}")

        return "\n\n".join(parts) if parts else ""

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

    def cycle_reasoning_effort(self) -> str:
        order = ["off", "high", "max"]
        current = self.config.reasoning_effort
        if current not in order:
            current = "off"
        idx = order.index(current)
        next_idx = (idx + 1) % len(order)
        self.config.reasoning_effort = order[next_idx]
        return order[next_idx]

    def auto_select_model(self, user_input: str) -> str:
        text = user_input.lower()
        if "explain" in text:
            return "claude-sonnet-4"
        if "debug" in text:
            return "claude-sonnet-4"
        if "refactor" in text or "create" in text:
            return "gpt-4o"
        if "reason" in text:
            return "deepseek-reasoner"
        if len(text) > 2000:
            return "claude-sonnet-4"
        return "gpt-4o-mini"

    def reset_history(self) -> None:
        self.history = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _check_tool_permission(self, tool_name: str, tool_args: dict | None = None) -> tuple[bool, str]:
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
                return False, f"Agent '{self._current_agent}' requires approval for this bash command"
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

    def _chat_as_subagent(
        self, subagent_name: str, task: str, max_rounds: int | None = None
    ) -> str:
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
        if not _LITELLM_AVAILABLE:
            return "ERROR: litellm is not installed. Run: pip install litellm"
        max_rounds = max_rounds or 10
        messages = [self._system_message] + self.history + [{"role": "user", "content": user_input}]
        model_str = MODELS.get(self.model, self.model)

        for round_num in range(max_rounds):
            try:
                response = litellm.completion(
                    model=model_str, messages=messages, tools=get_all_tool_schemas(), timeout=120
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
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError as e:
                            logging.getLogger(__name__).error(f"Invalid tool args JSON: {e}")
                            messages.append(
                                {
                                    "role": "assistant",
                                    "tool_calls": [
                                        {
                                            "id": tc.id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": tc.function.arguments,
                                            },
                                        }
                                    ],
                                }
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": "ERROR: Invalid tool arguments format",
                                }
                            )
                            continue

                    if not isinstance(tool_args, dict):
                        logging.getLogger(__name__).error(
                            f"Tool args is not a dict: {type(tool_args)}"
                        )
                        messages.append(
                            {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": tool_name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": f"ERROR: Tool arguments must be a dict, got {type(tool_args).__name__}",
                            }
                        )
                        continue

                    allowed, message = self._check_tool_permission(tool_name, tool_args)
                    if not allowed:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {"role": "tool", "tool_call_id": tc.id, "content": f"ERROR: {message}"}
                        )
                        continue

                    tool_calls_data.append((tc.id, tool_name, tool_args))
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                }
                            ],
                        }
                    )

                results = self._execute_tools(tool_calls_data)
                for tc_id, result in results:
                    messages.append({"role": "tool", "tool_call_id": tc_id, "content": result})
            except AuthenticationError as e:
                return f"ERROR: Authentication failed. Check your API key for {self.model}. Details: {e}"
            except RateLimitError as e:
                return f"ERROR: Rate limit exceeded. Please wait and try again. Details: {e}"
            except BadRequestError as e:
                logging.getLogger(__name__).error(f"BadRequestError: {e}")
                return f"ERROR: Bad request. The model may not support tools. Details: {e}"
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"Unexpected error in _chat_internal: {type(e).__name__}: {e}"
                )
                return f"ERROR: {type(e).__name__}: {e}"

        return "ERROR: Max tool rounds reached. The conversation was terminated due to too many tool calls."

    async def chat_streaming(
        self, user_input: str, max_rounds: int | None = None
    ) -> AsyncGenerator[str, None]:
        subagent_name, actual_input = self._parse_subagent_invocation(user_input)

        if subagent_name:
            original_agent = self._current_agent
            self._current_agent = subagent_name
            self._set_agent_system_prompt()

            try:
                async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
                    yield f"[@{subagent_name}]: {chunk}"
            finally:
                self._current_agent = original_agent
                self._set_agent_system_prompt()
        else:
            async for chunk in self._chat_internal_streaming(actual_input, max_rounds):
                yield chunk

    async def _chat_internal_streaming(
        self, user_input: str, max_rounds: int | None = None
    ) -> AsyncGenerator[str, None]:
        if not _LITELLM_AVAILABLE:
            yield "ERROR: litellm is not installed. Run: pip install litellm"
            return
        max_rounds = max_rounds or 10
        messages = [self._system_message] + self.history + [{"role": "user", "content": user_input}]
        model_str = MODELS.get(self.model, self.model)

        for round_num in range(max_rounds):
            try:
                response = await litellm.acompletion(
                    model=model_str, messages=messages, tools=get_all_tool_schemas(), stream=True, timeout=120
                )

                full_content = ""
                tool_call_deltas: dict[int, dict[str, Any]] = {}
                usage_data = None

                async for chunk in response:
                    if chunk.usage:
                        usage_data = chunk.usage
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    if delta.content:
                        full_content += delta.content
                        yield delta.content

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_call_deltas:
                                tool_call_deltas[idx] = {
                                    "id": tc_delta.id or "",
                                    "name": "",
                                    "arguments": "",
                                }
                            if tc_delta.id:
                                tool_call_deltas[idx]["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    tool_call_deltas[idx]["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    tool_call_deltas[idx]["arguments"] += tc_delta.function.arguments

                self._update_usage(usage_data)

                if tool_call_deltas and not full_content:
                    tool_calls_data = []
                    for idx in sorted(tool_call_deltas.keys()):
                        tc_info = tool_call_deltas[idx]
                        tc_id = tc_info["id"]
                        tool_name = tc_info["name"]
                        raw_args = tc_info["arguments"]

                        tool_args: Any = raw_args
                        if isinstance(raw_args, str):
                            try:
                                tool_args = json.loads(raw_args) if raw_args.strip() else {}
                            except json.JSONDecodeError as e:
                                logging.getLogger(__name__).error(
                                    f"Invalid tool args JSON in streaming: {e}"
                                )
                                messages.append(
                                    {
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [
                                            {
                                                "id": tc_id,
                                                "type": "function",
                                                "function": {
                                                    "name": tool_name,
                                                    "arguments": raw_args,
                                                },
                                            }
                                        ],
                                    }
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc_id,
                                        "content": "ERROR: Invalid tool arguments format",
                                    }
                                )
                                continue

                        if not isinstance(tool_args, dict):
                            logging.getLogger(__name__).error(
                                f"Tool args is not a dict: {type(tool_args)}"
                            )
                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": tc_id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": raw_args,
                                            },
                                        }
                                    ],
                                }
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": f"ERROR: Tool arguments must be a dict, got {type(tool_args).__name__}",
                                }
                            )
                            continue

                        allowed, message = self._check_tool_permission(tool_name, tool_args)
                        if not allowed:
                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": tc_id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": raw_args,
                                            },
                                        }
                                    ],
                                }
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": f"ERROR: {message}",
                                }
                            )
                            continue

                        tool_calls_data.append((tc_id, tool_name, tool_args))
                        messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": tc_id,
                                        "type": "function",
                                        "function": {
                                            "name": tool_name,
                                            "arguments": raw_args,
                                        },
                                    }
                                ],
                            }
                        )

                    results = await self._execute_tools_parallel_async(tool_calls_data)
                    for tc_id, result in results:
                        messages.append({"role": "tool", "tool_call_id": tc_id, "content": result})

                    follow_up = await litellm.acompletion(
                        model=model_str, messages=messages, tools=get_all_tool_schemas(), timeout=120
                    )
                    self._update_usage(follow_up.usage)

                    if not follow_up.choices[0].message.tool_calls:
                        assistant_text = follow_up.choices[0].message.content or ""
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

    def _execute_tools(
        self, tool_calls_data: list[tuple[str, str, dict]]
    ) -> list[tuple[str, str]]:
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
        return [(tc_id, result) for (tc_id, _, _), result in zip(tool_calls_data, results)]

    def _update_usage(self, usage: Any) -> None:
        if usage:
            self._usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            self._usage["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            self._usage["total_tokens"] += getattr(usage, "total_tokens", 0) or 0
