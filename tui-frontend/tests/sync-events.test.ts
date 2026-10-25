/**
 * Protocol normalization + mock-transport integration.
 *
 * The fake WebSocket exercises SyncClient exactly like the real `/ws/events`
 * socket, without binding a port or starting the Python backend.
 */

import { describe, it } from "node:test"
import assert from "node:assert/strict"
import { SyncClient } from "../src/sync.js"
import { normalizeAgentEvent } from "../src/streaming/events.js"
import {
  initialStreamState,
  streamActionFromEvent,
  streamReducer,
  type StreamState,
} from "../src/streaming/reducer.js"
import type { AgentStreamEvent } from "../src/types.js"

const timestamp = 1_700_000_000_000

describe("normalizeAgentEvent", () => {
  it("normalizes the real state/connected/chat_complete payloads", () => {
    const connected = normalizeAgentEvent({
      event: "connected",
      data: { version: "2.0.0", model: "claude-sonnet-4", agent: "build", cwd: "/repo" },
      timestamp,
    })
    assert.equal(connected?.type, "session_state")
    if (connected?.type !== "session_state") throw new Error("expected session_state")
    assert.equal(connected.state.model, "claude-sonnet-4")
    assert.equal(connected.state.cwd, "/repo")
    assert.equal(connected.state.version, "2.0.0")

    const state = normalizeAgentEvent({
      event: "state",
      data: {
        model: "gpt-5",
        agent: "plan",
        history_length: 7,
        undo_available: true,
        redo_available: false,
      },
      timestamp,
    })
    if (state?.type !== "session_state") throw new Error("expected session_state")
    assert.equal(state.state.historyLength, 7)
    assert.equal(state.state.undoAvailable, true)
    assert.equal(state.state.redoAvailable, false)

    const complete = normalizeAgentEvent({
      event: "chat_complete",
      data: { model: "gpt-5", usage: { prompt_tokens: 10, completion_tokens: 3 } },
      timestamp,
    })
    if (complete?.type !== "chat_complete") throw new Error("expected chat_complete")
    assert.equal(complete.usage?.prompt_tokens, 10)
    assert.equal(complete.usage?.completion_tokens, 3)
  })

  it("normalizes assistant delta aliases and rejects empty deltas", () => {
    const delta = normalizeAgentEvent({
      event: "message_delta",
      data: { session_id: "s1", message_id: "m1", delta: "Hello", seq: 4 },
      timestamp,
    })
    if (delta?.type !== "assistant_delta") throw new Error("expected assistant_delta")
    assert.equal(delta.delta, "Hello")
    assert.equal(delta.messageId, "m1")
    assert.equal(delta.sessionId, "s1")
    assert.equal(delta.seq, 4)

    assert.equal(
      normalizeAgentEvent({ event: "assistant_delta", data: {}, timestamp }),
      null,
    )
    assert.equal(normalizeAgentEvent({ event: "theme_changed", data: { theme: "nord" }, timestamp }), null)
  })

  it("normalizes tool start/end aliases and payload variants", () => {
    const start = normalizeAgentEvent({
      event: "tool_started",
      data: { tool_call_id: "c1", tool: "write_file", arguments: '{"path":"a.ts"}', session_id: "s1" },
      timestamp,
    })
    if (start?.type !== "tool_start") throw new Error("expected tool_start")
    assert.equal(start.name, "write_file")
    assert.equal(start.toolCallId, "c1")
    assert.deepEqual(start.args, { path: "a.ts" })

    const end = normalizeAgentEvent({
      event: "tool_error",
      data: { call_id: "c1", error: "permission denied", duration_ms: 12 },
      timestamp,
    })
    if (end?.type !== "tool_end") throw new Error("expected tool_end")
    assert.equal(end.status, "error")
    assert.equal(end.error, "permission denied")
    assert.equal(end.durationMs, 12)
  })

  it("does not append non-assistant message_added events", () => {
    const user = normalizeAgentEvent({
      event: "message_added",
      data: { message: { role: "user", content: "hi" } },
      timestamp,
    })
    assert.equal(user, null)

    const assistant = normalizeAgentEvent({
      event: "message_added",
      data: { message: { role: "assistant", content: "hello", id: "m2" } },
      timestamp,
    })
    if (assistant?.type !== "assistant_message") throw new Error("expected assistant_message")
    assert.equal(assistant.content, "hello")
    assert.equal(assistant.messageId, "m2")
    assert.equal(assistant.final, true)
  })
})

class FakeWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3

  readyState = FakeWebSocket.CONNECTING
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  readonly sent: string[] = []

  constructor(readonly url: string) {}

  send(data: string): void {
    this.sent.push(data)
  }

  close(): void {
    this.readyState = FakeWebSocket.CLOSED
    this.onclose?.()
  }

  open(): void {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.()
  }

  receive(event: unknown): void {
    this.onmessage?.({ data: JSON.stringify(event) })
  }
}

function controlledClient(): { client: SyncClient; socket: FakeWebSocket } {
  const sockets: FakeWebSocket[] = []
  class TrackingWebSocket extends FakeWebSocket {
    constructor(url: string) {
      super(url)
      sockets.push(this)
    }
  }
  const client = new SyncClient("ws://127.0.0.1:9/ws/events", "http://127.0.0.1:9", {
    webSocketImpl: TrackingWebSocket as unknown as typeof WebSocket,
  })
  client.connect()
  const socket = sockets[0]
  assert.ok(socket, "transport should have been constructed")
  return { client, socket: socket! }
}

describe("SyncClient mock transport", () => {
  it("emits typed stream events while preserving legacy listeners", () => {
    const { client, socket } = controlledClient()
    const stream: AgentStreamEvent[] = []
    const legacyStates: Array<Record<string, unknown>> = []
    const legacyChat: Array<Record<string, unknown>> = []
    const themes: Array<Record<string, unknown>> = []

    client.onStream((event) => stream.push(event))
    client.on("state", (state) => legacyStates.push(state))
    client.on("chat_complete", (data) => legacyChat.push(data))
    client.on("theme_changed", (data) => themes.push(data))

    socket.open()
    socket.receive({
      event: "connected",
      data: { version: "2.0.0", model: "claude-sonnet-4", agent: "build", cwd: "/repo" },
      timestamp,
    })
    socket.receive({
      event: "assistant_delta",
      data: { session_id: "s1", delta: "Hi", seq: 1 },
      timestamp,
    })
    socket.receive({ event: "pong", data: {}, timestamp })
    socket.receive({
      event: "chat_complete",
      data: { usage: { prompt_tokens: 2, completion_tokens: 1 } },
      timestamp,
    })
    socket.receive({ event: "theme_changed", data: { theme: "nord" }, timestamp })

    assert.equal(client.connected, true)
    assert.deepEqual(stream.map((event) => event.type), [
      "session_state",
      "assistant_delta",
      "chat_complete",
    ])
    assert.equal(legacyStates.length, 1)
    assert.equal(legacyStates[0]!.model, "claude-sonnet-4")
    assert.equal(legacyChat.length, 1)
    assert.deepEqual(themes, [{ theme: "nord" }])

    client.disconnect()
    assert.equal(client.connected, false)
  })

  it("drives the reducer from transport events end-to-end", () => {
    const { client, socket } = controlledClient()
    let state: StreamState = initialStreamState()
    client.onStream((event) => {
      const action = streamActionFromEvent(event)
      if (action) state = streamReducer(state, action)
    })

    socket.open()
    socket.receive({
      event: "assistant_delta",
      data: { session_id: "s1", message_id: "m1", delta: "Checking", seq: 1 },
      timestamp,
    })
    socket.receive({
      event: "tool_started",
      data: { session_id: "s1", tool_call_id: "c1", name: "read_file", args: { path: "a.ts" }, seq: 2 },
      timestamp,
    })
    socket.receive({
      event: "tool_finished",
      data: { session_id: "s1", tool_call_id: "c1", output: "ok", seq: 3 },
      timestamp,
    })
    socket.receive({
      event: "chat_complete",
      data: { usage: { prompt_tokens: 3, completion_tokens: 2 }, seq: 4 },
      timestamp,
    })

    assert.equal(state.messages.length, 1)
    assert.equal(state.messages[0]!.content, "Checking")
    assert.equal(state.messages[0]!.streaming, false)
    assert.equal(state.tools.length, 1)
    assert.equal(state.tools[0]!.name, "read_file")
    assert.equal(state.tools[0]!.status, "success")
    assert.equal(state.tools[0]!.output, "ok")
    assert.equal(state.status, "complete")
    assert.equal(state.session.id, "s1")

    client.disconnect()
  })
})
