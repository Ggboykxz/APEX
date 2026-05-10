"""Theme manager - Like OpenCode's theme system."""

import json
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Theme:
    name: str
    type: str
    colors: Dict[str, str]


APEX_THEME: Dict[str, str] = {
    "name": "apex-dark",
    "type": "dark",
    "bg": "#0d1117",
    "fg": "#c9d1d9",
    "accent": "#58a6ff",
    "error": "#f85149",
    "warning": "#d29922",
    "success": "#3fb950",
    "border": "#30363d",
    "selection": "#264f78",
    "cursor": "#58a6ff",
    "lineNumbers": "#6e7681",
    "comment": "#8b949e",
    "keyword": "#ff7b72",
    "string": "#a5d6ff",
    "function": "#d2a8ff",
    "variable": "#79c0ff",
    "constant": "#ffa657",
    "type": "#7ee787",
}


class ThemeManager:
    """Theme manager - like OpenCode's ThemeManager."""

    BUILT_IN_THEMES = {
        "opencode": {
            "name": "opencode",
            "type": "dark",
            "bg": "#0d1117",
            "fg": "#c9d1d9",
            "accent": "#58a6ff",
            "error": "#f85149",
            "warning": "#d29922",
            "success": "#3fb950",
            "border": "#30363d",
            "selection": "#264f78",
            "cursor": "#58a6ff",
            "lineNumbers": "#6e7681",
            "comment": "#8b949e",
            "keyword": "#ff7b72",
            "string": "#a5d6ff",
            "function": "#d2a8ff",
            "variable": "#79c0ff",
            "constant": "#ffa657",
            "type": "#7ee787",
        },
        "dracula": {
            "name": "dracula",
            "type": "dark",
            "bg": "#282a36",
            "fg": "#f8f8f2",
            "accent": "#bd93f9",
            "error": "#ff5555",
            "warning": "#ffb86c",
            "success": "#50fa7b",
            "border": "#44475a",
            "selection": "#44475a",
            "cursor": "#f8f8f2",
            "lineNumbers": "#6272a4",
            "comment": "#6272a4",
            "keyword": "#ff79c6",
            "string": "#f1fa8c",
            "function": "#50fa7b",
            "variable": "#f8f8f2",
            "constant": "#ffb86c",
            "type": "#8be9fd",
        },
        "nord": {
            "name": "nord",
            "type": "dark",
            "bg": "#2e3440",
            "fg": "#eceff4",
            "accent": "#88c0d0",
            "error": "#bf616a",
            "warning": "#ebcb8b",
            "success": "#a3be8c",
            "border": "#4c566a",
            "selection": "#434c5e",
            "cursor": "#d8dee9",
            "lineNumbers": "#4c566a",
            "comment": "#616e88",
            "keyword": "#81a1c1",
            "string": "#a3be8c",
            "function": "#88c0d0",
            "variable": "#d8dee9",
            "constant": "#d08770",
            "type": "#8fbcbb",
        },
        "tokyonight": {
            "name": "tokyonight",
            "type": "dark",
            "bg": "#1a1b26",
            "fg": "#c0caf5",
            "accent": "#7aa2f7",
            "error": "#f7768e",
            "warning": "#e0af68",
            "success": "#9ece6a",
            "border": "#3b4261",
            "selection": "#283457",
            "cursor": "#c0caf5",
            "lineNumbers": "#565f89",
            "comment": "#565f89",
            "keyword": "#bb9af7",
            "string": "#9ece6a",
            "function": "#7aa2f7",
            "variable": "#7dcfff",
            "constant": "#ff9e64",
            "type": "#2ac3de",
        },
        "gruvbox": {
            "name": "gruvbox",
            "type": "dark",
            "bg": "#282828",
            "fg": "#ebdbb2",
            "accent": "#83a598",
            "error": "#fb4934",
            "warning": "#fabd2f",
            "success": "#b8bb26",
            "border": "#3c3836",
            "selection": "#504945",
            "cursor": "#ebdbb2",
            "lineNumbers": "#665c54",
            "comment": "#928374",
            "keyword": "#fb4934",
            "string": "#b8bb26",
            "function": "#83a598",
            "variable": "#fabd2f",
            "constant": "#fe8019",
            "type": "#8ec07c",
        },
        "github": {
            "name": "github",
            "type": "dark",
            "bg": "#0d1117",
            "fg": "#c9d1d9",
            "accent": "#58a6ff",
            "error": "#f85149",
            "warning": "#d29922",
            "success": "#3fb950",
            "border": "#30363d",
            "selection": "#388bfd26",
            "cursor": "#c9d1d9",
            "lineNumbers": "#6e7681",
            "comment": "#8b949e",
            "keyword": "#ff7b72",
            "string": "#a5d6ff",
            "function": "#d2a8ff",
            "variable": "#79c0ff",
            "constant": "#ffa657",
            "type": "#7ee787",
        },
    }

    def __init__(self, themes_dir: Optional[Path] = None):
        self.themes_dir = themes_dir or Path(__file__).parent
        self._themes: Dict[str, Dict] = dict(self.BUILT_IN_THEMES)
        self._load_json_themes()

    def _load_json_themes(self) -> None:
        if self.themes_dir.exists():
            for json_file in self.themes_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        theme_data = json.load(f)
                        name = theme_data.get("name", json_file.stem)
                        self._themes[name] = theme_data
                except Exception:
                    pass

    def get_theme(self, name: str) -> Dict:
        return self._themes.get(name, self.BUILT_IN_THEMES.get("opencode", {}))

    def list_themes(self) -> list[str]:
        return list(self._themes.keys())

    def add_theme(self, name: str, theme_data: Dict) -> None:
        self._themes[name] = theme_data

    def remove_theme(self, name: str) -> None:
        self._themes.pop(name, None)