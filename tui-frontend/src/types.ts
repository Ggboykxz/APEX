/**
 * Shared types for the APEX TUI (Ink/React frontend).
 * Kept small and framework-agnostic so a future OpenTUI renderer can reuse them.
 */

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "tool"
  content: string
  agent?: string
  model?: string
  timestamp: number
  promptTokens?: number
  completionTokens?: number
  cost?: number
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  contextWindow: number
  inputCostPer1K: number
  outputCostPer1K: number
}

export interface AgentInfo {
  id: string
  name: string
  description: string
  mode: "primary" | "subagent" | "system"
  color?: string
}

export interface ThemeInfo {
  id: string
  name: string
}

export interface SessionInfo {
  id: string
  name: string
  model?: string
}

export interface Usage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

export interface StreamChunk {
  chunk?: string
  usage?: Usage
  error?: string
}

/**
 * Raw WebSocket envelope emitted by `apex/http_api.py` (`EventBus.publish`).
 *
 * The Python backend currently emits `connected`, `state`, `chat_complete`,
 * `undo`, `redo`, `compact`, `theme_changed` and `pong`. The streaming events
 * below are normalized from those names plus the aliases the backend is
 * expected to grow (see `streaming/events.ts`). Keeping the wire type separate
 * from the UI state means an older backend and a newer one can both be
 * consumed without changing components.
 */
export interface SyncEvent {
  event: string
  data: Record<string, unknown>
  timestamp: number
}

export interface SyncState {
  model: string
  agent: string
  cwd: string
  historyLength: number
  undoAvailable: boolean
  redoAvailable: boolean
  connected: boolean
  version: string
}

/**
 * Normalized real-time events consumed by the streaming reducer.
 *
 * Only `assistant_delta` is genuinely incremental; `assistant_message`
 * carries a full snapshot (used by `message_added` style events) and
 * `chat_complete` finalizes the turn.
 */
export interface AssistantDeltaData {
  message_id?: string
  messageId?: string
  session_id?: string
  sessionId?: string
  delta?: string
  text?: string
  content?: string
  chunk?: string
  agent?: string
  model?: string
  seq?: number
  sequence?: number
}

export interface AssistantMessageData {
  message_id?: string
  messageId?: string
  session_id?: string
  sessionId?: string
  role?: string
  content?: string
  text?: string
  agent?: string
  model?: string
  final?: boolean
  done?: boolean
  complete?: boolean
  message?: Record<string, unknown>
  seq?: number
  sequence?: number
}

export interface ToolStartData {
  tool_call_id?: string
  toolCallId?: string
  call_id?: string
  id?: string
  name?: string
  tool?: string
  tool_name?: string
  args?: Record<string, unknown>
  arguments?: Record<string, unknown> | string
  input?: Record<string, unknown>
  session_id?: string
  sessionId?: string
  seq?: number
  sequence?: number
}

export interface ToolEndData extends ToolStartData {
  output?: unknown
  result?: unknown
  content?: unknown
  error?: string
  status?: string
  duration_ms?: number
  durationMs?: number
  duration?: number
}

export interface SessionStateData {
  session_id?: string
  sessionId?: string
  model?: string
  agent?: string
  cwd?: string
  history_length?: number
  historyLength?: number
  undo_available?: boolean
  undoAvailable?: boolean
  redo_available?: boolean
  redoAvailable?: boolean
  version?: string
  status?: string
  seq?: number
  sequence?: number
}

export type AssistantDeltaStreamEvent = {
  type: "assistant_delta"
  delta: string
  messageId?: string
  sessionId?: string
  agent?: string
  model?: string
  seq?: number
}

export type AssistantMessageStreamEvent = {
  type: "assistant_message"
  content: string
  messageId?: string
  sessionId?: string
  agent?: string
  model?: string
  final: boolean
  seq?: number
}

export type ToolStartStreamEvent = {
  type: "tool_start"
  toolCallId: string
  name: string
  args?: Record<string, unknown>
  sessionId?: string
  seq?: number
}

export type ToolEndStreamEvent = {
  type: "tool_end"
  toolCallId?: string
  name?: string
  output?: string
  error?: string
  status: "success" | "error"
  durationMs?: number
  sessionId?: string
  seq?: number
}

export type SessionStateStreamEvent = {
  type: "session_state"
  state: {
    sessionId?: string
    model?: string
    agent?: string
    cwd?: string
    historyLength?: number
    undoAvailable?: boolean
    redoAvailable?: boolean
    version?: string
    status?: string
  }
  seq?: number
}

export type SessionResetStreamEvent = {
  type: "session_reset"
  sessionId?: string
  model?: string
  agent?: string
  cwd?: string
  seq?: number
}

export type ChatCompleteStreamEvent = {
  type: "chat_complete"
  usage?: Usage
  model?: string
  sessionId?: string
  seq?: number
}

export type StreamErrorEvent = {
  type: "stream_error"
  error: string
  sessionId?: string
  seq?: number
}

export type AgentStreamEvent =
  | AssistantDeltaStreamEvent
  | AssistantMessageStreamEvent
  | ToolStartStreamEvent
  | ToolEndStreamEvent
  | SessionStateStreamEvent
  | SessionResetStreamEvent
  | ChatCompleteStreamEvent
  | StreamErrorEvent

export interface TuiConfig {
  theme?: string
  keybinds?: Record<string, string>
  leader_timeout?: number
  scroll_speed?: number
  mouse?: boolean
  [key: string]: unknown
}

export interface OverlayState {
  commandPalette: boolean
  fileFinder: boolean
  help: boolean
  modelSelector: boolean
  themeSelector: boolean
  agentSelector: boolean
  status: boolean
  sessions: boolean
}

export const createInitialOverlayState = (): OverlayState => ({
  commandPalette: false,
  fileFinder: false,
  help: false,
  modelSelector: false,
  themeSelector: false,
  agentSelector: false,
  status: false,
  sessions: false,
})
