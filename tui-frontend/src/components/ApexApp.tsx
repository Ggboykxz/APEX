"use strict";

/**
 * ApexApp — root TUI component.
 *
 * Deliberately a layout shell: it reads the central store, wires the
 * side-effecting hooks (chat, WebSocket sync, keyboard) and renders the
 * surfaces. Every key binding lives in `useApexKeyboard`; every modal surface
 * in `OverlayLayers`; all state transitions go through the store reducer.
 */

import React, { useCallback, useEffect } from "react"
import { Box, Text, useApp } from "ink"
import { ChatPanel } from "./ChatPanel.js"
import { StatusBar } from "./StatusBar.js"
import { Sidebar } from "./Sidebar.js"
import { StatusHeader } from "./StatusHeader.js"
import { ConnectionError } from "./ConnectionError.js"
import { LeaderKeys } from "./LeaderKeys.js"
import { OverlayLayers } from "./OverlayLayers.js"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"
import { api } from "../api/client.js"
import type { DiffDecision } from "../diff/preview.js"
import { useChat, type SlashResult } from "../hooks/useChat.js"
import { useComposer, currentTrigger } from "../hooks/useComposer.js"
import { useApexKeyboard } from "../hooks/useApexKeyboard.js"
import { useTuiStore } from "../context/TuiStoreProvider.js"
import { KeymapProvider } from "../keymap/react.js"
import { useTuiSync } from "../hooks/useTuiSync.js"
import { useTuiPersistence } from "../hooks/useTuiPersistence.js"
import type { TuiDispatch, TuiState } from "../store/tuiStore.js"
import { selectToasts } from "../store/tuiStore.js"
import { Autocomplete } from "./Autocomplete.js"
import { Toasts } from "./Toast.js"

const DEFAULT_LEADER_TIMEOUT = 2000
const ERROR_AUTO_DISMISS_MS = 5000

// ────────────────────────── derived values ──────────────────────────

function formatDuration(startedAt: number): string {
  const elapsed = Math.floor((Date.now() - startedAt) / 1000)
  const minutes = Math.floor(elapsed / 60)
  return `${minutes}:${(elapsed % 60).toString().padStart(2, "0")}`
}

function contextPercentage(totalTokens: number, contextWindow: number | undefined): number {
  if (!contextWindow) return 0
  return Math.min(100, (totalTokens / contextWindow) * 100)
}

function hasVisibleOverlay(overlays: TuiState["overlays"]): boolean {
  return Object.values(overlays).some(Boolean)
}

// ────────────────────────── leader commands ──────────────────────────

interface CommandContext {
  dispatch: TuiDispatch
  exit: () => void
  sendMessage: (text: string) => Promise<unknown>
  sendEditorPrompt: () => void
  sendCost: () => Promise<unknown>
  messages: ChatMessage[]
  state: TuiState
}

function openModelSelector(ctx: CommandContext): void {
  const { dispatch, state } = ctx
  dispatch({ type: "SET_OVERLAY", payload: { name: "showMS", visible: true } })
  dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: "msSearch", value: "" } })
  dispatch({
    type: "SET_OVERLAY_INDEX",
    payload: {
      name: "msIdx",
      index: Math.max(0, APEX_MODELS.findIndex((model) => model.id === state.activeModel)),
    },
  })
}

function openThemeSelector(ctx: CommandContext): void {
  const { dispatch } = ctx
  void api.listThemes().then((themes) => dispatch({ type: "SET_THEMES", payload: themes })).catch(() => {})
  dispatch({ type: "SET_OVERLAY", payload: { name: "showTS", visible: true } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "tsIdx", index: 0 } })
}

function openAgentSelector(ctx: CommandContext): void {
  const { dispatch, state } = ctx
  dispatch({ type: "SET_OVERLAY", payload: { name: "showAS", visible: true } })
  dispatch({
    type: "SET_OVERLAY_INDEX",
    payload: {
      name: "asIdx",
      index: APEX_AGENTS.findIndex((agent) => agent.id === state.activeAgent),
    },
  })
}

function openSessionList(ctx: CommandContext): void {
  const { dispatch } = ctx
  void api.listSessions().then((sessions) => dispatch({ type: "SET_SESSIONS", payload: sessions })).catch(() => {})
  dispatch({ type: "SET_OVERLAY", payload: { name: "showSL", visible: true } })
  dispatch({ type: "SET_OVERLAY_INDEX", payload: { name: "slIdx", index: 0 } })
}

// ────────────────────────── slash results ──────────────────────────

async function openDiffPreview(ctx: CommandContext): Promise<void> {
  const { dispatch } = ctx
  dispatch({ type: "SET_CONNECTION_ERROR", payload: "Loading working-tree diff…" })
  try {
    const diff = await api.sessionDiff(ctx.state.activeSession || "current")
    if (diff.error) {
      dispatch({ type: "SET_CONNECTION_ERROR", payload: `Diff error: ${diff.error}` })
      return
    }
    dispatch({
      type: "SET_DIFF",
      payload: { diff: diff.diff ?? "", fingerprint: diff.fingerprint ?? "", paths: diff.paths ?? [] },
    })
    dispatch({ type: "SET_DIFF_SUBMITTING", payload: false })
    dispatch({ type: "SET_OVERLAY", payload: { name: "showDiff", visible: true } })
  } catch {
    dispatch({ type: "SET_CONNECTION_ERROR", payload: "Diff request failed — backend unreachable" })
  }
}

function copyLastResponse(ctx: CommandContext): void {
  const last = ctx.messages.filter((message) => message.role === "assistant").pop()
  if (!last?.content) return
  try {
    ;(navigator as { clipboard?: { writeText?: (text: string) => void } }).clipboard?.writeText?.(last.content)
  } catch {
    // Clipboard access is best-effort: the TUI works without it.
  }
  ctx.dispatch({ type: "SET_CONNECTION_ERROR", payload: "Copied last response" })
}

/**
 * Slash commands are a table so the runner stays a lookup instead of a long
 * switch. Anything with real logic is a named function above.
 */
const SLASH_ACTIONS: Record<string, (ctx: CommandContext) => void> = {
  reset: (ctx) => ctx.dispatch({ type: "RESET_SESSION" }),
  help: (ctx) => ctx.dispatch({ type: "SET_OVERLAY", payload: { name: "showHelp", visible: true } }),
  models: openModelSelector,
  themes: openThemeSelector,
  agents: openAgentSelector,
  sessions: openSessionList,
  editor: (ctx) => ctx.sendEditorPrompt(),
  cost: (ctx) => void ctx.sendCost(),
  diff: (ctx) => void openDiffPreview(ctx),
  copy: copyLastResponse,
  exit: (ctx) => ctx.exit(),
}

function runSlashResult(result: SlashResult | boolean, ctx: CommandContext): void {
  if (result === true || result === false) return
  if (typeof result !== "object" || !("type" in result)) return
  const type = result.type
  if (typeof type !== "string") return
  const action = SLASH_ACTIONS[type]
  if (action) action(ctx)
}

// ────────────────────────── component ──────────────────────────

export function ApexApp() {
  const { exit } = useApp()
  const { state, dispatch } = useTuiStore()
  const {
    activeAgent,
    activeModel,
    activeSession,
    messages,
    inputValue,
    isGenerating,
    connectionError,
    isReconnecting,
    retryCount,
    sidebarVisible,
    overlays,
    overlaySearch,
    overlayIndex,
    themes,
    sessions,
    totalPromptTokens,
    totalCompletionTokens,
    totalSpent,
    livePromptTokens,
    liveCompletionTokens,
    diffFingerprint,
    diffPaths,
    tail,
    committedCount,
    staticEpoch,
    expandedToolId,
    tools,
    completion,
    toasts,
    thinkingMode,
    sessionStart,
  } = state

  const {
    sendMessageRef,
    sendMessage,
    sendBash,
    sendCost,
    sendEditorPrompt,
    filteredCommands,
  } = useChat({ dispatch, getState: () => state })

  // Recompute the autocomplete list whenever the input changes.
  useComposer({
    inputValue,
    dispatch,
    commands: filteredCommands(overlaySearch.cpSearch),
    themes,
    sessions,
  })

  const selectCompletion = useCallback(
    (value: string) => {
      const hit = currentTrigger(inputValue)
      if (!hit) return
      const before = inputValue.slice(0, inputValue.length - hit.prefix.length - 1)
      const next = `${before}${hit.trigger}${value} `
      dispatch({ type: "SET_INPUT_VALUE", payload: next })
      dispatch({ type: "INC_COMPLETION_FREQ", payload: value })
      dispatch({ type: "HIDE_COMPLETION" })
    },
    [inputValue, dispatch]
  )

  // Persist config (theme, agent, model, sidebar, thinking, frecency).
  useTuiPersistence()

  // Slash commands can re-submit the accumulated prompt (e.g. /theme, /session).
  useEffect(() => {
    sendMessageRef.current = sendMessage as unknown as (message: string) => Promise<{ type: string }>
  }, [sendMessage])

  const agent = APEX_AGENTS.find((candidate) => candidate.id === activeAgent) ?? APEX_AGENTS[0]!
  const model = APEX_MODELS.find((candidate) => candidate.id === activeModel)
  const totalTokens = totalPromptTokens + totalCompletionTokens
  const contextPct = contextPercentage(totalTokens, model?.contextWindow)
  const sessionDuration = formatDuration(sessionStart)
  const anyOverlay = hasVisibleOverlay(overlays)

  const handleSubmit = useCallback(
    async (userMessage: string) => {
      const result = await sendMessage(userMessage)
      if (result.type === "reset") {
        dispatch({ type: "RESET_SESSION" })
        return
      }
      if (result.type === "done") {
        dispatch({ type: "SET_RETRY_COUNT", payload: 0 })
        return
      }
      // Slash commands that only drive the UI (help, diff, cost, copy, …).
      runSlashResult(result as SlashResult, {
        dispatch,
        exit,
        sendMessage,
        sendEditorPrompt,
        sendCost,
        messages,
        state,
      })
    },
    [sendMessage, dispatch, exit, sendEditorPrompt, sendCost, messages, state]
  )

  const retryConnection = useCallback(() => {
    dispatch({ type: "SET_CONNECTION_ERROR", payload: null })
    dispatch({ type: "SET_IS_RECONNECTING", payload: false })
    const last = messages[messages.length - 1]
    if (last?.role === "user") void sendMessage(last.content)
  }, [messages, sendMessage, dispatch])

  useTuiSync({ dispatch, getState: () => state })

  const { leaderActive, leaderStrokes, keymap } = useApexKeyboard({
    state,
    dispatch,
    commands: filteredCommands(overlaySearch.cpSearch),
    sendMessage,
    sendBash,
    submit: (text) => void handleSubmit(text),
    exit,
    retryConnection,
    sendEditorPrompt,
    completion,
    selectCompletion,
    api: { listThemes: () => api.listThemes(), listSessions: () => api.listSessions() },
  })

  const statusHint = completion.visible ? "↑↓ navigate · Enter accept · Esc close" : "Ctrl+P palette · Ctrl+K models · ? help"

  // A stale connection banner must not outlive the outage it describes.
  useEffect(() => {
    if (!connectionError) return
    const timer = setTimeout(() => {
      dispatch({ type: "SET_CONNECTION_ERROR", payload: null })
      dispatch({ type: "SET_IS_RECONNECTING", payload: false })
    }, ERROR_AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [connectionError, dispatch])

  // Returning to idle re-anchors the viewport unless an overlay is covering it.
  useEffect(() => {
    if (!isGenerating && !anyOverlay) dispatch({ type: "SET_TAIL", payload: true })
  }, [isGenerating, messages.length, dispatch, anyOverlay])

  const handleDiffDecision = useCallback(
    async (decision: DiffDecision) => {
      dispatch({ type: "SET_DIFF_SUBMITTING", payload: true })
      dispatch({ type: "SET_DIFF_ERROR", payload: undefined })
      try {
        const result = await api.decideDiff(activeSession || "current", {
          decision,
          files: diffPaths,
          fingerprint: diffFingerprint,
        })
        if (result.error) throw new Error(result.error)
        const failed = result.failed ?? []
        if (decision === "reject" && failed.length > 0) {
          dispatch({
            type: "SET_DIFF_ERROR",
            payload: `Reverted ${result.reverted?.length ?? 0} file(s); failed: ${failed.join(", ")} — reopen /diff to review`,
          })
          return
        }
        dispatch({ type: "SET_OVERLAY", payload: { name: "showDiff", visible: false } })
        dispatch({
          type: "SET_CONNECTION_ERROR",
          payload:
            decision === "accept"
              ? "Diff accepted — changes kept"
              : `Diff rejected — ${result.reverted?.length ?? diffPaths.length} file(s) restored`,
        })
      } catch (error) {
        dispatch({ type: "SET_DIFF_ERROR", payload: error instanceof Error ? error.message : String(error) })
      } finally {
        dispatch({ type: "SET_DIFF_SUBMITTING", payload: false })
      }
    },
    [activeSession, diffPaths, diffFingerprint, dispatch]
  )

  return (
    <KeymapProvider keymap={keymap}>
      <Box flexDirection="column" flexGrow={1}>
        <ConnectionError error={connectionError} isReconnecting={isReconnecting} retryCount={retryCount} />
        <LeaderKeys active={leaderActive} strokes={leaderStrokes} timeout={DEFAULT_LEADER_TIMEOUT} />
        <StatusHeader
          activeAgent={activeAgent}
          activeModel={activeModel}
          messageCount={messages.length}
          contextPct={contextPct}
          totalSpent={totalSpent}
        />

        <OverlayLayers
          state={state}
          dispatch={dispatch}
          agent={agent}
          model={model}
          totalTokens={totalTokens}
          contextPct={contextPct}
          sessionDuration={sessionDuration}
          commands={filteredCommands(overlaySearch.cpSearch)}
          sendMessage={sendMessage}
          submit={(text) => void handleSubmit(text)}
          onDiffDecision={handleDiffDecision}
        />

        {!anyOverlay && (
          <Box flexDirection="row" flexGrow={1}>
            {sidebarVisible && (
              <Sidebar
                activeAgent={activeAgent}
                onAgentSelect={(id) => dispatch({ type: "SET_ACTIVE_AGENT", payload: id })}
              />
            )}
            <ChatPanel
              messages={messages}
              committedCount={committedCount}
              staticEpoch={staticEpoch}
              tail={tail}
              inputValue={inputValue}
              activeAgent={activeAgent}
              activeModel={activeModel}
              isGenerating={isGenerating}
              tools={tools}
              expandedToolId={expandedToolId}
              completion={completion}
              onSelectCompletion={selectCompletion}
            />
          </Box>
        )}

        {!anyOverlay && thinkingMode !== "show" && (
          <Text color={apexTheme.gray}>Thinking: {thinkingMode} (Ctrl+T to cycle)</Text>
        )}

        <Toasts toasts={toasts} />

        <StatusBar
          activeAgent={activeAgent}
          activeModel={activeModel}
          totalTokens={totalTokens}
          totalPromptTokens={totalPromptTokens}
          totalCompletionTokens={totalCompletionTokens}
          totalSpent={totalSpent}
          contextPct={contextPct}
          messageCount={messages.length}
          sessionDuration={sessionDuration}
          livePromptTokens={livePromptTokens}
          liveCompletionTokens={liveCompletionTokens}
          thinkingMode={thinkingMode}
          hint={statusHint}
        />
      </Box>
    </KeymapProvider>
  )
}
