/**
 * Diff preview decision state machine tests (accept/reject/reset).
 */

import { describe, it } from "node:test"
import assert from "node:assert/strict"
import {
  createDiffPreviewState,
  DiffPreviewController,
  diffDecisionBanner,
  reduceDiffPreview,
  reduceRejectConfirmation,
  type DiffDecisionResult,
} from "../src/diff/preview.js"

describe("reduceDiffPreview", () => {
  it("starts pending and accepts exactly once", () => {
    let state = createDiffPreviewState()
    assert.equal(state.status, "pending")
    assert.equal(state.decision, undefined)
    assert.equal(state.scrollOffset, 0)

    state = reduceDiffPreview(state, { type: "accept" })
    assert.equal(state.status, "accepted")
    assert.equal(state.decision, "accept")

    const afterSecondAccept = reduceDiffPreview(state, { type: "accept" })
    assert.equal(afterSecondAccept, state)

    const afterReject = reduceDiffPreview(state, { type: "reject" })
    assert.equal(afterReject, state)
  })

  it("rejects and blocks a later accept until reset", () => {
    let state = reduceDiffPreview(createDiffPreviewState(), { type: "reject" })
    assert.equal(state.status, "rejected")
    assert.equal(state.decision, "reject")

    const afterAccept = reduceDiffPreview(state, { type: "accept" })
    assert.equal(afterAccept.status, "rejected")

    state = reduceDiffPreview(state, { type: "reset" })
    assert.equal(state.status, "pending")
    assert.equal(state.decision, undefined)

    state = reduceDiffPreview(state, { type: "accept" })
    assert.equal(state.status, "accepted")
  })

  it("clamps scrolling and file focus", () => {
    let state = createDiffPreviewState()
    state = reduceDiffPreview(state, { type: "scroll", delta: 5, max: 10 })
    assert.equal(state.scrollOffset, 5)
    state = reduceDiffPreview(state, { type: "scroll", delta: 100, max: 10 })
    assert.equal(state.scrollOffset, 10)
    state = reduceDiffPreview(state, { type: "scroll", delta: -100, max: 10 })
    assert.equal(state.scrollOffset, 0)

    state = reduceDiffPreview(state, { type: "focus-file", index: 7, fileCount: 3 })
    assert.equal(state.focusedFile, 2)
    state = reduceDiffPreview(state, { type: "focus-file", index: -2, fileCount: 3 })
    assert.equal(state.focusedFile, 0)
  })
})

describe("reduceRejectConfirmation", () => {
  it("requires a second r before emitting the reject decision", () => {
    const first = reduceRejectConfirmation("idle", "r")
    assert.equal(first.confirmation, "confirm")
    assert.equal(first.decision, undefined)

    const second = reduceRejectConfirmation(first.confirmation, "r")
    assert.equal(second.confirmation, "idle")
    assert.equal(second.decision, "reject")
  })

  it("cancels on any other key and re-arms on a later r", () => {
    const armed = reduceRejectConfirmation("idle", "r")
    assert.equal(armed.confirmation, "confirm")

    const canceled = reduceRejectConfirmation(armed.confirmation, "a")
    assert.equal(canceled.confirmation, "idle")
    assert.equal(canceled.decision, undefined)

    const rearmed = reduceRejectConfirmation(canceled.confirmation, "r")
    assert.equal(rearmed.confirmation, "confirm")
    assert.equal(rearmed.decision, undefined)
  })
})

describe("diffDecisionBanner", () => {
  it("reports applied decisions and transient submission states", () => {
    assert.deepEqual(diffDecisionBanner({ status: "accepted" }), {
      text: "✓ accepted — changes kept",
      tone: "success",
    })
    assert.deepEqual(diffDecisionBanner({ status: "rejected" }), {
      text: "✓ rejected — changes restored",
      tone: "warning",
    })
    assert.equal(
      diffDecisionBanner({ status: "pending", submitting: true }).text,
      "submitting…",
    )
    assert.equal(
      diffDecisionBanner({ status: "pending", error: "HTTP 409" }).text,
      "✗ HTTP 409",
    )
  })

  it("asks for confirmation before rejecting", () => {
    assert.equal(
      diffDecisionBanner({ status: "pending", confirmReject: true }).text,
      "press r again to confirm revert, any other key cancels",
    )
  })
})

describe("DiffPreviewController", () => {
  it("invokes the programmatic callback once per decision", () => {
    const decisions: DiffDecisionResult[] = []
    const controller = new DiffPreviewController(undefined, (result) => decisions.push(result))

    assert.equal(controller.state.status, "pending")
    const accepted = controller.accept()
    assert.equal(accepted.status, "accepted")
    assert.equal(accepted.decision, "accept")
    assert.equal(decisions.length, 1)
    assert.equal(decisions[0]!.decision, "accept")

    controller.accept()
    controller.reject()
    assert.equal(decisions.length, 1)
    assert.equal(controller.state.status, "accepted")

    controller.reset()
    assert.equal(controller.state.status, "pending")
    const rejected = controller.reject()
    assert.equal(rejected.status, "rejected")
    assert.equal(decisions.length, 2)
    assert.equal(decisions[1]!.decision, "reject")

    controller.scroll(50, 20)
    assert.equal(controller.state.scrollOffset, 20)
    controller.focusFile(4, 2)
    assert.equal(controller.state.focusedFile, 1)
  })
})
