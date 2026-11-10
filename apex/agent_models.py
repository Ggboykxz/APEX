"""Model and agent selection for the APEX agent.

Split out of ``apex.agent`` so that module keeps a single responsibility: the
chat loop itself. The mixin expects its host class to expose ``config``,
``model`` and ``_current_agent``.
"""

from __future__ import annotations

from typing import Any

from .agents import agent_manager
from .config import MODELS

__all__ = ["ModelSelectionMixin"]


class ModelSelectionMixin:
    """Pick the model and the agent a turn runs with."""

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
        """Pick the model alias that best fits the request.

        The keyword heuristic only suggests aliases the registry knows; the
        agent's own model is the fallback when it does not.
        """
        text = user_input.lower()
        if "explain" in text or "debug" in text:
            alias = "claude-sonnet-4"
        elif "refactor" in text or "create" in text:
            alias = "gpt-4o"
        elif "reason" in text:
            alias = "deepseek-reasoner"
        elif len(text) > 2000:
            alias = "claude-sonnet-4"
        else:
            alias = "gpt-4o-mini"
        return alias if alias in MODELS else self.model

    def _resolve_model_alias(self) -> str:
        """Resolve the model alias to use: per-agent override, else global."""
        agent_config = agent_manager.get(self._current_agent)
        if agent_config is not None and getattr(agent_config, "model", None):
            return agent_config.model
        return self.model

    def _completion_kwargs(self) -> dict[str, Any]:
        """Extra kwargs (temperature, top_p, reasoning_effort) for litellm calls."""
        kwargs: dict[str, Any] = {}
        agent_config = agent_manager.get(self._current_agent)
        if agent_config is not None:
            if getattr(agent_config, "temperature", 0.0):
                kwargs["temperature"] = agent_config.temperature
            if getattr(agent_config, "top_p", None) is not None:
                kwargs["top_p"] = agent_config.top_p
        effort = getattr(self.config, "reasoning_effort", "off")
        if effort and effort != "off":
            kwargs["reasoning_effort"] = effort
        return kwargs
