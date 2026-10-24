import React, { useState, useCallback, useEffect, useRef } from "react"
import { Box, Text, useInput, useApp } from "ink"
import { spawnSync } from "node:child_process"
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { ChatPanel } from "./ChatPanel.js"
import { StatusBar } from "./StatusBar.js"
import { Sidebar } from "./Sidebar.js"
import { apexTheme, hasTheme, setTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"
import { SyncClient } from "../sync.js"
import { api } from "../api/client.js"
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

const HTTP_PORT = Number(process.env.APEX_HTTP_PORT ?? "0") || 8765
const API_BASE = api.baseUrl
const WS_URL = api.wsUrl
const DEFAULT_LEADER_TIMEOUT = 2000
const MAX_VISIBLE = 20

const COMMANDS = [
  { id: "/help", desc: "Show help" }, { id: "/models", desc: "List models" },
  { id: "/themes", desc: "List themes" }, { id: "/new", desc: "New session" },
  { id: "/clear", desc: "Clear chat" }, { id: "/compact", desc: "Compact" },
  { id: "/undo", desc: "Undo last" }, { id: "/redo", desc: "Redo last" },
  { id: "/share", desc: "Share session" }, { id: "/export", desc: "Export" },
  { id: "/editor", desc: "Open editor" }, { id: "/sessions", desc: "Sessions" },
  { id: "/cost", desc: "Token usage & cost" },
  { id: "/init", desc: "Initialize" }, { id: "/connect", desc: "Connect remote" },
  { id: "/thinking", desc: "Toggle thinking" }, { id: "/details", desc: "Details" },
  { id: "/agent", desc: "Switch agent" },
  { id: "/exit", desc: "Exit APEX" },
]

const LEADER_CMDS: Record<string, { action: string; cmd?: string }> = {
  n: { action: "cmd", cmd: "/new" }, u: { action: "cmd", cmd: "/undo" },
  r: { action: "cmd", cmd: "/redo" }, c: { action: "cmd", cmd: "/compact" },
  m: { action: "overlay", cmd: "model" }, t: { action: "overlay", cmd: "theme" },
  s: { action: "overlay", cmd: "status" }, e: { action: "cmd", cmd: "/editor" },
  x: { action: "cmd", cmd: "/export" }, b: { action: "sidebar" },
  a: { action: "overlay", cmd: "agent" }, l: { action: "overlay", cmd: "session" },
  y: { action: "cmd", cmd: "/copy" }, q: { action: "quit" },
}

function calcMessageCost(pt: number, ct: number, mid: string) {
  const m = APEX_MODELS.find((x) => x.id === mid)
  if (!m?.inputCostPer1K || !m?.outputCostPer1K) return 0
  return (pt / 1000) * m.inputCostPer1K + (ct / 1000) * m.outputCostPer1K
}

function fuzzyMatch(text: string, query: string) {
  if (!query) return true
  const t = text.toLowerCase(), q = query.toLowerCase()
  let qi = 0
  for (let i = 0; i < t.length && qi < q.length; i++) if (t[i] === q[qi]) qi++
  return qi === q.length
}

function getKeybind(key: string) {
  try { return (globalThis as any).__TUI_CONFIG__?.keybinds?.[key] } catch { return undefined }
}
function getTuiConfig(key: string, def: any = undefined) {
  try { return (globalThis as any).__TUI_CONFIG__?.[key] ?? def } catch { return def }
}

export function ApexApp() {
  const { exit } = useApp()
  const [activeAgent, setActiveAgent] = useState("build")
  const [activeModel, setActiveModel] = useState("claude-sonnet-4")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [sessionStart] = useState(Date.now())
  const [totalPromptTokens, setTotalPromptTokens] = useState(0)
  const [totalCompletionTokens, setTotalCompletionTokens] = useState(0)
  const [totalSpent, setTotalSpent] = useState(0)
  const [livePromptTokens, setLivePromptTokens] = useState(0)
  const [liveCompletionTokens, setLiveCompletionTokens] = useState(0)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [leaderTimeout, setLeaderTimeout] = useState(DEFAULT_LEADER_TIMEOUT)

  const [leaderKeyActive, setLeaderKeyActive] = useState(false)
  const leaderTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showCP, setShowCP] = useState(false)
  const [cpSearch, setCpSearch] = useState("")
  const [cpIdx, setCpIdx] = useState(0)
  const [showFF, setShowFF] = useState(false)
  const [ffQuery, setFfQuery] = useState("")
  const [ffResults, setFfResults] = useState<string[]>([])
  const [ffIdx, setFfIdx] = useState(0)
  const ffCache = useRef<string[]>([])
  const sendMessageRef = useRef<((message: string) => void) | null>(null)
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
  const [retryCount, setRetryCount] = useState(0)
  const [inputHistory, setInputHistory] = useState<string[]>([])
  const [historyIdx, setHistoryIdx] = useState(-1)
  // Live usage of the request being streamed, and of the last accounted one
  // (used to dedupe the `chat_complete` WebSocket event).
  const liveUsageRef = useRef<{ pt: number; ct: number }>({ pt: 0, ct: 0 })
  const accountedUsageRef = useRef<{ pt: number; ct: number }>({ pt: 0, ct: 0 })
  const activeModelRef = useRef(activeModel)
  useEffect(() => { activeModelRef.current = activeModel }, [activeModel])

  // ── SyncClient (WebSocket EventBus) ──────────────────────
  const syncRef = useRef<SyncClient | null>(null)

  useEffect(() => {
    if (!HTTP_PORT) return
    const sync = new SyncClient(WS_URL, API_BASE)
    syncRef.current = sync

    sync.on("connected", () => { setConnectionError(null); setIsReconnecting(false) })
    sync.on("disconnected", () => { setConnectionError("WebSocket disconnected — reconnecting..."); setIsReconnecting(true) })
    sync.on("state", (state: any) => {
      if (state.model) setActiveModel(state.model)
      if (state.agent) setActiveAgent(state.agent)
    })
    sync.on("theme_changed", (data: any) => {
      // Theme was changed externally — apply it locally too.
      if (data.theme && setTheme(data.theme)) {
        setConnectionError(`Theme changed: ${data.theme}`)
      }
    })
    sync.on("chat_complete", (data: any) => {
      // Chat completed — update tokens if the SSE stream did not already.
      const u = data?.usage
      if (!u) return
      const pt = u.prompt_tokens ?? 0
      const ct = u.completion_tokens ?? 0
      if (pt === accountedUsageRef.current.pt && ct === accountedUsageRef.current.ct) return
      setTotalPromptTokens((p) => p + pt)
      setTotalCompletionTokens((c) => c + ct)
      setTotalSpent((s) => s + calcMessageCost(pt, ct, activeModelRef.current))
    })

    sync.connect()
    return () => { sync.disconnect(); syncRef.current = null }
  }, [])

  const agent = APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!
  const model = APEX_MODELS.find((m) => m.id === activeModel)
  const totalTokens = totalPromptTokens + totalCompletionTokens
  const contextPct = model?.contextWindow && totalTokens > 0 ? Math.min(100, (totalTokens / model.contextWindow) * 100) : (model?.contextWindow ? 0 : 0)
  const sessionDuration = (() => { const e = Math.floor((Date.now() - sessionStart) / 1000); return `${Math.floor(e / 60)}:${(e % 60).toString().padStart(2, "0")}` })()

  const scrollEndIdx = messages.length - scrollOffset
  const visibleMessages = messages.slice(Math.max(0, scrollEndIdx - MAX_VISIBLE), scrollEndIdx)
  const isScrolled = scrollOffset > 0
  const scrollPct = messages.length > MAX_VISIBLE ? Math.round((scrollOffset / Math.max(1, messages.length - MAX_VISIBLE)) * 100) : 0

  const anyOverlay = showCP || showFF || showHelp || showMS || showTS || showAS || showSO || showSL

  useEffect(() => { if (connectionError) { const t = setTimeout(() => { setConnectionError(null); setIsReconnecting(false) }, 5000); return () => clearTimeout(t) } }, [connectionError])
  useEffect(() => {
    api.getTuiConfig().then((cfg) => {
      try {
        (globalThis as any).__TUI_CONFIG__ = cfg
        if (cfg.leader_timeout) setLeaderTimeout(cfg.leader_timeout)
      } catch {}
    }).catch((err: Error) => {
      // Backend unavailable — TUI can still work with defaults for chat/stream
      // SyncClient will handle reconnection via WebSocket
      if (!syncRef.current?.connected) {
        console.warn(`TUI config fetch failed: ${err.message}`)
        setConnectionError("Backend API unavailable — some features may not work")
      }
    })
  }, [])
  useEffect(() => { if (!isGenerating && !anyOverlay) setScrollOffset(0) }, [isGenerating, messages.length])

  const handleSlashCommand = useCallback((cmd: string, arg: string) => {
    switch (cmd) {
      case "/new": case "/clear": setMessages([]); setInputValue(""); setTotalPromptTokens(0); setTotalCompletionTokens(0); setTotalSpent(0); setScrollOffset(0); setActiveSession(""); return true
      case "/help": setShowHelp(true); return true
      case "/models": setShowMS(true); setMsSearch(""); setMsIdx(0); return true
      case "/themes": fetchThemes(); setShowTS(true); setTsIdx(0); return true
      case "/agent": { const idx = APEX_AGENTS.findIndex((a) => a.id === (arg || "build")); if (idx >= 0) { setActiveAgent(APEX_AGENTS[idx].id); } else setShowAS(true); return true }
      case "/thinking": setThinkingMode((m) => m === "show" ? "hide" : m === "hide" ? "off" : "show"); return true
      case "/details": return true
      case "/copy": {
        const last = messages.filter((m) => m.role === "assistant").pop()
        if (last?.content) {
          try { (navigator as any).clipboard?.writeText?.(last.content) } catch {}
          setConnectionError("Copied last response")
        }
        return true
      }
      case "/exit": case "/quit": case "/q": exit(); return true
      case "/sessions": fetchSessions(); setShowSL(true); setSlIdx(0); return true
      case "/undo": api.undo().then((d) => { setConnectionError(d.error ? null : null) }).catch(() => { setConnectionError("Undo failed — backend unreachable") }); return true
      case "/redo": api.redo().then(() => {}).catch(() => { setConnectionError("Redo failed — backend unreachable") }); return true
      case "/compact": api.compact().then(() => {}).catch(() => { setConnectionError("Compact failed — backend unreachable") }); return true
      case "/theme": {
        if (!arg) { fetchThemes(); setShowTS(true); setTsIdx(0); return true }
        if (!hasTheme(arg)) { setConnectionError(`Unknown theme: ${arg}`); return true }
        setTheme(arg)
        syncRef.current?.rpc("theme_changed", { theme: arg })
        setConnectionError(`Theme: ${arg}`)
        return true
      }
      case "/session": {
        if (!arg) { fetchSessions(); setShowSL(true); setSlIdx(0); return true }
        setConnectionError(`Loading session ${arg}...`)
        api.loadSession(arg)
          .then((d) => {
            if (d.error) { setConnectionError(`Session error: ${d.error}`); return }
            setActiveSession(arg)
            return api.sessionHistory(arg)
              .then((h) => {
                const msgs: ChatMessage[] = (h.messages ?? [])
                  .filter((m: any) => m?.role === "user" || m?.role === "assistant")
                  .map((m: any, i: number) => ({
                    id: `msg-${i}-loaded`,
                    role: m.role,
                    content: typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? ""),
                    agent: activeAgent,
                    model: h.model ?? activeModel,
                    timestamp: Date.now(),
                    promptTokens: 0,
                    completionTokens: 0,
                    cost: 0,
                  }))
                setMessages(msgs)
                setScrollOffset(0)
                setConnectionError(`Session "${arg}" loaded (${msgs.length} messages)`)
              })
          })
          .catch(() => setConnectionError("Session load failed — backend unreachable"))
        return true
      }
      case "/export": {
        api.exportSession(activeSession)
          .then((d) => setConnectionError(d.path ? `Exported to ${d.path}` : `Export failed: ${d.error ?? "unknown"}`))
          .catch(() => setConnectionError("Export failed — backend unreachable"))
        return true
      }
      case "/share": {
        api.share(activeSession, arg)
          .then((d) => setConnectionError(d.url ? `Shared: ${d.url}` : `Share failed: ${d.error ?? "unknown"}`))
          .catch(() => setConnectionError("Share failed — backend unreachable"))
        return true
      }
      case "/unshare": {
        if (!arg) { setConnectionError("Usage: /unshare <share_id>"); return true }
        api.unshare(arg)
          .then((d) => setConnectionError(d.ok ? `Unshared ${arg}` : `Share not found: ${arg}`))
          .catch(() => setConnectionError("Unshare failed — backend unreachable"))
        return true
      }
      case "/editor": {
        const editor = process.env.EDITOR || process.env.VISUAL || "vi"
        const dir = mkdtempSync(join(tmpdir(), "apex-editor-"))
        const file = join(dir, "prompt.md")
        try {
          writeFileSync(file, "# Enter your prompt\n\n")
          // Leave the alternate screen so the editor gets a clean terminal.
          process.stdout.write("\x1b[?1049l")
          try {
            spawnSync(editor, [file], { stdio: "inherit" })
          } catch {
            setConnectionError(`Could not launch editor: ${editor}`)
          }
          process.stdout.write("\x1b[?1049h\x1b[2J\x1b[H")
          const content = readFileSync(file, "utf8")
          const prompt = content
            .split("\n")
            .filter((l) => !l.startsWith("#"))
            .join("\n")
            .trim()
          if (prompt) sendMessageRef.current?.(prompt)
        } finally {
          try { rmSync(dir, { recursive: true, force: true }) } catch {}
        }
        return true
      }
      case "/cost": {
        api.cost().then((d) => {
          const usage = d.usage ?? {}
          const content = [
            "Token usage (session):",
            `  Input: ${usage.prompt_tokens ?? 0}`,
            `  Output: ${usage.completion_tokens ?? 0}`,
            `  Total tokens: ${usage.total_tokens ?? 0}`,
            `  Cost: $${(d.total_cost ?? 0).toFixed(6)} (${d.currency ?? "USD"}, model ${d.model ?? activeModelRef.current})`,
          ].join("\n")
          setMessages((prev) => [...prev, { id: `msg-${Date.now()}-c`, role: "assistant", content, agent: "build", model: activeModelRef.current, timestamp: Date.now(), promptTokens: 0, completionTokens: 0, cost: 0 }])
        }).catch(() => setConnectionError("Cost request failed — backend unreachable"))
        return true
      }
      case "/init": case "/connect": return false
      default: return false
    }
  }, [exit, activeSession, activeAgent, activeModel])

  const sendMessage = useCallback(async (userMessage: string) => {
    if (userMessage.startsWith("/")) {
      const parts = userMessage.split(/\s+/)
      const cmd = parts[0].toLowerCase()
      const arg = parts.slice(1).join(" ")
      if (handleSlashCommand(cmd, arg)) { return }
    }
    setIsGenerating(true); setConnectionError(null); setIsReconnecting(false)
    setLivePromptTokens(0); setLiveCompletionTokens(0)
    liveUsageRef.current = { pt: 0, ct: 0 }
    const userMsg: ChatMessage = { id: `msg-${Date.now()}-u`, role: "user", content: userMessage, timestamp: Date.now() }
    setMessages((p) => [...p, userMsg])
    const aid = `msg-${Date.now()}-a`
    setMessages((p) => [...p, { id: aid, role: "assistant", content: "", agent: activeAgent, model: activeModel, timestamp: Date.now(), promptTokens: 0, completionTokens: 0, cost: 0 }])
    try {
      const { full, usage } = await api.chatStream({
        message: userMessage,
        model: activeModel,
        onChunk: (fullText) => {
          setMessages((prev) => { const l = prev[prev.length - 1]; if (l?.id === aid) return [...prev.slice(0, -1), { ...l, content: fullText }]; return prev })
        },
      })
      const fp = usage.prompt_tokens ?? 0
      const fc = usage.completion_tokens ?? 0
      liveUsageRef.current = { pt: fp, ct: fc }
      setLivePromptTokens(fp); setLiveCompletionTokens(fc)
      const mc = calcMessageCost(fp, fc, activeModel)
      setMessages((prev) => { const l = prev[prev.length - 1]; if (l?.id === aid) return [...prev.slice(0, -1), { ...l, content: full || "(empty)", promptTokens: fp, completionTokens: fc, cost: mc }]; return prev })
      setTotalPromptTokens((p) => p + fp); setTotalCompletionTokens((c) => c + fc); setTotalSpent((s) => s + mc)
      accountedUsageRef.current = { pt: fp, ct: fc }
      setRetryCount(0)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes("fetch") || msg.includes("ECONNREFUSED") || msg.includes("NetworkError")) { setConnectionError("Cannot connect to APEX backend on port " + HTTP_PORT); setIsReconnecting(true); setRetryCount((c) => c + 1) }
      else setConnectionError(`Error: ${msg}`)
      setMessages((p) => [...p, { id: aid, role: "assistant", content: `Error: ${msg}`, agent: activeAgent, model: activeModel, timestamp: Date.now(), promptTokens: 0, completionTokens: 0, cost: 0 }])
    } finally { setIsGenerating(false); setLivePromptTokens(0); setLiveCompletionTokens(0) }
  }, [activeAgent, activeModel, livePromptTokens, liveCompletionTokens])

  // Allow slash commands declared above to dispatch prompts (used by /editor).
  sendMessageRef.current = sendMessage as (message: string) => Promise<void>

  const sendBash = useCallback(async (cmd: string) => {
    setIsGenerating(true); setConnectionError(null)
    setMessages((p) => [...p, { id: `msg-${Date.now()}-u`, role: "user", content: `! ${cmd}`, timestamp: Date.now() }])
    const rid = `msg-${Date.now()}-bash`
    try {
      const d = await api.bash(cmd)
      setMessages((p) => [...p, { id: rid, role: "assistant", content: "```\n" + (d.stdout ?? d.output ?? d.result ?? JSON.stringify(d)) + "\n```", agent: "shell", timestamp: Date.now(), promptTokens: 0, completionTokens: 0, cost: 0 }])
    } catch (e: any) { setConnectionError(`Bash error: ${e.message}`); setMessages((p) => [...p, { id: rid, role: "assistant", content: `Bash error: ${e.message}`, agent: "shell", timestamp: Date.now(), promptTokens: 0, completionTokens: 0, cost: 0 }]) }
    finally { setIsGenerating(false) }
  }, [])

  const fetchFiles = useCallback(async () => {
    if (ffCache.current.length > 0) return
    try { ffCache.current = await api.listFiles() }
    catch { ffCache.current = ["src/", "README.md", "package.json", "tsconfig.json"] }
  }, [])

  const fetchThemes = useCallback(async () => {
    try { setThemes(await api.listThemes()) }
    catch { setThemes([{ id: "default", name: "Default" }, { id: "light", name: "Light" }]) }
  }, [])

  const fetchSessions = useCallback(async () => {
    try { setSessions(await api.listSessions()) }
    catch { setSessions([]) }
  }, [])

  const handleLeader = useCallback((k: string) => {
    const e = LEADER_CMDS[k]; if (!e) return
    if (e.action === "cmd" && e.cmd) sendMessage(e.cmd)
    else if (e.action === "sidebar") setSidebarVisible((v) => !v)
    else if (e.action === "quit") exit()
    else if (e.action === "overlay") {
      if (e.cmd === "model") { setShowMS(true); setMsSearch(""); setMsIdx(Math.max(0, APEX_MODELS.findIndex((m) => m.id === activeModel))) }
      if (e.cmd === "theme") { fetchThemes(); setShowTS(true); setTsIdx(0) }
      if (e.cmd === "status") setShowSO(true)
      if (e.cmd === "agent") { setShowAS(true); setAsIdx(APEX_AGENTS.findIndex((a) => a.id === activeAgent)) }
      if (e.cmd === "session") { fetchSessions(); setShowSL(true); setSlIdx(0) }
    }
  }, [sendMessage, fetchThemes, fetchSessions, activeAgent, exit])

  const retryConnection = useCallback(() => {
    setConnectionError(null); setIsReconnecting(false)
    const last = messages[messages.length - 1]
    if (last?.role === "user") sendMessage(last.content)
  }, [messages, sendMessage])

  const filteredCommands = COMMANDS.filter((c) => fuzzyMatch(c.id + " " + c.desc, cpSearch))
  const filteredModels = APEX_MODELS.filter((m) => fuzzyMatch(m.id + " " + m.name + " " + m.provider, msSearch))
  const filteredFiles = ffResults.filter((f) => fuzzyMatch(f, ffQuery))

  useInput((input, key) => {
    if (leaderKeyActive) { clearTimeout(leaderTimer.current!); setLeaderKeyActive(false); handleLeader(input.toLowerCase()); return }
    if (showCP) {
      if (key.escape) { setShowCP(false); setCpSearch("") }
      else if (key.return && filteredCommands.length > 0) { const c = filteredCommands[cpIdx % filteredCommands.length]; setShowCP(false); setCpSearch(""); sendMessage(c.id) }
      else if (key.upArrow) setCpIdx((i) => (i - 1 + filteredCommands.length) % filteredCommands.length)
      else if (key.downArrow) setCpIdx((i) => (i + 1) % filteredCommands.length)
      else if (key.backspace || key.delete) { setCpSearch((s) => s.slice(0, -1)); setCpIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setCpSearch((s) => s + input); setCpIdx(0) }
      return
    }
    if (showHelp) { if (key.escape) setShowHelp(false); return }
    if (showMS) {
      if (key.escape) { setShowMS(false); setMsSearch("") }
      else if (key.return && filteredModels.length > 0) { setActiveModel(filteredModels[msIdx % filteredModels.length].id); setShowMS(false); setMsSearch("") }
      else if (key.upArrow) setMsIdx((i) => (i - 1 + filteredModels.length) % filteredModels.length)
      else if (key.downArrow) setMsIdx((i) => (i + 1) % filteredModels.length)
      else if (key.backspace || key.delete) { setMsSearch((s) => s.slice(0, -1)); setMsIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setMsSearch((s) => s + input); setMsIdx(0) }
      return
    }
    if (showTS) {
      if (key.escape) setShowTS(false)
      else if (key.return && themes.length > 0) { setShowTS(false); sendMessage(`/theme ${themes[tsIdx % themes.length].id}`) }
      else if (key.upArrow) setTsIdx((i) => (i - 1 + themes.length) % themes.length)
      else if (key.downArrow) setTsIdx((i) => (i + 1) % themes.length)
      return
    }
    if (showAS) {
      if (key.escape) setShowAS(false)
      else if (key.return) { setActiveAgent(APEX_AGENTS[asIdx % APEX_AGENTS.length].id); setShowAS(false) }
      else if (key.upArrow) setAsIdx((i) => (i - 1 + APEX_AGENTS.length) % APEX_AGENTS.length)
      else if (key.downArrow) setAsIdx((i) => (i + 1) % APEX_AGENTS.length)
      return
    }
    if (showSO) { if (key.escape) setShowSO(false); return }
    if (showSL) {
      if (key.escape) setShowSL(false)
      else if (key.return && sessions.length > 0) { setShowSL(false); sendMessage(`/session ${sessions[slIdx % sessions.length].id}`) }
      else if (key.upArrow) setSlIdx((i) => (i - 1 + sessions.length) % sessions.length)
      else if (key.downArrow) setSlIdx((i) => (i + 1) % sessions.length)
      return
    }
    if (showFF) {
      if (key.escape) { setShowFF(false); setFfQuery("") }
      else if ((key.return || key.tab) && filteredFiles.length > 0) {
        const f = filteredFiles[ffIdx % filteredFiles.length]
        const at = inputValue.lastIndexOf("@"); setInputValue((at >= 0 ? inputValue.slice(0, at) : inputValue) + "@" + f)
        setShowFF(false); setFfQuery("")
      }
      else if (key.upArrow) setFfIdx((i) => (i - 1 + filteredFiles.length) % filteredFiles.length)
      else if (key.downArrow) setFfIdx((i) => (i + 1) % filteredFiles.length)
      else if (key.backspace || key.delete) { setFfQuery((q) => q.slice(0, -1)); setFfIdx(0) }
      else if (input && !key.ctrl && !key.meta) { setFfQuery((q) => q + input); setFfIdx(0) }
      return
    }
    if (key.ctrl && input === "x") { setLeaderKeyActive(true); leaderTimer.current = setTimeout(() => setLeaderKeyActive(false), leaderTimeout); return }
    if (key.ctrl && input === "p") { setShowCP(true); setCpSearch(""); setCpIdx(0); return }
    if (key.ctrl && input === "k") { setShowMS(true); setMsSearch(""); setMsIdx(APEX_MODELS.findIndex((m) => m.id === activeModel)); return }
    if (key.ctrl && input === "t") { setThinkingMode((m) => m === "show" ? "hide" : m === "hide" ? "off" : "show"); return }
    if (input === "?" && !key.ctrl) { setShowHelp(true); return }
    if (key.ctrl && input === "q") { exit(); return }
    if (key.ctrl && input === "o") { setSidebarVisible((v) => !v); return }
    if (key.ctrl && input === "l") { setMessages([]); setInputValue(""); setTotalPromptTokens(0); setTotalCompletionTokens(0); setTotalSpent(0); setScrollOffset(0); return }
    if (key.ctrl && input === "u") { setInputValue(""); return }
    if (key.ctrl && input === "w") { setInputValue((v) => v.replace(/\s*\S+\s*$/, "")); return }
    if (key.ctrl && input === "d") { const nv = inputValue.slice(1); setInputValue(nv); const at = nv.lastIndexOf("@"); if (at >= 0) { setShowFF(true); setFfQuery(nv.slice(at + 1)); setFfIdx(0); fetchFiles() } return }
    if (input === "r" && !key.ctrl && !key.meta && isReconnecting) { retryConnection?.(); return }
    if (key.tab && !key.shift && !showFF) { const i = APEX_AGENTS.findIndex((a) => a.id === activeAgent); setActiveAgent(APEX_AGENTS[(i + 1) % APEX_AGENTS.length]!.id); return }
    if (key.shift && key.tab && !showFF) { const i = APEX_AGENTS.findIndex((a) => a.id === activeAgent); setActiveAgent(APEX_AGENTS[(i - 1 + APEX_AGENTS.length) % APEX_AGENTS.length]!.id); return }
    if (key.return && !key.shift && inputValue.trim() && !isGenerating) { const m = inputValue.trim(); setInputValue(""); setInputHistory((h) => [m, ...h].slice(0, 50)); setHistoryIdx(-1); if (m.startsWith("!")) sendBash(m.slice(1).trim()); else sendMessage(m); return }
    if (key.return && key.shift) { setInputValue((v) => v + "\n"); return }
    if (key.upArrow && inputHistory.length > 0) {
      const next = Math.min(historyIdx + 1, inputHistory.length - 1)
      setHistoryIdx(next); setInputValue(inputHistory[next] ?? ""); return
    }
    if (key.downArrow && historyIdx >= 0) {
      const next = historyIdx - 1
      if (next < 0) { setHistoryIdx(-1); setInputValue(""); return }
      setHistoryIdx(next); setInputValue(inputHistory[next] ?? ""); return
    }
    if (key.ctrl && input === "g") { setScrollOffset(Math.max(0, messages.length - 1)); return }
    if ((key as any).home) { setScrollOffset(Math.max(0, messages.length - 1)); return }
    if ((key as any).end) { setScrollOffset(0); return }
    if (key.pageUp) { setScrollOffset((o) => Math.min(o + MAX_VISIBLE, Math.max(0, messages.length - 1))); return }
    if (key.pageDown) { setScrollOffset((o) => Math.max(0, o - MAX_VISIBLE)); return }
    if (key.backspace || key.delete) {
      const at = inputValue.lastIndexOf("@")
      if (at >= 0 && inputValue.slice(at).startsWith("@")) {
        const nv = inputValue.slice(0, -1); setInputValue(nv)
        const newAt = nv.lastIndexOf("@")
        if (newAt >= 0) { setShowFF(true); setFfQuery(nv.slice(newAt + 1)); setFfIdx(0); fetchFiles() } else { setShowFF(false); setFfQuery("") }
        return
      }
      setInputValue((v) => v.slice(0, -1)); return
    }
    if (input && !key.ctrl && !key.meta) {
      const nv = inputValue + input; setInputValue(nv)
      if (input === "@") { setShowFF(true); setFfQuery(""); setFfIdx(0); fetchFiles() }
      else if (showFF || inputValue.includes("@")) { const at = nv.lastIndexOf("@"); if (at >= 0) { setShowFF(true); setFfQuery(nv.slice(at + 1)); setFfIdx(0) } }
    }
  })

  const closeOverlay = () => { setShowCP(false); setShowHelp(false); setShowMS(false); setShowTS(false); setShowAS(false); setShowSO(false); setShowSL(false); setShowFF(false); setFfQuery("") }

  const mainContent = (
    <Box flexDirection="row" flexGrow={1}>
      {sidebarVisible && <Sidebar activeAgent={activeAgent} onAgentSelect={setActiveAgent} />}
      <ChatPanel messages={visibleMessages} inputValue={inputValue} activeAgent={activeAgent} activeModel={activeModel} isGenerating={isGenerating} />
    </Box>
  )

  return (
    <Box flexDirection="column" flexGrow={1}>
      {connectionError && (
        <Box width="100%" justifyContent="space-between">
          <Text backgroundColor={apexTheme.error} color="#000000" bold> [!] {connectionError} </Text>
          {isReconnecting && <Text backgroundColor={apexTheme.warning} color="#000000" bold> [~] Retry {retryCount} — press R to retry </Text>}
        </Box>
      )}
      {leaderKeyActive && (
        <Box width="100%" justifyContent="center">
          <Text backgroundColor={apexTheme.accent} color="#000000" bold> ⌨ Leader key active — press a shortcut key </Text>
        </Box>
      )}
      <Box width="100%" justifyContent="space-between">
        <Box>
          <Text color={agent.color} bold>{agent.name}</Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={apexTheme.fg}>{model?.name ?? "No Model"}</Text>
        </Box>
        <Box>
          <Text color={apexTheme.dimGray}>{messages.length} msgs</Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={contextPct > 80 ? apexTheme.warning : apexTheme.fg}>{contextPct.toFixed(1)}% ctx</Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={apexTheme.green}>${totalSpent.toFixed(4)}</Text>
        </Box>
      </Box>

      {showCP && (
        <CommandPalette
          commands={COMMANDS}
          query={cpSearch}
          index={cpIdx}
          onSelect={(id) => { setShowCP(false); setCpSearch(""); sendMessage(id) }}
        />
      )}
      {showHelp && (
        <HelpOverlay onClose={() => setShowHelp(false)} />
      )}
      {showMS && (
        <ModelSelector
          models={APEX_MODELS}
          query={msSearch}
          index={msIdx}
          onSelect={(id) => { setActiveModel(id); setShowMS(false); setMsSearch("") }}
        />
      )}
      {showTS && (
        <ThemeSelector
          themes={themes}
          index={tsIdx}
          onSelect={(id) => { setShowTS(false); sendMessage(`/theme ${id}`) }}
        />
      )}
      {showAS && (
        <AgentSelector
          agents={APEX_AGENTS}
          index={asIdx}
          onSelect={(id) => { setActiveAgent(id); setShowAS(false) }}
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
          onSelect={(id) => { setShowSL(false); sendMessage(`/session ${id}`) }}
        />
      )}

      {!anyOverlay && mainContent}

      {!anyOverlay && isScrolled && (
        <Text color={apexTheme.yellow} bold>↑ Scrolled up ({scrollPct}%) — PgUp/PgDown to scroll</Text>
      )}
      {!anyOverlay && thinkingMode !== "show" && (
        <Text color={apexTheme.gray}>Thinking: {thinkingMode} (Ctrl+T to cycle)</Text>
      )}

      {showFF && (
        <FileFinder
          files={ffResults}
          query={ffQuery}
          index={ffIdx}
          onSelect={(f) => {
            const at = inputValue.lastIndexOf("@")
            setInputValue((at >= 0 ? inputValue.slice(0, at) : inputValue) + "@" + f)
            setShowFF(false); setFfQuery("")
          }}
        />
      )}

      <StatusBar activeAgent={activeAgent} activeModel={activeModel} totalTokens={totalTokens} totalPromptTokens={totalPromptTokens} totalCompletionTokens={totalCompletionTokens} totalSpent={totalSpent} contextPct={contextPct} messageCount={messages.length} sessionDuration={sessionDuration} livePromptTokens={livePromptTokens} liveCompletionTokens={liveCompletionTokens} thinkingMode={thinkingMode} />
    </Box>
  )
}
