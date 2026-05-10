/**
 * APEX TUI - Main Application Component
 * The complete APEX Terminal User Interface
 */

import { TextAttributes } from "@opentui/core"
import { useKeyboard, useRenderer } from "@opentui/react"
import { useCallback, useEffect, useMemo, useState } from "react"

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

  // ---- State ----
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

  // ---- Computed ----
  const agent = useMemo(() => APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!, [activeAgent])
  const model = useMemo(() => APEX_MODELS.find((m) => m.id === activeModel), [activeModel])

  const sessionDuration = useMemo(() => {
    const elapsed = Math.floor((Date.now() - sessionStart) / 1000)
    const mins = Math.floor(elapsed / 60)
    const secs = elapsed % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }, [sessionStart, messages.length])

  // ---- Keyboard handler ----
  useKeyboard((key) => {
    // Model selector toggle
    if (key.ctrl && key.name === "k") {
      setModelSelectorVisible((v) => !v)
      setModelSearch("")
      return
    }

    // Toggle sidebar
    if (key.ctrl && key.name === "o") {
      setSidebarVisible((v) => !v)
      return
    }

    // Toggle tools panel
    if (key.ctrl && key.name === "t") {
      setToolPanelVisible((v) => !v)
      return
    }

    // Help panel toggle
    if (key.name === "?" && !modelSelectorVisible) {
      setHelpVisible((v) => !v)
      return
    }

    // Close overlays with Escape
    if (key.name === "escape") {
      if (modelSelectorVisible) {
        setModelSelectorVisible(false)
        return
      }
      if (helpVisible) {
        setHelpVisible(false)
        return
      }
    }

    // Switch agent with Tab
    if (key.name === "tab" && !modelSelectorVisible && !helpVisible) {
      const currentIdx = APEX_AGENTS.findIndex((a) => a.id === activeAgent)
      const nextIdx = (currentIdx + 1) % APEX_AGENTS.length
      setActiveAgent(APEX_AGENTS[nextIdx]!.id)
      return
    }

    // Quit
    if (key.ctrl && key.name === "q") {
      process.exit(0)
    }
  })

  // ---- Set background color ----
  useEffect(() => {
    if (renderer) {
      renderer.setBackgroundColor(apexTheme.bg)
    }
  }, [renderer])

  // ---- Simulate AI response ----
  const simulateResponse = useCallback(
    (userMessage: string) => {
      setIsGenerating(true)

      const responses: Record<string, string[]> = {
        coder: [
          "I'll analyze the code and make the necessary changes. Let me search for the relevant files first.",
          "The implementation looks good. I've refactored the code to follow best practices and added type safety.",
          "I've created the new module with proper error handling and comprehensive tests.",
        ],
        architect: [
          "Based on the requirements, I recommend a microservices architecture with event-driven communication.",
          "The current architecture has a coupling issue. Let me propose a cleaner separation of concerns.",
          "I've designed the system with horizontal scalability in mind. Here's the component diagram.",
        ],
        reviewer: [
          "I found 3 potential issues: a memory leak in the event handler, an unhandled promise rejection, and a race condition.",
          "The code quality is good overall, but I suggest adding input validation and improving error messages.",
          "Security audit complete: 1 critical vulnerability found in the authentication module.",
        ],
        devops: [
          "I've set up the Docker configuration with multi-stage builds for optimal image size.",
          "The CI/CD pipeline is configured with automated testing and deployment stages.",
          "Infrastructure is provisioned. The Kubernetes manifests are ready for deployment.",
        ],
        analyst: [
          "Based on the data analysis, the performance bottleneck is in the database queries. I recommend adding indexes.",
          "The metrics show a 23% improvement after the optimization. Here's the detailed report.",
          "I've generated the visualization showing the trend over the last 30 days.",
        ],
      }

      const agentResponses = responses[activeAgent] ?? responses["coder"]!
      const responseText = agentResponses[Math.floor(Math.random() * agentResponses.length)]!

      setTimeout(() => {
        const tokens = Math.floor(Math.random() * 500) + 100
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
      }, 800 + Math.random() * 1200)
    },
    [activeAgent, activeModel],
  )

  // ---- Submit message ----
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

  // ---- Render ----
  return (
    <box id="apex-root" style={{ flexDirection: "column", flexGrow: 1, backgroundColor: apexTheme.bg }}>
      {/* Title bar */}
      <box
        id="apex-titlebar"
        style={{
          height: 1,
          flexDirection: "row",
          justifyContent: "center",
          backgroundColor: apexTheme.bgSurface,
        }}
      >
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>APEX</span>
          <span style={{ fg: apexTheme.textMuted }}> - AI-Powered Engineering eXtended</span>
          <span style={{ fg: apexTheme.textMuted }}> | </span>
          <span style={{ fg: apexTheme.green }}>100+ Models</span>
          <span style={{ fg: apexTheme.textMuted }}> </span>
          <span style={{ fg: apexTheme.cyan }}>75+ Tools</span>
          <span style={{ fg: apexTheme.textMuted }}> </span>
          <span style={{ fg: apexTheme.warning }}>5 Agents</span>
        </text>
      </box>

      {/* Main content area */}
      <box id="apex-main" style={{ flexDirection: "row", flexGrow: 1 }}>
        {/* Sidebar */}
        <Sidebar
          activeAgent={activeAgent}
          onAgentSelect={setActiveAgent}
          visible={sidebarVisible}
        />

        {/* Chat panel */}
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSubmit={handleSubmit}
          activeAgent={activeAgent}
          activeModel={activeModel}
          isGenerating={isGenerating}
        />

        {/* Tool panel */}
        <ToolPanel visible={toolPanelVisible} />
      </box>

      {/* Status bar */}
      <StatusBar
        activeAgent={activeAgent}
        activeModel={activeModel}
        totalTokens={totalTokens}
        messageCount={messages.length}
        sessionDuration={sessionDuration}
      />

      {/* Overlay: Model selector */}
      <ModelSelector
        visible={modelSelectorVisible}
        searchQuery={modelSearch}
        onSearchChange={setModelSearch}
        onSelect={setActiveModel}
        onClose={() => setModelSelectorVisible(false)}
        activeModel={activeModel}
      />

      {/* Overlay: Help panel */}
      <HelpPanel
        visible={helpVisible}
        onClose={() => setHelpVisible(false)}
        tab={helpTab}
        onTabChange={setHelpTab}
      />
    </box>
  )
}
