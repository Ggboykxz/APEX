"use strict";

/**
 * ApexApp — root TUI component (refactored).
 *
 * Architecture:
 *   - `useChat` owns slash commands, message sending, bash, cost, editor.
 *   - Leader key is handled with a ref (immediate detection in useInput) +
 *     state (banner display).
 *   - Rendering uses atomic components: ChatMessage, ToolCall, StatusHeader,
 *     ConnectionError, LeaderKeys. Overlays remain stateless.
 *   - Styled with the APEX charter: cyan #00e5ff primary, agent colors from
 *     apex-data.ts, five built-in themes.
 */

import React, { useCallback, useEffect, useRef, useState } from "react"
import { Box, Text, useApp, useInput } from "ink"
import { ChatPanel } from "./ChatPanel.js"
import { DiffPreview, type DiffPreviewHandle } from "./DiffPreview.js"
import { StatusBar } from "./StatusBar.js"
import { Sidebar } from "./Sidebar.js"
import { StatusHeader } from "./StatusHeader.js"
import { ConnectionError } from "./ConnectionError.js"
import { LeaderKeys } from "./LeaderKeys.js"
import { apexTheme, hasTheme, setTheme, listThemes } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"
import { SyncClient } from "../sync.js"
import { api } from "../api/client.js"
import type { DiffDecision } from "../diff/preview.js"
import {
  useSyncStream,
  useStreamingState,
} from "../streaming/useStream.js"
import { streamActionFromEvent } from "../streaming/reducer.js"
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
import { useChat } from "../hooks/useChat.js"
import { useTuiConfig } from "../hooks/useTuiConfig.js"

const HTTP_PORT = Number(process.env.APEX_HTTP_PORT ?? "0") || 8765
const DEFAULT_LEADER_TIMEOUT = 2000
const MAX_VISIBLE = 20

const LEADER_CMDS: Record<string, { action: string; cmd?: string }> = {
  n: { action: "cmd", cmd: "/new" },
  u: { action: "cmd", cmd: "/undo" },
  r: { action: "cmd", cmd: "/redo" },
  c: { action: "cmd", cmd: "/compact" },
  m: { action: "overlay", cmd: "model" },
  t: { action: "overlay", cmd: "theme" },
  s: { action: "overlay", cmd: "status" },
  e: { action: "cmd", cmd: "/editor" },
  x: { action: "cmd", cmd: "/export" },
  b: { action: "sidebar" },
  a: { action: "overlay", cmd: "agent" },
  l: { action: "overlay", cmd: "session" },
  y: { action: "cmd", cmd: "/copy" },
  q: { action: "quit" },
}

export function ApexApp() {
  const { exit } = useApp()

  // ── React state (declared before hooks that depend on them) ────────
  const [activeAgent, setActiveAgent] = useState("build")
  const [activeModel, setActiveModel] = useState("claude-sonnet-4")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const [showDiff, setShowDiff] = useState(false)
  const [diffText, setDiffText] = useState("")
  const [diffFingerprint, setDiffFingerprint] = useState("")
  const [diffPaths, setDiffPaths] = useState<string[]>([])
  const [diffSubmitting, setDiffSubmitting] = useState(false)
  const [diffError, setDiffError] = useState<string | undefined>(undefined)
  const diffPreviewRef = useRef<DiffPreviewHandle>(null)

  const [sessionStart] = useState(Date.now())
  const [totalPromptTokens, setTotalPromptTokens] = useState(0)
  const [totalCompletionTokens, setTotalCompletionTokens] = useState(0)
  const [totalSpent, setTotalSpent] = useState(0)
  const [livePromptTokens, setLivePromptTokens] = useState(0)
  const [liveCompletionTokens, setLiveCompletionTokens] = useState(0)

  // Overlays
  const [showCP, setShowCP] = useState(false)
  const [cpSearch, setCpSearch] = useState("")
  const [cpIdx, setCpIdx] = useState(0)
  const [showHelp, setShowHelp] = useState(false)
  const [showMS, setShowMS] = useState(false)
  const [msSearch, setMsSearch] = useState("")
  const [msIdx, setMsIdx] = useState(0)
  const [showTS, setShowTS] = useState(false)
  const [themes, setThemes] = useState<{ id: string; name: string }[]>([])
  const [tsIdx, setTsIdx] = useState(0)
  const [showAS, setShowAS] = useState(false)
  const [asIdx, setAsIdx] = useState(0)
  const [thinkingMode, setThinkingMode] = useState<"show" | "hide" | "off">("show")
  const [showSO, setShowSO] = useState(false)
  const [showSL, setShowSL] = useState(false)
  const [sessions, setSessions] = useState<{ id: string; name: string; model?: string }[]>([])
  const [slIdx, setSlIdx] = useState(0)
  const [activeSession, setActiveSession] = useState("")
  const [scrollOffset, setScrollOffset] = useState(0)
  const [showFF, setShowFF] = useState(false)
  const [ffQuery, setFfQuery] = useState("")
  const [ffResults, setFfResults] = useState<string[]>([])
  const [ffIdx, setFfIdx] = useState(0)
  const ffCache = useRef<string[]>([])

  // Leader key: ref for immediate detection in useInput, state for banner
  const [leaderActive, setLeaderActive] = useState(false)
  const leaderTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const leaderKeyActiveRef = useRef(false)

  // ── Hooks ────────────────────────────────────────────────────────
  const {
    inputHistory,
    setInputHistory,
    historyIdx,
    setHistoryIdx,
    sendMessageRef,
    sendMessage,
    sendBash,
    sendCost,
    sendEditorPrompt,
    handleSlashCommand,
    filteredCommands,
    COMMANDS,
  } = useChat({
    activeAgent,
    activeModel,
    onConnectionError: (msg) => setConnectionError(msg),
    onSetIsGenerating: (v) => setIsGenerating(v),
    onSetIsReconnecting: (v) => setIsReconnecting(v),
    onSetRetryCount: (c) => setRetryCount(c),
  })

  const { refetch: refetchTuiConfig } = useTuiConfig()

  // ── Streaming ────────────────────────────────────────────────────
  const {
    state: streamState,
    dispatch: dispatchStream,
    complete: completeStream,
  } = useStreamingState()

  const liveUsageRef = useRef<{ pt: number; ct: number }>({ pt: 0, ct: 0 })
  const accountedUsageRef = useRef<{ pt: number; ct: number }>({ pt: 0, ct: 0 })
  const activeModelRef = useRef(activeModel)
  useEffect(() => { activeModelRef.current = activeModel }, [activeModel])

  const syncRef = useRef<SyncClient | null>(null)
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!
  const model = APEX_MODELS.find((m) => m.id === activeModel)

  const totalTokens = totalPromptTokens + totalCompletionTokens
  const contextPct = model?.contextWindow && totalTokens > 0
    ? Math.min(100, (totalTokens / model.contextWindow) * 100)
    : (model?.contextWindow ? 0 : 0)
  const sessionDuration = (() => {
    const e = Math.floor((Date.now() - sessionStart) / 1000)
    return `${Math.floor(e / 60)}:${(e % 60).toString().padStart(2, "0")}`
  })()

  const scrollEndIdx = messages.length - scrollOffset
  const visibleMessages = messages.slice(Math.max(0, scrollEndIdx - MAX_VISIBLE), scrollEndIdx)
  const isScrolled = scrollOffset > 0
  const scrollPct = messages.length > MAX_VISIBLE
    ? Math.round((scrollOffset / Math.max(1, messages.length - MAX_VISIBLE)) * 100)
    : 0

  const anyOverlay =
    showCP || showFF || showHelp || showMS || showTS || showAS || showSO || showSL || showDiff

  // ── Effects ──────────────────────────────────────────────────────
  useEffect(() => {
    if (connectionError) {
      const t = setTimeout(() => {
        setConnectionError(null)
        setIsReconnecting(false)
      }, 5000)
      return () => clearTimeout(t)
    }
  }, [connectionError])

  useEffect(() => {
    refetchTuiConfig().catch((err) => {
      if (!syncRef.current?.connected) {
        console.warn(`TUI config fetch failed: ${err.message}`)
        setConnectionError("Backend API unavailable — some features may not work")
      }
    })
  }, [refetchTuiConfig])

  useEffect(() => {
    if (!isGenerating && !anyOverlay) {
      setTimeout(() => setScrollOffset(0), 0)
    }
  }, [isGenerating, messages.length])

  // ── WebSocket ────────────────────────────────────────────────────
  useEffect(() => {
    if (!HTTP_PORT) return
    const sync = new SyncClient(api.wsUrl, api.baseUrl)
    syncRef.current = sync

    sync.on("connected", () => {
      setConnectionError(null)
      setIsReconnecting(false)
    })
    sync.on("disconnected", () => {
      setConnectionError("WebSocket disconnected — reconnecting...")
      setIsReconnecting(true)
    })
    sync.on("state", (state: any) => {
      if (state.model) setActiveModel(state.model)
      if (state.agent) setActiveAgent(state.agent)
    })
    sync.on("theme_changed", (data: any) => {
      if (data.theme && setTheme(data.theme)) {
        setConnectionError(`Theme changed: ${data.theme}`)
      }
    })
    sync.on("chat_complete", (data: any) => {
      const u = data?.usage
      if (!u) return
      const pt = u.prompt_tokens ?? 0
      const ct = u.completion_tokens ?? 0
      if (pt === accountedUsageRef.current.pt && ct === accountedUsageRef.current.ct) return
      setTotalPromptTokens((p) => p + pt)
      setTotalCompletionTokens((c) => c + ct)
      setTotalSpent((s) => s + ((pt / 1000) * (model?.inputCostPer1K ?? 0) + (ct / 1000) * (model?.outputCostPer1K ?? 0)))
    })
    sync.onStream((event) => {
      const action = streamActionFromEvent(event)
      if (action) dispatchStream(action)
    })

    sync.connect()
    return () => { sync.disconnect(); syncRef.current = null }
  }, [])

  // ── Slash command result handler ─────────────────────────────────
  const fetchThemes = useCallback(async () => {
    try {
      setThemes(await api.listThemes())
    } catch {
      setThemes([
        { id: "default", name: "Default" },
        { id: "light", name: "Light" },
      ])
    }
  }, [])

  const fetchSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
    } catch {
      setSessions([])
    }
  }, [])

  const handleSlashResult = useCallback(
    (result: ReturnType<typeof handleSlashCommand>) => {
      if (result === true || result === false) return
      if (typeof result === "object" && "type" in result) {
        switch (result.type) {
          case "reset":
            setMessages([])
            setInputValue("")
            setTotalPromptTokens(0)
            setTotalCompletionTokens(0)
            setTotalSpent(0)
            setScrollOffset(0)
            setActiveSession("")
            return
          case "help":
            setShowHelp(true)
            return
          case "models":
            setShowMS(true)
            setMsSearch("")
            setMsIdx(0)
            return
          case "themes":
            fetchThemes()
            setShowTS(true)
            setTsIdx(0)
            return
          case "agents":
            setShowAS(true)
            setAsIdx(APEX_AGENTS.findIndex((a) => a.id === activeAgent))
            return
          case "sessions":
            fetchSessions()
            setShowSL(true)
            setSlIdx(0)
            return
          case "editor":
            sendEditorPrompt()
            return
          case "cost":
            sendCost().then((res) => {
              if (res.type === "done" && res.assistantMsg) {
                setMessages((p) => [...p, res.assistantMsg])
                setTotalSpent((s) => s + (res.assistantMsg.cost ?? 0))
              }
            })
            return
          case "diff":
            setConnectionError("Loading working-tree diff…")
            api.sessionDiff(activeSession || "current")
              .then((d) => {
                if (d.error) {
                  setConnectionError(`Diff error: ${d.error}`)
                  return
                }
                setDiffText(d.diff ?? "")
                setDiffFingerprint(d.fingerprint ?? "")
                setDiffPaths(d.paths ?? [])
                setDiffError(undefined)
                setDiffSubmitting(false)
                setShowDiff(true)
              })
              .catch(() => setConnectionError("Diff request failed — backend unreachable"))
            return
          case "copy": {
            const last = messages.filter((m) => m.role === "assistant").pop()
            if (last?.content) {
              try {
                ;(navigator as any).clipboard?.writeText?.(last.content)
              } catch {}
              setConnectionError("Copied last response")
            }
            return
          }
          case "exit":
            exit()
            return
        }
      }
    },
    [
      activeAgent, activeSession, activeModel, messages, exit,
      fetchThemes, fetchSessions, sendEditorPrompt, sendCost,
    ]
  )

  const handleDiffDecision = useCallback(async (decision: DiffDecision) => {
    setDiffSubmitting(true)
    setDiffError(undefined)
    try {
      const result = await api.decideDiff(activeSession || "current", {
        decision,
        files: diffPaths,
        fingerprint: diffFingerprint,
      })
      if (result.error) throw new Error(result.error)
      const failed = result.failed ?? []
      if (decision === "reject" && failed.length > 0) {
        setDiffError(
          `Reverted ${result.reverted?.length ?? 0} file(s); failed: ${failed.join(", ")} — reopen /diff to review`,
        )
        diffPreviewRef.current?.reset()
        return
      }
      setShowDiff(false)
      setConnectionError(
        decision === "accept"
          ? "Diff accepted — changes kept"
          : `Diff rejected — ${result.reverted?.length ?? diffPaths.length} file(s) restored`,
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setDiffError(message)
      diffPreviewRef.current?.reset()
    } finally {
      setDiffSubmitting(false)
    }
  }, [activeSession, diffPaths, diffFingerprint])

  const retryConnection = useCallback(() => {
    setConnectionError(null)
    setIsReconnecting(false)
    const last = messages[messages.length - 1]
    if (last?.role === "user") {
      void sendMessage(last.content)
    }
  }, [messages, sendMessage])

  const closeOverlay = () => {
    setShowCP(false)
    setShowHelp(false)
    setShowMS(false)
    setShowTS(false)
    setShowAS(false)
    setShowSO(false)
    setShowSL(false)
    setShowFF(false)
    setShowDiff(false)
    setFfQuery("")
  }

  // ── Chat submit ──────────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (userMessage: string) => {
      const result = await sendMessage(userMessage)
      if (result.type === "reset") {
        setMessages([])
        setInputValue("")
        setTotalPromptTokens(0)
        setTotalCompletionTokens(0)
        setTotalSpent(0)
        setScrollOffset(0)
        setActiveSession("")
        return
      }
      if (result.type === "done" && result.assistantMsg) {
        setMessages((p) => [...p, result.userMsg!, result.assistantMsg!])
        setTotalPromptTokens((p) => p + (result.totalPromptTokens ?? 0))
        setTotalCompletionTokens((c) => c + (result.totalCompletionTokens ?? 0))
        setTotalSpent((s) => s + (result.totalSpent ?? 0))
        liveUsageRef.current = {
          pt: result.totalPromptTokens ?? 0,
          ct: result.totalCompletionTokens ?? 0,
        }
        setLivePromptTokens(result.totalPromptTokens ?? 0)
        setLiveCompletionTokens(result.totalCompletionTokens ?? 0)
        accountedUsageRef.current = {
          pt: result.totalPromptTokens ?? 0,
          ct: result.totalCompletionTokens ?? 0,
        }
        setRetryCount(0)
        return
      }
      if (result.type === "error" && result.assistantMsg) {
        setMessages((p) => [...p, result.userMsg!, result.assistantMsg!])
        return
      }
    },
    [sendMessage]
  )

  const handleInputSubmit = useCallback(
    (value: string) => {
      if (!value.trim() || isGenerating) return
      setInputValue("")
      setInputHistory((h) => [value, ...h].slice(0, 50))
      setHistoryIdx(-1)
      void handleSubmit(value)
    },
    [isGenerating, handleSubmit]
  )

  // ── File listing ─────────────────────────────────────────────────
  const fetchFiles = useCallback(async () => {
    if (ffCache.current.length > 0) return
    try {
      ffCache.current = await api.listFiles()
    } catch {
      ffCache.current = ["src/", "README.md", "package.json", "tsconfig.json"]
    }
  }, [])

  // ── Keyboard input ───────────────────────────────────────────────
  useInput((input, key) => {
    if (showDiff) return

    // Leader key: ref is set immediately by activateLeader, state follows for banner
    if (leaderKeyActiveRef.current) {
      leaderKeyActiveRef.current = false
      if (leaderTimer.current) {
        clearTimeout(leaderTimer.current)
        leaderTimer.current = null
      }
      setLeaderActive(false)
      const e = LEADER_CMDS[input.toLowerCase()]
      if (!e) return
      if (e.action === "cmd" && e.cmd) {
        void sendMessage(e.cmd)
      } else if (e.action === "sidebar") {
        setSidebarVisible((v) => !v)
      } else if (e.action === "quit") {
        exit()
      } else if (e.action === "overlay") {
        if (e.cmd === "model") {
          setShowMS(true)
          setMsSearch("")
          setMsIdx(Math.max(0, APEX_MODELS.findIndex((m) => m.id === activeModel)))
        }
        if (e.cmd === "theme") {
          fetchThemes()
          setShowTS(true)
          setTsIdx(0)
        }
        if (e.cmd === "status") setShowSO(true)
        if (e.cmd === "agent") {
          setShowAS(true)
          setAsIdx(APEX_AGENTS.findIndex((a) => a.id === activeAgent))
        }
        if (e.cmd === "session") {
          fetchSessions()
          setShowSL(true)
          setSlIdx(0)
        }
      }
      return
    }

    if (showCP) {
      if (key.escape) { setShowCP(false); setCpSearch("") }
      else if (key.return && filteredCommands(cpSearch).length > 0) {
        const c = filteredCommands(cpSearch)[cpIdx % filteredCommands(cpSearch).length]
        setShowCP(false); setCpSearch(""); void handleSubmit(c.id)
      }
      else if (key.upArrow) setCpIdx((i) => (i - 1 + filteredCommands(cpSearch).length) % filteredCommands(cpSearch).length)
      else if (key.downArrow) setCpIdx((i) => (i + 1) % filteredCommands(cpSearch).length)
      else if (key.backspace || key.delete) { setCpSearch((s) => s.slice(0, -1)); setCpIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setCpSearch((s) => s + input); setCpIdx(0) }
      return
    }

    if (showHelp) { if (key.escape) setShowHelp(false); return }
    if (showMS) {
      if (key.escape) { setShowMS(false); setMsSearch("") }
      else if (key.return && APEX_MODELS.length > 0) {
        setActiveModel(APEX_MODELS[msIdx % APEX_MODELS.length].id)
        setShowMS(false); setMsSearch("")
      }
      else if (key.upArrow) setMsIdx((i) => (i - 1 + APEX_MODELS.length) % APEX_MODELS.length)
      else if (key.downArrow) setMsIdx((i) => (i + 1) % APEX_MODELS.length)
      else if (key.backspace || key.delete) { setMsSearch((s) => s.slice(0, -1)); setMsIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setMsSearch((s) => s + input); setMsIdx(0) }
      return
    }
    if (showTS) {
      if (key.escape) setShowTS(false)
      else if (key.return && themes.length > 0) {
        setShowTS(false); void sendMessage(`/theme ${themes[tsIdx % themes.length].id}`)
      }
      else if (key.upArrow) setTsIdx((i) => (i - 1 + themes.length) % themes.length)
      else if (key.downArrow) setTsIdx((i) => (i + 1) % themes.length)
      return
    }
    if (showAS) {
      if (key.escape) setShowAS(false)
      else if (key.return) {
        setActiveAgent(APEX_AGENTS[asIdx % APEX_AGENTS.length].id)
        setShowAS(false)
      }
      else if (key.upArrow) setAsIdx((i) => (i - 1 + APEX_AGENTS.length) % APEX_AGENTS.length)
      else if (key.downArrow) setAsIdx((i) => (i + 1) % APEX_AGENTS.length)
      return
    }
    if (showSO) { if (key.escape) setShowSO(false); return }
    if (showSL) {
      if (key.escape) setShowSL(false)
      else if (key.return && sessions.length > 0) {
        setShowSL(false); void sendMessage(`/session ${sessions[slIdx % sessions.length].id}`)
      }
      else if (key.upArrow) setSlIdx((i) => (i - 1 + sessions.length) % sessions.length)
      else if (key.downArrow) setSlIdx((i) => (i + 1) % sessions.length)
      return
    }
    if (showFF) {
      if (key.escape) { setShowFF(false); setFfQuery("") }
      else if ((key.return || key.tab) && ffResults.length > 0) {
        const f = ffResults[ffIdx % ffResults.length]
        const at = inputValue.lastIndexOf("@")
        setInputValue((at >= 0 ? inputValue.slice(0, at) : inputValue) + "@" + f)
        setShowFF(false); setFfQuery("")
      }
      else if (key.upArrow) setFfIdx((i) => (i - 1 + ffResults.length) % ffResults.length)
      else if (key.downArrow) setFfIdx((i) => (i + 1) % ffResults.length)
      else if (key.backspace || key.delete) { setFfQuery((q) => q.slice(0, -1)); setFfIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setFfQuery((q) => q + input); setFfIdx(0) }
      return
    }

    // Global shortcuts
    if (key.ctrl && input === "x") {
      leaderKeyActiveRef.current = true
      setLeaderActive(true)
      leaderTimer.current = setTimeout(() => {
        leaderKeyActiveRef.current = false
        setLeaderActive(false)
      }, DEFAULT_LEADER_TIMEOUT)
      return
    }
    if (key.ctrl && input === "p") { setShowCP(true); setCpSearch(""); setCpIdx(0); return }
    if (key.ctrl && input === "k") {
      setShowMS(true)
      setMsSearch("")
      setMsIdx(APEX_MODELS.findIndex((m) => m.id === activeModel))
      return
    }
    if (key.ctrl && input === "t") {
      setThinkingMode((m) => m === "show" ? "hide" : m === "hide" ? "off" : "show")
      return
    }
    if (input === "?" && !key.ctrl) { setShowHelp(true); return }
    if (key.ctrl && input === "q") { exit(); return }
    if (key.ctrl && input === "o") { setSidebarVisible((v) => !v); return }
    if (key.ctrl && input === "l") {
      setMessages([]); setInputValue(""); setTotalPromptTokens(0); setTotalCompletionTokens(0)
      setTotalSpent(0); setScrollOffset(0)
      return
    }
    if (key.ctrl && input === "u") { setInputValue(""); return }
    if (key.ctrl && input === "w") {
      setInputValue((v) => v.replace(/\s*\S+\s*$/, ""))
      return
    }
    if (key.ctrl && input === "d") {
      const nv = inputValue.slice(1)
      setInputValue(nv)
      const at = nv.lastIndexOf("@")
      if (at >= 0) {
        setShowFF(true); setFfQuery(nv.slice(at + 1)); setFfIdx(0); fetchFiles()
      }
      return
    }
    if (input === "r" && !key.ctrl && !key.meta && isReconnecting) { retryConnection?.(); return }
    if (key.tab && !key.shift && !showFF) {
      const i = APEX_AGENTS.findIndex((a) => a.id === activeAgent)
      setActiveAgent(APEX_AGENTS[(i + 1) % APEX_AGENTS.length]!.id)
      return
    }
    if (key.shift && key.tab && !showFF) {
      const i = APEX_AGENTS.findIndex((a) => a.id === activeAgent)
      setActiveAgent(APEX_AGENTS[(i - 1 + APEX_AGENTS.length) % APEX_AGENTS.length]!.id)
      return
    }
    if (key.return && !key.shift && inputValue.trim() && !isGenerating) {
      const m = inputValue.trim()
      setInputValue("")
      setInputHistory((h) => [m, ...h].slice(0, 50))
      setHistoryIdx(-1)
      if (m.startsWith("!")) void sendBash(m.slice(1).trim())
      else void handleSubmit(m)
      return
    }
    if (key.return && key.shift) { setInputValue((v) => v + "\n"); return }
    if (key.upArrow && inputHistory.length > 0) {
      const next = Math.min(historyIdx + 1, inputHistory.length - 1)
      setHistoryIdx(next); setInputValue(inputHistory[next] ?? "")
      return
    }
    if (key.downArrow && historyIdx >= 0) {
      const next = historyIdx - 1
      if (next < 0) { setHistoryIdx(-1); setInputValue(""); return }
      setHistoryIdx(next); setInputValue(inputHistory[next] ?? "")
      return
    }
    if (key.ctrl && input === "g") { setScrollOffset(Math.max(0, messages.length - 1)); return }
    if ((key as any).home) { setScrollOffset(Math.max(0, messages.length - 1)); return }
    if ((key as any).end) { setScrollOffset(0); return }
    if (key.pageUp) {
      setScrollOffset((o) => Math.min(o + MAX_VISIBLE, Math.max(0, messages.length - 1)))
      return
    }
    if (key.pageDown) {
      setScrollOffset((o) => Math.max(0, o - MAX_VISIBLE))
      return
    }
    if (key.backspace || key.delete) {
      const at = inputValue.lastIndexOf("@")
      if (at >= 0 && inputValue.slice(at).startsWith("@")) {
        const nv = inputValue.slice(0, -1); setInputValue(nv)
        const newAt = nv.lastIndexOf("@")
        if (newAt >= 0) {
          setShowFF(true); setFfQuery(nv.slice(newAt + 1)); setFfIdx(0); fetchFiles()
        } else {
          setShowFF(false); setFfQuery("")
        }
        return
      }
      setInputValue((v) => v.slice(0, -1))
      return
    }
    if (input && !key.ctrl && !key.meta) {
      const nv = inputValue + input
      setInputValue(nv)
      if (input === "@") {
        setShowFF(true); setFfQuery(""); setFfIdx(0); fetchFiles()
      } else if (showFF || inputValue.includes("@")) {
        const at = nv.lastIndexOf("@")
        if (at >= 0) { setShowFF(true); setFfQuery(nv.slice(at + 1)); setFfIdx(0) }
      }
    }
  })
  // ── Render ───────────────────────────────────────────────────────
  const mainContent = (
    <Box flexDirection="row" flexGrow={1}>
      {sidebarVisible && (
        <Sidebar activeAgent={activeAgent} onAgentSelect={setActiveAgent} />
      )}
      <ChatPanel
        messages={visibleMessages}
        inputValue={inputValue}
        activeAgent={activeAgent}
        activeModel={activeModel}
        isGenerating={isGenerating}
        tools={streamState.tools}
      />
    </Box>
  )

  return (
    <Box flexDirection="column" flexGrow={1}>
      <ConnectionError
        error={connectionError}
        isReconnecting={isReconnecting}
        retryCount={retryCount}
      />
      <LeaderKeys active={leaderActive} timeout={DEFAULT_LEADER_TIMEOUT} />
      <StatusHeader
        activeAgent={activeAgent}
        activeModel={activeModel}
        messageCount={messages.length}
        contextPct={contextPct}
        totalSpent={totalSpent}
      />

      {showCP && (
        <CommandPalette
          commands={COMMANDS}
          query={cpSearch}
          index={cpIdx}
          onSelect={(id) => {
            setShowCP(false)
            setCpSearch("")
            void handleSubmit(id)
          }}
        />
      )}
      {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} />}
      {showDiff && (
        <DiffPreview
          ref={diffPreviewRef}
          diff={diffText}
          title="Working-tree diff"
          submitting={diffSubmitting}
          error={diffError}
          onDecision={handleDiffDecision}
        />
      )}
      {showMS && (
        <ModelSelector
          models={APEX_MODELS}
          query={msSearch}
          index={msIdx}
          onSelect={(id) => {
            setActiveModel(id)
            setShowMS(false)
            setMsSearch("")
          }}
        />
      )}
      {showTS && (
        <ThemeSelector
          themes={themes}
          index={tsIdx}
          onSelect={(id) => {
            setShowTS(false)
            void sendMessage(`/theme ${id}`)
          }}
        />
      )}
      {showAS && (
        <AgentSelector
          agents={APEX_AGENTS}
          index={asIdx}
          onSelect={(id) => {
            setActiveAgent(id)
            setShowAS(false)
          }}
        />
      )}
      {showSO && (
        <StatusOverlay
          agentName={agent.name}
          agentColor={agent.color}
          modelName={model?.name ?? activeModel}
          provider={model?.provider ?? "—"}
          contextWindow={model?.contextWindow ?? 0}
          messageCount={messages.length}
          totalPromptTokens={totalPromptTokens}
          totalCompletionTokens={totalCompletionTokens}
          totalTokens={totalTokens}
          totalSpent={totalSpent}
          sessionDuration={sessionDuration}
          thinkingMode={thinkingMode}
          contextPct={contextPct}
        />
      )}
      {showSL && (
        <SessionList
          sessions={sessions}
          index={slIdx}
          onSelect={(id) => {
            setShowSL(false)
            void sendMessage(`/session ${id}`)
          }}
        />
      )}

      {!anyOverlay && mainContent}

      {!anyOverlay && isScrolled && (
        <Text color={apexTheme.yellow} bold>
          ↑ Scrolled up ({scrollPct}%) — PgUp/PgDown to scroll
        </Text>
      )}
      {!anyOverlay && thinkingMode !== "show" && (
        <Text color={apexTheme.gray}>
          Thinking: {thinkingMode} (Ctrl+T to cycle)
        </Text>
      )}

      {showFF && (
        <FileFinder
          files={ffResults}
          query={ffQuery}
          index={ffIdx}
          onSelect={(f) => {
            const at = inputValue.lastIndexOf("@")
            setInputValue(
              (at >= 0 ? inputValue.slice(0, at) : inputValue) + "@" + f
            )
            setShowFF(false)
            setFfQuery("")
          }}
        />
      )}

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
      />
    </Box>
  )
}
