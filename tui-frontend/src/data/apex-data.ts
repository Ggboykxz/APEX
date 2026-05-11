export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  agent?: string
  model?: string
  timestamp: number
  promptTokens?: number
  completionTokens?: number
  cost?: number
}

export interface AgentInfo {
  id: string
  name: string
  description: string
  color: string
  mode: "primary" | "subagent"
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  contextWindow: number
  inputCostPer1K: number
  outputCostPer1K: number
}

export const APEX_AGENTS: AgentInfo[] = [
  { id: "coder", name: "Coder", description: "Full-access coding agent", color: "#00e5ff", mode: "primary" },
  { id: "architect", name: "Architect", description: "Architecture & design (read-only)", color: "#ff6b6b", mode: "primary" },
  { id: "planner", name: "Planner", description: "Analysis & planning (read-only)", color: "#ffd93d", mode: "primary" },
  { id: "reviewer", name: "Reviewer", description: "Code review specialist", color: "#c084fc", mode: "subagent" },
  { id: "shell", name: "Shell", description: "Infrastructure & DevOps", color: "#00ff88", mode: "primary" },
]

export const APEX_MODELS: ModelInfo[] = [
  { id: "claude-4-sonnet", name: "Claude 4 Sonnet", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "claude-4-opus", name: "Claude 4 Opus", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.015, outputCostPer1K: 0.075 },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", contextWindow: 128000, inputCostPer1K: 0.0025, outputCostPer1K: 0.01 },
  { id: "gpt-4.1", name: "GPT-4.1", provider: "OpenAI", contextWindow: 1047576, inputCostPer1K: 0.002, outputCostPer1K: 0.008 },
  { id: "o3", name: "o3", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.002, outputCostPer1K: 0.008 },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "Google", contextWindow: 1048576, inputCostPer1K: 0.00125, outputCostPer1K: 0.005 },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "Google", contextWindow: 1048576, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
  { id: "deepseek-v3", name: "DeepSeek V3", provider: "DeepSeek", contextWindow: 65536, inputCostPer1K: 0.00027, outputCostPer1K: 0.0011 },
  { id: "deepseek-r1", name: "DeepSeek R1", provider: "DeepSeek", contextWindow: 65536, inputCostPer1K: 0.00055, outputCostPer1K: 0.0022 },
  { id: "llama-4-maverick", name: "Llama 4 Maverick", provider: "Meta", contextWindow: 1048576, inputCostPer1K: 0.0002, outputCostPer1K: 0.0008 },
  { id: "grok-3", name: "Grok 3", provider: "xAI", contextWindow: 131072, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "qwen3-235b", name: "Qwen3 235B", provider: "Qwen", contextWindow: 131072, inputCostPer1K: 0.0002, outputCostPer1K: 0.0006 },
  { id: "mistral-large", name: "Mistral Large", provider: "Mistral", contextWindow: 128000, inputCostPer1K: 0.002, outputCostPer1K: 0.006 },
  { id: "ollama-llama3", name: "Llama 3 (Local)", provider: "Ollama", contextWindow: 8192, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-codellama", name: "Code Llama (Local)", provider: "Ollama", contextWindow: 16384, inputCostPer1K: 0, outputCostPer1K: 0 },
]
