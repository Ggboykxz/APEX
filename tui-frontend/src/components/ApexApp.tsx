import { useKeyboard, useRenderer } from "@opentui/react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"
import { Sidebar } from "./Sidebar.js"
import { ChatPanel } from "./ChatPanel.js"
import { StatusBar } from "./StatusBar.js"
import { ModelSelector } from "./ModelSelector.js"
import { HelpPanel } from "./HelpPanel.js"
import { ToolPanel } from "./ToolPanel.js"

const HTTP_PORT = parseInt(process.env.APEX_HTTP_PORT ?? "8080", 10)
const API_BASE = `http://127.0.0.1:${HTTP_PORT}`

function parseSSE(data: string): { chunk?: string; usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number } } {
  if (data.startsWith("data: ")) {
    try {
      return JSON.parse(data.slice(6))
    } catch {
      return {}
    }
  }
  return {}
}

function calcMessageCost(promptTokens: number, completionTokens: number, modelId: string): number {
  const model = APEX_MODELS.find((m) => m.id === modelId)
  if (!model?.inputCostPer1K || !model?.outputCostPer1K) return 0
  return (promptTokens / 1000) * model.inputCostPer1K + (completionTokens / 1000) * model.outputCostPer1K
}

export function ApexApp() {
  const renderer = useRenderer()

  const [activeAgent, setActiveAgent] = useState("coder")
  const [activeModel, setActiveModel] = useState("claude-4-sonnet")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [toolPanelVisible, setToolPanelVisible] = useState(false)
  const [modelSelectorVisible, setModelSelectorVisible] = useState(false)
  const [modelSearch, setModelSearch] = useState("")
  const [helpVisible, setHelpVisible] = useState(false)
  const [helpTab, setHelpTab] = useState<"keybindings" | "agents" | "tools">("keybindings")
  const [sessionStart] = useState(Date.now())
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const [totalPromptTokens, setTotalPromptTokens] = useState(0)
  const [totalCompletionTokens, setTotalCompletionTokens] = useState(0)
  const [totalSpent, setTotalSpent] = useState(0)

  const [livePromptTokens, setLivePromptTokens] = useState(0)
  const [liveCompletionTokens, setLiveCompletionTokens] = useState(0)

  const agent = useMemo(() => APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!, [activeAgent])
  const model = useMemo(() => APEX_MODELS.find((m) => m.id === activeModel), [activeModel])

  const totalTokens = useMemo(() => totalPromptTokens + totalCompletionTokens, [totalPromptTokens, totalCompletionTokens])

  const contextPct = useMemo(() => {
    if (!model?.contextWindow || totalTokens === 0) return 0
    return Math.min(100, (totalTokens / model.contextWindow) * 100)
  }, [model, totalTokens])

  const sessionDuration = useMemo(() => {
    const elapsed = Math.floor((Date.now() - sessionStart) / 1000)
    const mins = Math.floor(elapsed / 60)
    const secs = elapsed % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }, [sessionStart, messages.length])

  useKeyboard((key) => {
    if (key.ctrl && key.name === "k") {
      setModelSelectorVisible((v) => !v)
      setModelSearch("")
      return
    }
    if (key.ctrl && key.name === "o") {
      setSidebarVisible((v) => !v)
      return
    }
    if (key.ctrl && key.name === "t") {
      setToolPanelVisible((v) => !v)
      return
    }
    if (key.name === "?" && !modelSelectorVisible) {
      setHelpVisible((v) => !v)
      return
    }
    if (key.name === "escape") {
      if (modelSelectorVisible) { setModelSelectorVisible(false); return }
      if (helpVisible) { setHelpVisible(false); return }
    }
    if (key.name === "tab" && !modelSelectorVisible && !helpVisible) {
      const currentIdx = APEX_AGENTS.findIndex((a) => a.id === activeAgent)
      const nextIdx = (currentIdx + 1) % APEX_AGENTS.length
      setActiveAgent(APEX_AGENTS[nextIdx]!.id)
      return
    }
    if (key.ctrl && key.name === "q") {
      process.exit(0)
    }
    if (key.ctrl && key.name === "l") {
      setMessages([])
      setInputValue("")
      setTotalPromptTokens(0)
      setTotalCompletionTokens(0)
      setTotalSpent(0)
      return
    }
  })

  useEffect(() => {
    if (renderer) renderer.setBackgroundColor(apexTheme.bg)
  }, [renderer])

  useEffect(() => {
    if (connectionError) {
      const timer = setTimeout(() => setConnectionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [connectionError])

  const sendMessage = useCallback(async (userMessage: string) => {
    setIsGenerating(true)
    setConnectionError(null)
    setLivePromptTokens(0)
    setLiveCompletionTokens(0)

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-u`,
      role: "user",
      content: userMessage,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])

    const assistantId = `msg-${Date.now()}-a`

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, model: activeModel }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        setConnectionError(`Server error ${response.status}: ${errorText}`)
        setIsGenerating(false)
        return
      }

      if (!response.body) {
        setConnectionError("Empty response from server")
        setIsGenerating(false)
        return
      }

      let fullContent = ""

      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          agent: activeAgent,
          model: activeModel,
          timestamp: Date.now(),
          promptTokens: 0,
          completionTokens: 0,
          cost: 0,
        },
      ])

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.trim() || line.startsWith(":")) continue
          const parsed = parseSSE(line)
          if (parsed.chunk) {
            fullContent += parsed.chunk
            setMessages((prev) => {
              const last = prev[prev.length - 1]
              if (last?.id === assistantId) {
                return [...prev.slice(0, -1), { ...last, content: fullContent }]
              }
              return prev
            })
          }
          if (parsed.usage) {
            const pt = parsed.usage.prompt_tokens ?? 0
            const ct = parsed.usage.completion_tokens ?? 0
            setLivePromptTokens(pt)
            setLiveCompletionTokens(ct)
          }
        }
      }

      if (buffer.trim()) {
        const parsed = parseSSE(buffer)
        if (parsed.chunk) fullContent += parsed.chunk
      }

      const finalPrompt = livePromptTokens || 0
      const finalCompletion = liveCompletionTokens || 0
      const msgCost = calcMessageCost(finalPrompt, finalCompletion, activeModel)

      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.id === assistantId) {
          return [...prev.slice(0, -1), {
            ...last,
            content: fullContent || "(empty response)",
            promptTokens: finalPrompt,
            completionTokens: finalCompletion,
            cost: msgCost,
          }]
        }
        return prev
      })

      setTotalPromptTokens((p) => p + finalPrompt)
      setTotalCompletionTokens((c) => c + finalCompletion)
      setTotalSpent((s) => s + msgCost)

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes("fetch") || msg.includes("ECONNREFUSED") || msg.includes("NetworkError")) {
        setConnectionError("Cannot connect to APEX backend. Make sure `apex --tui` is running.")
      } else {
        setConnectionError(`Error: ${msg}`)
      }
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: `Error: ${msg}`,
          agent: activeAgent,
          model: activeModel,
          timestamp: Date.now(),
          promptTokens: 0,
          completionTokens: 0,
          cost: 0,
        },
      ])
    } finally {
      setIsGenerating(false)
      setLivePromptTokens(0)
      setLiveCompletionTokens(0)
    }
  }, [activeAgent, activeModel])

  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isGenerating) return
    const msg = inputValue.trim()
    setInputValue("")
    sendMessage(msg)
  }, [inputValue, isGenerating, sendMessage])

  return (
    <box id="apex-root" style={{ flexDirection: "column", flexGrow: 1, backgroundColor: apexTheme.bg }}>
      {connectionError ? (
        <box style={{ height: 1, flexDirection: "row", backgroundColor: apexTheme.error }}>
          <text>
            <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>⚠ {connectionError}</span>
          </text>
        </box>
      ) : null}

      <box id="apex-titlebar" style={{ height: 1, flexDirection: "row", justifyContent: "center", backgroundColor: agent?.color ?? apexTheme.cyan }}>
        <text>
          <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>▲ APEX</span>
          <span style={{ fg: "#000000" }}> — {agent?.name ?? "Coder"} · {model?.name ?? "No Model"}</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000" }}>{messages.length} msgs</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000" }}>{contextPct.toFixed(1)}% ctx</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000" }}>${totalSpent.toFixed(4)}</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>Ctrl+K</span>
          <span style={{ fg: "#000000" }}> Models  </span>
          <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>Tab</span>
          <span style={{ fg: "#000000" }}> Agents  </span>
          <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>?</span>
          <span style={{ fg: "#000000" }}> Help</span>
        </text>
      </box>

      <box id="apex-main" style={{ flexDirection: "row", flexGrow: 1 }}>
        <Sidebar activeAgent={activeAgent} onAgentSelect={setActiveAgent} visible={sidebarVisible} />
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSubmit={handleSubmit}
          activeAgent={activeAgent}
          activeModel={activeModel}
          isGenerating={isGenerating}
          livePromptTokens={livePromptTokens}
          liveCompletionTokens={liveCompletionTokens}
          liveCost={calcMessageCost(livePromptTokens, liveCompletionTokens, activeModel)}
        />
        <ToolPanel visible={toolPanelVisible} activeAgent={activeAgent} />
      </box>

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
      />

      <ModelSelector
        visible={modelSelectorVisible}
        searchQuery={modelSearch}
        onSearchChange={setModelSearch}
        onSelect={setActiveModel}
        onClose={() => setModelSelectorVisible(false)}
        activeModel={activeModel}
        activeAgent={activeAgent}
      />

      <HelpPanel
        visible={helpVisible}
        onClose={() => setHelpVisible(false)}
        tab={helpTab}
        onTabChange={setHelpTab}
        activeAgent={activeAgent}
      />
    </box>
  )
}