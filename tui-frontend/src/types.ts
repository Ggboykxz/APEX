/**
 * Shared types for the APEX TUI (Ink/React frontend).
 * Kept small and framework-agnostic so a future OpenTUI renderer can reuse them.
 */

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "tool"
  content: string
  agent?: string
  model?: string
  timestamp: number
  promptTokens?: number
  completionTokens?: number
  cost?: number
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  contextWindow: number
  inputCostPer1K: number
  outputCostPer1K: number
}

export interface AgentInfo {
  id: string
  name: string
  description: string
  mode: "primary" | "subagent" | "system"
  color?: string
}

export interface ThemeInfo {
  id: string
  name: string
}

export interface SessionInfo {
  id: string
  name: string
  model?: string
}

export interface Usage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

export interface StreamChunk {
  chunk?: string
  usage?: Usage
  error?: string
}

export interface TuiConfig {
  theme?: string
  keybinds?: Record<string, string>
  leader_timeout?: number
  scroll_speed?: number
  mouse?: boolean
  [key: string]: unknown
}

export interface OverlayState {
  commandPalette: boolean
  fileFinder: boolean
  help: boolean
  modelSelector: boolean
  themeSelector: boolean
  agentSelector: boolean
  status: boolean
  sessions: boolean
}

export const createInitialOverlayState = (): OverlayState => ({
  commandPalette: false,
  fileFinder: false,
  help: false,
  modelSelector: false,
  themeSelector: false,
  agentSelector: false,
  status: false,
  sessions: false,
})
