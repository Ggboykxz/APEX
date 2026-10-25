/**
 * Pure streaming reducer for agent turns.
 *
 * It is intentionally independent from React, Ink and the WebSocket client so
 * every rule (delta accumulation, tool lifecycle, session isolation, ordering)
 * can be tested without a live server. `useStreamingState` in `useStream.ts`
 * is the thin React adapter used by App.tsx.
 */

import type { AgentStreamEvent, Usage } from "../types.js"

export type StreamStatus = "idle" | "streaming" | "tool" | "complete" | "error"

export interface StreamAssistantMessage {
  id: string
  content: string
  agent?: string
  model?: string
  startedAt: number
  updatedAt: number
  streaming: boolean
}

export interface StreamToolCall {
  id: string
  name: string
  args?: Record<string, unknown>
  status: "running" | "success" | "error"
  output?: string
  error?: string
  startedAt: number
  endedAt?: number
  durationMs?: number
}

export interface StreamSession {
  id?: string
  model?: string
  agent?: string
  cwd?: string
  historyLength?: number
  undoAvailable?: boolean
  redoAvailable?: boolean
  version?: string
}

export interface StreamState {
  session: StreamSession
  /** Assistant drafts in arrival order; the last streaming one is "current". */
  messages: StreamAssistantMessage[]
  tools: StreamToolCall[]
  status: StreamStatus
  /** Last accepted monotonic sequence number (0 when the backend sends none). */
  lastSeq: number
  lastEventAt?: number
  error?: string
}

interface ActionMeta {
  sessionId?: string
  seq?: number
  /** Injectable clock to keep tests deterministic. */
  now?: number
}

export type StreamAction =
  | ({ type: "session/reset"; session?: Partial<StreamSession> } & ActionMeta)
  | ({ type: "session/state"; session: Partial<StreamSession> } & ActionMeta)
  | ({
      type: "assistant/start"
      messageId?: string
      agent?: string
      model?: string
    } & ActionMeta)
  | ({
      type: "assistant/delta"
      delta: string
      messageId?: string
      agent?: string
      model?: string
    } & ActionMeta)
  | ({
      type: "assistant/message"
      content: string
      messageId?: string
      agent?: string
      model?: string
      final?: boolean
    } & ActionMeta)
  | ({
      type: "assistant/finalize"
      messageId?: string
      content?: string
    } & ActionMeta)
  | ({
      type: "tool/start"
      toolCallId?: string
      name: string
      args?: Record<string, unknown>
    } & ActionMeta)
  | ({
      type: "tool/end"
      toolCallId?: string
      name?: string
      output?: string
      error?: string
      status?: "success" | "error"
      durationMs?: number
    } & ActionMeta)
  | ({ type: "session/complete"; usage?: Usage } & ActionMeta)
  | ({ type: "stream/error"; error: string } & ActionMeta)

export function initialStreamState(sessionId?: string): StreamState {
  return {
    session: sessionId ? { id: sessionId } : {},
    messages: [],
    tools: [],
    status: "idle",
    lastSeq: 0,
  }
}

function nowOf(action: { now?: number }): number {
  return action.now ?? Date.now()
}

/** A reset is never considered stale: it is how a client leaves a session. */
function isStale(state: StreamState, action: StreamAction): boolean {
  if (action.type === "session/reset") return false
  if (
    action.sessionId &&
    state.session.id !== undefined &&
    action.sessionId !== state.session.id
  ) {
    return true
  }
  if (
    action.seq !== undefined &&
    state.lastSeq !== 0 &&
    action.seq <= state.lastSeq
  ) {
    return true
  }
  return false
}

function withMeta(
  state: StreamState,
  action: { seq?: number; now?: number; sessionId?: string },
  patch: Partial<StreamState>,
): StreamState {
  const session = action.sessionId
    ? { ...state.session, ...(patch.session ?? {}), id: action.sessionId }
    : { ...state.session, ...(patch.session ?? {}) }
  return {
    ...state,
    ...patch,
    session,
    lastSeq: action.seq !== undefined ? Math.max(state.lastSeq, action.seq) : state.lastSeq,
    lastEventAt: nowOf(action),
  }
}

function currentAssistantIndex(state: StreamState, messageId?: string): number {
  if (messageId !== undefined) {
    return state.messages.findIndex((message) => message.id === messageId)
  }
  for (let index = state.messages.length - 1; index >= 0; index -= 1) {
    if (state.messages[index]?.streaming) return index
  }
  return -1
}

function uniqueAssistantId(state: StreamState, wanted?: string): string {
  if (wanted !== undefined && !state.messages.some((message) => message.id === wanted)) {
    return wanted
  }
  let index = state.messages.length + 1
  while (state.messages.some((message) => message.id === `assistant-${index}`)) {
    index += 1
  }
  return `assistant-${index}`
}

function hasRunningTools(state: StreamState): boolean {
  return state.tools.some((tool) => tool.status === "running")
}

function activityStatus(state: StreamState, fallback: StreamStatus = "idle"): StreamStatus {
  if (hasRunningTools(state)) return "tool"
  if (state.messages.some((message) => message.streaming)) return "streaming"
  return fallback
}

function updateAssistant(
  state: StreamState,
  index: number,
  patch: Partial<StreamAssistantMessage>,
): StreamAssistantMessage[] {
  return state.messages.map((message, i) => (i === index ? { ...message, ...patch } : message))
}

function upsertDelta(state: StreamState, action: Extract<StreamAction, { type: "assistant/delta" }>): StreamState {
  if (action.delta.length === 0) {
    return withMeta(state, action, {})
  }
  const index = currentAssistantIndex(state, action.messageId)
  if (index >= 0) {
    const current = state.messages[index]!
    const messages = updateAssistant(state, index, {
      content: current.content + action.delta,
      updatedAt: nowOf(action),
      streaming: true,
      ...(action.agent !== undefined ? { agent: action.agent } : {}),
      ...(action.model !== undefined ? { model: action.model } : {}),
    })
    const next = { ...state, messages }
    return withMeta(next, action, { status: activityStatus(next, "streaming") })
  }
  const id = uniqueAssistantId(state, action.messageId)
  const messages = [
    ...state.messages,
    {
      id,
      content: action.delta,
      agent: action.agent,
      model: action.model,
      startedAt: nowOf(action),
      updatedAt: nowOf(action),
      streaming: true,
    } satisfies StreamAssistantMessage,
  ]
  const next = { ...state, messages }
  return withMeta(next, action, { status: activityStatus(next, "streaming") })
}

function applyMessage(
  state: StreamState,
  action: Extract<StreamAction, { type: "assistant/message" }>,
  finalByDefault: boolean,
): StreamState {
  const index = currentAssistantIndex(state, action.messageId)
  const final = action.final ?? finalByDefault
  if (index >= 0) {
    const messages = updateAssistant(state, index, {
      content: action.content,
      updatedAt: nowOf(action),
      streaming: !final,
      ...(action.agent !== undefined ? { agent: action.agent } : {}),
      ...(action.model !== undefined ? { model: action.model } : {}),
    })
    const next = { ...state, messages }
    return withMeta(next, action, {
      status: final ? activityStatus(next, "complete") : activityStatus(next, "streaming"),
    })
  }
  const messages = [
    ...state.messages,
    {
      id: uniqueAssistantId(state, action.messageId),
      content: action.content,
      agent: action.agent,
      model: action.model,
      startedAt: nowOf(action),
      updatedAt: nowOf(action),
      streaming: !final,
    } satisfies StreamAssistantMessage,
  ]
  const next = { ...state, messages }
  return withMeta(next, action, {
    status: final ? activityStatus(next, "complete") : activityStatus(next, "streaming"),
  })
}

function startTool(
  state: StreamState,
  action: Extract<StreamAction, { type: "tool/start" }>,
): StreamState {
  const id = action.toolCallId ?? action.name
  const existing = state.tools.findIndex((tool) => tool.id === id)
  const now = nowOf(action)
  let tools: StreamToolCall[]
  if (existing >= 0) {
    tools = state.tools.map((tool, index) =>
      index === existing
        ? {
            ...tool,
            name: action.name,
            args: action.args ?? tool.args,
            status: "running",
            error: undefined,
            endedAt: undefined,
            durationMs: undefined,
          }
        : tool,
    )
  } else {
    tools = [
      ...state.tools,
      {
        id,
        name: action.name,
        args: action.args,
        status: "running",
        startedAt: now,
      },
    ]
  }
  return withMeta({ ...state, tools }, action, { status: "tool" })
}

function endTool(
  state: StreamState,
  action: Extract<StreamAction, { type: "tool/end" }>,
): StreamState {
  const index = findToolIndex(state, action.toolCallId, action.name)
  const now = nowOf(action)
  let tools: StreamToolCall[]
  if (index >= 0) {
    tools = state.tools.map((tool, i) =>
      i === index
        ? {
            ...tool,
            status: action.status ?? (action.error ? "error" : "success"),
            output: action.output ?? tool.output,
            error: action.error ?? tool.error,
            endedAt: now,
            durationMs: action.durationMs ?? Math.max(0, now - tool.startedAt),
          }
        : tool,
    )
  } else {
    // Graceful handling of an end event whose start was missed (e.g. a
    // reconnect): synthesize a completed call rather than dropping it.
    tools = [
      ...state.tools,
      {
        id: action.toolCallId ?? action.name ?? `tool-${state.tools.length + 1}`,
        name: action.name ?? action.toolCallId ?? "unknown",
        status: action.status ?? (action.error ? "error" : "success"),
        output: action.output,
        error: action.error,
        startedAt: now,
        endedAt: now,
        durationMs: action.durationMs ?? 0,
      },
    ]
  }
  const next = { ...state, tools }
  const fallback: StreamStatus =
    next.status === "complete" && !hasRunningTools(next) ? "complete" : "idle"
  return withMeta(next, action, { status: activityStatus(next, fallback) })
}

function findToolIndex(state: StreamState, id?: string, name?: string): number {
  if (id !== undefined) {
    const direct = state.tools.findIndex((tool) => tool.id === id)
    if (direct >= 0) return direct
  }
  if (name !== undefined) {
    for (let index = state.tools.length - 1; index >= 0; index -= 1) {
      const tool = state.tools[index]!
      if (tool.status === "running" && tool.name === name) return index
    }
  }
  return -1
}

function finalizeAssistant(
  state: StreamState,
  action: Extract<StreamAction, { type: "assistant/finalize" }>,
): StreamState {
  const index = currentAssistantIndex(state, action.messageId)
  if (index < 0) {
    if (action.content === undefined) return withMeta(state, action, {})
    return applyMessage(
      state,
      {
        type: "assistant/message",
        content: action.content,
        messageId: action.messageId,
        final: true,
        seq: action.seq,
        sessionId: action.sessionId,
        now: action.now,
      },
      true,
    )
  }
  const messages = updateAssistant(state, index, {
    ...(action.content !== undefined ? { content: action.content } : {}),
    streaming: false,
    updatedAt: nowOf(action),
  })
  const next = { ...state, messages }
  return withMeta(next, action, { status: activityStatus(next, "complete") })
}

function completeSession(
  state: StreamState,
  action: Extract<StreamAction, { type: "session/complete" }>,
): StreamState {
  const now = nowOf(action)
  const messages = state.messages.map((message) =>
    message.streaming ? { ...message, streaming: false, updatedAt: now } : message,
  )
  // A completed chat turn should never leave tools stuck in-flight.
  const tools = state.tools.map((tool) =>
    tool.status === "running"
      ? {
          ...tool,
          status: "success" as const,
          endedAt: now,
          durationMs: Math.max(0, now - tool.startedAt),
        }
      : tool,
  )
  const next = { ...state, messages, tools }
  return withMeta(next, action, { status: "complete" })
}

export function streamReducer(state: StreamState, action: StreamAction): StreamState {
  if (isStale(state, action)) return state
  switch (action.type) {
    case "session/reset": {
      const session: StreamSession = { ...asSession(action.session) }
      if (action.sessionId !== undefined) session.id = action.sessionId
      return {
        session,
        messages: [],
        tools: [],
        status: "idle",
        lastSeq: action.seq ?? 0,
        lastEventAt: nowOf(action),
      }
    }
    case "session/state": {
      const session: StreamSession = { ...state.session, ...definedSession(action.session) }
      if (action.sessionId !== undefined) session.id = action.sessionId
      return withMeta({ ...state, session }, action, {})
    }
    case "assistant/start": {
      if (currentAssistantIndex(state, action.messageId) >= 0) {
        return withMeta(state, action, {})
      }
      const now = nowOf(action)
      const messages = [
        ...state.messages,
        {
          id: uniqueAssistantId(state, action.messageId),
          content: "",
          agent: action.agent,
          model: action.model,
          startedAt: now,
          updatedAt: now,
          streaming: true,
        } satisfies StreamAssistantMessage,
      ]
      const next = { ...state, messages }
      return withMeta(next, action, { status: activityStatus(next, "streaming") })
    }
    case "assistant/delta":
      return upsertDelta(state, action)
    case "assistant/message":
      return applyMessage(state, action, false)
    case "assistant/finalize":
      return finalizeAssistant(state, action)
    case "tool/start":
      return startTool(state, action)
    case "tool/end":
      return endTool(state, action)
    case "session/complete":
      return completeSession(state, action)
    case "stream/error": {
      const messages = state.messages.map((message) =>
        message.streaming ? { ...message, streaming: false, updatedAt: nowOf(action) } : message,
      )
      return withMeta({ ...state, messages, error: action.error }, action, { status: "error" })
    }
    default:
      return state
  }
}

function asSession(session?: Partial<StreamSession>): Partial<StreamSession> {
  return session ?? {}
}

/** Drop undefined fields so a partial payload never erases known state. */
function definedSession(session?: Partial<StreamSession>): Partial<StreamSession> {
  const result: Partial<StreamSession> = {}
  for (const key of Object.keys(session ?? {}) as Array<keyof StreamSession>) {
    const value = session?.[key]
    if (value !== undefined) {
      ;(result as Record<string, unknown>)[key] = value
    }
  }
  return result
}

/** Convert a normalized WS event into a reducer action. */
export function streamActionFromEvent(event: AgentStreamEvent): StreamAction | null {
  switch (event.type) {
    case "assistant_delta":
      return {
        type: "assistant/delta",
        delta: event.delta,
        messageId: event.messageId,
        sessionId: event.sessionId,
        agent: event.agent,
        model: event.model,
        seq: event.seq,
      }
    case "assistant_message":
      return {
        type: "assistant/message",
        content: event.content,
        messageId: event.messageId,
        sessionId: event.sessionId,
        agent: event.agent,
        model: event.model,
        final: event.final,
        seq: event.seq,
      }
    case "tool_start":
      return {
        type: "tool/start",
        toolCallId: event.toolCallId,
        name: event.name,
        args: event.args,
        sessionId: event.sessionId,
        seq: event.seq,
      }
    case "tool_end":
      return {
        type: "tool/end",
        toolCallId: event.toolCallId,
        name: event.name,
        output: event.output,
        error: event.error,
        status: event.status,
        durationMs: event.durationMs,
        sessionId: event.sessionId,
        seq: event.seq,
      }
    case "session_state": {
      const session: Partial<StreamSession> = {
        id: event.state.sessionId,
        model: event.state.model,
        agent: event.state.agent,
        cwd: event.state.cwd,
        historyLength: event.state.historyLength,
        undoAvailable: event.state.undoAvailable,
        redoAvailable: event.state.redoAvailable,
        version: event.state.version,
      }
      return { type: "session/state", session, seq: event.seq }
    }
    case "session_reset":
      return {
        type: "session/reset",
        session: {
          id: event.sessionId,
          model: event.model,
          agent: event.agent,
          cwd: event.cwd,
        },
        seq: event.seq,
      }
    case "chat_complete":
      return { type: "session/complete", usage: event.usage, sessionId: event.sessionId, seq: event.seq }
    case "stream_error":
      return { type: "stream/error", error: event.error, sessionId: event.sessionId, seq: event.seq }
    default:
      return null
  }
}

/**
 * Apply an SSE cumulative snapshot (`onChunk` gives the full text so far).
 * A prefix means "only the new suffix is a delta"; a rewritten snapshot
 * replaces the draft instead of corrupting it with duplicated text.
 */
export function applyCumulativeAssistantText(
  state: StreamState,
  full: string,
  options: { messageId?: string; sessionId?: string; agent?: string; model?: string; now?: number } = {},
): StreamState {
  const index = currentAssistantIndex(state, options.messageId)
  const current = index >= 0 ? state.messages[index]!.content : ""
  if (full.startsWith(current)) {
    return streamReducer(state, {
      type: "assistant/delta",
      delta: full.slice(current.length),
      ...options,
    })
  }
  return streamReducer(state, {
    type: "assistant/message",
    content: full,
    final: false,
    ...options,
  })
}

export function getCurrentAssistant(state: StreamState): StreamAssistantMessage | undefined {
  for (let index = state.messages.length - 1; index >= 0; index -= 1) {
    const message = state.messages[index]!
    if (message.streaming) return message
  }
  return state.messages[state.messages.length - 1]
}

export function getRunningTools(state: StreamState): StreamToolCall[] {
  return state.tools.filter((tool) => tool.status === "running")
}

export function getStreamSummary(state: StreamState): {
  status: StreamStatus
  assistantChars: number
  runningTools: number
  failedTools: number
} {
  return {
    status: state.status,
    assistantChars: state.messages.reduce((total, message) => total + message.content.length, 0),
    runningTools: state.tools.filter((tool) => tool.status === "running").length,
    failedTools: state.tools.filter((tool) => tool.status === "error").length,
  }
}
