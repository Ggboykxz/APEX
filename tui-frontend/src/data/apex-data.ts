export interface ToolCall {
  name: string
  args: Record<string, any>
  id: string
}

export interface ToolResult {
  toolCallId: string
  output: string
  error?: string
}

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
  toolCalls?: ToolCall[]
  toolResults?: ToolResult[]
  thinking?: string
  isStreaming?: boolean
}

export interface AgentInfo {
  id: string
  name: string
  description: string
  color: string
  mode: "primary" | "subagent"
  temperature?: number
  maxSteps?: number
  hidden?: boolean
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  contextWindow: number
  inputCostPer1K: number
  outputCostPer1K: number
}

export interface KeybindInfo {
  key: string
  description: string
  category: string
}

export const APEX_AGENTS: AgentInfo[] = [
  { id: "build", name: "Build", description: "Full-access development agent with all tools", color: "#00e5ff", mode: "primary", temperature: 0, maxSteps: 50 },
  { id: "plan", name: "Plan", description: "Architecture & planning (read-only)", color: "#a855f7", mode: "primary", temperature: 0.2, maxSteps: 30, hidden: false },
  { id: "planner", name: "Planner", description: "Detailed planning (read-only, no delegation)", color: "#eab308", mode: "primary", temperature: 0.4, maxSteps: 20, hidden: false },
  { id: "reviewer", name: "Reviewer", description: "Code review & audit specialist", color: "#22c55e", mode: "subagent", temperature: 0.1, maxSteps: 15, hidden: false },
  { id: "shell", name: "Shell", description: "Infrastructure, DevOps & shell scripting", color: "#f97316", mode: "primary", temperature: 0, maxSteps: 40 },
  { id: "general", name: "General", description: "General-purpose assistant for any task", color: "#3b82f6", mode: "subagent", temperature: 0.7, maxSteps: 10, hidden: false },
  { id: "explore", name: "Explore", description: "Codebase exploration & understanding", color: "#14b8a6", mode: "subagent", temperature: 0.3, maxSteps: 15, hidden: false },
  { id: "scout", name: "Scout", description: "Quick lookup & information gathering", color: "#ec4899", mode: "subagent", temperature: 0.2, maxSteps: 8, hidden: false },
]

export const APEX_MODELS: ModelInfo[] = [
  // Anthropic
  { id: "claude-sonnet-4", name: "Claude 4 Sonnet", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "claude-opus-4", name: "Claude 4 Opus", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.015, outputCostPer1K: 0.075 },
  { id: "claude-haiku-4", name: "Claude 4 Haiku", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.001, outputCostPer1K: 0.005 },
  { id: "claude-sonnet-4-5", name: "Claude 4.5 Sonnet", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "claude-opus-4-5", name: "Claude 4.5 Opus", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.015, outputCostPer1K: 0.075 },
  { id: "claude-haiku-4-5", name: "Claude 4.5 Haiku", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.0008, outputCostPer1K: 0.004 },
  { id: "claude-sonnet-4-6", name: "Claude 4.6 Sonnet", provider: "Anthropic", contextWindow: 200000, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },

  // OpenAI
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", contextWindow: 128000, inputCostPer1K: 0.0025, outputCostPer1K: 0.01 },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI", contextWindow: 128000, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
  { id: "gpt-4-1", name: "GPT-4.1", provider: "OpenAI", contextWindow: 1047576, inputCostPer1K: 0.002, outputCostPer1K: 0.008 },
  { id: "gpt-4-1-mini", name: "GPT-4.1 Mini", provider: "OpenAI", contextWindow: 1047576, inputCostPer1K: 0.0004, outputCostPer1K: 0.0016 },
  { id: "gpt-4-1-nano", name: "GPT-4.1 Nano", provider: "OpenAI", contextWindow: 1047576, inputCostPer1K: 0.0001, outputCostPer1K: 0.0004 },
  { id: "gpt-5", name: "GPT-5", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.005, outputCostPer1K: 0.02 },
  { id: "gpt-5-pro", name: "GPT-5 Pro", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.015, outputCostPer1K: 0.06 },
  { id: "o1", name: "o1", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.015, outputCostPer1K: 0.06 },
  { id: "o3", name: "o3", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.01, outputCostPer1K: 0.04 },
  { id: "o3-mini", name: "o3 Mini", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.0011, outputCostPer1K: 0.0044 },
  { id: "o4-mini", name: "o4 Mini", provider: "OpenAI", contextWindow: 200000, inputCostPer1K: 0.0011, outputCostPer1K: 0.0044 },

  // Google
  { id: "gemini-2-5-pro", name: "Gemini 2.5 Pro", provider: "Google", contextWindow: 1048576, inputCostPer1K: 0.00125, outputCostPer1K: 0.005 },
  { id: "gemini-2-5-flash", name: "Gemini 2.5 Flash", provider: "Google", contextWindow: 1048576, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
  { id: "gemini-3-flash", name: "Gemini 3 Flash", provider: "Google", contextWindow: 1048576, inputCostPer1K: 0.0003, outputCostPer1K: 0.0012 },
  { id: "gemma-3", name: "Gemma 3", provider: "Google", contextWindow: 8192, inputCostPer1K: 0, outputCostPer1K: 0 },

  // Meta
  { id: "llama-4-maverick", name: "Llama 4 Maverick", provider: "Meta", contextWindow: 1048576, inputCostPer1K: 0.0002, outputCostPer1K: 0.0008 },
  { id: "llama-4-scout", name: "Llama 4 Scout", provider: "Meta", contextWindow: 1048576, inputCostPer1K: 0.0001, outputCostPer1K: 0.0004 },

  // DeepSeek
  { id: "deepseek-chat", name: "DeepSeek Chat", provider: "DeepSeek", contextWindow: 65536, inputCostPer1K: 0.00027, outputCostPer1K: 0.0011 },
  { id: "deepseek-reasoner", name: "DeepSeek Reasoner", provider: "DeepSeek", contextWindow: 65536, inputCostPer1K: 0.00055, outputCostPer1K: 0.0022 },
  { id: "deepseek-v4-flash", name: "DeepSeek V4 Flash", provider: "DeepSeek", contextWindow: 131072, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
  { id: "deepseek-v4-pro", name: "DeepSeek V4 Pro", provider: "DeepSeek", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.002 },

  // Mistral
  { id: "mistral-large", name: "Mistral Large", provider: "Mistral", contextWindow: 128000, inputCostPer1K: 0.002, outputCostPer1K: 0.006 },
  { id: "mistral-small", name: "Mistral Small", provider: "Mistral", contextWindow: 32000, inputCostPer1K: 0.0005, outputCostPer1K: 0.0015 },
  { id: "codestral", name: "Codestral", provider: "Mistral", contextWindow: 32000, inputCostPer1K: 0.001, outputCostPer1K: 0.003 },

  // xAI
  { id: "grok-3", name: "Grok 3", provider: "xAI", contextWindow: 131072, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "grok-4", name: "Grok 4", provider: "xAI", contextWindow: 262144, inputCostPer1K: 0.005, outputCostPer1K: 0.025 },

  // Qwen
  { id: "qwen3-235b", name: "Qwen3 235B", provider: "Qwen", contextWindow: 131072, inputCostPer1K: 0.0002, outputCostPer1K: 0.0006 },
  { id: "qwen3-coder", name: "Qwen3 Coder", provider: "Qwen", contextWindow: 131072, inputCostPer1K: 0.00015, outputCostPer1K: 0.0005 },

  // Ollama (local, free)
  { id: "ollama-llama3", name: "Llama 3 (Local)", provider: "Ollama", contextWindow: 8192, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-codellama", name: "Code Llama (Local)", provider: "Ollama", contextWindow: 16384, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-mistral", name: "Mistral (Local)", provider: "Ollama", contextWindow: 8192, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-qwen3", name: "Qwen3 (Local)", provider: "Ollama", contextWindow: 32768, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-deepseek", name: "DeepSeek (Local)", provider: "Ollama", contextWindow: 32768, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "ollama-gemma3", name: "Gemma 3 (Local)", provider: "Ollama", contextWindow: 8192, inputCostPer1K: 0, outputCostPer1K: 0 },

  // OpenCode Zen (free tier — no API key needed)
  { id: "zen-minimax-m2.5-free", name: "MiniMax M2.5 Free", provider: "Zen", contextWindow: 1048576, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "zen-qwen3.6-plus-free", name: "Qwen3.6 Plus Free", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "zen-nemotron-3-super-free", name: "Nemotron 3 Super Free", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0, outputCostPer1K: 0 },
  { id: "zen-grok-code-fast", name: "Grok Code Fast 1", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0, outputCostPer1K: 0 },

  // OpenCode Zen (pay-as-you-go, $20 top-up)
  { id: "zen-claude-sonnet-4.6", name: "Claude 4.6 Sonnet", provider: "Zen", contextWindow: 200000, inputCostPer1K: 0.003, outputCostPer1K: 0.015 },
  { id: "zen-claude-opus-4.6", name: "Claude 4.6 Opus", provider: "Zen", contextWindow: 200000, inputCostPer1K: 0.005, outputCostPer1K: 0.025 },
  { id: "zen-gpt-5", name: "GPT-5", provider: "Zen", contextWindow: 200000, inputCostPer1K: 0.00107, outputCostPer1K: 0.0085 },
  { id: "zen-gpt-5.4", name: "GPT-5.4", provider: "Zen", contextWindow: 200000, inputCostPer1K: 0.005, outputCostPer1K: 0.0225 },
  { id: "zen-gemini-3-flash", name: "Gemini 3 Flash", provider: "Zen", contextWindow: 1048576, inputCostPer1K: 0.0005, outputCostPer1K: 0.003 },
  { id: "zen-gemini-3.1-pro", name: "Gemini 3.1 Pro", provider: "Zen", contextWindow: 1048576, inputCostPer1K: 0.004, outputCostPer1K: 0.018 },
  { id: "zen-kimi-k2.5", name: "Kimi K2.5", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.0006, outputCostPer1K: 0.003 },
  { id: "zen-kimi-k2.6", name: "Kimi K2.6", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.00095, outputCostPer1K: 0.004 },
  { id: "zen-glm-5", name: "GLM-5", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.001, outputCostPer1K: 0.0032 },
  { id: "zen-glm-5.1", name: "GLM-5.1", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.0014, outputCostPer1K: 0.0044 },
  { id: "zen-minimax-m2.5", name: "MiniMax M2.5", provider: "Zen", contextWindow: 1048576, inputCostPer1K: 0.0003, outputCostPer1K: 0.0012 },
  { id: "zen-minimax-m2.7", name: "MiniMax M2.7", provider: "Zen", contextWindow: 1048576, inputCostPer1K: 0.0003, outputCostPer1K: 0.0012 },
  { id: "zen-deepseek-v4-pro", name: "DeepSeek V4 Pro", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.002 },
  { id: "zen-deepseek-v4-flash", name: "DeepSeek V4 Flash", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
  { id: "zen-qwen3.5-plus", name: "Qwen3.5 Plus", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.003 },
  { id: "zen-qwen3.6-plus", name: "Qwen3.6 Plus", provider: "Zen", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.003 },

  // OpenCode Go ($10/mo subscription, curated open models)
  { id: "go-glm-5", name: "GLM-5 (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.001, outputCostPer1K: 0.0032 },
  { id: "go-glm-5.1", name: "GLM-5.1 (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.0014, outputCostPer1K: 0.0044 },
  { id: "go-kimi-k2.5", name: "Kimi K2.5 (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.0006, outputCostPer1K: 0.003 },
  { id: "go-kimi-k2.6", name: "Kimi K2.6 (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.00095, outputCostPer1K: 0.004 },
  { id: "go-minimax-m2.5", name: "MiniMax M2.5 (Go)", provider: "Go", contextWindow: 1048576, inputCostPer1K: 0.0003, outputCostPer1K: 0.0012 },
  { id: "go-minimax-m2.7", name: "MiniMax M2.7 (Go)", provider: "Go", contextWindow: 1048576, inputCostPer1K: 0.0003, outputCostPer1K: 0.0012 },
  { id: "go-qwen3.5-plus", name: "Qwen3.5 Plus (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.003 },
  { id: "go-qwen3.6-plus", name: "Qwen3.6 Plus (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.003 },
  { id: "go-deepseek-v4-pro", name: "DeepSeek V4 Pro (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.0005, outputCostPer1K: 0.002 },
  { id: "go-deepseek-v4-flash", name: "DeepSeek V4 Flash (Go)", provider: "Go", contextWindow: 131072, inputCostPer1K: 0.00015, outputCostPer1K: 0.0006 },
]

export const DEFAULT_KEYBINDS: KeybindInfo[] = [
  { key: "Tab", description: "Switch agent", category: "global" },
  { key: "Ctrl+K", description: "Model selector", category: "global" },
  { key: "Ctrl+L", description: "Clear messages", category: "global" },
  { key: "Ctrl+O", description: "Toggle sidebar", category: "global" },
  { key: "Ctrl+Q", description: "Quit", category: "global" },
  { key: "Ctrl+P", description: "Command palette", category: "global" },
  { key: "Ctrl+X", description: "Leader key prefix", category: "leader" },
  { key: "Ctrl+X N", description: "New session", category: "leader" },
  { key: "Ctrl+X U", description: "Undo", category: "leader" },
  { key: "Ctrl+X R", description: "Redo", category: "leader" },
  { key: "Ctrl+X C", description: "Compact", category: "leader" },
  { key: "Ctrl+X M", description: "Models list", category: "leader" },
  { key: "Ctrl+X T", description: "Themes", category: "leader" },
  { key: "Ctrl+X S", description: "Status", category: "leader" },
  { key: "Ctrl+X E", description: "Editor", category: "leader" },
  { key: "Ctrl+X X", description: "Export", category: "leader" },
  { key: "Ctrl+X B", description: "Toggle sidebar", category: "leader" },
  { key: "Ctrl+X A", description: "Agent list", category: "leader" },
  { key: "Ctrl+X L", description: "Sessions list", category: "leader" },
  { key: "Ctrl+T", description: "Cycle reasoning variants", category: "global" },
  { key: "Escape", description: "Close overlay", category: "global" },
  { key: "?", description: "Help", category: "global" },
  { key: "Ctrl+Shift+F", description: "Toggle fullscreen permission", category: "global" },
]
