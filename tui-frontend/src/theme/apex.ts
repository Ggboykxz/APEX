/**
 * Theme registry.
 *
 * `apexTheme` is a live object: components read its fields at render time, so
 * `setTheme()` mutates it in place and the next Ink render picks the new
 * palette up without threading a context through every component.
 */

export interface ApexTheme {
  bg: string
  fg: string
  cyan: string
  green: string
  red: string
  yellow: string
  purple: string
  gray: string
  dimGray: string
  border: string
  accent: string
  titleBg: string
  inputBg: string
  error: string
  success: string
  warning: string
}

export const THEMES: Record<string, ApexTheme> = {
  default: {
    bg: "#0d1117",
    fg: "#e6edf3",
    cyan: "#00e5ff",
    green: "#00ff88",
    red: "#ff6b6b",
    yellow: "#ffd93d",
    purple: "#c084fc",
    gray: "#484f58",
    dimGray: "#30363d",
    border: "#30363d",
    accent: "#00e5ff",
    titleBg: "#161b22",
    inputBg: "#0d1117",
    error: "#ff6b6b",
    success: "#00ff88",
    warning: "#ffd93d",
  },
  light: {
    bg: "#f6f8fa",
    fg: "#1f2328",
    cyan: "#0550ae",
    green: "#1a7f37",
    red: "#cf222e",
    yellow: "#9a6700",
    purple: "#8250df",
    gray: "#8b949e",
    dimGray: "#d0d7de",
    border: "#d0d7de",
    accent: "#0550ae",
    titleBg: "#eaeef2",
    inputBg: "#ffffff",
    error: "#cf222e",
    success: "#1a7f37",
    warning: "#9a6700",
  },
  dark: {
    bg: "#000000",
    fg: "#d0d0d0",
    cyan: "#4fc3f7",
    green: "#66bb6a",
    red: "#ef5350",
    yellow: "#ffee58",
    purple: "#ba68c8",
    gray: "#616161",
    dimGray: "#212121",
    border: "#212121",
    accent: "#4fc3f7",
    titleBg: "#111111",
    inputBg: "#000000",
    error: "#ef5350",
    success: "#66bb6a",
    warning: "#ffee58",
  },
  forest: {
    bg: "#0f1a12",
    fg: "#d8e8dc",
    cyan: "#1b5e3f",
    green: "#4caf50",
    red: "#e57373",
    yellow: "#e8913a",
    purple: "#8d6e63",
    gray: "#3f5747",
    dimGray: "#1d2f24",
    border: "#1d2f24",
    accent: "#4caf50",
    titleBg: "#16281c",
    inputBg: "#0f1a12",
    error: "#e57373",
    success: "#4caf50",
    warning: "#e8913a",
  },
  sunset: {
    bg: "#1a0f1e",
    fg: "#f3e6ed",
    cyan: "#ff8a65",
    green: "#aed581",
    red: "#ff5252",
    yellow: "#ffb74d",
    purple: "#ce93d8",
    gray: "#6d5566",
    dimGray: "#2b1a30",
    border: "#2b1a30",
    accent: "#ff8a65",
    titleBg: "#241528",
    inputBg: "#1a0f1e",
    error: "#ff5252",
    success: "#aed581",
    warning: "#ffb74d",
  },
}

let currentThemeId = "default"

/** Live palette object used by every component. */
export const apexTheme: ApexTheme = { ...THEMES.default }

export function listThemes(): { id: string; name: string }[] {
  return Object.keys(THEMES).map((id) => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1),
  }))
}

export function getThemeId(): string {
  return currentThemeId
}

export function hasTheme(id: string): boolean {
  return id in THEMES
}

/** Switch the active palette. Returns false for unknown ids. */
export function setTheme(id: string): boolean {
  const next = THEMES[id]
  if (!next) return false
  Object.assign(apexTheme, next)
  currentThemeId = id
  return true
}
