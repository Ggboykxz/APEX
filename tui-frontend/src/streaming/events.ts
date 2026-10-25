/**
 * Wire-event normalization.
 *
 * The Python backend (`apex/http_api.py`) publishes a small, stable set of
 * EventBus messages today:
 *
 *   connected      {version, model, agent, cwd}
 *   state          {model, agent, history_length, undo_available, redo_available}
 *   chat_complete  {model, usage}
 *   undo / redo    {action}
 *   compact        {tokens_saved}
 *   theme_changed  {theme}
 *   pong           {}
 *
 * Incremental assistant/tool events are not emitted yet, so this module also
 * accepts the conventional aliases a backend can adopt without breaking the
 * current contract (`assistant_delta`, `message_delta`, `tool_started`,
 * `tool_finished`, `session_updated`, ...). Anything unrecognized returns
 * `null` and is left to the existing generic `"event"` listener in sync.ts.
 */

import type {
  AgentStreamEvent,
  SessionStateData,
  SyncEvent,
  ToolEndData,
  ToolStartData,
  Usage,
} from "../types.js"

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined
}

function asBoolean(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}

function asArgs(value: unknown): Record<string, unknown> | undefined {
  const direct = asRecord(value)
  if (direct) return direct
  if (typeof value !== "string") return undefined
  try {
    return asRecord(JSON.parse(value))
  } catch {
    return undefined
  }
}

function asOutput(value: unknown): string | undefined {
  if (value === undefined || value === null) return undefined
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function eventName(msg: SyncEvent): string {
  return typeof msg.event === "string" ? msg.event.trim().toLowerCase() : ""
}

function eventData(msg: SyncEvent): Record<string, unknown> {
  return asRecord(msg.data) ?? {}
}

function sequenceOf(msg: SyncEvent, data: Record<string, unknown>): number | undefined {
  return (
    asNumber(data.seq) ??
    asNumber(data.sequence) ??
    asNumber((msg as unknown as { sequence?: unknown }).sequence)
  )
}

function sessionIdOf(data: Record<string, unknown>): string | undefined {
  return asString(data.session_id) ?? asString(data.sessionId) ?? asString(data.sessionID)
}

function messageIdOf(data: Record<string, unknown>): string | undefined {
  return asString(data.message_id) ?? asString(data.messageId) ?? asString(data.messageID)
}

function toolIdOf(data: Record<string, unknown>): string | undefined {
  return (
    asString(data.tool_call_id) ??
    asString(data.toolCallId) ??
    asString(data.call_id) ??
    asString(data.id)
  )
}

function toolNameOf(data: Record<string, unknown>): string | undefined {
  return (
    asString(data.name) ??
    asString(data.tool) ??
    asString(data.tool_name) ??
    asString(asRecord(data.tool)?.name)
  )
}

function toolArgsOf(data: Record<string, unknown>): Record<string, unknown> | undefined {
  return (
    asArgs(data.args) ??
    asArgs(data.arguments) ??
    asArgs(data.input) ??
    asArgs(asRecord(data.tool)?.args)
  )
}

const DELTA_EVENTS = new Set([
  "assistant_delta",
  "message_delta",
  "text_delta",
  "delta",
  "assistant.delta",
])

const MESSAGE_EVENTS = new Set([
  "assistant_message",
  "assistant_message_complete",
  "message_added",
  "message_updated",
  "message.updated",
  "chat_message",
])

const TOOL_START_EVENTS = new Set([
  "tool_start",
  "tool_started",
  "tool_call_started",
  "tool_call",
  "tool.execution_started",
])

const TOOL_END_EVENTS = new Set([
  "tool_end",
  "tool_finished",
  "tool_result",
  "tool_executed",
  "tool_error",
  "tool_call_completed",
  "tool.execution_completed",
])

const SESSION_STATE_EVENTS = new Set([
  "state",
  "session_state",
  "session_updated",
  "connected",
])

const SESSION_RESET_EVENTS = new Set([
  "session_reset",
  "session_created",
  "session_switched",
])

const CHAT_COMPLETE_EVENTS = new Set(["chat_complete", "chat_completed", "chat_done"])

const ERROR_EVENTS = new Set(["stream_error", "chat_error"])

function normalizeAssistantDelta(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent | null {
  const part = asRecord(data.part)
  const delta =
    asString(data.delta) ??
    asString(data.text) ??
    asString(data.content) ??
    asString(data.chunk) ??
    asString(part?.delta) ??
    asString(part?.text)
  if (delta === undefined) return null
  return {
    type: "assistant_delta",
    delta,
    messageId: messageIdOf(data) ?? messageIdOf(part ?? {}),
    sessionId: sessionIdOf(data) ?? sessionIdOf(part ?? {}),
    agent: asString(data.agent),
    model: asString(data.model),
    seq: sequenceOf(msg, data),
  }
}

function normalizeAssistantMessage(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent | null {
  const nested = asRecord(data.message)
  const source = nested ?? data
  const role = asString(source.role) ?? asString(data.role)
  // `message_added` also carries user/tool messages; never append those to
  // the assistant draft.
  if (role !== undefined && role !== "assistant") return null
  const content =
    asString(source.content) ?? asString(source.text) ?? asString(data.content) ?? asString(data.text)
  if (content === undefined) return null
  const final =
    asBoolean(source.final) ??
    asBoolean(source.done) ??
    asBoolean(source.complete) ??
    asBoolean(data.final) ??
    asBoolean(data.done) ??
    asBoolean(data.complete) ??
    true
  return {
    type: "assistant_message",
    content,
    messageId:
      messageIdOf(source) ??
      asString(source.id) ??
      messageIdOf(data) ??
      asString(data.id),
    sessionId: sessionIdOf(source) ?? sessionIdOf(data),
    agent: asString(source.agent) ?? asString(data.agent),
    model: asString(source.model) ?? asString(data.model),
    final,
    seq: sequenceOf(msg, data),
  }
}

function normalizeToolStart(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent | null {
  const nested = asRecord(data.tool)
  const source = nested ?? data
  const name = toolNameOf(data) ?? asString(source.name)
  if (name === undefined) return null
  const toolCallId = toolIdOf(data) ?? asString(source.id) ?? name
  return {
    type: "tool_start",
    toolCallId,
    name,
    args: toolArgsOf(data),
    sessionId: sessionIdOf(data) ?? sessionIdOf(source),
    seq: sequenceOf(msg, data),
  }
}

function normalizeToolEnd(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent | null {
  const toolCallId = toolIdOf(data)
  const name = toolNameOf(data)
  if (toolCallId === undefined && name === undefined) return null
  const error = asString(data.error)
  const rawStatus = asString(data.status)?.toLowerCase()
  const status =
    error !== undefined || eventName(msg) === "tool_error" || rawStatus === "error" || rawStatus === "failed"
      ? "error"
      : "success"
  return {
    type: "tool_end",
    toolCallId,
    name,
    output: asOutput(data.output) ?? asOutput(data.result) ?? asOutput(data.content),
    error,
    status,
    durationMs:
      asNumber(data.duration_ms) ?? asNumber(data.durationMs) ?? asNumber(data.duration),
    sessionId: sessionIdOf(data),
    seq: sequenceOf(msg, data),
  }
}

function normalizeSessionState(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent | null {
  const nested = asRecord(data.session)
  const state = {
    sessionId: sessionIdOf(data) ?? sessionIdOf(nested ?? {}),
    model: asString(data.model) ?? asString(nested?.model),
    agent: asString(data.agent) ?? asString(nested?.agent),
    cwd: asString(data.cwd) ?? asString(nested?.cwd),
    historyLength:
      asNumber(data.history_length ?? data.historyLength) ??
      asNumber(nested?.history_length ?? nested?.historyLength),
    undoAvailable:
      asBoolean(data.undo_available ?? data.undoAvailable) ??
      asBoolean(nested?.undo_available ?? nested?.undoAvailable),
    redoAvailable:
      asBoolean(data.redo_available ?? data.redoAvailable) ??
      asBoolean(nested?.redo_available ?? nested?.redoAvailable),
    version: asString(data.version) ?? asString(nested?.version),
    status: asString(data.status) ?? asString(nested?.status),
  }
  const hasField = Object.values(state).some((value) => value !== undefined)
  if (!hasField) return null
  return { type: "session_state", state, seq: sequenceOf(msg, data) }
}

function normalizeSessionReset(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent {
  return {
    type: "session_reset",
    sessionId: sessionIdOf(data),
    model: asString(data.model),
    agent: asString(data.agent),
    cwd: asString(data.cwd),
    seq: sequenceOf(msg, data),
  }
}

function normalizeChatComplete(
  msg: SyncEvent,
  data: Record<string, unknown>,
): AgentStreamEvent {
  const rawUsage = asRecord(data.usage)
  const usage: Usage | undefined = rawUsage
    ? {
        prompt_tokens: asNumber(rawUsage.prompt_tokens),
        completion_tokens: asNumber(rawUsage.completion_tokens),
        total_tokens: asNumber(rawUsage.total_tokens),
      }
    : undefined
  return {
    type: "chat_complete",
    usage,
    model: asString(data.model),
    sessionId: sessionIdOf(data),
    seq: sequenceOf(msg, data),
  }
}

/**
 * Convert one raw WebSocket envelope into a typed, UI-friendly event.
 * Returns `null` for heartbeat/unknown events so callers can keep their
 * existing fallback handling untouched.
 */
export function normalizeAgentEvent(msg: SyncEvent): AgentStreamEvent | null {
  const name = eventName(msg)
  const data = eventData(msg)

  if (DELTA_EVENTS.has(name)) return normalizeAssistantDelta(msg, data)
  if (MESSAGE_EVENTS.has(name)) return normalizeAssistantMessage(msg, data)
  if (TOOL_START_EVENTS.has(name)) return normalizeToolStart(msg, data)
  if (TOOL_END_EVENTS.has(name)) return normalizeToolEnd(msg, data)
  if (SESSION_RESET_EVENTS.has(name)) return normalizeSessionReset(msg, data)
  if (SESSION_STATE_EVENTS.has(name)) return normalizeSessionState(msg, data)
  if (CHAT_COMPLETE_EVENTS.has(name)) return normalizeChatComplete(msg, data)
  if (ERROR_EVENTS.has(name)) {
    return {
      type: "stream_error",
      error: asString(data.error) ?? asString(data.message) ?? "Unknown stream error",
      sessionId: sessionIdOf(data),
      seq: sequenceOf(msg, data),
    }
  }
  return null
}

/** Exported for tests/documentation; keeps the accepted aliases inspectable. */
export const KNOWN_EVENT_ALIASES = {
  assistantDelta: [...DELTA_EVENTS],
  assistantMessage: [...MESSAGE_EVENTS],
  toolStart: [...TOOL_START_EVENTS],
  toolEnd: [...TOOL_END_EVENTS],
  sessionState: [...SESSION_STATE_EVENTS],
  sessionReset: [...SESSION_RESET_EVENTS],
  chatComplete: [...CHAT_COMPLETE_EVENTS],
  error: [...ERROR_EVENTS],
} as const

// Keeps `SessionStateData`/`ToolStartData`/`ToolEndData` documented as the
// canonical payload shapes even though normalization reads them structurally.
export type WireSessionStateData = SessionStateData
export type WireToolStartData = ToolStartData
export type WireToolEndData = ToolEndData
