"""Plugin system for APEX (future feature)."""

from typing import Any


class Plugin:
    name: str = ""
    version: str = "0.0.0"

    def initialize(self) -> None:
        pass

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


def load_plugins() -> list[Plugin]:
    """Load all installed plugins."""
    return []