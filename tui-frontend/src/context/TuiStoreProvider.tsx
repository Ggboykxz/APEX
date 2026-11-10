"use strict";

/**
 * TuiStoreProvider — React context holding the single TUI store.
 *
 * Components consume `useTuiStore()` to read `state` and call `dispatch`.
 * One source of truth for the whole TUI (OpenCode SyncProvider pattern).
 */

import React, { createContext, useContext, useReducer } from "react"
import type { TuiAction, TuiDispatch, TuiState } from "../store/tuiStore.js"
import { initialTuiState, tuiReducer } from "../store/tuiStore.js"

const TuiContext = createContext<{ state: TuiState; dispatch: TuiDispatch } | null>(null)

export function TuiStoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(tuiReducer, initialTuiState)
  return (
    <TuiContext.Provider value={{ state, dispatch }}>
      {children}
    </TuiContext.Provider>
  )
}

export function useTuiStore() {
  const ctx = useContext(TuiContext)
  if (!ctx) {
    throw new Error("useTuiStore must be used within a TuiStoreProvider")
  }
  return ctx
}
