/**
 * Pure TUI store tests — no React, no Ink.
 *
 * The viewport rules are the interesting part: `<Static>` is append-only, so
 * the committed boundary must be monotonic and must freeze while the user is
 * scrolled up.
 */

import { describe, it } from "node:test"
import assert from "node:assert/strict"
import {
  initialTuiState,
  tuiReducer,
  LIVE_WINDOW,
} from "../src/store/tuiStore.js"
import type { ChatMessage } from "../src/data/apex-data.js"
import type { StreamToolCall } from "../src/streaming/reducer.js"

function message(index: number): ChatMessage {
  return {
    id: `m-${index}`,
    role: index % 2 === 0 ? "user" : "assistant",
    content: `msg ${index}`,
    timestamp: index,
  }
}

function messages(count: number, offset = 0): ChatMessage[] {
  return Array.from({ length: count }, (_, i) => message(offset + i))
}

function tool(index: number, overrides: Partial<StreamToolCall> = {}): StreamToolCall {
  return {
    id: `t-${index}`,
    name: `tool_${index}`,
    status: "success",
    startedAt: index,
    ...overrides,
  }
}

describe("tuiReducer viewport", () => {
  it("tails by default with nothing committed", () => {
    assert.equal(initialTuiState.tail, true)
    assert.equal(initialTuiState.committedCount, 0)
  })

  it("keeps the live window bounded while tailing", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(LIVE_WINDOW + 5) })

    assert.equal(state.messages.length, LIVE_WINDOW + 5)
    assert.equal(state.committedCount, 5)
  })

  it("freezes the committed boundary when the user scrolls up", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(LIVE_WINDOW + 5) })
    state = tuiReducer(state, { type: "SET_TAIL", payload: false })

    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(5, 100) })

    assert.equal(state.messages.length, LIVE_WINDOW + 10)
    assert.equal(state.committedCount, 5)
  })

  it("catches up when the user returns to the bottom", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(LIVE_WINDOW + 5) })
    state = tuiReducer(state, { type: "SET_TAIL", payload: false })
    state = tuiReducer(state, { type: "ADD_MESSAGE", payload: message(99) })
    state = tuiReducer(state, { type: "SET_TAIL", payload: true })

    assert.equal(state.committedCount, state.messages.length - LIVE_WINDOW)
  })

  it("resets the boundary on CLEAR_MESSAGES", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(LIVE_WINDOW * 2) })
    assert.equal(state.committedCount, LIVE_WINDOW)

    state = tuiReducer(state, { type: "CLEAR_MESSAGES" })

    assert.equal(state.committedCount, 0)
    assert.equal(state.messages.length, 0)
  })

  it("resets the viewport on RESET_SESSION", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(LIVE_WINDOW * 2) })
    state = tuiReducer(state, { type: "SET_TAIL", payload: false })

    state = tuiReducer(state, { type: "RESET_SESSION" })

    assert.equal(state.committedCount, 0)
    assert.equal(state.tail, true)
    assert.equal(state.messages.length, 0)
  })

  it("bumps the static epoch so a cleared transcript remounts <Static>", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(5) })

    state = tuiReducer(state, { type: "CLEAR_MESSAGES" })
    assert.equal(state.staticEpoch, 1)

    state = tuiReducer(state, { type: "ADD_MESSAGES", payload: messages(5) })
    state = tuiReducer(state, { type: "RESET_SESSION" })
    assert.equal(state.staticEpoch, 2)
    assert.equal(state.committedCount, 0)
  })
})

describe("tuiReducer tool expansion", () => {
  it("collapses a tool that disappears", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "SET_TOOLS", payload: [tool(1)] })
    state = tuiReducer(state, { type: "SET_EXPANDED_TOOL", payload: "t-1" })
    assert.equal(state.expandedToolId, "t-1")

    state = tuiReducer(state, { type: "SET_TOOLS", payload: [] })

    assert.equal(state.expandedToolId, null)
  })

  it("keeps a tool expanded while it is still present", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "SET_TOOLS", payload: [tool(1), tool(2)] })
    state = tuiReducer(state, { type: "SET_EXPANDED_TOOL", payload: "t-1" })

    state = tuiReducer(state, {
      type: "SET_TOOLS",
      payload: [tool(1), tool(2, { status: "running" })],
    })

    assert.equal(state.expandedToolId, "t-1")
  })

  it("clears the expanded tool explicitly", () => {
    let state = initialTuiState
    state = tuiReducer(state, { type: "SET_EXPANDED_TOOL", payload: "t-9" })
    state = tuiReducer(state, { type: "SET_EXPANDED_TOOL", payload: null })

    assert.equal(state.expandedToolId, null)
  })
})
