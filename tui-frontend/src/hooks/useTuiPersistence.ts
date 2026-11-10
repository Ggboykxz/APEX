"use strict";

/**
 * useTuiPersistence — loads persisted TUI config on mount and writes it back
 * whenever a persisted field changes.
 *
 * Kept separate from ApexApp so the root component stays a layout shell.
 * Persistence is best-effort: a read-only or missing config directory never
 * breaks the TUI.
 */

import { useEffect } from "react"
import { useTuiStore } from "../context/TuiStoreProvider.js"
import { loadTuiConfig, saveTuiConfig } from "../config/tuiConfig.js"
import { setTheme } from "../theme/apex.js"
import type { TuiState } from "../store/tuiStore.js"

export function useTuiPersistence(): void {
  const { state, dispatch } = useTuiStore()

  // ── Load on mount ──────────────────────────────────────────────────
  useEffect(() => {
    const cfg = loadTuiConfig()
    if (cfg.activeTheme) setTheme(cfg.activeTheme)
    if (cfg.activeAgent) dispatch({ type: "SET_ACTIVE_AGENT", payload: cfg.activeAgent })
    if (cfg.activeModel) dispatch({ type: "SET_ACTIVE_MODEL", payload: cfg.activeModel })
    if (cfg.activeTheme) dispatch({ type: "SET_ACTIVE_THEME", payload: cfg.activeTheme })
    if (cfg.sidebarVisible !== undefined)
      dispatch({ type: "SET_SIDEBAR_VISIBLE", payload: cfg.sidebarVisible })
    if (cfg.thinkingMode) dispatch({ type: "SET_THINKING_MODE", payload: cfg.thinkingMode })
  }, [dispatch])

  // ── Persist on change ──────────────────────────────────────────────
  useEffect(() => {
    saveTuiConfig({
      activeAgent: state.activeAgent,
      activeModel: state.activeModel,
      activeTheme: state.activeTheme,
      sidebarVisible: state.sidebarVisible,
      thinkingMode: state.thinkingMode,
      completionFreq: state.completionFreq,
    })
  }, [
    state.activeAgent,
    state.activeModel,
    state.activeTheme,
    state.sidebarVisible,
    state.thinkingMode,
    state.completionFreq,
  ])
}
