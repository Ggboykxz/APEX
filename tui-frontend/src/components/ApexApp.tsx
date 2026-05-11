import React, { useState, useCallback, useEffect, useRef } from "react"
import { Box, Text, useInput, useApp } from "ink"
import { ChatPanel } from "./ChatPanel.js"
import { StatusBar } from "./StatusBar.js"
import { Sidebar } from "./Sidebar.js"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"

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
  const { exit } = useApp()

  const [activeAgent, setActiveAgent] = useState("coder")
  const [activeModel, setActiveModel] = useState("claude-4-sonnet")
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

  const agent = APEX_AGENTS.find((a) => a.id === activeAgent) ?? APEX_AGENTS[0]!
  const model = APEX_MODELS.find((m) => m.id === activeModel)
  const totalTokens = totalPromptTokens + totalCompletionTokens
  const contextPct = model?.contextWindow && totalTokens > 0
    ? Math.min(100, (totalTokens / model.contextWindow) * 100)
    : 0

  const sessionDuration = (() => {
    const elapsed = Math.floor((Date.now() - sessionStart) / 1000)
    const mins = Math.floor(elapsed / 60)
    const secs = elapsed % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  })()

  // Auto-dismiss connection errors
  useEffect(() => {
    if (connectionError) {
      const timer = setTimeout(() => setConnectionError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [connectionError])

  // Send message to API
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

      // Process remaining buffer
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
        setConnectionError("Cannot connect to APEX backend on port " + HTTP_PORT)
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
  }, [activeAgent, activeModel, livePromptTokens, liveCompletionTokens])

  // Handle keyboard input
  useInput((input, key) => {
    if (key.ctrl && input === "q") {
      exit()
      return
    }
    if (key.ctrl && input === "o") {
      setSidebarVisible((v) => !v)
      return
    }
    if (key.ctrl && input === "l") {
      setMessages([])
      setInputValue("")
      setTotalPromptTokens(0)
      setTotalCompletionTokens(0)
      setTotalSpent(0)
      return
    }
    if (key.tab) {
      const currentIdx = APEX_AGENTS.findIndex((a) => a.id === activeAgent)
      const nextIdx = (currentIdx + 1) % APEX_AGENTS.length
      setActiveAgent(APEX_AGENTS[nextIdx]!.id)
      return
    }
    if (key.return && inputValue.trim() && !isGenerating) {
      const msg = inputValue.trim()
      setInputValue("")
      sendMessage(msg)
      return
    }
    if (key.backspace || key.delete) {
      setInputValue((v) => v.slice(0, -1))
      return
    }
    if (input && !key.ctrl && !key.meta) {
      setInputValue((v) => v + input)
    }
  })

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Connection Error Banner */}
      {connectionError && (
        <Box width="100%">
          <Text backgroundColor={apexTheme.error} color="#000000" bold>
            {" "}⚠ {connectionError}{" "}
          </Text>
        </Box>
      )}

      {/* Title Bar */}
      <Box width="100%" justifyContent="center" backgroundColor={agent.color}>
        <Text color="#000000" bold>
          ▲ APEX — {agent.name} · {model?.name ?? "No Model"} │ {messages.length} msgs │ {contextPct.toFixed(1)}% ctx │ ${totalSpent.toFixed(4)}
        </Text>
      </Box>

      {/* Main Area */}
      <Box flexDirection="row" flexGrow={1}>
        {sidebarVisible && (
          <Sidebar activeAgent={activeAgent} onAgentSelect={setActiveAgent} />
        )}
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          activeAgent={activeAgent}
          activeModel={activeModel}
          isGenerating={isGenerating}
        />
      </Box>

      {/* Status Bar */}
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
    </Box>
  )
}
