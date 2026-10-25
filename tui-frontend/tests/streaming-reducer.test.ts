/**
 * Pure streaming reducer tests — no server, no React, injected clock.
 */

import { describe, it } from "node:test"
import assert from "node:assert/strict"
import {
  applyCumulativeAssistantText,
  getCurrentAssistant,
  getRunningTools,
  getStreamSummary,
  initialStreamState,
  streamReducer,
  type StreamState,
} from "../src/streaming/reducer.js"

const T0 = 1_700_000_000_000

describe("streamReducer", () => {
  it("appends assistant deltas to one draft and updates timestamps", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, {
      type: "assistant/delta",
      delta: "Hel",
      sessionId: "session-a",
      seq: 1,
      now: T0,
    })
    state = streamReducer(state, {
      type: "assistant/delta",
      delta: "lo",
      sessionId: "session-a",
      seq: 2,
      now: T0 + 25,
    })

    assert.equal(state.messages.length, 1)
    assert.equal(state.messages[0]!.content, "Hello")
    assert.equal(state.messages[0]!.startedAt, T0)
    assert.equal(state.messages[0]!.updatedAt, T0 + 25)
    assert.equal(state.status, "streaming")
    assert.equal(getCurrentAssistant(state)?.content, "Hello")
    assert.equal(state.lastSeq, 2)
  })

  it("finalizes the assistant draft on chat completion", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, { type: "assistant/delta", delta: "done", seq: 1, now: T0 })
    state = streamReducer(state, { type: "session/complete", seq: 2, now: T0 + 10 })

    assert.equal(state.status, "complete")
    assert.equal(state.messages[0]!.streaming, false)
    assert.equal(state.messages[0]!.content, "done")
  })

  it("tracks a tool from start to success with output and duration", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, { type: "assistant/delta", delta: "Checking…", seq: 1, now: T0 })
    state = streamReducer(state, {
      type: "tool/start",
      toolCallId: "call-1",
      name: "read_file",
      args: { path: "src/app.ts" },
      seq: 2,
      now: T0 + 100,
    })

    assert.equal(state.status, "tool")
    assert.equal(state.tools.length, 1)
    assert.equal(state.tools[0]!.status, "running")
    assert.deepEqual(getRunningTools(state).map((tool) => tool.name), ["read_file"])

    state = streamReducer(state, {
      type: "tool/end",
      toolCallId: "call-1",
      output: "file contents",
      seq: 3,
      now: T0 + 350,
    })

    assert.equal(state.tools[0]!.status, "success")
    assert.equal(state.tools[0]!.output, "file contents")
    assert.equal(state.tools[0]!.endedAt, T0 + 350)
    assert.equal(state.tools[0]!.durationMs, 250)
    assert.equal(getRunningTools(state).length, 0)
    assert.equal(state.status, "streaming")
  })

  it("marks tool errors and synthesizes an end whose start was missed", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, {
      type: "tool/end",
      toolCallId: "call-lost",
      name: "bash",
      error: "command failed",
      now: T0,
    })

    assert.equal(state.tools.length, 1)
    assert.equal(state.tools[0]!.status, "error")
    assert.equal(state.tools[0]!.error, "command failed")
    assert.equal(state.tools[0]!.durationMs, 0)
    assert.equal(state.status, "idle")

    state = streamReducer(state, {
      type: "tool/start",
      toolCallId: "call-2",
      name: "grep",
      now: T0 + 1,
    })
    state = streamReducer(state, {
      type: "tool/end",
      toolCallId: "call-2",
      error: "bad regex",
      now: T0 + 5,
    })
    assert.equal(state.tools[1]!.status, "error")
    assert.equal(state.tools[1]!.durationMs, 4)
  })

  it("resets all state and isolates a previous session", () => {
    let state = initialStreamState("session-old")
    state = streamReducer(state, { type: "assistant/delta", delta: "old", seq: 5, now: T0 })
    state = streamReducer(state, { type: "tool/start", toolCallId: "old-tool", name: "read_file", now: T0 })

    state = streamReducer(state, {
      type: "session/reset",
      session: { id: "session-new", model: "gpt-5", agent: "build" },
      seq: 1,
      now: T0 + 1000,
    })

    assert.equal(state.messages.length, 0)
    assert.equal(state.tools.length, 0)
    assert.equal(state.session.id, "session-new")
    assert.equal(state.session.model, "gpt-5")
    assert.equal(state.status, "idle")

    const afterOldEvent = streamReducer(state, {
      type: "assistant/delta",
      delta: "stale",
      sessionId: "session-old",
      seq: 6,
    })
    assert.equal(afterOldEvent, state)
    assert.equal(afterOldEvent.messages.length, 0)
  })

  it("ignores duplicate and out-of-order sequence numbers", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, { type: "assistant/delta", delta: "two", seq: 2, now: T0 })
    const duplicate = streamReducer(state, {
      type: "assistant/delta",
      delta: "dup",
      seq: 2,
      now: T0 + 1,
    })
    assert.equal(duplicate, state)

    const stale = streamReducer(state, {
      type: "assistant/delta",
      delta: "one",
      seq: 1,
      now: T0 + 2,
    })
    assert.equal(stale, state)

    state = streamReducer(state, { type: "assistant/delta", delta: "three", seq: 3, now: T0 + 3 })
    assert.equal(state.messages[0]!.content, "twothree")
    assert.equal(state.lastSeq, 3)
  })

  it("applies partial session state without erasing known fields", () => {
    let state = initialStreamState()
    state = streamReducer(state, {
      type: "session/state",
      session: { model: "claude-sonnet-4", agent: "plan", historyLength: 4, undoAvailable: true },
      seq: 1,
      now: T0,
    })
    state = streamReducer(state, {
      type: "session/state",
      session: { id: "s-1", redoAvailable: false },
      seq: 2,
      now: T0 + 1,
    })

    assert.equal(state.session.id, "s-1")
    assert.equal(state.session.model, "claude-sonnet-4")
    assert.equal(state.session.agent, "plan")
    assert.equal(state.session.historyLength, 4)
    assert.equal(state.session.undoAvailable, true)
    assert.equal(state.session.redoAvailable, false)
  })

  it("converts cumulative SSE snapshots into deltas and handles rewrites", () => {
    let state = initialStreamState("session-a")
    state = applyCumulativeAssistantText(state, "Hello", { now: T0 })
    state = applyCumulativeAssistantText(state, "Hello world", { now: T0 + 1 })
    assert.equal(state.messages[0]!.content, "Hello world")
    assert.equal(state.messages.length, 1)

    state = applyCumulativeAssistantText(state, "Rewritten", { now: T0 + 2 })
    assert.equal(state.messages[0]!.content, "Rewritten")
    assert.equal(state.messages.length, 1)
  })

  it("reports a concise activity summary", () => {
    let state = initialStreamState("session-a")
    state = streamReducer(state, {
      type: "assistant/delta",
      delta: "abc",
      seq: 1,
      now: T0,
    })
    state = streamReducer(state, { type: "tool/start", name: "bash", now: T0 + 1 })
    state = streamReducer(state, {
      type: "tool/start",
      toolCallId: "failed",
      name: "write_file",
      now: T0 + 2,
    })
    state = streamReducer(state, {
      type: "tool/end",
      toolCallId: "failed",
      error: "denied",
      now: T0 + 3,
    })

    const summary = getStreamSummary(state)
    assert.equal(summary.status, "tool")
    assert.equal(summary.assistantChars, 3)
    assert.equal(summary.runningTools, 1)
    assert.equal(summary.failedTools, 1)
  })
})
