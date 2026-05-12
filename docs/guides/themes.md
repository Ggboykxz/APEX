# Themes

APEX comes with **12 built-in themes** with dark/light mode support. You can also create custom themes.

## Built-in Themes

| Theme | Description |
|-------|-------------|
| `apex` | Default dark cyan theme |
| `nord` | Based on the Nord palette |
| `catppuccin` | Catppuccin Mocha |
| `catppuccin-macchiato` | Catppuccin Macchiato |
| `tokyonight` | Based on TokyoNight |
| `gruvbox` | Gruvbox dark |
| `everforest` | Everforest |
| `kanagawa` | Kanagawa wave |
| `ayu` | Ayu dark |
| `one-dark` | Atom One Dark |
| `matrix` | Hacker green-on-black |
| `system` | Adapts to terminal colors |

## Switching Themes

### Via TUI
```
Ctrl+X + T    # Open theme selector
```

### Via Config
```json
// ~/.config/apex/tui.json
{
  "theme": "nord"
}
```

## Custom Themes

Create JSON files in:
- Global: `~/.config/apex/themes/*.json`
- Project: `.apex/themes/*.json`

### Theme Format

```json
{
  "defs": {
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord8": "#88C0D0"
  },
  "theme": {
    "primary": { "dark": "nord8", "light": "#5E81AC" },
    "secondary": { "dark": "#81A1C1", "light": "#81A1C1" },
    "accent": { "dark": "#8FBCBB", "light": "#8FBCBB" },
    "error": { "dark": "#BF616A", "light": "#BF616A" },
    "warning": { "dark": "#D08770", "light": "#D08770" },
    "success": { "dark": "#A3BE8C", "light": "#A3BE8C" },
    "info": { "dark": "#88C0D0", "light": "#5E81AC" },
    "text": { "dark": "#D8DEE9", "light": "#2E3440" },
    "textMuted": { "dark": "#4C566A", "light": "#3B4252" },
    "background": { "dark": "#2E3440", "light": "#ECEFF4" },
    "backgroundPanel": { "dark": "#3B4252", "light": "#E5E9F0" },
    "backgroundElement": { "dark": "#3B4252", "light": "#D8DEE9" },
    "border": { "dark": "#434C5E", "light": "#4C566A" },
    "borderActive": { "dark": "#4C566A", "light": "#3B4252" },
    "diffAdded": { "dark": "#A3BE8C", "light": "#A3BE8C" },
    "diffRemoved": { "dark": "#BF616A", "light": "#BF616A" },
    "markdownCode": { "dark": "#A3BE8C", "light": "#A3BE8C" },
    "syntaxKeyword": { "dark": "#81A1C1", "light": "#81A1C1" },
    "syntaxString": { "dark": "#A3BE8C", "light": "#A3BE8C" }
  }
}
```

### Color Values

Colors can be:
- **Hex**: `"#88C0D0"`
- **Reference**: `"nord8"` (from `defs`)
- **ANSI**: `3` (0-255)
- **None**: `"none"` (terminal default)
- **Dark/light object**: `{"dark": "#000", "light": "#fff"}`
