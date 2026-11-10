"use strict";

/**
 * OverlayLayers — every modal surface in the TUI, rendered from the store.
 *
 * Stateless: all state comes from the central TUI store and every mutation is
 * dispatched straight back into it. Extracted from ApexApp so the root
 * component stays a layout shell instead of a 120-line JSX tree.
 */

import React from "react"
import type { TuiDispatch, TuiState } from "../store/tuiStore.js"
import { APEX_AGENTS, APEX_MODELS, type AgentInfo, type ModelInfo } from "../data/apex-data.js"
import type { DiffDecision } from "../diff/preview.js"
import { DiffPreview } from "./DiffPreview.js"
import {
  AgentSelector,
  CommandPalette,
  FileFinder,
  HelpOverlay,
  ModelSelector,
  SessionList,
  StatusOverlay,
  ThemeSelector,
} from "./overlays.js"
import { setTheme } from "../theme/apex.js"

export interface OverlayLayersProps {
  state: TuiState
  dispatch: TuiDispatch
  agent: AgentInfo
  model: ModelInfo | undefined
  totalTokens: number
  contextPct: number
  sessionDuration: string
  /** Command-palette rows, already filtered by the current query. */
  commands: Array<{ id: string; desc: string }>
  sendMessage: (text: string) => Promise<unknown>
  submit: (text: string) => void
  onDiffDecision: (decision: DiffDecision) => void
}

function OverlayLayer({ visible, children }: { visible: boolean; children: React.ReactNode }) {
  if (!visible) return null
  return <>{children}</>
}

function SelectorOverlays(props: OverlayLayersProps) {
  const { state, dispatch, commands, submit, sendMessage, agent, model } = props
  const { overlays, overlaySearch, overlayIndex, themes, sessions } = state

  const close = (name: keyof TuiState["overlays"]) =>
    dispatch({ type: "SET_OVERLAY", payload: { name, visible: false } })
  const clearSearch = (name: keyof TuiState["overlaySearch"]) =>
    dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name, value: "" } })

  return (
    <>
      <OverlayLayer visible={overlays.showCP}>
        <CommandPalette
          commands={commands}
          query={overlaySearch.cpSearch}
          index={overlayIndex.cpIdx}
          onSelect={(id) => {
            close("showCP")
            clearSearch("cpSearch")
            void submit(id)
          }}
        />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showMS}>
        <ModelSelector
          models={APEX_MODELS}
          query={overlaySearch.msSearch}
          index={overlayIndex.msIdx}
          onSelect={(id) => {
            dispatch({ type: "SET_ACTIVE_MODEL", payload: id })
            close("showMS")
            clearSearch("msSearch")
          }}
        />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showTS}>
        <ThemeSelector
          themes={themes}
          index={overlayIndex.tsIdx}
          onSelect={(id) => {
            setTheme(id)
            dispatch({ type: "SET_ACTIVE_THEME", payload: id })
            close("showTS")
            void sendMessage(`/theme ${id}`)
          }}
        />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showAS}>
        <AgentSelector
          agents={APEX_AGENTS}
          index={overlayIndex.asIdx}
          onSelect={(id) => {
            dispatch({ type: "SET_ACTIVE_AGENT", payload: id })
            close("showAS")
          }}
        />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showSL}>
        <SessionList
          sessions={sessions}
          index={overlayIndex.slIdx}
          onSelect={(id) => {
            close("showSL")
            void sendMessage(`/session ${id}`)
          }}
        />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showHelp}>
        <HelpOverlay onClose={() => close("showHelp")} />
      </OverlayLayer>
      <OverlayLayer visible={overlays.showSO}>
        <StatusOverlay
          agentName={agent.name}
          agentColor={agent.color}
          modelName={model?.name ?? state.activeModel}
          provider={model?.provider ?? "—"}
          contextWindow={model?.contextWindow ?? 0}
          messageCount={state.messages.length}
          totalPromptTokens={state.totalPromptTokens}
          totalCompletionTokens={state.totalCompletionTokens}
          totalTokens={props.totalTokens}
          totalSpent={state.totalSpent}
          sessionDuration={props.sessionDuration}
          thinkingMode={state.thinkingMode}
          contextPct={props.contextPct}
        />
      </OverlayLayer>
    </>
  )
}

function PreviewOverlays(props: OverlayLayersProps) {
  const { state, dispatch, onDiffDecision } = props
  const { overlays, overlaySearch, overlayIndex, diffText, diffSubmitting, diffError, inputValue } = state

  return (
    <>
      {overlays.showDiff && (
        <DiffPreview
          title="Working-tree diff"
          diff={diffText}
          submitting={diffSubmitting}
          error={diffError}
          onDecision={onDiffDecision}
        />
      )}
      {overlays.showFF && (
        <FileFinder
          files={[]}
          query={overlaySearch.ffQuery}
          index={overlayIndex.ffIdx}
          onSelect={(file) => {
            const at = inputValue.lastIndexOf("@")
            dispatch({
              type: "SET_INPUT_VALUE",
              payload: (at >= 0 ? inputValue.slice(0, at) : inputValue) + "@" + file,
            })
            dispatch({ type: "SET_OVERLAY", payload: { name: "showFF", visible: false } })
            dispatch({ type: "SET_OVERLAY_SEARCH", payload: { name: "ffQuery", value: "" } })
          }}
        />
      )}
    </>
  )
}

export function OverlayLayers(props: OverlayLayersProps) {
  return (
    <>
      <SelectorOverlays {...props} />
      <PreviewOverlays {...props} />
    </>
  )
}
