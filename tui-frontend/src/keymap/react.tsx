"use strict";

/**
 * React integration for the keymap (OpenTUI `KeymapProvider`/`useBindings`
 * pattern). A `Keymap` instance lives in context; components register layers
 * with `useBindings` for their own lifecycle.
 */

import React, { createContext, useContext, useEffect } from "react"
import { Keymap } from "./engine.js"
import type { KeymapLayer } from "./types.js"

interface KeymapContextValue {
  keymap: Keymap | null
}

const KeymapContext = createContext<KeymapContextValue>({ keymap: null })

export function KeymapProvider({ keymap, children }: { keymap: Keymap | null; children: React.ReactNode }) {
  return <KeymapContext.Provider value={{ keymap }}>{children}</KeymapContext.Provider>
}

/** The current keymap, or null before it is created. */
export function useKeymap(): Keymap | null {
  return useContext(KeymapContext).keymap
}

/** Register a layer for the lifetime of the component. */
export function useBindings(createLayer: () => KeymapLayer, deps: readonly unknown[] = []): void {
  const keymap = useKeymap()
  useEffect(() => {
    if (!keymap) return
    return keymap.register(createLayer())
  }, [keymap, createLayer, ...deps])
}
