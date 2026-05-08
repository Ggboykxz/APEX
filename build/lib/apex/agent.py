"""Core agent loop for APEX - litellm integration and tool orchestration."""

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator

import litellm
from litellm import BadRequestError, RateLimitError, AuthenticationError

from .config import Config, MODELS, SYSTEM_PROMPT, DEFAULT_MODEL
from .tools import ToolExecutor, AsyncToolExecutor, TOOL_SCHEMAS
from .ui import UI


class Agent:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.model = self.config.model
        self._executor = ToolExecutor(cwd=self.config.cwd)
        self._async_executor = AsyncToolExecutor(cwd=self.config.cwd)
        self._ui = UI()
        self.history: list[dict[str, Any]] = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._setup_system_message()

    def _setup_system_message(self) -> None:
        self._system_message = {
            "role": "system",
            "content": SYSTEM_PROMPT
        }

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

    def reset_history(self) -> None:
        self.history = []
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def chat(self, user_input: str, max_rounds: int | None = None) -> str:
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

    def chat_streaming(self, user_input: str, max_rounds: int | None = None) -> AsyncGenerator[str, None]:
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