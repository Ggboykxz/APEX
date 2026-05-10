"""Theme context - Like OpenCode's ThemeProvider."""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable

_THEME_DIR = Path(__file__).parent.parent / "themes"


@dataclass
class Theme:
    name: str
    background: str
    foreground: str
    comment: str
    string: str
    keyword: str
    function: str
    variable: str
    number: str
    operator: str
    selection_bg: str
    selection_fg: str
    border: str
    accent: str
    error: str
    warning: str
    info: str
    link: str


class ThemeManager:
    """Theme manager - loads JSON themes like OpenCode."""

    def __init__(self):
        self._themes: dict[str, Theme] = {}
        self._load_builtin_themes()

    def _load_builtin_themes(self) -> None:
        builtin_themes = {
            "opencode": {
                "name": "OpenCode Dark",
                "background": "#0d1117",
                "foreground": "#e6edf3",
                "comment": "#8b949e",
                "string": "#a5d6ff",
                "keyword": "#ff7b72",
                "function": "#d2a8ff",
                "variable": "#ffa657",
                "number": "#79c0ff",
                "operator": "#ff7b72",
                "selection_bg": "#264f78",
                "selection_fg": "#ffffff",
                "border": "#30363d",
                "accent": "#58a6ff",
                "error": "#f85149",
                "warning": "#d29922",
                "info": "#58a6ff",
                "link": "#58a6ff",
            },
            "dracula": {
                "name": "Dracula",
                "background": "#282a36",
                "foreground": "#f8f8f2",
                "comment": "#6272a4",
                "string": "#f1fa8c",
                "keyword": "#ff79c6",
                "function": "#50fa7b",
                "variable": "#bd93f9",
                "number": "#bd93f9",
                "operator": "#ff79c6",
                "selection_bg": "#44475a",
                "selection_fg": "#f8f8f2",
                "border": "#6272a4",
                "accent": "#bd93f9",
                "error": "#ff5555",
                "warning": "#ffb86c",
                "info": "#8be9fd",
                "link": "#8be9fd",
            },
            "nord": {
                "name": "Nord",
                "background": "#2e3440",
                "foreground": "#d8dee9",
                "comment": "#616e87",
                "string": "#a3be8c",
                "keyword": "#81a1c1",
                "function": "#88c0d0",
                "variable": "#d8dee9",
                "number": "#b48ead",
                "operator": "#81a1c1",
                "selection_bg": "#434c5e",
                "selection_fg": "#d8dee9",
                "border": "#4c566a",
                "accent": "#88c0d0",
                "error": "#bf616a",
                "warning": "#ebcb8b",
                "info": "#88c0d0",
                "link": "#8be9fd",
            },
            "tokyonight": {
                "name": "Tokyo Night",
                "background": "#1a1b26",
                "foreground": "#c0caf5",
                "comment": "#565f89",
                "string": "#9ece6a",
                "keyword": "#bb9af7",
                "function": "#7aa2f7",
                "variable": "#c0caf5",
                "number": "#ff9e64",
                "operator": "#bb9af7",
                "selection_bg": "#283457",
                "selection_fg": "#c0caf5",
                "border": "#414868",
                "accent": "#7aa2f7",
                "error": "#f7768e",
                "warning": "#e0af68",
                "info": "#7aa2f7",
                "link": "#7aa2f7",
            },
            "gruvbox": {
                "name": "Gruvbox Dark",
                "background": "#282828",
                "foreground": "#ebdbb2",
                "comment": "#928374",
                "string": "#98971a",
                "keyword": "#fb4934",
                "function": "#fabd2f",
                "variable": "#ebdbb2",
                "number": "#d79921",
                "operator": "#fb4934",
                "selection_bg": "#504945",
                "selection_fg": "#ebdbb2",
                "border": "#504945",
                "accent": "#fabd2f",
                "error": "#fb4934",
                "warning": "#fabd2f",
                "info": "#fabd2f",
                "link": "#83a598",
            },
            "github": {
                "name": "GitHub Dark",
                "background": "#0d1117",
                "foreground": "#c9d1d9",
                "comment": "#8b949e",
                "string": "#a5d6ff",
                "keyword": "#ff7b72",
                "function": "#d2a8ff",
                "variable": "#ffa657",
                "number": "#79c0ff",
                "operator": "#ff7b72",
                "selection_bg": "#264f78",
                "selection_fg": "#ffffff",
                "border": "#30363d",
                "accent": "#58a6ff",
                "error": "#f85149",
                "warning": "#d29922",
                "info": "#58a6ff",
                "link": "#58a6ff",
            },
        }

        for name, data in builtin_themes.items():
            self._themes[name] = Theme(name=name, **data)

    def load_theme(self, name: str) -> Optional[Theme]:
        if name in self._themes:
            return self._themes[name]

        theme_file = _THEME_DIR / f"{name}.json"
        if theme_file.exists():
            with open(theme_file) as f:
                data = json.load(f)
            theme = Theme(name=name, **data)
            self._themes[name] = theme
            return theme

        return self._themes.get("opencode")

    def list_themes(self) -> list[str]:
        return list(self._themes.keys())


class ThemeProvider:
    """Theme context provider - like OpenCode's ThemeProvider."""

    def __init__(self, theme_manager: Optional[ThemeManager] = None):
        self.theme_manager = theme_manager or ThemeManager()
        self._current_theme_name = "opencode"
        self._mode = "dark"
        self._listeners: list[Callable] = []

    @property
    def theme(self) -> Theme:
        return self.theme_manager.load_theme(self._current_theme_name) or self.theme_manager.load_theme("opencode")

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._mode = value
        self._notify()

    def set_theme(self, name: str) -> None:
        if self.theme_manager.load_theme(name):
            self._current_theme_name = name
            self._notify()

    def get_color(self, key: str) -> str:
        return getattr(self.theme, key, "#000000")

    def on_change(self, listener: Callable) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener(self.theme, self._mode)


def get_default_theme() -> Theme:
    """Get the default APEX theme."""
    manager = ThemeManager()
    return manager.load_theme("opencode")