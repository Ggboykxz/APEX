"use strict";

/**
 * TuiStore — single source of truth for the APEX TUI.
 *
 * Pure reducer (no React, no Ink): every state transition is a plain
 * function (state, action) => newState, fully unit-testable.
 *
 * Inspired by OpenCode's SyncProvider + createSessionRows: one store, one
 * dispatcher, pure reconciliation. Components only read state and dispatch.
 */

import type { Dispatch } from "react"
import { randomUUID } from "node:crypto"
import type { ChatMessage } from "../data/apex-data.js"
import type { StreamToolCall } from "../streaming/reducer.js"

/**
 * Rows kept in the live window; anything older is handed to `<Static>` and
 * printed once into the terminal scrollback.
 */
export const LIVE_WINDOW = 20

/** One autocomplete suggestion, frecency-ranked by the composer. */
export interface CompletionItem {
  label: string
  value: string
  kind: "command" | "file" | "agent" | "model" | "theme" | "session"
}

// ────────────────────────── State ──────────────────────────

export interface OverlayState {
  showDiff: boolean
  showCP: boolean
  showHelp: boolean
  showMS: boolean
  showTS: boolean
  showAS: boolean
  showSO: boolean
  showSL: boolean
  showFF: boolean
}

export interface OverlaySearch {
  cpSearch: string
  msSearch: string
  ffQuery: string
}

export interface OverlayIndex {
  cpIdx: number
  msIdx: number
  tsIdx: number
  asIdx: number
  slIdx: number
  ffIdx: number
}

export interface TuiState {
  // ── Agent / model / session ──
  activeAgent: string
  activeModel: string
  activeSession: string

  // ── Messages ──
  messages: ChatMessage[]

  // ── Input ──
  inputValue: string
  isGenerating: boolean

  // ── Connection ──
  connectionError: string | null
  isReconnecting: boolean
  retryCount: number

  // ── Sidebar ──
  sidebarVisible: boolean

  // ── Overlays ──
  overlays: OverlayState
  overlaySearch: OverlaySearch
  overlayIndex: OverlayIndex
  themes: { id: string; name: string }[]
  sessions: { id: string; name: string; model?: string }[]

  // ── Stats ──
  totalPromptTokens: number
  totalCompletionTokens: number
  totalSpent: number
  livePromptTokens: number
  liveCompletionTokens: number

  // ── Diff ──
  diffText: string
  diffFingerprint: string
  diffPaths: string[]
  diffSubmitting: boolean
  diffError: string | undefined

  // ── Viewport ──
  /**
   * When true the live area follows the newest message. When false the user
   * has scrolled up: finished rows keep flowing into `<Static>` but the live
   * window is never re-anchored, so the view is not yanked back down.
   */
  tail: boolean
  /** Monotonic count of rows already printed into `<Static>`. */
  committedCount: number
  /**
   * Bumped whenever the transcript is cleared. `<Static>` is keyed on it so a
   * fresh session remounts the component and its internal print cursor resets.
   */
  staticEpoch: number

  // ── Tools (streaming) ──
  tools: StreamToolCall[]
  /** Tool call whose I/O is expanded; `null` collapses all. */
  expandedToolId: string | null

  // ── Input completion (frecency) ──
  /**
   * When set, an autocomplete list is shown under the composer. `trigger` is
   * "/" or "@", `prefix` is the text being completed, `items` are already
   * frecency-ranked, `index` is the highlighted row.
   */
  completion: {
    visible: boolean
    trigger: "/" | "@"
    prefix: string
    items: CompletionItem[]
    index: number
  }
  /** Usage counter per completion value, persisted across sessions. */
  completionFreq: Record<string, number>

  // ── Toasts ──
  /** Ephemeral notifications (info / success / warn / error). */
  toasts: Toast[]

  // ── Thinking ──
  thinkingMode: "show" | "hide" | "off"

  // ── Session ──
  sessionStart: number

  // ── Theme ──
  activeTheme: string
}

/**
 * One ephemeral notification.
 */
export interface Toast {
  id: string
  kind: "info" | "success" | "warn" | "error"
  message: string
  /** Auto-dismiss delay in ms (default 4000). */
  duration?: number
  /** Creation timestamp (epoch ms). */
  ts: number
}

export const initialTuiState: TuiState = {
  activeAgent: "build",
  activeModel: "claude-sonnet-4",
  activeSession: "",
  activeTheme: "default",
  messages: [],
  inputValue: "",
  isGenerating: false,
  connectionError: null,
  isReconnecting: false,
  retryCount: 0,
  sidebarVisible: true,
  overlays: {
    showDiff: false,
    showCP: false,
    showHelp: false,
    showMS: false,
    showTS: false,
    showAS: false,
    showSO: false,
    showSL: false,
    showFF: false,
  },
  overlaySearch: { cpSearch: "", msSearch: "", ffQuery: "" },
  overlayIndex: { cpIdx: 0, msIdx: 0, tsIdx: 0, asIdx: 0, slIdx: 0, ffIdx: 0 },
  themes: [],
  sessions: [],
  totalPromptTokens: 0,
  totalCompletionTokens: 0,
  totalSpent: 0,
  livePromptTokens: 0,
  liveCompletionTokens: 0,
  diffText: "",
  diffFingerprint: "",
  diffPaths: [],
  diffSubmitting: false,
  diffError: undefined,
  tail: true,
  committedCount: 0,
  staticEpoch: 0,
  tools: [],
  expandedToolId: null,
  completion: { visible: false, trigger: "/", prefix: "", items: [], index: 0 },
  completionFreq: {},
  toasts: [],
  thinkingMode: "show",
  sessionStart: Date.now(),
}

// ────────────────────────── Actions ──────────────────────────

export type TuiAction =
  | { type: "SET_ACTIVE_AGENT"; payload: string }
  | { type: "SET_ACTIVE_MODEL"; payload: string }
  | { type: "SET_ACTIVE_SESSION"; payload: string }
  | { type: "ADD_MESSAGE"; payload: ChatMessage }
  | { type: "ADD_MESSAGES"; payload: ChatMessage[] }
  | { type: "CLEAR_MESSAGES" }
  | { type: "SET_INPUT_VALUE"; payload: string }
  | { type: "SET_IS_GENERATING"; payload: boolean }
  | { type: "SET_CONNECTION_ERROR"; payload: string | null }
  | { type: "SET_IS_RECONNECTING"; payload: boolean }
  | { type: "SET_RETRY_COUNT"; payload: number | ((prev: number) => number) }
  | { type: "SET_STATS"; payload: { totalPromptTokens: number; totalCompletionTokens: number; totalSpent: number } }
  | { type: "SET_LIVE_TOKENS"; payload: { pt: number; ct: number } }
  | { type: "SET_SIDEBAR_VISIBLE"; payload: boolean }
  | { type: "SET_OVERLAY"; payload: { name: keyof OverlayState; visible: boolean } }
  | { type: "SET_OVERLAY_SEARCH"; payload: { name: keyof OverlaySearch; value: string } }
  | { type: "SET_OVERLAY_INDEX"; payload: { name: keyof OverlayIndex; index: number } }
  | { type: "SET_THEMES"; payload: { id: string; name: string }[] }
  | { type: "SET_SESSIONS"; payload: { id: string; name: string; model?: string }[] }
  | { type: "SET_DIFF"; payload: { diff: string; fingerprint: string; paths: string[] } }
  | { type: "SET_DIFF_SUBMITTING"; payload: boolean }
  | { type: "SET_DIFF_ERROR"; payload: string | undefined }
  | { type: "SET_TAIL"; payload: boolean }
  | { type: "SET_TOOLS"; payload: StreamToolCall[] }
  | { type: "SET_EXPANDED_TOOL"; payload: string | null }
  | { type: "SET_COMPLETION"; payload: { visible: boolean; trigger: "/" | "@"; prefix: string; items: CompletionItem[]; index?: number } }
  | { type: "SET_COMPLETION_INDEX"; payload: number }
  | { type: "INC_COMPLETION_FREQ"; payload: string }
  | { type: "HIDE_COMPLETION" }
  | { type: "ADD_TOAST"; payload: { kind: Toast["kind"]; message: string; duration?: number } }
  | { type: "REMOVE_TOAST"; payload: string }
  | { type: "CLEAR_TOASTS" }
  | { type: "SET_ACTIVE_THEME"; payload: string }
  | { type: "SET_THINKING_MODE"; payload: "show" | "hide" | "off" }
  | { type: "RESET_SESSION" }

// ────────────────────────── Reducer ──────────────────────────

type Patch = Partial<TuiState>

/**
 * `<Static>` is append-only, so the committed boundary only ever moves
 * forward. While tailing it follows the message count; when the user has
 * scrolled up it freezes so the view is not yanked back down.
 */
function withCommitted(state: TuiState, messages: ChatMessage[]): Patch {
  if (!state.tail) return { messages }
  const target = Math.max(0, messages.length - LIVE_WINDOW)
  return { messages, committedCount: Math.max(state.committedCount, target) }
}

function agentPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_ACTIVE_AGENT":
      return { activeAgent: action.payload }
    case "SET_ACTIVE_MODEL":
      return { activeModel: action.payload }
    case "SET_ACTIVE_SESSION":
      return { activeSession: action.payload }
    case "SET_ACTIVE_THEME":
      return { activeTheme: action.payload }
    case "SET_SIDEBAR_VISIBLE":
      return { sidebarVisible: action.payload }
    case "SET_THINKING_MODE":
      return { thinkingMode: action.payload }
    default:
      return {}
  }
}

function messagePatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "ADD_MESSAGE":
      return withCommitted(state, [...state.messages, action.payload])
    case "ADD_MESSAGES":
      return withCommitted(state, [...state.messages, ...action.payload])
    case "CLEAR_MESSAGES":
      return {
        messages: [],
        committedCount: 0,
        staticEpoch: state.staticEpoch + 1,
        completion: { visible: false, trigger: "/", prefix: "", items: [], index: 0 },
      }
    case "SET_INPUT_VALUE":
      return { inputValue: action.payload }
    case "SET_IS_GENERATING":
      return { isGenerating: action.payload }
    default:
      return {}
  }
}

function resolveRetryCount(current: number, payload: number | ((prev: number) => number)): number {
  return typeof payload === "function" ? payload(current) : payload
}

function connectionPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_CONNECTION_ERROR":
      return { connectionError: action.payload }
    case "SET_IS_RECONNECTING":
      return { isReconnecting: action.payload }
    case "SET_RETRY_COUNT":
      return { retryCount: resolveRetryCount(state.retryCount, action.payload) }
    default:
      return {}
  }
}

function overlayPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_OVERLAY":
      return { overlays: { ...state.overlays, [action.payload.name]: action.payload.visible } }
    case "SET_OVERLAY_SEARCH":
      return { overlaySearch: { ...state.overlaySearch, [action.payload.name]: action.payload.value } }
    case "SET_OVERLAY_INDEX":
      return { overlayIndex: { ...state.overlayIndex, [action.payload.name]: action.payload.index } }
    case "SET_THEMES":
      return { themes: action.payload }
    case "SET_SESSIONS":
      return { sessions: action.payload }
    default:
      return {}
  }
}

function statsPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_STATS":
      return {
        totalPromptTokens: action.payload.totalPromptTokens,
        totalCompletionTokens: action.payload.totalCompletionTokens,
        totalSpent: action.payload.totalSpent,
      }
    case "SET_LIVE_TOKENS":
      return { livePromptTokens: action.payload.pt, liveCompletionTokens: action.payload.ct }
    default:
      return {}
  }
}

function diffPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_DIFF":
      return {
        diffText: action.payload.diff,
        diffFingerprint: action.payload.fingerprint,
        diffPaths: action.payload.paths,
        diffError: undefined,
      }
    case "SET_DIFF_SUBMITTING":
      return { diffSubmitting: action.payload }
    case "SET_DIFF_ERROR":
      return { diffError: action.payload }
    default:
      return {}
  }
}

function committedFor(state: TuiState, tail: boolean): number {
  if (!tail) return state.committedCount
  return Math.max(state.committedCount, Math.max(0, state.messages.length - LIVE_WINDOW))
}

function pruneExpandedTool(id: string | null, tools: StreamToolCall[]): string | null {
  if (!id) return null
  return tools.some((tool) => tool.id === id) ? id : null
}

function viewportPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_TAIL":
      return { tail: action.payload, committedCount: committedFor(state, action.payload) }
    case "SET_TOOLS":
      return { tools: action.payload, expandedToolId: pruneExpandedTool(state.expandedToolId, action.payload) }
    case "SET_EXPANDED_TOOL":
      return { expandedToolId: action.payload }
    default:
      return {}
  }
}

function completionPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "SET_COMPLETION":
      return {
        completion: {
          visible: action.payload.visible,
          trigger: action.payload.trigger,
          prefix: action.payload.prefix,
          items: action.payload.items,
          index: action.payload.index ?? 0,
        },
      }
    case "SET_COMPLETION_INDEX":
      return { completion: { ...state.completion, index: action.payload } }
    case "INC_COMPLETION_FREQ": {
      const freq = { ...state.completionFreq }
      freq[action.payload] = (freq[action.payload] ?? 0) + 1
      return { completionFreq: freq }
    }
    case "HIDE_COMPLETION":
      return { completion: { ...state.completion, visible: false } }
    default:
      return {}
  }
}

function toastPatch(state: TuiState, action: TuiAction): Patch {
  switch (action.type) {
    case "ADD_TOAST": {
      const toast: Toast = {
        id: randomUUID(),
        kind: action.payload.kind,
        message: action.payload.message,
        duration: action.payload.duration ?? 4000,
        ts: Date.now(),
      }
      return { toasts: [...state.toasts, toast] }
    }
    case "REMOVE_TOAST":
      return { toasts: state.toasts.filter((t) => t.id !== action.payload) }
    case "CLEAR_TOASTS":
      return { toasts: [] }
    default:
      return {}
  }
}

function resetSession(state: TuiState): TuiState {
  return {
    ...state,
    messages: [],
    inputValue: "",
    totalPromptTokens: 0,
    totalCompletionTokens: 0,
    totalSpent: 0,
    tail: true,
    committedCount: 0,
    staticEpoch: state.staticEpoch + 1,
    expandedToolId: null,
    completion: { visible: false, trigger: "/", prefix: "", items: [], index: 0 },
    completionFreq: state.completionFreq,
    activeSession: "",
    livePromptTokens: 0,
    liveCompletionTokens: 0,
  }
}

/**
 * Each action domain is delegated to its own patch function, so the root
 * reducer stays a composition and no single function grows a branch per action.
 */
export function tuiReducer(state: TuiState, action: TuiAction): TuiState {
  if (action.type === "RESET_SESSION") return resetSession(state)
  return {
    ...state,
    ...agentPatch(state, action),
    ...messagePatch(state, action),
    ...connectionPatch(state, action),
    ...overlayPatch(state, action),
    ...statsPatch(state, action),
    ...diffPatch(state, action),
    ...viewportPatch(state, action),
    ...completionPatch(state, action),
    ...toastPatch(state, action),
  }
}

// ────────────────────────── Selectors ──────────────────────────

export const selectActiveAgent = (s: TuiState) => s.activeAgent
export const selectActiveModel = (s: TuiState) => s.activeModel
export const selectMessages = (s: TuiState) => s.messages
export const selectConnectionError = (s: TuiState) => s.connectionError
export const selectIsReconnecting = (s: TuiState) => s.isReconnecting
export const selectRetryCount = (s: TuiState) => s.retryCount
export const selectIsGenerating = (s: TuiState) => s.isGenerating
export const selectTools = (s: TuiState) => s.tools
export const selectTotalSpent = (s: TuiState) => s.totalSpent
export const selectTail = (s: TuiState) => s.tail
export const selectExpandedToolId = (s: TuiState) => s.expandedToolId
export const selectCompletion = (s: TuiState) => s.completion
export const selectCompletionFreq = (s: TuiState) => s.completionFreq
export const selectToasts = (s: TuiState) => s.toasts
export const selectActiveTheme = (s: TuiState) => s.activeTheme

/**
 * Frecency rank: frequent + recent items first, then alphabetical.
 */
export function rankByFrecency<T extends { value: string; label: string }>(
  items: T[],
  freq: Record<string, number>,
): T[] {
  return [...items].sort(
    (a, b) => (freq[b.value] ?? 0) - (freq[a.value] ?? 0) || a.label.localeCompare(b.label),
  )
}

export type TuiDispatch = Dispatch<TuiAction>
