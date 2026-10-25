/**
 * Diff preview decision state machine.
 *
 * Accept/reject is a local decision only: this module never writes to disk.
 * Callers receive the decision through `onDecision` and are responsible for
 * forwarding it to a backend endpoint (nothing is wired yet in increment 1).
 */

export type DiffDecision = "accept" | "reject"
export type DiffPreviewStatus = "pending" | "accepted" | "rejected"

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
