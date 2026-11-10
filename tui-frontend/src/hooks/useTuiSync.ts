"use strict";

/**
 * useTuiSync — binds the WebSocket sync client to the central TUI store.
 *
 * Every backend event becomes a reducer action (OpenCode SyncProvider pattern).
 * Streaming events feed the pure streaming reducer so tool lifecycle is
 * reconciled in one place; the resulting tool list is mirrored into the store,
 * which is the single source of truth the tool cards render from.
 */

import { useCallback, useEffect } from "react"
import type { AgentStreamEvent } from "../types.js"
import { SyncClient } from "../sync.js"
import { api } from "../api/client.js"
import { useStreamingState } from "../streaming/useStream.js"
import { streamActionFromEvent } from "../streaming/reducer.js"
import type { TuiDispatch, TuiState } from "../store/tuiStore.js"

interface UseTuiSyncProps {
  dispatch: TuiDispatch
  getState: () => TuiState
}

export function useTuiSync({ dispatch, getState }: UseTuiSyncProps) {
  const { state: streamState, dispatch: dispatchStream } = useStreamingState()

  // The tool list is the only streaming projection the chat surface needs;
  // assistant text arrives through the HTTP SSE path in useChat.
  useEffect(() => {
    dispatch({ type: "SET_TOOLS", payload: streamState.tools })
  }, [dispatch, streamState.tools])

  const connect = useCallback(() => {
    const port = Number(process.env.APEX_HTTP_PORT ?? "0") || 8765
    if (!port) return

    const sync = new SyncClient(api.wsUrl, api.baseUrl)

    sync.on("connected", () => {
      dispatch({ type: "SET_CONNECTION_ERROR", payload: null })
      dispatch({ type: "SET_IS_RECONNECTING", payload: false })
    })

    sync.on("disconnected", () => {
      dispatch({ type: "SET_CONNECTION_ERROR", payload: "WebSocket disconnected — reconnecting..." })
      dispatch({ type: "SET_IS_RECONNECTING", payload: true })
    })

    sync.on("state", (state: unknown) => {
      const s = state as { model?: string; agent?: string }
      if (s.model) dispatch({ type: "SET_ACTIVE_MODEL", payload: s.model })
      if (s.agent) dispatch({ type: "SET_ACTIVE_AGENT", payload: s.agent })
    })

    sync.on("chat_complete", () => {
      dispatch({ type: "SET_IS_RECONNECTING", payload: false })
      dispatch({ type: "SET_RETRY_COUNT", payload: 0 })
    })

    const onStream = (event: AgentStreamEvent) => {
      const action = streamActionFromEvent(event)
      if (action) dispatchStream(action)
    }
    sync.onStream(onStream)

    sync.connect()
    return () => {
      sync.offStream(onStream)
      sync.disconnect()
    }
  }, [dispatch, getState, dispatchStream])

  useEffect(() => {
    const cleanup = connect()
    return cleanup
  }, [connect])
}
