"use strict";

/**
 * Key parsing — turns Ink key objects and key strings into canonical `KeyMatch`
 * strings. A stroke is `[mods]+name` with mods sorted (ctrl, shift, meta).
 * Multi-stroke bindings are space-separated (`"ctrl+x n"`).
 */

import type { KeyLike, KeyMatch, Stroke } from "./types.js"

const MODIFIERS = ["ctrl", "shift", "meta"] as const

export function strokeToMatch(s: Stroke): KeyMatch {
  const mods = MODIFIERS.filter((m) => s[m])
  return mods.length > 0 ? `${mods.join("+")}+${s.name}` : s.name
}

/** Normalize one stroke part (lowercase) into a canonical KeyMatch. */
function normalizePart(part: string): KeyMatch {
  const bits = part.trim().toLowerCase().split("+")
  const name = bits[bits.length - 1] ?? ""
  const mods = bits.slice(0, -1)
  return strokeToMatch({
    name,
    ctrl: mods.includes("ctrl"),
    shift: mods.includes("shift"),
    meta: mods.includes("meta"),
  })
}

/** Parse a binding key (string or object) into an array of KeyMatch strokes. */
export function parseKey(key: KeyLike): KeyMatch[] {
  if (typeof key === "object") {
    return [strokeToMatch({ name: key.name ?? "", ctrl: !!key.ctrl, shift: !!key.shift, meta: !!key.meta })]
  }
  return key
    .split(/\s+/)
    .filter(Boolean)
    .map(normalizePart)
}

/**
 * Convert Ink's `useInput(input, key)` arguments into a Stroke. Reuses Ink's
 * named booleans; falls back to the raw character for printable input.
 */
export function fromInkKey(input: string, key: InkKeyLike): Stroke {
  const map: Array<[keyof InkKeyLike, string]> = [
    ["return", "return"],
    ["escape", "escape"],
    ["tab", "tab"],
    ["backspace", "backspace"],
    ["delete", "delete"],
    ["upArrow", "up"],
    ["downArrow", "down"],
    ["leftArrow", "left"],
    ["rightArrow", "right"],
    ["pageUp", "pageup"],
    ["pageDown", "pagedown"],
  ]
  for (const [prop, name] of map) {
    if (key[prop]) return { name, ctrl: !!key.ctrl, shift: !!key.shift, meta: !!key.meta }
  }
  return { name: input.toLowerCase(), ctrl: !!key.ctrl, shift: !!key.shift, meta: !!key.meta }
}

/** Subset of Ink's key object we read. */
export interface InkKeyLike {
  ctrl?: boolean
  shift?: boolean
  meta?: boolean
  return?: boolean
  escape?: boolean
  tab?: boolean
  backspace?: boolean
  delete?: boolean
  upArrow?: boolean
  downArrow?: boolean
  leftArrow?: boolean
  rightArrow?: boolean
  pageUp?: boolean
  pageDown?: boolean
}
