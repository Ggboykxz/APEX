"use strict";

/**
 * Keymap — the engine ported from OpenTUI's `@opentui/keymap` core.
 *
 * Services collapsed into one class (they are coordination, not reuse points):
 *  - command catalog: named commands registered per layer, resolved by dispatch
 *  - layer service: register/unregister, priority sorting (higher first, newer
 *    wins ties), and active-layer filtering by focus context
 *  - activation: pending multi-stroke sequences (leader keys)
 *  - dispatch: resolve a key stroke → the winning binding/command
 *  - runtime: a small key→value data store (`setData`/`getData`)
 *
 * The engine is pure: no React, no timers, fully unit-testable. Commands read
 * the live context via `getCtx()` (a function so callers can pass fresh state).
 */

import { parseKey, strokeToMatch } from "./parser.js"
import type {
  ActiveKeyInfo,
  CommandCtx,
  KeymapCommand,
  KeymapLayer,
  KeyMatch,
  ListedKey,
  ResolveResult,
  Stroke,
} from "./types.js"

interface CompiledBinding {
  parts: KeyMatch[]
  cmd: string
  preventDefault: boolean
  fallthrough: boolean
}

interface RegisteredLayer {
  id: string
  target?: string
  priority: number
  order: number
  swallowAll: boolean
  commands: Map<string, KeymapCommand>
  bindings: CompiledBinding[]
}

interface PendingCapture {
  layer: RegisteredLayer
  binding: CompiledBinding
  partIndex: number
}

const NO_MATCH: ResolveResult = { handled: false, reason: "no-match", pending: false }

export class Keymap {
  private layers: RegisteredLayer[] = []
  private nextOrder = 0
  private pending: PendingCapture[] = []
  private data = new Map<string, unknown>()
  private pendingListeners = new Set<() => void>()
  private ctx: () => CommandCtx

  constructor(getCtx: () => CommandCtx) {
    this.ctx = getCtx
  }

  // ── layer service ─────────────────────────────────────────────────────

  /** Register a layer; returns a disposer. */
  register(layer: KeymapLayer): () => void {
    const registered: RegisteredLayer = {
      id: layer.id,
      target: layer.target,
      priority: layer.priority ?? 0,
      order: this.nextOrder++,
      swallowAll: layer.swallowAll ?? false,
      commands: new Map(layer.commands.map((c) => [c.name, c])),
      bindings: layer.bindings.map((b) => ({
        parts: parseKey(b.key),
        cmd: b.cmd,
        preventDefault: b.preventDefault ?? true,
        fallthrough: b.fallthrough ?? false,
      })),
    }
    this.layers.push(registered)
    this.sortLayers()
    return () => this.unregister(registered)
  }

  private unregister(layer: RegisteredLayer): void {
    this.layers = this.layers.filter((l) => l !== layer)
    if (this.pending.some((p) => p.layer === layer)) this.clearPending()
  }

  /** Sort by priority desc, then registration order desc (newer wins ties). */
  private sortLayers(): void {
    this.layers.sort((a, b) => b.priority - a.priority || b.order - a.order)
  }

  /** Layers whose target is global or matches the focus context. */
  private activeLayers(targets: readonly string[]): RegisteredLayer[] {
    return this.layers.filter((l) => !l.target || targets.includes(l.target))
  }

  // ── runtime data ──────────────────────────────────────────────────────

  setData(name: string, value: unknown): void {
    if (value === undefined) this.data.delete(name)
    else this.data.set(name, value)
  }

  getData(name: string): unknown {
    return this.data.get(name)
  }

  // ── pending sequence (leader keys) ────────────────────────────────────

  hasPending(): boolean {
    return this.pending.length > 0
  }

  getPendingStrokes(): KeyMatch[] {
    if (this.pending.length === 0) return []
    return this.pending[0]!.binding.parts.slice(0, this.pending[0]!.partIndex + 1)
  }

  clearPending(): void {
    if (this.pending.length === 0) return
    this.pending = []
    this.emitPending()
  }

  /** Subscribe to pending-state changes; returns a disposer. */
  onPendingChange(listener: () => void): () => void {
    this.pendingListeners.add(listener)
    return () => this.pendingListeners.delete(listener)
  }

  private emitPending(): void {
    for (const l of this.pendingListeners) l()
  }

  // ── dispatch ──────────────────────────────────────────────────────────

  /**
   * Resolve a key stroke against the active layers. Returns the first command
   * whose binding matches and does not reject; a sequence is started when the
   * stroke is a prefix of a multi-stroke binding. If no binding matches but an
   * active layer is `swallowAll`, the key is consumed (modal behavior).
   */
  resolve(stroke: Stroke, targets: readonly string[] = []): ResolveResult {
    const match = strokeToMatch(stroke)
    const pendingResult = this.advancePending(match)
    if (pendingResult) return pendingResult
    return this.searchActive(match, targets)
  }

  /** Advance an in-flight leader sequence, or null when none is pending. */
  private advancePending(match: KeyMatch): ResolveResult | null {
    if (this.pending.length === 0) return null
    const next: PendingCapture[] = []
    let done: PendingCapture | null = null
    for (const cap of this.pending) {
      const idx = cap.partIndex + 1
      if (cap.binding.parts[idx] !== match) continue
      if (idx >= cap.binding.parts.length - 1) {
        // final stroke: execute (keep first match, like OpenTUI)
        if (!done) done = cap
      } else {
        next.push({ ...cap, partIndex: idx })
      }
    }
    if (done) {
      this.clearPending()
      return this.run(done.layer, done.binding, "sequence-executed")
    }
    if (next.length > 0) {
      this.pending = next
      this.emitPending()
      return { handled: true, reason: "sequence-advance", pending: true }
    }
    // Miss: clear and swallow (leader window consumes the next key).
    this.clearPending()
    return { handled: true, reason: "sequence-miss", pending: false }
  }

  /** Search active layers for a matching binding or a prefix. */
  private searchActive(match: KeyMatch, targets: readonly string[]): ResolveResult {
    const active = this.activeLayers(targets)
    for (const layer of active) {
      for (const binding of layer.bindings) {
        const hit = this.tryBinding(layer, binding, match)
        if (hit) return hit
      }
    }
    if (active.some((l) => l.swallowAll)) return { handled: true, reason: "no-match", pending: false }
    return NO_MATCH
  }

  /** Try one binding; returns a result when it wins, null to keep searching. */
  private tryBinding(layer: RegisteredLayer, binding: CompiledBinding, match: KeyMatch): ResolveResult | null {
    if (binding.parts.length === 1) {
      if (binding.parts[0] !== match) return null
      const r = this.run(layer, binding, "executed")
      // Handled: stop unless fallthrough; rejected: keep searching.
      if (r.reason === "executed" && !binding.fallthrough) return r
      return null
    }
    if (binding.parts[0] === match) {
      this.pending = [{ layer, binding, partIndex: 0 }]
      this.emitPending()
      return { handled: true, reason: "sequence-start", pending: true }
    }
    return null
  }

  private run(layer: RegisteredLayer, binding: CompiledBinding, reason: ResolveResult["reason"]): ResolveResult {
    const cmd = layer.commands.get(binding.cmd)
    if (!cmd) return NO_MATCH
    const liveCtx = this.ctx()
    if (cmd.enabled && !cmd.enabled(liveCtx)) return { handled: false, reason: "rejected", pending: false }
    const result = cmd.run(liveCtx)
    if (result === false) return { handled: false, reason: "rejected", pending: false }
    return { handled: true, reason, cmd: binding.cmd, pending: false }
  }

  // ── query ─────────────────────────────────────────────────────────────

  /** Active (reachable) single-stroke bindings across active layers. */
  getActiveKeys(targets: readonly string[] = []): ActiveKeyInfo[] {
    const out: ActiveKeyInfo[] = []
    for (const layer of this.activeLayers(targets)) {
      for (const binding of layer.bindings) {
        if (binding.parts.length > 1) continue
        const cmd = layer.commands.get(binding.cmd)
        out.push({
          key: binding.parts[0]!,
          cmd: binding.cmd,
          layer: layer.id,
          enabled: !cmd?.enabled || cmd.enabled(this.ctx()),
        })
      }
    }
    return out
  }

  /** Every registered binding (single and multi-stroke) for help/listing. */
  listKeys(): ListedKey[] {
    const out: ListedKey[] = []
    for (const layer of this.layers) {
      for (const binding of layer.bindings) {
        out.push({ key: binding.parts.join(" "), cmd: binding.cmd, layer: layer.id })
      }
    }
    return out
  }
}
