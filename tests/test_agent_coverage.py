"""Comprehensive tests for apex/agent.py — aiming for 100% line coverage."""

import logging
from unittest.mock import MagicMock, patch

import litellm
import pytest

from apex.agent import Agent
from apex.config import Config, MODELS
from apex.agents import agent_manager
from apex.permission import permission_manager


# ---------------------------------------------------------------------------
# Helpers: build mock litellm responses
# ---------------------------------------------------------------------------


def _make_usage(prompt=10, completion=5):
    u = MagicMock()
    u.prompt_tokens = prompt
    u.completion_tokens = completion
    u.total_tokens = prompt + completion
    return u


def _make_choice(message):
    c = MagicMock()
    c.message = message
    return c


def _make_message(content=None, tool_calls=None):
    m = MagicMock()
    m.content = content
    m.tool_calls = tool_calls
    return m


def _make_tool_call(id="call_1", name="read_file", arguments='{"path": "test.txt"}'):
    tc = MagicMock()
    tc.id = id
    tc.function.name = name
    tc.function.arguments = arguments
    tc.type = "function"
    return tc


def _make_response(choices, usage=None):
    r = MagicMock()
    r.choices = choices
    r.usage = usage or _make_usage()
    return r


def _make_chunk(content=None, tool_calls=None, usage=None):
    """Build a mock streaming chunk."""
    ch = MagicMock()
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls
    choice = MagicMock()
    choice.delta = delta
    ch.choices = [choice]
    ch.usage = usage
    return ch


def _make_litellm_exception(exc_class, message="test error"):
    """Create a litellm exception of the given class."""
    resp = MagicMock()
    resp.status_code = 400
    resp.request = MagicMock()
    try:
        return exc_class(
            message=message,
            response=resp,
            llm_provider="openai",
            model="gpt-4o",
        )
    except TypeError:
        return exc_class(
            message=message,
            response=resp,
            model="gpt-4o",
            llm_provider="openai",
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent(tmp_path):
    """Fresh Agent with isolated config (no global config interference)."""
    cfg = Config(config_path=tmp_path / "test_config.json")
    return Agent(config=cfg)


@pytest.fixture
def agent_with_fake_config(tmp_path):
    """Agent with a config that writes to a temp directory."""
    cfg = Config(config_path=tmp_path / "test_config.json")
    return Agent(config=cfg)


@pytest.fixture(autouse=True)
def reset_permission_state():
    """Reset the singleton permission_manager before each test."""
    permission_manager._rules.clear()
    permission_manager._setup_default_rules()
    permission_manager._requests.clear()
    permission_manager._initialized = True
    yield


# ---------------------------------------------------------------------------
# Lines 61 — switch_model
# ---------------------------------------------------------------------------


class TestSwitchModel:
    def test_invalid_model_returns_false(self, agent):
        assert agent.switch_model("does-not-exist") is False

    def test_valid_model(self, agent):
        valid = next(k for k in MODELS if k != agent.model)
        assert agent.switch_model(valid) is True
        assert agent.model == valid

    def test_empty_string(self, agent):
        assert agent.switch_model("") is False


# ---------------------------------------------------------------------------
# Lines 68 — switch_agent
# ---------------------------------------------------------------------------


class TestSwitchAgent:
    def test_invalid_agent_returns_false(self, agent):
        assert agent.switch_agent("nonexistent") is False

    def test_valid_agent_switches(self, agent):
        assert agent.switch_agent("planner") is True
        assert agent.current_agent == "planner"


# ---------------------------------------------------------------------------
# Lines 74-82 — cycle_agent
# ---------------------------------------------------------------------------


class TestCycleAgent:
    def test_normal_cycle(self, agent):
        current = agent.current_agent
        result = agent.cycle_agent()
        assert isinstance(result, str)
        assert result != current

    def test_empty_primary_list(self, agent):
        with patch.object(agent_manager, "list_agents", return_value=[]):
            result = agent.cycle_agent()
            assert result == agent.current_agent

    def test_cycle_when_not_in_primary(self, agent):
        agent._current_agent = "reviewer"
        result = agent.cycle_agent()
        assert result in {"coder", "architect", "planner", "shell"}

    def test_cycle_wraps_around(self, agent):
        first = agent.current_agent
        primary = agent_manager.list_agents("primary")
        for _ in range(len(primary)):
            agent.cycle_agent()
        assert agent.current_agent == first


# ---------------------------------------------------------------------------
# Lines 85-92 — cycle_reasoning_effort
# ---------------------------------------------------------------------------


class TestCycleReasoningEffort:
    def test_off_to_high(self, agent):
        agent.config.reasoning_effort = "off"
        assert agent.cycle_reasoning_effort() == "high"

    def test_high_to_max(self, agent):
        agent.config.reasoning_effort = "high"
        assert agent.cycle_reasoning_effort() == "max"

    def test_max_to_off(self, agent):
        agent.config.reasoning_effort = "max"
        assert agent.cycle_reasoning_effort() == "off"

    def test_unknown_resets_to_off_then_cycles(self, agent):
        """Bypass Config setter (which would normalize 'ultra' to 'off')."""
        agent.config._data["reasoning_effort"] = "ultra"
        assert agent.cycle_reasoning_effort() == "high"


# ---------------------------------------------------------------------------
# Lines 46-53 — cwd property
# ---------------------------------------------------------------------------


class TestCwdProperty:
    def test_cwd_getter(self, agent):
        assert isinstance(agent.cwd, type(agent.cwd))

    def test_cwd_setter_updates_executor(self, agent, tmp_path):
        agent.cwd = tmp_path
        assert agent._executor.cwd == tmp_path
        assert agent._async_executor.cwd == tmp_path
        assert agent.config.cwd == tmp_path


# ---------------------------------------------------------------------------
# Lines 94-106 — auto_select_model
# ---------------------------------------------------------------------------


class TestAutoSelectModel:
    def test_explain(self, agent):
        assert agent.auto_select_model("explain this") == "claude-4-sonnet"

    def test_debug(self, agent):
        assert agent.auto_select_model("debug the app") == "claude-4-opus"

    def test_refactor(self, agent):
        assert agent.auto_select_model("refactor module") == "gpt-4o"

    def test_create(self, agent):
        assert agent.auto_select_model("create a file") == "gpt-4o"

    def test_reason(self, agent):
        assert agent.auto_select_model("reason deeply") == "deepseek-r1"

    def test_long_input(self, agent):
        assert agent.auto_select_model("x" * 2001) == "claude-4-sonnet"

    def test_default_short(self, agent):
        assert agent.auto_select_model("hi") == "gpt-4o-mini"

    def test_explain_precedes_length(self, agent):
        assert agent.auto_select_model("explain " + "x" * 2000) == "claude-4-sonnet"

    def test_case_insensitive(self, agent):
        assert agent.auto_select_model("DEBUG that") == "claude-4-opus"

    def test_explain_matches_first(self, agent):
        """'explain' is checked before 'debug', so 'explain' wins."""
        assert agent.auto_select_model("explain debug refactor") == "claude-4-sonnet"

    def test_debug_wins_when_explain_absent(self, agent):
        assert agent.auto_select_model("debug my code") == "claude-4-opus"


# ---------------------------------------------------------------------------
# Lines 108-110 — reset_history
# ---------------------------------------------------------------------------


class TestResetHistory:
    def test_reset_clears_history(self, agent):
        agent.history.append({"role": "user", "content": "x"})
        agent.reset_history()
        assert agent.history == []

    def test_reset_clears_usage(self, agent):
        agent._usage["prompt_tokens"] = 50
        agent.reset_history()
        assert agent.usage["prompt_tokens"] == 0


# ---------------------------------------------------------------------------
# Lines 112-114 — _check_tool_permission
# ---------------------------------------------------------------------------


class TestCheckToolPermission:
    def test_allowed_tool(self, agent):
        allowed, _ = agent._check_tool_permission("read_file")
        assert allowed is True

    def test_denied_tool(self, agent):
        allowed, msg = agent._check_tool_permission("write_file")
        assert allowed is False
        assert "Requires permission" in msg or "ASK" in msg


# ---------------------------------------------------------------------------
# Lines 116-165 — permission request / approve / deny
# ---------------------------------------------------------------------------


class TestPermissionRequestFlow:
    def test_request_permission(self, agent):
        rid = agent._request_permission("write_file", {"path": "x"}, "tc_1")
        assert rid.startswith("req_")
        assert rid in agent._pending_permissions

    def test_approve_permission(self, agent):
        rid = agent._request_permission("write_file", {}, "tc_1")
        assert agent.approve_permission(rid) is True
        assert rid not in agent._pending_permissions

    def test_approve_unknown(self, agent):
        assert agent.approve_permission("req_nonexistent") is False

    def test_approve_with_remember(self, agent):
        rid = agent._request_permission("write_file", {}, "tc_1")
        assert agent.approve_permission(rid, remember=True, expires_in=3600) is True

    def test_deny_permission(self, agent):
        rid = agent._request_permission("write_file", {}, "tc_1")
        assert agent.deny_permission(rid) is True
        assert rid not in agent._pending_permissions

    def test_deny_unknown(self, agent):
        assert agent.deny_permission("req_nonexistent") is False

    def test_get_pending_permissions(self, agent):
        rid = agent._request_permission("write_file", {"p": "x"}, "tc_1")
        pending = agent.get_pending_permissions()
        ids = [p["request_id"] for p in pending]
        assert rid in ids

    def test_pending_permissions_is_list(self, agent):
        assert isinstance(agent.get_pending_permissions(), list)


# ---------------------------------------------------------------------------
# Lines 167-176 — _parse_subagent_invocation
# ---------------------------------------------------------------------------


class TestParseSubagentInvocation:
    def test_subagent_match(self, agent):
        name, task = agent._parse_subagent_invocation("@reviewer check this")
        assert name == "reviewer"
        assert task == "check this"

    def test_no_subagent_match(self, agent):
        name, task = agent._parse_subagent_invocation("just a normal message")
        assert name is None
        assert task == "just a normal message"

    def test_unknown_subagent(self, agent):
        name, task = agent._parse_subagent_invocation("@ghost hi")
        assert name is None
        assert task == "@ghost hi"

    def test_subagent_not_subagent_mode(self, agent):
        name, task = agent._parse_subagent_invocation("@coder do something")
        assert name is None


# ---------------------------------------------------------------------------
# Lines 178-184 — chat (sync entry)
# ---------------------------------------------------------------------------


class TestChatSync:
    def test_chat_subagent_delegation(self, agent):
        with patch.object(agent, "_chat_as_subagent", return_value="[reviewer]: ok"):
            result = agent.chat("@reviewer check this")
            assert result == "[reviewer]: ok"

    def test_chat_normal(self, agent):
        with patch.object(agent, "_chat_internal", return_value="hello"):
            result = agent.chat("hi there")
            assert result == "hello"


# ---------------------------------------------------------------------------
# Lines 186-198 — _chat_as_subagent
# ---------------------------------------------------------------------------


class TestChatAsSubagent:
    def test_subagent_chat_preserves_original_agent(self, agent):
        assert agent.current_agent == "coder"
        with patch.object(agent, "_chat_internal", return_value="done"):
            result = agent._chat_as_subagent("reviewer", "review this")
            assert result == "[@reviewer]: done"
        assert agent.current_agent == "coder"

    def test_subagent_chat_restores_on_error(self, agent):
        class CustomError(Exception):
            pass

        with patch.object(agent, "_chat_internal", side_effect=CustomError("boom")):
            with pytest.raises(CustomError):
                agent._chat_as_subagent("reviewer", "review this")
        assert agent.current_agent == "coder"


# ---------------------------------------------------------------------------
# Lines 200-314 — _chat_internal
# ---------------------------------------------------------------------------


class TestChatInternal:
    def test_no_tool_calls_returns_text(self, agent):
        response = _make_response(
            [_make_choice(_make_message(content="Hello world"))],
            usage=_make_usage(10, 5),
        )
        with patch("apex.agent.litellm.completion", return_value=response):
            result = agent.chat("say hello")

        assert result == "Hello world"
        assert len(agent.history) == 2
        assert agent.usage["total_tokens"] == 15

    def test_tool_call_execution_flow(self, agent):
        tc = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "x"}')
        response1 = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        response2 = _make_response(
            [_make_choice(_make_message(content="file content"))],
        )
        with (
            patch("apex.agent.litellm.completion", side_effect=[response1, response2]),
            patch.object(agent._executor, "execute", return_value="x content"),
        ):
            result = agent.chat("read x")
        assert result == "file content"
        assert len(agent.history) == 2

    def test_tool_call_invalid_json_args(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        tc = _make_tool_call(id="call_1", name="read_file", arguments="{invalid json}")
        response1 = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        response2 = _make_response(
            [_make_choice(_make_message(content="error handled"))],
        )
        with patch("apex.agent.litellm.completion", side_effect=[response1, response2]):
            result = agent.chat("do it")
        assert result == "error handled"
        assert any("Invalid tool args JSON" in msg for msg in caplog.messages)

    def test_tool_call_args_not_dict(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        tc = _make_tool_call(id="call_1", name="read_file", arguments="[1, 2, 3]")
        response1 = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        with (
            patch("apex.agent.litellm.completion", return_value=response1),
            patch.object(agent._executor, "execute", return_value="result"),
        ):
            result = agent.chat("do it")
        assert "Max tool rounds reached" in result
        assert any("Tool args is not a dict" in msg for msg in caplog.messages)

    def test_tool_call_permission_denied(self, agent):
        tc = _make_tool_call(id="call_1", name="write_file", arguments='{"path": "x"}')
        response1 = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        response2 = _make_response(
            [_make_choice(_make_message(content="permission handled"))],
        )
        with patch("apex.agent.litellm.completion", side_effect=[response1, response2]):
            result = agent.chat("write x")
        assert result == "permission handled"

    def test_authentication_error(self, agent):
        with patch("apex.agent.litellm.completion", side_effect=_make_litellm_exception(litellm.AuthenticationError)):
            result = agent.chat("hi")
        assert "Authentication failed" in result
        assert agent.history == []

    def test_rate_limit_error(self, agent):
        with patch("apex.agent.litellm.completion", side_effect=_make_litellm_exception(litellm.RateLimitError)):
            result = agent.chat("hi")
        assert "Rate limit exceeded" in result

    def test_bad_request_error(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        with patch("apex.agent.litellm.completion", side_effect=_make_litellm_exception(litellm.BadRequestError)):
            result = agent.chat("hi")
        assert "Bad request" in result
        assert any("BadRequestError" in msg for msg in caplog.messages)

    def test_generic_exception(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        with patch("apex.agent.litellm.completion", side_effect=ValueError("boom")):
            result = agent.chat("hi")
        assert "ValueError" in result
        assert any("Unexpected error" in msg for msg in caplog.messages)

    def test_max_rounds_reached(self, agent):
        tc = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "x"}')
        response = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        agent.config._data["max_tool_rounds"] = 1
        with (
            patch("apex.agent.litellm.completion", return_value=response),
            patch.object(agent._executor, "execute", return_value="result"),
        ):
            result = agent.chat("do it")
        assert "Max tool rounds reached" in result

    def test_multiple_tool_calls(self, agent):
        tc1 = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "a"}')
        tc2 = _make_tool_call(id="call_2", name="read_file", arguments='{"path": "b"}')
        response1 = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc1, tc2]))],
        )
        response2 = _make_response(
            [_make_choice(_make_message(content="both done"))],
        )
        with (
            patch("apex.agent.litellm.completion", side_effect=[response1, response2]),
            patch.object(agent._executor, "execute", return_value="content"),
        ):
            result = agent.chat("read both")
        assert result == "both done"

    def test_usage_none_does_not_raise(self, agent):
        agent._update_usage(None)
        assert agent.usage["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Lines 316-334 — chat_streaming (async, subagent + normal)
# ---------------------------------------------------------------------------


class TestChatStreaming:
    @pytest.mark.asyncio
    async def test_streaming_subagent(self, agent):
        with patch.object(agent, "_chat_internal_streaming") as mock_stream:
            async def _gen():
                yield "hello"
                yield "world"
            mock_stream.return_value = _gen()

            chunks = []
            async for chunk in agent.chat_streaming("@reviewer check"):
                chunks.append(chunk)
            assert chunks == ["[@reviewer]: hello", "[@reviewer]: world"]

    @pytest.mark.asyncio
    async def test_streaming_normal(self, agent):
        with patch.object(agent, "_chat_internal_streaming") as mock_stream:
            async def _gen():
                yield "chunk1"
                yield "chunk2"
            mock_stream.return_value = _gen()

            chunks = []
            async for chunk in agent.chat_streaming("hi"):
                chunks.append(chunk)
            assert chunks == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_streaming_subagent_restores_agent_on_error(self, agent):
        agent.switch_agent("planner")
        with patch.object(agent, "_chat_internal_streaming") as mock_stream:
            async def _gen():
                yield "hello"
                raise ValueError("boom")
            mock_stream.return_value = _gen()

            with pytest.raises(ValueError):
                async for _ in agent.chat_streaming("@reviewer check"):
                    pass
        assert agent.current_agent == "planner"


# ---------------------------------------------------------------------------
# Lines 343-488 — _chat_internal_streaming
# ---------------------------------------------------------------------------


class TestChatInternalStreaming:
    @pytest.mark.asyncio
    async def test_streaming_text_response(self, agent):
        chunk1 = _make_chunk(content="Hello")
        chunk2 = _make_chunk(content=" world")
        with patch("apex.agent.litellm.completion", return_value=[chunk1, chunk2]):
            chunks = []
            async for c in agent._chat_internal_streaming("say hi"):
                chunks.append(c)
        assert chunks == ["Hello", " world"]
        assert len(agent.history) == 2

    @pytest.mark.asyncio
    async def test_streaming_tool_call_then_text(self, agent):
        tc = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "x"}')
        chunk_tc = _make_chunk(content=None, tool_calls=[tc])
        response2 = _make_response([_make_choice(_make_message(content="file result"))])
        with (
            patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response2]),
            patch.object(agent._executor, "execute", return_value="x content"),
        ):
            chunks = []
            async for c in agent._chat_internal_streaming("read x"):
                chunks.append(c)
        assert chunks == ["file result"]
        assert len(agent.history) == 2

    @pytest.mark.asyncio
    async def test_streaming_bad_request_error(self, agent):
        exc = _make_litellm_exception(litellm.BadRequestError)
        with patch("apex.agent.litellm.completion", side_effect=exc):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert any("Bad request" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_rate_limit_error(self, agent):
        exc = _make_litellm_exception(litellm.RateLimitError)
        with patch("apex.agent.litellm.completion", side_effect=exc):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert any("Rate limit exceeded" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_auth_error(self, agent):
        exc = _make_litellm_exception(litellm.AuthenticationError)
        with patch("apex.agent.litellm.completion", side_effect=exc):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert any("Authentication failed" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_generic_exception(self, agent):
        with patch("apex.agent.litellm.completion", side_effect=RuntimeError("crash")):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert any("RuntimeError" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_max_rounds(self, agent):
        tc = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "x"}')
        chunk_tc = _make_chunk(content=None, tool_calls=[tc])
        response_with_tc = _make_response(
            [_make_choice(_make_message(content=None, tool_calls=[tc]))],
        )
        agent.config._data["max_tool_rounds"] = 1
        with (
            patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response_with_tc]),
            patch.object(agent._executor, "execute", return_value="result"),
        ):
            chunks = []
            async for c in agent._chat_internal_streaming("read x"):
                chunks.append(c)
        assert any("Max tool rounds" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_tool_call_invalid_json(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        tc = _make_tool_call(id="call_1", name="read_file", arguments="{bad json}")
        chunk_tc = _make_chunk(content=None, tool_calls=[tc])
        response2 = _make_response([_make_choice(_make_message(content="done"))])
        with patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response2]):
            chunks = []
            async for c in agent._chat_internal_streaming("read x"):
                chunks.append(c)
        assert any("done" in c for c in chunks)
        assert any("Invalid tool args JSON in streaming" in m for m in caplog.messages)

    @pytest.mark.asyncio
    async def test_streaming_tool_call_args_not_dict(self, agent, caplog):
        caplog.set_level(logging.ERROR)
        tc = _make_tool_call(id="call_1", name="read_file", arguments="[1, 2]")
        chunk_tc = _make_chunk(content=None, tool_calls=[tc])
        response2 = _make_response([_make_choice(_make_message(content="fallback"))])
        with patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response2]):
            chunks = []
            async for c in agent._chat_internal_streaming("do it"):
                chunks.append(c)
        assert any("Tool args is not a dict" in m for m in caplog.messages)

    @pytest.mark.asyncio
    async def test_streaming_tool_call_permission_denied(self, agent):
        tc = _make_tool_call(id="call_1", name="write_file", arguments='{"path": "x"}')
        chunk_tc = _make_chunk(content=None, tool_calls=[tc])
        response2 = _make_response([_make_choice(_make_message(content="permission resolved"))])
        with patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response2]):
            chunks = []
            async for c in agent._chat_internal_streaming("write x"):
                chunks.append(c)
        assert any("permission resolved" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_content_with_tool_calls_takes_else_branch(self, agent):
        tc = _make_tool_call(id="call_1", name="read_file", arguments='{"path": "x"}')
        chunk = _make_chunk(content="some text", tool_calls=[tc])
        with patch("apex.agent.litellm.completion", return_value=[chunk]):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert "some text" in chunks
        assert len(agent.history) == 2

    @pytest.mark.asyncio
    async def test_streaming_usage_on_chunk(self, agent):
        chunk = _make_chunk(content="hello", usage=_make_usage(5, 3))
        with patch("apex.agent.litellm.completion", return_value=[chunk]):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert agent.usage["total_tokens"] == 8

    @pytest.mark.asyncio
    async def test_streaming_usage_none(self, agent):
        chunk = _make_chunk(content="hi")
        with patch("apex.agent.litellm.completion", return_value=[chunk]):
            chunks = []
            async for c in agent._chat_internal_streaming("hi"):
                chunks.append(c)
        assert agent.usage["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_streaming_multiple_tool_calls(self, agent):
        tc1 = _make_tool_call(id="c1", name="read_file", arguments='{"path": "a"}')
        tc2 = _make_tool_call(id="c2", name="read_file", arguments='{"path": "b"}')
        chunk_tc = _make_chunk(content=None, tool_calls=[tc1, tc2])
        response2 = _make_response([_make_choice(_make_message(content="multi done"))])
        with (
            patch("apex.agent.litellm.completion", side_effect=[[chunk_tc], response2]),
            patch.object(agent._executor, "execute", return_value="content"),
        ):
            chunks = []
            async for c in agent._chat_internal_streaming("read"):
                chunks.append(c)
        assert "multi done" in chunks


# ---------------------------------------------------------------------------
# Lines 490-497 — _execute_tools_parallel
# ---------------------------------------------------------------------------


class TestExecuteToolsParallel:
    def test_execute_multiple_tools(self, agent):
        data = [("tc_1", "read_file", {"path": "a.txt"}), ("tc_2", "read_file", {"path": "b.txt"})]
        with patch.object(agent._executor, "execute", side_effect=["content_a", "content_b"]):
            results = agent._execute_tools_parallel(data)
        assert results == [("tc_1", "content_a"), ("tc_2", "content_b")]

    def test_execute_single_tool(self, agent):
        data = [("tc_1", "read_file", {"path": "x.txt"})]
        with patch.object(agent._executor, "execute", return_value="result"):
            results = agent._execute_tools_parallel(data)
        assert results == [("tc_1", "result")]

    def test_execute_empty(self, agent):
        results = agent._execute_tools_parallel([])
        assert results == []


# ---------------------------------------------------------------------------
# Lines 499-504 — _execute_tools_parallel_async
# ---------------------------------------------------------------------------


class TestExecuteToolsParallelAsync:
    @pytest.mark.asyncio
    async def test_async_execute(self, agent):
        data = [("tc_1", "read_file", {"path": "a.txt"}), ("tc_2", "read_file", {"path": "b.txt"})]
        with patch.object(agent._async_executor, "execute_all_parallel", return_value=["content_a", "content_b"]):
            results = await agent._execute_tools_parallel_async(data)
        assert results == [("tc_1", "content_a"), ("tc_2", "content_b")]


# ---------------------------------------------------------------------------
# Lines 506-510 — _update_usage
# ---------------------------------------------------------------------------


class TestUpdateUsage:
    def test_none_usage(self, agent):
        agent._update_usage(None)
        assert agent.usage["total_tokens"] == 0

    def test_partial_usage(self, agent):
        u = MagicMock()
        u.prompt_tokens = 10
        u.completion_tokens = None
        u.total_tokens = None
        agent._update_usage(u)
        assert agent.usage["prompt_tokens"] == 10
        assert agent.usage["completion_tokens"] == 0
        assert agent.usage["total_tokens"] == 0

    def test_full_usage(self, agent):
        agent._update_usage(_make_usage(100, 50))
        assert agent.usage["prompt_tokens"] == 100
        assert agent.usage["completion_tokens"] == 50
        assert agent.usage["total_tokens"] == 150

    def test_accumulates(self, agent):
        agent._update_usage(_make_usage(10, 5))
        agent._update_usage(_make_usage(20, 10))
        assert agent.usage["prompt_tokens"] == 30
        assert agent.usage["total_tokens"] == 45


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_init_with_none_config(self):
        agent = Agent(config=None)
        assert isinstance(agent.config, Config)

    def test_parse_subagent_no_match_short(self, agent):
        name, task = agent._parse_subagent_invocation("@")
        assert name is None
        assert task == "@"

    def test_parse_subagent_just_name(self, agent):
        name, task = agent._parse_subagent_invocation("@reviewer")
        assert name is None


# ---------------------------------------------------------------------------
# _set_agent_system_prompt / _set_agent_prompt coverage
# ---------------------------------------------------------------------------


class TestAgentPrompt:
    def test_set_agent_system_prompt(self, agent):
        old = agent._system_message["content"]
        agent.switch_agent("planner")
        assert agent._system_message["content"] != old

    def test_set_agent_prompt_direct(self, agent):
        agent._current_agent = "reviewer"
        agent._set_agent_prompt()
        assert agent._system_message["role"] == "system"
        assert len(agent._system_message["content"]) > 0
