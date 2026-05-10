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
  const [totalTokens, setTotalTokens] = useState(0)
  const [sessionStart] = useState(Date.now())

  const agent = useMemo(() => APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!, [activeAgent])
  const model = useMemo(() => APEX_MODELS.find((m) => m.id === activeModel), [activeModel])

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
      return
    }
  })

  useEffect(() => {
    if (renderer) renderer.setBackgroundColor(apexTheme.bg)
  }, [renderer])

  const simulateResponse = useCallback((userMessage: string) => {
    setIsGenerating(true)
    const responses: Record<string, string[]> = {
      coder: [
        "I'll analyze the code and make the necessary changes. Let me search for the relevant files first.",
        "The implementation looks good. I've refactored the code to follow best practices and added type safety.",
        "I've created the new module with proper error handling and comprehensive tests.",
        "Let me check the current architecture and propose an optimal solution for this feature.",
      ],
      architect: [
        "Based on the requirements, I recommend a microservices architecture with event-driven communication.",
        "The current architecture has a coupling issue. Let me propose a cleaner separation of concerns.",
        "After analysis, the optimal approach would be a hexagonal architecture with dependency injection.",
      ],
      reviewer: [
        "I found 3 potential issues: a memory leak in the event handler, an unhandled promise rejection, and a race condition.",
        "The code quality is good overall, but I suggest adding input validation and improving error messages.",
        "Security audit complete: 1 critical vulnerability found. I'll recommend a patch immediately.",
      ],
      devops: [
        "I've set up the Docker configuration with multi-stage builds for optimal image size.",
        "The CI/CD pipeline is configured with automated testing and deployment stages.",
        "Kubernetes manifests generated with auto-scaling policies and health checks.",
      ],
      analyst: [
        "Based on the data analysis, the performance bottleneck is in the database queries.",
        "The metrics show a 23% improvement after the optimization. Here's the detailed report.",
        "Research complete: the optimal strategy is to implement caching at the API layer.",
      ],
    }
    const agentResponses = responses[activeAgent] ?? responses["coder"]!
    const responseText = agentResponses[Math.floor(Math.random() * agentResponses.length)]!

    const toolCallDelay = 200 + Math.random() * 400

    setTimeout(() => {
      const tokens = Math.floor(Math.random() * 600) + 150
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: responseText,
        agent: activeAgent,
        model: activeModel,
        timestamp: Date.now(),
        tokens,
      }
      setMessages((prev) => [...prev, assistantMessage])
      setTotalTokens((prev) => prev + tokens)
      setIsGenerating(false)
    }, 600 + Math.random() * 1000)
  }, [activeAgent, activeModel])

  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isGenerating) return
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: inputValue.trim(),
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    simulateResponse(inputValue.trim())
  }, [inputValue, isGenerating, simulateResponse])

  return (
    <box id="apex-root" style={{ flexDirection: "column", flexGrow: 1, backgroundColor: apexTheme.bg }}>
      <box id="apex-titlebar" style={{ height: 1, flexDirection: "row", justifyContent: "center", backgroundColor: agent?.color ?? apexTheme.cyan }}>
        <text>
          <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>▲ APEX</span>
          <span style={{ fg: "#000000" }}> — {agent?.name ?? "Coder"} · {model?.name ?? "No Model"}</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000" }}>{messages.length} messages</span>
          <span style={{ fg: "#000000" }}> │ </span>
          <span style={{ fg: "#000000" }}>{totalTokens.toLocaleString()} tokens</span>
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
        />
        <ToolPanel visible={toolPanelVisible} activeAgent={activeAgent} />
      </box>

      <StatusBar
        activeAgent={activeAgent}
        activeModel={activeModel}
        totalTokens={totalTokens}
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