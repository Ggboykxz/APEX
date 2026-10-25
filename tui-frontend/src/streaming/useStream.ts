/**
 * React adapters for the pure streaming reducer.
 *
 * App.tsx can either feed the reducer from the WebSocket client (`useSyncStream`)
 * or from the existing SSE `onChunk` callback (`applyCumulativeAssistantText`).
 * Both paths share exactly the same state machine, so the HTTP fallback keeps
 * working when no WebSocket is available.
 */

import { useCallback, useEffect, useReducer, useRef } from "react"
import type { Dispatch } from "react"
import type { AgentStreamEvent } from "../types.js"
import type { SyncClient } from "../sync.js"
import {
  applyCumulativeAssistantText,
  getCurrentAssistant,
  getRunningTools,
  initialStreamState,
  streamActionFromEvent,
  streamReducer,
  type StreamAction,
  type StreamSession,
  type StreamState,
} from "./reducer.js"

export interface StreamingStateApi {
  state: StreamState
  dispatch: Dispatch<StreamAction>
  reset: (session?: Partial<StreamSession>, seq?: number) => void
  appendDelta: (delta: string, options?: { messageId?: string; sessionId?: string }) => void
  applyCumulative: (full: string, options?: { messageId?: string; sessionId?: string }) => void
  startTool: (name: string, id?: string, args?: Record<string, unknown>) => void
  endTool: (id: string | undefined, options?: { name?: string; output?: string; error?: string; durationMs?: number }) => void
  finalize: (messageId?: string, content?: string) => void
  complete: () => void
}

export function useStreamingState(sessionId?: string): StreamingStateApi {
  const [state, dispatch] = useReducer(streamReducer, undefined, () => initialStreamState(sessionId))
  // SSE `onChunk` can fire several times before React commits a render, so the
  // cumulative snapshot must be tracked synchronously in a ref.
  const cumulativeRef = useRef<{ messageId?: string; text: string }>({ text: "" })

  const reset = useCallback(
    (session?: Partial<StreamSession>, seq?: number) => {
      cumulativeRef.current = { text: "" }
      dispatch({ type: "session/reset", session, seq })
    },
    [],
  )
  const appendDelta = useCallback(
    (delta: string, options: { messageId?: string; sessionId?: string } = {}) => {
      cumulativeRef.current = {
        messageId: options.messageId ?? cumulativeRef.current.messageId,
        text: cumulativeRef.current.text + delta,
      }
      dispatch({ type: "assistant/delta", delta, ...options })
    },
    [],
  )
  const applyCumulative = useCallback(
    (full: string, options: { messageId?: string; sessionId?: string } = {}) => {
      const previous = cumulativeRef.current
      if (
        options.messageId !== undefined &&
        previous.messageId !== undefined &&
        options.messageId !== previous.messageId
      ) {
        previous.text = ""
      }
      if (full.startsWith(previous.text)) {
        const delta = full.slice(previous.text.length)
        if (delta.length > 0) {
          dispatch({ type: "assistant/delta", delta, ...options })
        }
      } else {
        dispatch({ type: "assistant/message", content: full, final: false, ...options })
      }
      cumulativeRef.current = {
        messageId: options.messageId ?? previous.messageId,
        text: full,
      }
    },
    [],
  )
  const startTool = useCallback(
    (name: string, id?: string, args?: Record<string, unknown>) =>
      dispatch({ type: "tool/start", name, toolCallId: id, args }),
    [],
  )
  const endTool = useCallback(
    (
      id: string | undefined,
      options: { name?: string; output?: string; error?: string; durationMs?: number } = {},
    ) => dispatch({ type: "tool/end", toolCallId: id, ...options }),
    [],
  )
  const finalize = useCallback(
    (messageId?: string, content?: string) =>
      dispatch({ type: "assistant/finalize", messageId, content }),
    [],
  )
  const complete = useCallback(() => dispatch({ type: "session/complete" }), [])

  return { state, dispatch, reset, appendDelta, applyCumulative, startTool, endTool, finalize, complete }
}

/** Subscribe a `SyncClient` to the streaming reducer. */
export function useSyncStream(client: SyncClient | null, dispatch: Dispatch<StreamAction>): void {
  useEffect(() => {
    if (!client) return
    const handler = (event: AgentStreamEvent) => {
      const action = streamActionFromEvent(event)
      if (action) dispatch(action)
    }
    client.onStream(handler)
    return () => client.offStream(handler)
  }, [client, dispatch])
}

/**
 * Convenience adapter for the SSE path: a cumulative snapshot is converted to
 * the smallest delta/replacement action before entering the reducer.
 */
export function applySseSnapshot(
  state: StreamState,
  full: string,
  options: { messageId?: string; sessionId?: string } = {},
): StreamState {
  return applyCumulativeAssistantText(state, full, options)
}

export { getCurrentAssistant, getRunningTools }
