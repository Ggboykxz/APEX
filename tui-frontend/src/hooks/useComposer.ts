"use strict";

/**
 * useComposer — computes the frecency-ranked autocomplete list for the
 * composer input.
 *
 * When the user types "/" (commands) or "@" (files / agents) at the end of a
 * word, the hook ranks candidates by usage frequency then alphabetically and
 * dispatches `SET_COMPLETION`. Otherwise it hides the list.
 *
 * OpenCode equivalent: the textarea's autocomplete popup (frecency-based).
 */

import { useEffect } from "react"
import { APEX_AGENTS, APEX_MODELS } from "../data/apex-data.js"
import {
  rankByFrecency,
  type CompletionItem,
  type TuiDispatch,
} from "../store/tuiStore.js"

interface UseComposerProps {
  inputValue: string
  dispatch: TuiDispatch
  /** Command-palette entries already filtered by the current query. */
  commands: { id: string; desc: string }[]
  /** Themes known to the store. */
  themes: { id: string; name: string }[]
  /** Sessions known to the store. */
  sessions: { id: string; name: string; model?: string }[]
}

/** The word under the cursor, if it starts with a completion trigger. */
export function currentTrigger(value: string): { trigger: "/" | "@"; prefix: string } | null {
  const match = value.match(/([/@])([\w./-]*)$/)
  if (!match) return null
  return { trigger: match[1] as "/" | "@", prefix: match[2] }
}

export function useComposer({
  inputValue,
  dispatch,
  commands,
  themes,
  sessions,
}: UseComposerProps) {
  useEffect(() => {
    const hit = currentTrigger(inputValue)
    if (!hit) {
      dispatch({ type: "SET_COMPLETION", payload: { visible: false, trigger: "/", prefix: "", items: [] } })
      return
    }

    let items: CompletionItem[] = []

    if (hit.trigger === "/") {
      items = commands.map((c) => ({
        label: c.id,
        value: c.id,
        kind: "command" as const,
      }))
    } else {
      // "@": files are listed by the file finder overlay; here we surface
      // agents and models as quick mentions.
      items = [
        ...APEX_AGENTS.map((a) => ({ label: `@${a.id}`, value: `@${a.id}`, kind: "agent" as const })),
        ...APEX_MODELS.map((m) => ({ label: `@${m.id}`, value: `@${m.id}`, kind: "model" as const })),
        ...themes.map((t) => ({ label: `/theme ${t.id}`, value: `/theme ${t.id}`, kind: "theme" as const })),
        ...sessions.map((s) => ({ label: `/session ${s.id}`, value: `/session ${s.id}`, kind: "session" as const })),
      ]
    }

    // Filter to items matching the prefix (after the trigger).
    const needle = hit.prefix
    items = items.filter((item) => item.value.toLowerCase().includes(needle.toLowerCase()))

    items = rankByFrecency(items, {})

    dispatch({
      type: "SET_COMPLETION",
      payload: {
        visible: items.length > 0,
        trigger: hit.trigger,
        prefix: needle,
        items,
        index: 0,
      },
    })
  }, [inputValue, dispatch, commands, themes, sessions])
}
