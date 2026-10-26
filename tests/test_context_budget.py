"""Tests for apex.context_budget and its agent/config integration."""

from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace
from unittest.mock import patch

# litellm attempts a network fetch on import unless this is set. Tests must not
# depend on internet access.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import pytest

from apex import context_budget
from apex.context_budget import (
    REPO_MAP_MARKER,
    ContextStats,
    count_message_tokens,
    estimate_tokens,
    inject_repo_map,
    prune_tool_outputs,
)

_MARKER_RE = re.compile(r"^\[tool output pruned: (\d+) chars, sha256:([0-9a-f]{8})\]$")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_repomap_cache(monkeypatch, tmp_path):
    """Keep repository-map cache writes inside the test sandbox."""
    monkeypatch.setattr("apex.repomap._cache_dir", lambda: tmp_path / "repomap-cache")


@pytest.fixture
def repo(tmp_path):
    """A small repository with Python symbols."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "models.py").write_text(
        "class Widget:\n"
        "    def render(self, text: str) -> str:\n"
        "        return text\n"
        "\n"
        "def build_widget(name: str) -> Widget:\n"
        "    return Widget()\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from package.models import build_widget\n\ndef main():\n    return build_widget('x')\n",
        encoding="utf-8",
    )
    return tmp_path


def _tool(index: int, size: int = 100, char: str = "x") -> dict:
    return {
        "role": "tool",
        "tool_call_id": f"call_{index}",
        "content": char * size,
    }


def _conversation(tool_count: int = 5, size: int = 100) -> list[dict]:
    messages = [
        {"role": "system", "content": "You are APEX."},
        {"role": "user", "content": "Do the thing."},
        {"role": "assistant", "content": "Working on it."},
    ]
    messages.extend(_tool(index, size=size) for index in range(tool_count))
    return messages


# ---------------------------------------------------------------------------
# estimate_tokens / ContextStats
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_delegates_to_repomap(self):
        from apex.repomap import estimate_tokens as repomap_estimate

        for text in ("", "a", "abcd", "a" * 101):
            assert estimate_tokens(text) == repomap_estimate(text)

    def test_empty_and_rounding(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("abcde") == 2


class TestContextStats:
    def test_defaults(self):
        stats = ContextStats()
        assert stats.tokens_before == 0
        assert stats.tokens_after == 0
        assert stats.pruned_messages == 0
        assert stats.pruned_chars == 0
        assert stats.repo_map_tokens == 0

    def test_to_dict(self):
        stats = ContextStats(100, 40, 3, 250, 12)
        assert stats.to_dict() == {
            "tokens_before": 100,
            "tokens_after": 40,
            "pruned_messages": 3,
            "pruned_chars": 250,
            "repo_map_tokens": 12,
        }

    def test_to_dict_is_a_copy(self):
        stats = ContextStats(1, 2, 3, 4, 5)
        payload = stats.to_dict()
        payload["tokens_before"] = 99
        assert stats.tokens_before == 1


# ---------------------------------------------------------------------------
# prune_tool_outputs
# ---------------------------------------------------------------------------


class TestPruneToolOutputs:
    def test_preserves_non_tool_and_recent_messages(self):
        messages = _conversation(tool_count=5, size=100)
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=20, keep_recent=2)

        assert [m["role"] for m in pruned] == [m["role"] for m in messages]
        assert pruned[0] == messages[0]
        assert pruned[1] == messages[1]
        assert pruned[2] == messages[2]
        # First three tool results are old and oversized; last two are recent.
        for message in pruned[3:6]:
            assert _MARKER_RE.fullmatch(message["content"])
        assert pruned[6]["content"] == "x" * 100
        assert pruned[7]["content"] == "x" * 100
        assert stats.pruned_messages == 3
        assert stats.pruned_chars == 3 * (100 - len(pruned[3]["content"]))
        assert stats.tokens_before > stats.tokens_after

    def test_does_not_mutate_input(self):
        messages = _conversation(tool_count=4, size=120)
        snapshot = [dict(message) for message in messages]

        pruned, _ = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=1)

        assert messages == snapshot
        assert all(message["content"] == "x" * 120 for message in messages[3:])
        assert pruned is not messages
        assert pruned[3] is not messages[3]

    def test_marker_is_deterministic(self):
        first, _ = prune_tool_outputs(_conversation(tool_count=1, size=40), 10, 0)
        second, _ = prune_tool_outputs(_conversation(tool_count=1, size=40), 10, 0)
        marker = first[3]["content"]
        assert marker == second[3]["content"]
        match = _MARKER_RE.fullmatch(marker)
        assert match is not None
        assert match.group(1) == "40"
        assert len(match.group(2)) == 8

    def test_idempotent(self):
        messages = _conversation(tool_count=4, size=80)
        first, first_stats = prune_tool_outputs(messages, 10, 1)
        second, second_stats = prune_tool_outputs(first, 10, 1)

        assert second == first
        assert first_stats.pruned_messages == 3
        assert second_stats.pruned_messages == 0
        assert second_stats.pruned_chars == 0
        assert second_stats.tokens_before == second_stats.tokens_after

    def test_idempotent_with_marker_longer_than_limit(self):
        messages = [_tool(0, size=50)]
        first, _ = prune_tool_outputs(messages, max_chars_per_result=1, keep_recent=0)
        second, stats = prune_tool_outputs(first, max_chars_per_result=1, keep_recent=0)
        assert second == first
        assert stats.pruned_messages == 0

    def test_keep_recent_zero_prunes_every_oversized_tool(self):
        messages = _conversation(tool_count=3, size=30) + [_tool(99, size=5)]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=0)
        assert stats.pruned_messages == 3
        assert pruned[6]["content"] == "x" * 5

    def test_keep_recent_larger_than_tool_count_prunes_nothing(self):
        messages = _conversation(tool_count=2, size=100)
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=99)
        assert pruned == messages
        assert stats.pruned_messages == 0

    def test_negative_keep_recent_is_zero(self):
        messages = _conversation(tool_count=2, size=100)
        _, stats = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=-3)
        assert stats.pruned_messages == 2

    def test_max_chars_zero_prunes_non_empty_only(self):
        messages = [_tool(0, size=10), _tool(1, size=0)]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=0, keep_recent=0)
        assert _MARKER_RE.fullmatch(pruned[0]["content"])
        assert pruned[1]["content"] == ""
        assert stats.pruned_messages == 1

    def test_negative_max_chars_behaves_as_zero(self):
        messages = [_tool(0, size=4)]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=-1, keep_recent=0)
        assert _MARKER_RE.fullmatch(pruned[0]["content"])
        assert stats.pruned_messages == 1

    def test_empty_input(self):
        pruned, stats = prune_tool_outputs([])
        assert pruned == []
        assert stats.to_dict() == {
            "tokens_before": 0,
            "tokens_after": 0,
            "pruned_messages": 0,
            "pruned_chars": 0,
            "repo_map_tokens": 0,
        }

    def test_no_tool_messages_is_a_noop(self):
        messages = [
            {"role": "system", "content": "s" * 500},
            {"role": "user", "content": "u" * 500},
            {"role": "assistant", "content": "a" * 500},
        ]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=1, keep_recent=0)
        assert pruned == messages
        assert stats.pruned_messages == 0
        assert stats.tokens_before == stats.tokens_after

    def test_non_string_content_is_skipped(self):
        messages = [
            {"role": "tool", "content": None},
            {"role": "tool", "content": [{"type": "text", "text": "x"}]},
            {"role": "user", "content": "keep"},
        ]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=0, keep_recent=0)
        assert pruned[0]["content"] is None
        assert isinstance(pruned[1]["content"], list)
        assert stats.pruned_messages == 0
        assert stats.tokens_before == estimate_tokens("keep")

    def test_supports_message_objects_without_mutating_them(self):
        messages = [
            SimpleNamespace(role="tool", content="y" * 50),
            SimpleNamespace(role="tool", content="z" * 4),
            SimpleNamespace(role="user", content="hello"),
        ]
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=1)
        assert messages[0].content == "y" * 50
        assert _MARKER_RE.fullmatch(pruned[0].content)
        assert pruned[1].content == "z" * 4
        assert pruned[2].content == "hello"
        assert stats.pruned_messages == 1

    def test_stats_match_token_helper(self):
        messages = _conversation(tool_count=3, size=60)
        pruned, stats = prune_tool_outputs(messages, max_chars_per_result=10, keep_recent=1)
        assert stats.tokens_before == count_message_tokens(messages)
        assert stats.tokens_after == count_message_tokens(pruned)

    def test_count_message_tokens_ignores_non_string_content(self):
        assert count_message_tokens([]) == 0
        assert count_message_tokens([{"role": "tool", "content": None}]) == 0
        assert count_message_tokens([{"role": "user", "content": "abcd"}]) == 1


# ---------------------------------------------------------------------------
# inject_repo_map
# ---------------------------------------------------------------------------


class TestInjectRepoMap:
    def test_appends_map_once(self, repo):
        prompt, tokens = inject_repo_map("You are APEX.", repo, max_tokens=500)

        assert prompt.startswith("You are APEX.")
        assert prompt.count(REPO_MAP_MARKER) == 1
        assert "package/models.py" in prompt
        assert "class Widget" in prompt
        assert tokens > 0

    def test_second_call_is_a_noop(self, repo):
        prompt, tokens = inject_repo_map("system", repo, max_tokens=500)
        again, second_tokens = inject_repo_map(prompt, repo, max_tokens=500)

        assert again == prompt
        assert second_tokens == 0
        assert again.count(REPO_MAP_MARKER) == 1

    def test_existing_marker_is_respected(self, repo):
        original = f"system\n\n{REPO_MAP_MARKER}\n\nold map"
        prompt, tokens = inject_repo_map(original, repo, max_tokens=500)
        assert prompt == original
        assert tokens == 0

    def test_disabled_budget(self, repo):
        prompt, tokens = inject_repo_map("system", repo, max_tokens=0)
        assert prompt == "system"
        assert tokens == 0

    def test_negative_budget(self, repo):
        prompt, tokens = inject_repo_map("system", repo, max_tokens=-10)
        assert prompt == "system"
        assert tokens == 0

    def test_respects_token_budget(self, repo):
        prompt, tokens = inject_repo_map("system", repo, max_tokens=80)
        if tokens:
            assert tokens <= 80
            assert estimate_tokens(prompt.split(REPO_MAP_MARKER, 1)[1].strip()) == tokens

    def test_empty_repository(self, tmp_path):
        prompt, tokens = inject_repo_map("system", tmp_path, max_tokens=500)
        assert prompt == "system"
        assert tokens == 0

    def test_missing_root(self, tmp_path):
        prompt, tokens = inject_repo_map("system", tmp_path / "missing", max_tokens=500)
        assert prompt == "system"
        assert tokens == 0

    def test_empty_prompt_gets_only_the_map(self, repo):
        prompt, tokens = inject_repo_map("", repo, max_tokens=500)
        assert prompt.startswith(REPO_MAP_MARKER)
        assert tokens > 0

    def test_non_string_prompt(self, repo):
        prompt, tokens = inject_repo_map(None, repo, max_tokens=500)  # type: ignore[arg-type]
        assert prompt.startswith(REPO_MAP_MARKER)
        assert tokens > 0


# ---------------------------------------------------------------------------
# Config normalization
# ---------------------------------------------------------------------------


@pytest.fixture
def config_module(monkeypatch, tmp_path):
    """Isolate config_v2 file paths without reloading the process singleton."""
    import apex.config_v2 as module

    paths = {
        "CONFIG_DIR": tmp_path / "config",
        "GLOBAL_JSON": tmp_path / "config" / "apex.json",
        "GLOBAL_JSONC": tmp_path / "config" / "apex.jsonc",
        "TUI_JSON": tmp_path / "config" / "tui.json",
        "OLD_CONFIG": tmp_path / "old-config.json",
    }
    for name, value in paths.items():
        monkeypatch.setattr(module, name, value)
    monkeypatch.delenv("APEX_CONFIG", raising=False)
    monkeypatch.delenv("APEX_CONFIG_CONTENT", raising=False)
    return module


class TestContextConfig:
    def test_normalize_defaults_for_missing(self, config_module):
        assert config_module.normalize_context_config(None) == {
            "max_repo_map_tokens": 2000,
            "prune_tool_outputs": True,
            "tool_output_max_chars": 4000,
            "keep_recent_tool_results": 3,
        }

    def test_normalize_defaults_for_non_dict(self, config_module):
        assert config_module.normalize_context_config("invalid")["max_repo_map_tokens"] == 2000

    def test_normalize_valid_overrides(self, config_module):
        result = config_module.normalize_context_config(
            {
                "max_repo_map_tokens": 500,
                "prune_tool_outputs": False,
                "tool_output_max_chars": 1200,
                "keep_recent_tool_results": 7,
            }
        )
        assert result == {
            "max_repo_map_tokens": 500,
            "prune_tool_outputs": False,
            "tool_output_max_chars": 1200,
            "keep_recent_tool_results": 7,
        }

    def test_normalize_invalid_values_fall_back_individually(self, config_module):
        result = config_module.normalize_context_config(
            {
                "max_repo_map_tokens": "lots",
                "prune_tool_outputs": "yes",
                "tool_output_max_chars": None,
                "keep_recent_tool_results": 1.5,
            }
        )
        assert result["max_repo_map_tokens"] == 2000
        assert result["prune_tool_outputs"] is True
        assert result["tool_output_max_chars"] == 4000
        assert result["keep_recent_tool_results"] == 3

    def test_normalize_rejects_booleans_for_integers(self, config_module):
        result = config_module.normalize_context_config(
            {"max_repo_map_tokens": True, "tool_output_max_chars": False}
        )
        assert result["max_repo_map_tokens"] == 2000
        assert result["tool_output_max_chars"] == 4000

    def test_normalize_clamps_negative_values(self, config_module):
        result = config_module.normalize_context_config(
            {
                "max_repo_map_tokens": -1,
                "tool_output_max_chars": -20,
                "keep_recent_tool_results": -3,
            }
        )
        assert result["max_repo_map_tokens"] == 0
        assert result["tool_output_max_chars"] == 0
        assert result["keep_recent_tool_results"] == 0

    def test_normalize_ignores_unknown_keys_and_returns_copy(self, config_module):
        first = config_module.normalize_context_config({"unknown": 1})
        first["max_repo_map_tokens"] = 0
        second = config_module.normalize_context_config({})
        assert second["max_repo_map_tokens"] == 2000
        assert "unknown" not in second

    def test_apex_config_defaults(self, config_module):
        cfg = config_module.ApexConfig(project_dir=config_module.CONFIG_DIR)
        assert cfg.context == {
            "max_repo_map_tokens": 2000,
            "prune_tool_outputs": True,
            "tool_output_max_chars": 4000,
            "keep_recent_tool_results": 3,
        }

    def test_apex_config_nested_override(self, config_module, monkeypatch):
        monkeypatch.setenv(
            "APEX_CONFIG_CONTENT",
            json.dumps({"context": {"max_repo_map_tokens": 50, "keep_recent_tool_results": 0}}),
        )
        cfg = config_module.ApexConfig(project_dir=config_module.CONFIG_DIR)
        context = cfg.context
        assert context["max_repo_map_tokens"] == 50
        assert context["keep_recent_tool_results"] == 0
        assert context["prune_tool_outputs"] is True
        assert context["tool_output_max_chars"] == 4000

    def test_apex_config_invalid_nested_values_use_defaults(self, config_module, monkeypatch):
        monkeypatch.setenv(
            "APEX_CONFIG_CONTENT",
            json.dumps(
                {
                    "context": {
                        "max_repo_map_tokens": "nope",
                        "prune_tool_outputs": 1,
                        "tool_output_max_chars": -5,
                        "keep_recent_tool_results": None,
                    }
                }
            ),
        )
        cfg = config_module.ApexConfig(project_dir=config_module.CONFIG_DIR)
        assert cfg.context["max_repo_map_tokens"] == 2000
        assert cfg.context["prune_tool_outputs"] is True
        assert cfg.context["tool_output_max_chars"] == 0
        assert cfg.context["keep_recent_tool_results"] == 3

    def test_apex_config_precedence_inline_wins(self, config_module, monkeypatch):
        config_module.GLOBAL_JSON.parent.mkdir(parents=True, exist_ok=True)
        config_module.GLOBAL_JSON.write_text(
            json.dumps({"context": {"max_repo_map_tokens": 111}}), encoding="utf-8"
        )
        monkeypatch.setenv(
            "APEX_CONFIG_CONTENT", json.dumps({"context": {"max_repo_map_tokens": 222}})
        )
        cfg = config_module.ApexConfig(project_dir=config_module.CONFIG_DIR)
        assert cfg.context["max_repo_map_tokens"] == 222

    def test_context_setter_normalizes(self, config_module):
        cfg = config_module.ApexConfig(project_dir=config_module.CONFIG_DIR)
        cfg.context = {"max_repo_map_tokens": -4, "prune_tool_outputs": False}
        assert cfg.context["max_repo_map_tokens"] == 0
        assert cfg.context["prune_tool_outputs"] is False
        assert cfg.context["tool_output_max_chars"] == 4000


# ---------------------------------------------------------------------------
# Agent integration
# ---------------------------------------------------------------------------


def _new_agent(tmp_path):
    from apex.agent import Agent
    from apex.config import Config

    agent = Agent(config=Config(config_path=tmp_path / "agent-config.json"))
    # Avoid Config.save() writing to the real home directory.
    agent._executor.cwd = tmp_path
    agent._async_executor.cwd = tmp_path
    agent._set_agent_system_prompt()
    return agent


def _fake_response(text: str = "done"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))],
        usage=None,
    )


@pytest.fixture
def agent_context(monkeypatch, repo):
    """Give the global config deterministic context settings."""
    from apex.agent import apex_config

    monkeypatch.setitem(
        apex_config._data,
        "context",
        {
            "max_repo_map_tokens": 500,
            "prune_tool_outputs": True,
            "tool_output_max_chars": 20,
            "keep_recent_tool_results": 1,
        },
    )
    return repo


class TestAgentIntegration:
    def test_stats_are_zero_before_any_request(self, agent_context):
        agent = _new_agent(agent_context)
        assert agent.get_context_stats() == {
            "tokens_before": 0,
            "tokens_after": 0,
            "pruned_messages": 0,
            "pruned_chars": 0,
            "repo_map_tokens": 0,
        }

    def test_repo_map_injected_once_across_two_turns(self, agent_context, monkeypatch):
        agent = _new_agent(agent_context)
        calls: list[int] = []
        real_build = context_budget.build_repo_map

        def counting_build(*args, **kwargs):
            calls.append(1)
            return real_build(*args, **kwargs)

        monkeypatch.setattr(context_budget, "build_repo_map", counting_build)
        captured: list[list[dict]] = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return _fake_response("turn done")

        with patch("apex.agent.litellm.completion", side_effect=fake_completion):
            assert agent.chat("first") == "turn done"
            assert agent.chat("second") == "turn done"

        assert len(captured) == 2
        for messages in captured:
            assert messages[0]["role"] == "system"
            assert messages[0]["content"].count(REPO_MAP_MARKER) == 1
            assert "package/models.py" in messages[0]["content"]
        assert len(calls) == 1
        assert agent.last_context_stats.repo_map_tokens > 0
        assert agent.get_context_stats()["repo_map_tokens"] > 0

    def test_tool_outputs_pruned_before_request(self, agent_context):
        agent = _new_agent(agent_context)
        agent.history = [
            _tool(0, size=100),
            _tool(1, size=100),
            _tool(2, size=100),
            _tool(3, size=100),
        ]
        captured: list[list[dict]] = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return _fake_response()

        with patch("apex.agent.litellm.completion", side_effect=fake_completion):
            agent.chat("next")

        messages = captured[0]
        tool_messages = [message for message in messages if message["role"] == "tool"]
        assert len(tool_messages) == 4
        assert [_MARKER_RE.fullmatch(m["content"]) is not None for m in tool_messages[:3]] == [
            True,
            True,
            True,
        ]
        assert tool_messages[3]["content"] == "x" * 100
        assert agent.last_context_stats.pruned_messages == 3
        assert agent.last_context_stats.pruned_chars > 0
        assert agent.last_context_stats.tokens_after < agent.last_context_stats.tokens_before

    def test_pruning_can_be_disabled(self, agent_context, monkeypatch):
        from apex.agent import apex_config

        monkeypatch.setitem(
            apex_config._data,
            "context",
            {
                "max_repo_map_tokens": 0,
                "prune_tool_outputs": False,
                "tool_output_max_chars": 1,
                "keep_recent_tool_results": 0,
            },
        )
        agent = _new_agent(agent_context)
        agent.history = [_tool(0, size=100)]
        captured: list[list[dict]] = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return _fake_response()

        with patch("apex.agent.litellm.completion", side_effect=fake_completion):
            agent.chat("next")

        tool_messages = [m for m in captured[0] if m["role"] == "tool"]
        assert tool_messages[0]["content"] == "x" * 100
        assert agent.last_context_stats.pruned_messages == 0
        assert agent.last_context_stats.tokens_before == agent.last_context_stats.tokens_after
        assert REPO_MAP_MARKER not in captured[0][0]["content"]

    def test_repo_map_is_reused_after_agent_switch(self, agent_context, monkeypatch):
        agent = _new_agent(agent_context)
        calls: list[int] = []
        real_build = context_budget.build_repo_map

        def counting_build(*args, **kwargs):
            calls.append(1)
            return real_build(*args, **kwargs)

        monkeypatch.setattr(context_budget, "build_repo_map", counting_build)

        with patch("apex.agent.litellm.completion", return_value=_fake_response()):
            agent.chat("first")
            agent.switch_agent("planner")
            agent.chat("second")

        assert len(calls) == 1
        assert agent._system_message["content"].count(REPO_MAP_MARKER) == 1
