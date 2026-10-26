/**
 * Diff preview decision state machine.
 *
 * Accept/reject is a local decision: this module never writes to disk.
 * Callers receive the decision through `onDecision` and forward it to the
 * backend decision endpoint (`POST .../diff/decision`).
 */

export type DiffDecision = "accept" | "reject"
export type DiffPreviewStatus = "pending" | "accepted" | "rejected"

export type DiffBannerTone = "error" | "warning" | "success" | "muted"

export interface DiffBanner {
  text: string
  tone: DiffBannerTone
}

/**
 * Banner shown under the diff. Kept pure so the overlay text is covered by
 * tests without rendering Ink.
 */
export function diffDecisionBanner(options: {
  status: DiffPreviewStatus
  confirmReject?: boolean
  submitting?: boolean
  error?: string
}): DiffBanner {
  if (options.error) return { text: `✗ ${options.error}`, tone: "error" }
  if (options.submitting) return { text: "submitting…", tone: "warning" }
  if (options.status === "accepted") {
    return { text: "✓ accepted — changes kept", tone: "success" }
  }
  if (options.status === "rejected") {
    return { text: "✓ rejected — changes restored", tone: "warning" }
  }
  if (options.confirmReject) {
    return {
      text: "press r again to confirm revert, any other key cancels",
      tone: "warning",
    }
  }
  return {
    text: "a accept · r reject (confirm) · ↑↓ scroll · PgUp/PgDn page",
    tone: "muted",
  }
}

export interface DiffPreviewState {
  status: DiffPreviewStatus
  decision?: DiffDecision
  /** Vertical line offset in the flattened rendered diff. */
  scrollOffset: number
  /** Index of the focused file (for future per-file decisions). */
  focusedFile: number
}

export type DiffPreviewAction =
  | { type: "accept" }
  | { type: "reject" }
  | { type: "reset" }
  | { type: "scroll"; delta: number; max?: number }
  | { type: "focus-file"; index: number; fileCount?: number }

export function createDiffPreviewState(): DiffPreviewState {
  return { status: "pending", scrollOffset: 0, focusedFile: 0 }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** Pure transition function; decisions are terminal until `reset`. */
export function reduceDiffPreview(
  state: DiffPreviewState,
  action: DiffPreviewAction,
): DiffPreviewState {
  switch (action.type) {
    case "accept":
      return state.status === "pending"
        ? { ...state, status: "accepted", decision: "accept" }
        : state
    case "reject":
      return state.status === "pending"
        ? { ...state, status: "rejected", decision: "reject" }
        : state
    case "reset":
      return createDiffPreviewState()
    case "scroll": {
      const max = action.max ?? Number.MAX_SAFE_INTEGER
      return { ...state, scrollOffset: clamp(state.scrollOffset + action.delta, 0, max) }
    }
    case "focus-file": {
      const max = action.fileCount === undefined ? Number.MAX_SAFE_INTEGER : Math.max(0, action.fileCount - 1)
      return { ...state, focusedFile: clamp(action.index, 0, max) }
    }
    default:
      return state
  }
}

export interface DiffDecisionResult {
  decision: DiffDecision
  status: DiffPreviewStatus
}

export type DiffRejectConfirmation = "idle" | "confirm"

export interface DiffRejectKeyResult {
  confirmation: DiffRejectConfirmation
  decision?: DiffDecision
}

/**
 * Two-step keyboard confirmation for destructive rejects: the first `r` arms
 * the confirmation, a second `r` emits the decision, and any other key
 * cancels without emitting.
 */
export function reduceRejectConfirmation(
  confirmation: DiffRejectConfirmation,
  input: string,
): DiffRejectKeyResult {
  if (confirmation === "confirm") {
    return input === "r"
      ? { confirmation: "idle", decision: "reject" }
      : { confirmation: "idle" }
  }
  return { confirmation: input === "r" ? "confirm" : "idle" }
}

/**
 * Programmatic controller: consumes the same pure reducer as the Ink
 * component, so key presses and external calls cannot diverge.
 */
export class DiffPreviewController {
  private current: DiffPreviewState

  constructor(
    initial: DiffPreviewState = createDiffPreviewState(),
    private readonly onDecision?: (result: DiffDecisionResult) => void,
  ) {
    this.current = initial
  }

  get state(): DiffPreviewState {
    return this.current
  }

  accept(): DiffDecisionResult {
    return this.decide("accept")
  }

  reject(): DiffDecisionResult {
    return this.decide("reject")
  }

  reset(): void {
    this.current = reduceDiffPreview(this.current, { type: "reset" })
  }

  scroll(delta: number, max?: number): DiffPreviewState {
    this.current = reduceDiffPreview(this.current, { type: "scroll", delta, max })
    return this.current
  }

  focusFile(index: number, fileCount?: number): DiffPreviewState {
    this.current = reduceDiffPreview(this.current, { type: "focus-file", index, fileCount })
    return this.current
  }

  private decide(decision: DiffDecision): DiffDecisionResult {
    const type = decision === "accept" ? "accept" : "reject"
    const wasPending = this.current.status === "pending"
    this.current = reduceDiffPreview(this.current, { type })
    const result: DiffDecisionResult = { decision, status: this.current.status }
    if (wasPending) this.onDecision?.(result)
    return result
  }
}
