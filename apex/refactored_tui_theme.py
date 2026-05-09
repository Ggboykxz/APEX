"""
Refactored TUI Theme - Testable theme system.

Themes are defined as data dictionaries, making them easy to test
and modify without UI code.
"""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """Color palette for a theme."""

    bg: str
    elevated: str
    surface: str
    accent: str
    success: str
    error: str
    warning: str
    text: str
    muted: str
    border: str


@dataclass
class Theme:
    """Complete theme configuration."""

    name: str
    colors: ThemeColors
    display_name: str
    icon: str = "●"


THEMES: dict[str, Theme] = {
    "apex-dark": Theme(
        name="apex-dark",
        display_name="APEX Dark",
        icon="●",
        colors=ThemeColors(
            bg="#0d1117",
            elevated="#161b22",
            surface="#21262d",
            accent="#00e5ff",
            success="#00ff88",
            error="#ff4444",
            warning="#ffaa00",
            text="#e6edf3",
            muted="#7d8590",
            border="#30363d",
        ),
    ),
    "gabon": Theme(
        name="gabon",
        display_name="GABON",
        icon="🇬🇦",
        colors=ThemeColors(
            bg="#0a0f0a",
            elevated="#0d1a0d",
            surface="#142414",
            accent="#009e60",
            success="#fcd116",
            error="#ff6b6b",
            warning="#fcd116",
            text="#e6ffe6",
            muted="#7d997d",
            border="#1a3d1a",
        ),
    ),
    "synthwave": Theme(
        name="synthwave",
        display_name="Synthwave",
        icon="🌌",
        colors=ThemeColors(
            bg="#1a1a2e",
            elevated="#16213e",
            surface="#0f3460",
            accent="#e94560",
            success="#ff2e63",
            error="#ff6b6b",
            warning="#ffd700",
            text="#eaeaea",
            muted="#a0a0a0",
            border="#533483",
        ),
    ),
    "solarized": Theme(
        name="solarized",
        display_name="Solarized",
        icon="☀",
        colors=ThemeColors(
            bg="#002b36",
            elevated="#073642",
            surface="#094150",
            accent="#268bd2",
            success="#859900",
            error="#dc322f",
            warning="#b58900",
            text="#839496",
            muted="#586e75",
            border="#657b83",
        ),
    ),
}


class ThemeService:
    """Theme management - testable without UI."""

    def __init__(self) -> None:
        self._current = "apex-dark"
        self._theme_list = list(THEMES.keys())

    @property
    def current(self) -> Theme:
        return THEMES[self._current]

    def set(self, theme_name: str) -> bool:
        if theme_name in THEMES:
            self._current = theme_name
            return True
        return False

    def cycle(self) -> Theme:
        current_idx = self._theme_list.index(self._current)
        next_idx = (current_idx + 1) % len(self._theme_list)
        self._current = self._theme_list[next_idx]
        return self.current

    def get_all(self) -> list[Theme]:
        return list(THEMES.values())

    def get_names(self) -> list[str]:
        return self._theme_list.copy()


def get_css_variables(theme: Theme) -> dict[str, str]:
    """Generate CSS variables from theme - for Textual CSS."""
    return {
        "$apex-bg": theme.colors.bg,
        "$apex-elevated": theme.colors.elevated,
        "$apex-surface": theme.colors.surface,
        "$apex-accent": theme.colors.accent,
        "$apex-success": theme.colors.success,
        "$apex-error": theme.colors.error,
        "$apex-warning": theme.colors.warning,
        "$apex-text": theme.colors.text,
        "$apex-muted": theme.colors.muted,
        "$apex-border": theme.colors.border,
    }


def generate_css(theme: Theme) -> str:
    """Generate CSS from theme - for dynamic theming."""
    vars = get_css_variables(theme)
    lines = [f"{k}: {v};" for k, v in vars.items()]
    return "\n".join(lines)