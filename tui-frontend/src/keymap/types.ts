"use strict";

/**
 * Keymap core types — a faithful, minimal port of OpenTUI's `@opentui/keymap`
 * model.
 *
 * The model: an app registers named commands and key bindings in layers. A
 * layer is global or targeted at a focus context. On each key event the engine
 * resolves the matching command from the active layers, honoring priority,
 * reject (`false`) and fallthrough. Multi-stroke bindings (leader keys) become
 * pending sequences.
 */

/** One normalized key stroke (mirrors Ink's useInput key object). */
export interface Stroke {
  name: string
  ctrl: boolean
  shift: boolean
  meta: boolean
}

/** A binding key: `"ctrl+p"`, `"ctrl+x n"` (multi-stroke), or an object. */
export type KeyLike = string | Partial<Stroke>

/** Canonical string identity of a stroke (e.g. `"ctrl+p"`, `"return"`). */
export type KeyMatch = string

/** Runtime context handed to every command. */
export interface CommandCtx {
  state: unknown
  input: string
  [extra: string]: unknown
}

/**
 * Command result. `true`/void = handled. `false` = reject → the engine tries
 * the next matching binding/layer (OpenTUI's reject semantics).
 */
export type CommandResult = boolean | void

export interface KeymapCommand {
  name: string
  run(ctx: CommandCtx): CommandResult
  /** Optional gate; when it returns false the binding is skipped. */
  enabled?: (ctx: CommandCtx) => boolean
  desc?: string
  category?: string
}

export interface KeyBinding {
  key: KeyLike
  cmd: string
  /**
   * Default `true`: after a handle the key is consumed. `false` lets the key
   * keep flowing to later host listeners (not used in a pure engine).
   */
  preventDefault?: boolean
  /** Default `false`: continue to later matching bindings after handling. */
  fallthrough?: boolean
}

export interface KeymapLayer {
  id: string
  /** Omit for a global layer; set to a focus context id otherwise. */
  target?: string
  /** Higher runs first; newer layers win ties. */
  priority?: number
  /**
   * When true, an active layer consumes every unhandled key (modal behavior:
   * an open overlay/diff swallows all input). Default false.
   */
  swallowAll?: boolean
  commands: KeymapCommand[]
  bindings: KeyBinding[]
}

export type ResolveReason =
  | "executed"
  | "rejected"
  | "no-match"
  | "sequence-start"
  | "sequence-advance"
  | "sequence-executed"
  | "sequence-miss"

export interface ResolveResult {
  handled: boolean
  reason: ResolveReason
  cmd?: string
  pending: boolean
}

export interface ActiveKeyInfo {
  key: string
  cmd: string
  layer: string
  enabled: boolean
}

/** A binding as listed for help/UI (multi-stroke keys joined by spaces). */
export interface ListedKey {
  key: string
  cmd: string
  layer: string
}
