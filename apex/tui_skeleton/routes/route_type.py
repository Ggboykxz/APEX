"""Route type enum."""

from enum import Enum


class RouteType(Enum):
    """Route types - like OpenCode's route types."""
    HOME = "home"
    SESSION = "session"
    PLUGIN = "plugin"
    SETTINGS = "settings"
    HELP = "help"