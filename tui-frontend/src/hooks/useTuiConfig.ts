"use strict";

/**
 * useTuiConfig — fetches TUI configuration from the backend and exposes it
 * as a global `__TUI_CONFIG__` for backward compatibility with keybinds.
 */

import { useCallback, useEffect, useState } from "react"
import { api } from "../api/client.js"
import type { TuiConfig } from "../types.js"

export function useTuiConfig() {
  const [config, setConfig] = useState<TuiConfig | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchConfig = useCallback(async () => {
    try {
      const cfg = await api.getTuiConfig()
      setConfig(cfg)
      setError(null)
      try {
        ;(globalThis as any).__TUI_CONFIG__ = cfg
      } catch {}
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "TUI config unavailable"
      )
    }
  }, [])

  useEffect(() => {
    void (async () => {
      await fetchConfig()
    })()
  }, [fetchConfig])

  return { config, error, refetch: fetchConfig }
}
