"use strict";

/**
 * Key formatting — turns canonical `KeyMatch` strings (e.g. "ctrl+p",
 * "shift+tab", "ctrl+x n") into compact terminal-friendly glyphs for help and
 * hints: `^P`, `⇧Tab`, `^X N`.
 */

const MOD_GLYPHS: Record<string, string> = {
  ctrl: "^",
  shift: "⇧",
  meta: "⌘",
  alt: "⌥",
}

const NAME_GLYPHS: Record<string, string> = {
  return: "Enter",
  tab: "Tab",
  escape: "Esc",
  backspace: "⌫",
  delete: "Del",
  up: "↑",
  down: "↓",
  left: "←",
  right: "→",
  pageup: "PgUp",
  pagedown: "PgDn",
  home: "Home",
  end: "End",
  space: "Space",
}

function formatStroke(part: string): string {
  const bits = part.split("+").filter(Boolean)
  const name = bits[bits.length - 1] ?? ""
  const mods = bits.slice(0, -1)
  const modGlyphs = mods.map((m) => MOD_GLYPHS[m] ?? `${m}+`).join("")
  const nameGlyph = NAME_GLYPHS[name] ?? (/^[a-z]$/.test(name) ? name.toUpperCase() : name)
  return `${modGlyphs}${nameGlyph}`
}

/** Format a KeyMatch (possibly multi-stroke, space-separated). */
export function formatKey(key: string): string {
  return key
    .split(/\s+/)
    .filter(Boolean)
    .map(formatStroke)
    .join(" ")
}
