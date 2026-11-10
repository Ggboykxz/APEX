"use strict";

/**
 * useApexKeyboard — wires the APEX TUI's key bindings as a declarative
 * `Keymap` (OpenTUI-style layers + named commands). Each focus context is a
 * layer with priority:
 *
 *   global     → shortcuts, scroll, agent cycle (always active in normal mode)
 *   completion → autocomplete navigation (when the list is visible)
 *   composer   → submit / newline / backspace (the default surface)
 *   overlay    → modal overlay navigation (swallows all keys while open)
 *   leader     → Ctrl+X multi-stroke sequences (via pending sequences)
 *   diff       → swallows everything while a diff is open
 *
 * The engine is pure and unit-tested; this hook builds the layer set, feeds it
 * Ink's input, and falls back to text entry for characters nothing bound.
 */

import React, { useRef, useEffect, useState } from "react"
import { useInput } from "ink"
import { Keymap } from "../keymap/engine.js"
import { fromInkKey } from "../keymap/parser.js"
import type { CommandCtx, KeymapLayer } from "../keymap/types.js"
import type { InkKeyLike } from "../keymap/parser.js"
import { APEX_AGENTS, APEX_MODELS } from "../data/apex-data.js"
import type {
  ApexKeyboardDeps,
  OverlaySpec,
} from "./useApexKeyboardTypes.js"

/** Leader-window pause (ms) after which a pending Ctrl+X sequence auto-clears. */
const LEADER_TIMEOUT = 2000

// ────────────────────────── context helpers ──────────────────────────

function D(ctx: CommandCtx): ApexKeyboardDeps {
  return ctx.deps as ApexKeyboardDeps
}

/** Which focus contexts are active right now. */
function activeTargets(deps: ApexKeyboardDeps): string[] {
  const { state } = deps
  const targets: string[] = []
  // Diff swallows everything, rendered in its own layer (early return in hook).
  const anyOverlay = Object.values(state.overlays).some(Boolean)
  if (anyOverlay) {
    targets.push("overlay")
    return targets
  }
  targets.push("global", "composer")
  if (state.completion.visible) targets.push("completion")
  return targets
}

// ────────────────────────── overlay navigation ──────────────────────────

function overlaySpecs(deps: ApexKeyboardDeps): OverlaySpec[] {
  const { state, dispatch, commands, sendMessage, submit } = deps
  const { themes, sessions } = state
  return [
    {
      name: "showCP",
      indexKey: "cpIdx",
      searchKey: "cpSearch",
      count: commands.length,
      wrap: true,
      select: (index) => void submit(commands[index]!.id),
    },
    {
      name: "showMS",
      indexKey: "msIdx",
      searchKey: "msSearch",
      count: APEX_MODELS.length,
      wrap: true,
      select: (index) => dispatch({ type: "SET_ACTIVE_MODEL", payload: APEX_MODELS[index]!.id }),
    },
    {
      name: "showTS",
      indexKey: "tsIdx",
      searchKey: null,
      count: themes.length,
      wrap: true,
      select: (index) => void sendMessage(`/theme ${themes[index]!.id}`),
    },
    {
      name: "showAS",
      indexKey: "asIdx",
      searchKey: null,
      count: APEX_AGENTS.length,
      wrap: true,
      select: (index) => dispatch({ type: "SET_ACTIVE_AGENT", payload: APEX_AGENTS[index]!.id }),
    },
    {
      name: "showSL",
      indexKey: "slIdx",
      searchKey: null,
      count: sessions.length,
      wrap: true,
      select: (index) => void sendMessage(`/session ${sessions[index]!.id}`),
    },
    {
      name: "showFF",
      indexKey: "ffIdx",
      searchKey: "ffQuery",
      count: 0,
      wrap: false,
      select: () => {},
    },
    { name: "showHelp", indexKey: null, searchKey: null, count: 0, wrap: false, select: () => {} },
    { name: "showSO", indexKey: null, searchKey: null, count: 0, wrap: false, select: () => {} },
    { name: "showDiff", indexKey: null, searchKey: null, count: 0, wrap: false, select: () => {} },
  ]
}

function activeOverlaySpec(deps: ApexKeyboardDeps): OverlaySpec | null {
  return overlaySpecs(deps).find((spec) => deps.state.overlays[spec.name]) ?? null
}

function closeOverlay(spec: OverlaySpec, deps: ApexKeyboardDeps): void {
  const { dispatch } = deps
  dispatch({ type: "SET_OVERLAY", payload: { name: spec.name, visible: false } })
  if (spec.searchKey) {
    dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: spec.searchKey, value: "" } })
  }
}

function moveOverlayIndex(spec: OverlaySpec, deps: ApexKeyboardDeps, delta: 1 | -1): void {
  if (!spec.indexKey || spec.count === 0) return
  const { state, dispatch } = deps
  const current = state.overlayIndex[spec.indexKey]
  const next = spec.wrap ? (current + delta + spec.count) % spec.count : Math.max(0, current + delta)
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: spec.indexKey, index: next } })
}

function selectOverlay(spec: OverlaySpec, deps: ApexKeyboardDeps): void {
  if (spec.count === 0 || !spec.indexKey) return
  closeOverlay(spec, deps)
  spec.select(deps.state.overlayIndex[spec.indexKey] % spec.count)
}

function editOverlaySearch(spec: OverlaySpec, deps: ApexKeyboardDeps, append: string | null): void {
  if (!spec.searchKey || !spec.indexKey) return
  const { state, dispatch } = deps
  const current = state.overlaySearch[spec.searchKey]
  const value = append === null ? current.slice(0, -1) : current + append
  dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: spec.searchKey, value } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: spec.indexKey, index: 0 } })
}

// ────────────────────────── composer helper ──────────────────────────

function syncFileFinder(deps: ApexKeyboardDeps, text: string): void {
  const at = text.lastIndexOf("@")
  const { dispatch } = deps
  dispatch({ type: "SET_OVERLAY", payload: { name: "showFF", visible: at >= 0 } })
  dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: "ffQuery", value: at >= 0 ? text.slice(at + 1) : "" } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "ffIdx", index: 0 } })
}

function setInputValue(deps: ApexKeyboardDeps, next: string): void {
  deps.dispatch({ type: "SET_INPUT_VALUE", payload: next })
  if (next.includes("@")) syncFileFinder(deps, next)
}

// ────────────────────────── layers ──────────────────────────

function makeLeaderLayer(): KeymapLayer {
  return {
    id: "leader",
    priority: 40,
    commands: [
      { name: "leader.new", run: (ctx) => void D(ctx).sendMessage("/new") },
      { name: "leader.undo", run: (ctx) => void D(ctx).sendMessage("/undo") },
      { name: "leader.redo", run: (ctx) => void D(ctx).sendMessage("/redo") },
      { name: "leader.compact", run: (ctx) => void D(ctx).sendMessage("/compact") },
      { name: "leader.model", run: (ctx) => openModelOverlay(D(ctx)) },
      { name: "leader.theme", run: (ctx) => openThemeOverlay(D(ctx)) },
      { name: "leader.status", run: (ctx) => D(ctx).dispatch({ type: "SET_OVERLAY", payload: { name: "showSO", visible: true } }) },
      { name: "leader.editor", run: (ctx) => D(ctx).sendEditorPrompt() },
      { name: "leader.export", run: (ctx) => void D(ctx).sendMessage("/export") },
      { name: "leader.sidebar", run: (ctx) => D(ctx).dispatch({ type: "SET_SIDEBAR_VISIBLE", payload: !D(ctx).state.sidebarVisible }) },
      { name: "leader.agent", run: (ctx) => openAgentOverlay(D(ctx)) },
      { name: "leader.session", run: (ctx) => openSessionOverlay(D(ctx)) },
      { name: "leader.copy", run: (ctx) => void D(ctx).sendMessage("/copy") },
      { name: "leader.quit", run: (ctx) => D(ctx).exit() },
    ],
    bindings: [
      { key: "ctrl+x n", cmd: "leader.new" },
      { key: "ctrl+x u", cmd: "leader.undo" },
      { key: "ctrl+x r", cmd: "leader.redo" },
      { key: "ctrl+x c", cmd: "leader.compact" },
      { key: "ctrl+x m", cmd: "leader.model" },
      { key: "ctrl+x t", cmd: "leader.theme" },
      { key: "ctrl+x s", cmd: "leader.status" },
      { key: "ctrl+x e", cmd: "leader.editor" },
      { key: "ctrl+x x", cmd: "leader.export" },
      { key: "ctrl+x b", cmd: "leader.sidebar" },
      { key: "ctrl+x a", cmd: "leader.agent" },
      { key: "ctrl+x l", cmd: "leader.session" },
      { key: "ctrl+x y", cmd: "leader.copy" },
      { key: "ctrl+x q", cmd: "leader.quit" },
    ],
  }
}

function openModelOverlay(deps: ApexKeyboardDeps): void {
  const { state, dispatch } = deps
  dispatch({ type: "SET_OVERLAY", payload: { name: "showMS", visible: true } })
  dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: "msSearch", value: "" } })
  dispatch({
    type: "SET_OVERLAY_INDEX",
    payload: { name: "msIdx", index: Math.max(0, APEX_MODELS.findIndex((model) => model.id === state.activeModel)) },
  })
}

function openThemeOverlay(deps: ApexKeyboardDeps): void {
  const { dispatch } = deps
  void deps.api?.listThemes?.().then((themes) => dispatch({ type: "SET_THEMES", payload: themes })).catch(() => {})
  dispatch({ type: "SET_OVERLAY", payload: { name: "showTS", visible: true } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "tsIdx", index: 0 } })
}

function openAgentOverlay(deps: ApexKeyboardDeps): void {
  const { state, dispatch } = deps
  dispatch({ type: "SET_OVERLAY", payload: { name: "showAS", visible: true } })
  dispatch({
    type: "SET_OVERLAY_INDEX",
    payload: { name: "asIdx", index: Math.max(0, APEX_AGENTS.findIndex((agent) => agent.id === state.activeAgent)) },
  })
}

function openSessionOverlay(deps: ApexKeyboardDeps): void {
  const { dispatch } = deps
  void deps.api?.listSessions?.().then((sessions) => dispatch({ type: "SET_SESSIONS", payload: sessions })).catch(() => {})
  dispatch({ type: "SET_OVERLAY", payload: { name: "showSL", visible: true } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "slIdx", index: 0 } })
}

function makeGlobalLayer(): KeymapLayer {
  return {
    id: "global",
    target: "global",
    priority: 30,
    commands: [
      { name: "palette.open", run: (ctx) => openPalette(D(ctx)) },
      { name: "models.open", run: (ctx) => openModelOverlay(D(ctx)) },
      { name: "thinking.cycle", run: (ctx) => cycleThinking(D(ctx)) },
      { name: "help.open", run: (ctx) => D(ctx).dispatch({ type: "SET_OVERLAY", payload: { name: "showHelp", visible: true } }) },
      { name: "app.quit", run: (ctx) => D(ctx).exit() },
      { name: "sidebar.toggle", run: (ctx) => D(ctx).dispatch({ type: "SET_SIDEBAR_VISIBLE", payload: !D(ctx).state.sidebarVisible }) },
      { name: "session.clear", run: (ctx) => clearSession(D(ctx)) },
      { name: "input.clear", run: (ctx) => D(ctx).dispatch({ type: "SET_INPUT_VALUE", payload: "" }) },
      { name: "input.deleteWord", run: (ctx) => D(ctx).dispatch({ type: "SET_INPUT_VALUE", payload: D(ctx).state.inputValue.replace(/\s*\S+\s*$/, "") }) },
      { name: "filefinder.open", run: (ctx) => openFileFinder(D(ctx)) },
      { name: "tool.toggle", run: (ctx) => toggleTool(D(ctx)) },
      { name: "connection.retry", enabled: (ctx) => D(ctx).state.isReconnecting, run: (ctx) => D(ctx).retryConnection() },
      { name: "scroll.up", run: (ctx) => D(ctx).dispatch({ type: "SET_TAIL", payload: false }) },
      { name: "scroll.down", run: (ctx) => D(ctx).dispatch({ type: "SET_TAIL", payload: true }) },
      {
        name: "agent.next",
        run: (ctx) => cycleAgent(D(ctx), 1),
      },
      {
        name: "agent.prev",
        run: (ctx) => cycleAgent(D(ctx), -1),
      },
    ],
    bindings: [
      { key: "ctrl+p", cmd: "palette.open" },
      { key: "ctrl+k", cmd: "models.open" },
      { key: "ctrl+t", cmd: "thinking.cycle" },
      { key: "?", cmd: "help.open" },
      { key: "ctrl+q", cmd: "app.quit" },
      { key: "ctrl+o", cmd: "sidebar.toggle" },
      { key: "ctrl+l", cmd: "session.clear" },
      { key: "ctrl+u", cmd: "input.clear" },
      { key: "ctrl+w", cmd: "input.deleteWord" },
      { key: "ctrl+d", cmd: "filefinder.open" },
      { key: "ctrl+e", cmd: "tool.toggle" },
      { key: "ctrl+r", cmd: "connection.retry" },
      { key: "pageup", cmd: "scroll.up" },
      { key: "home", cmd: "scroll.up" },
      { key: "pagedown", cmd: "scroll.down" },
      { key: "end", cmd: "scroll.down" },
      { key: "tab", cmd: "agent.next" },
      { key: "shift+tab", cmd: "agent.prev" },
    ],
  }
}

function makeCompletionLayer(): KeymapLayer {
  return {
    id: "completion",
    target: "completion",
    priority: 20,
    commands: [
      { name: "completion.hide", run: (ctx) => D(ctx).dispatch({ type: "HIDE_COMPLETION" }) },
      { name: "completion.prev", run: (ctx) => D(ctx).dispatch({ type: "SET_COMPLETION_INDEX", payload: Math.max(0, D(ctx).state.completion.index - 1) }) },
      { name: "completion.next", run: (ctx) => D(ctx).dispatch({ type: "SET_COMPLETION_INDEX", payload: D(ctx).state.completion.index + 1 }) },
      { name: "completion.select", run: (ctx) => selectCompletionItem(D(ctx)) },
    ],
    bindings: [
      { key: "escape", cmd: "completion.hide" },
      { key: "up", cmd: "completion.prev" },
      { key: "down", cmd: "completion.next" },
      { key: "return", cmd: "completion.select" },
    ],
  }
}

function selectCompletionItem(deps: ApexKeyboardDeps): void {
  const item = deps.state.completion.items[deps.state.completion.index]
  if (item) deps.selectCompletion(item.value)
  deps.dispatch({ type: "HIDE_COMPLETION" })
}

function makeComposerLayer(): KeymapLayer {
  return {
    id: "composer",
    target: "composer",
    priority: 10,
    commands: [
      { name: "composer.submit", enabled: (ctx) => D(ctx).state.inputValue.trim().length > 0 && !D(ctx).state.isGenerating, run: (ctx) => submitMessage(D(ctx)) },
      { name: "composer.newline", run: (ctx) => D(ctx).dispatch({ type: "SET_INPUT_VALUE", payload: D(ctx).state.inputValue + "\n" }) },
      { name: "composer.backspace", run: (ctx) => deleteComposerChar(D(ctx)) },
    ],
    bindings: [
      { key: "return", cmd: "composer.submit" },
      { key: "shift+return", cmd: "composer.newline" },
      { key: "backspace", cmd: "composer.backspace" },
      { key: "delete", cmd: "composer.backspace" },
    ],
  }
}

function makeOverlayLayer(): KeymapLayer {
  return {
    id: "overlay",
    target: "overlay",
    priority: 50,
    swallowAll: true,
    commands: [
      { name: "overlay.close", run: (ctx) => { const spec = activeOverlaySpec(D(ctx)); if (spec) closeOverlay(spec, D(ctx)) } },
      { name: "overlay.select", run: (ctx) => { const spec = activeOverlaySpec(D(ctx)); if (spec) selectOverlay(spec, D(ctx)) } },
      { name: "overlay.up", run: (ctx) => { const spec = activeOverlaySpec(D(ctx)); if (spec) moveOverlayIndex(spec, D(ctx), -1) } },
      { name: "overlay.down", run: (ctx) => { const spec = activeOverlaySpec(D(ctx)); if (spec) moveOverlayIndex(spec, D(ctx), 1) } },
      { name: "overlay.searchDelete", run: (ctx) => { const spec = activeOverlaySpec(D(ctx)); if (spec) editOverlaySearch(spec, D(ctx), null) } },
    ],
    bindings: [
      { key: "escape", cmd: "overlay.close" },
      { key: "return", cmd: "overlay.select" },
      { key: "up", cmd: "overlay.up" },
      { key: "down", cmd: "overlay.down" },
      { key: "backspace", cmd: "overlay.searchDelete" },
      { key: "delete", cmd: "overlay.searchDelete" },
    ],
  }
}

function makeDiffLayer(): KeymapLayer {
  return { id: "diff", target: "diff", priority: 60, swallowAll: true, commands: [], bindings: [] }
}

// ────────────────────────── command implementations ──────────────────────────

function openPalette(deps: ApexKeyboardDeps): void {
  const { dispatch } = deps
  dispatch({ type: "SET_OVERLAY", payload: { name: "showCP", visible: true } })
  dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: "cpSearch", value: "" } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "cpIdx", index: 0 } })
}

const NEXT_THINKING = { show: "hide", hide: "off", off: "show" } as const

function cycleThinking(deps: ApexKeyboardDeps): void {
  deps.dispatch({ type: "SET_THINKING_MODE", payload: NEXT_THINKING[deps.state.thinkingMode] })
}

function clearSession(deps: ApexKeyboardDeps): void {
  const { dispatch } = deps
  dispatch({ type: "CLEAR_MESSAGES" })
  dispatch({ type: "SET_INPUT_VALUE", payload: "" })
  dispatch({ type: "SET_STATS", payload: { totalPromptTokens: 0, totalCompletionTokens: 0, totalSpent: 0 } })
  dispatch({ type: "SET_TAIL", payload: true })
}

function openFileFinder(deps: ApexKeyboardDeps): void {
  const { state, dispatch } = deps
  const next = state.inputValue.slice(1)
  dispatch({ type: "SET_INPUT_VALUE", payload: next })
  syncFileFinder(deps, next)
}

function toggleTool(deps: ApexKeyboardDeps): void {
  const { state, dispatch } = deps
  const last = state.tools[state.tools.length - 1]
  if (!last) return
  dispatch({ type: "SET_EXPANDED_TOOL", payload: state.expandedToolId === last.id ? null : last.id })
}

function cycleAgent(deps: ApexKeyboardDeps, delta: 1 | -1): void {
  const { state, dispatch } = deps
  const index = APEX_AGENTS.findIndex((agent) => agent.id === state.activeAgent)
  const next = (index + delta + APEX_AGENTS.length) % APEX_AGENTS.length
  dispatch({ type: "SET_ACTIVE_AGENT", payload: APEX_AGENTS[next]!.id })
}

function submitMessage(deps: ApexKeyboardDeps): void {
  const text = deps.state.inputValue.trim()
  deps.dispatch({ type: "SET_INPUT_VALUE", payload: "" })
  if (text.startsWith("!")) void deps.sendBash(text.slice(1).trim())
  else deps.submit(text)
}

function deleteComposerChar(deps: ApexKeyboardDeps): void {
  const { state, dispatch } = deps
  const next = state.inputValue.slice(0, -1)
  dispatch({ type: "SET_INPUT_VALUE", payload: next })
  if (state.inputValue.includes("@")) syncFileFinder(deps, next)
}

function consumeComposerTyping(deps: ApexKeyboardDeps, input: string, key: InkKeyLike): void {
  if (!key.ctrl && !key.meta && input) setInputValue(deps, deps.state.inputValue + input)
}

function consumeOverlayTyping(deps: ApexKeyboardDeps, input: string, key: InkKeyLike): void {
  const spec = activeOverlaySpec(deps)
  if (!spec) return
  if (!key.ctrl && !key.meta && input) editOverlaySearch(spec, deps, input)
}

// ────────────────────────── hook ──────────────────────────

export function useApexKeyboard(deps: ApexKeyboardDeps): { leaderActive: boolean; leaderStrokes: string[]; keymap: Keymap | null } {
  // The keymap's command context must see the latest committed render. Keep the
  // live deps in a ref updated by an effect (not during render), and build the
  // keymap once inside an effect so no ref is touched in render.
  const depsRef = useRef(deps)
  useEffect(() => {
    depsRef.current = deps
  })

  const [keymap, setKeymap] = useState<Keymap | null>(null)
  const [leaderActive, setLeaderActive] = useState(false)
  const [leaderStrokes, setLeaderStrokes] = useState<string[]>([])

  useEffect(() => {
    const km = new Keymap(() => {
      const cur = depsRef.current
      return { state: cur.state, input: cur.state.inputValue, deps: cur }
    })
    const disposers = [
      km.register(makeDiffLayer()),
      km.register(makeOverlayLayer()),
      km.register(makeLeaderLayer()),
      km.register(makeGlobalLayer()),
      km.register(makeCompletionLayer()),
      km.register(makeComposerLayer()),
    ]
    setKeymap(km)
    return () => disposers.forEach((d) => d())
  }, [])

  useLeaderStatus(keymap, setLeaderActive, setLeaderStrokes)

  useInput((input, key) => {
    if (!keymap) return
    const cur = depsRef.current
    if (cur.state.overlays.showDiff) return
    const targets = activeTargets(cur)
    const result = keymap.resolve(fromInkKey(input, key), targets)
    if (result.handled) return
    // Fallback: unbound printable characters → text entry into the active
    // surface (composer or overlay search).
    if (targets.includes("overlay")) consumeOverlayTyping(cur, input, key)
    else if (targets.includes("composer")) consumeComposerTyping(cur, input, key)
  })

  return { leaderActive, leaderStrokes, keymap }
}

/**
 * Tracks the leader window (Ctrl+X sequences): mirrors pending state to the
 * UI and auto-clears it after a pause. The engine stays pure — the timer lives
 * here in React.
 */
function useLeaderStatus(
  keymap: Keymap | null,
  setLeaderActive: (v: boolean) => void,
  setLeaderStrokes: (v: string[]) => void
): void {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!keymap) return
    const off = keymap.onPendingChange(() => {
      if (timerRef.current) clearTimeout(timerRef.current)
      setLeaderActive(keymap.hasPending())
      setLeaderStrokes(keymap.getPendingStrokes())
      if (keymap.hasPending()) {
        timerRef.current = setTimeout(() => keymap.clearPending(), LEADER_TIMEOUT)
      } else {
        timerRef.current = null
      }
    })
    return () => {
      off()
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [keymap, setLeaderActive, setLeaderStrokes])
}
