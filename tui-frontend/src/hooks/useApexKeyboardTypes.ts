"use strict";

/**
 * Types for useApexKeyboard — the deps bundle the hook consumes and the
 * overlay navigation spec table. Kept in their own file so the hook stays
 * focused on wiring the keymap layers.
 */

import type { TuiDispatch, TuiState, OverlayIndex, OverlaySearch, OverlayState } from "../store/tuiStore.js"

/** One row of the overlay navigation table (palette, selectors, help…). */
export interface OverlaySpec {
  /** Overlay state key this spec drives (e.g. `showCP`). */
  name: keyof OverlayState
  /** Which overlayIndex entry the selection cursor lives in; null for non-list overlays. */
  indexKey: keyof OverlayIndex | null
  /** Which overlaySearch entry holds the filter text; null when there is none. */
  searchKey: keyof OverlaySearch | null
  /** Number of listable entries; 0 disables selection for informational overlays. */
  count: number
  /** Whether the cursor wraps around the edges. */
  wrap: boolean
  /** Called with the selected index on Enter. */
  select: (index: number) => void
}

export interface ApexKeyboardDeps {
  state: TuiState
  dispatch: TuiDispatch
  /** The palette items (filtered commands). */
  commands: { id: string; desc: string }[]
  sendMessage: (text: string) => Promise<unknown>
  /** Submit a user message (wraps handleSubmit). */
  submit: (text: string) => void
  exit: () => void
  retryConnection: () => void
  sendEditorPrompt: () => void
  sendBash: (cmd: string) => Promise<unknown> | void
  completion: TuiState["completion"]
  selectCompletion: (value: string) => void
  /** Optional client for overlay data that loads lazily (themes, sessions). */
  api?: {
    listThemes(): Promise<{ id: string; name: string }[]>
    listSessions(): Promise<{ id: string; name: string; model?: string }[]>
  }
}
