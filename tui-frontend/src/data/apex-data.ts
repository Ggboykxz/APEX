export interface ApexModel {
  id: string
  name: string
  provider: string
  description: string
  contextWindow: number
  maxTokens: number
  supportsVision: boolean
  supportsTools: boolean
}

export interface ApexAgent {
  id: string
  name: string
  role: string
  description: string
  color: string
  icon: string
  defaultModel: string
  capabilities: string[]
}

export interface ApexTool {
  id: string
  name: string
  category: string
  description: string
  agent: string
  status: "active" | "idle" | "error"
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  agent?: string
  model?: string
  timestamp: number
  tokens?: number
}

export const APEX_AGENTS: ApexAgent[] = [
  { id: "coder", name: "APEX Coder", role: "Code Generation & Editing", description: "Primary coding agent. Generates, edits, and refactors code.", color: "#00e5ff", icon: "<>", defaultModel: "claude-4-sonnet", capabilities: ["Code Generation", "Code Editing", "Refactoring", "File Ops", "Search"] },
  { id: "architect", name: "APEX Architect", role: "System Design & Planning", description: "Designs system architecture and creates implementation plans.", color: "#7c3aed", icon: "/\\", defaultModel: "o3", capabilities: ["System Design", "Architecture", "Planning"] },
  { id: "reviewer", name: "APEX Reviewer", role: "Code Review & Quality", description: "Reviews code for bugs, security vulnerabilities, and best practices.", color: "#f59e0b", icon: "()", defaultModel: "claude-4-sonnet", capabilities: ["Code Review", "Bug Detection", "Security", "Performance"] },
  { id: "devops", name: "APEX DevOps", role: "Infrastructure & Deployment", description: "Manages infrastructure, CI/CD pipelines, and deployment.", color: "#ef4444", icon: "=>", defaultModel: "gpt-4o", capabilities: ["CI/CD", "Docker", "K8s", "Cloud"] },
  { id: "analyst", name: "APEX Analyst", role: "Data & Research", description: "Analyzes data, performs research, and generates reports.", color: "#00ff88", icon: "[]", defaultModel: "gemini-2.5-pro", capabilities: ["Data Analysis", "Research", "Reports", "Statistics"] },
]

export const APEX_MODELS: ApexModel[] = [
  { id: "claude-4-sonnet", name: "Claude 4 Sonnet", provider: "Anthropic", description: "Latest Claude model", contextWindow: 200000, maxTokens: 16384, supportsVision: true, supportsTools: true },
  { id: "claude-4-opus", name: "Claude 4 Opus", provider: "Anthropic", description: "Most powerful Claude", contextWindow: 200000, maxTokens: 32768, supportsVision: true, supportsTools: true },
  { id: "claude-3.7-sonnet", name: "Claude 3.7 Sonnet", provider: "Anthropic", description: "Enhanced Sonnet", contextWindow: 200000, maxTokens: 8192, supportsVision: true, supportsTools: true },
  { id: "claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "Anthropic", description: "Fast and capable", contextWindow: 200000, maxTokens: 8192, supportsVision: true, supportsTools: true },
  { id: "claude-3.5-haiku", name: "Claude 3.5 Haiku", provider: "Anthropic", description: "Fastest Claude", contextWindow: 200000, maxTokens: 8192, supportsVision: true, supportsTools: true },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", description: "Most capable OpenAI model", contextWindow: 128000, maxTokens: 16384, supportsVision: true, supportsTools: true },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI", description: "Fast and affordable", contextWindow: 128000, maxTokens: 16384, supportsVision: true, supportsTools: true },
  { id: "gpt-4-turbo", name: "GPT-4 Turbo", provider: "OpenAI", description: "Previous gen flagship", contextWindow: 128000, maxTokens: 4096, supportsVision: true, supportsTools: true },
  { id: "o3", name: "o3", provider: "OpenAI", description: "Advanced reasoning", contextWindow: 200000, maxTokens: 100000, supportsVision: true, supportsTools: true },
  { id: "o1", name: "o1", provider: "OpenAI", description: "Reasoning model", contextWindow: 200000, maxTokens: 100000, supportsVision: true, supportsTools: false },
  { id: "o1-mini", name: "o1 Mini", provider: "OpenAI", description: "Fast reasoning", contextWindow: 128000, maxTokens: 65536, supportsVision: false, supportsTools: false },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "Google", description: "Most capable Gemini", contextWindow: 1000000, maxTokens: 65536, supportsVision: true, supportsTools: true },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "Google", description: "Fast Gemini", contextWindow: 1000000, maxTokens: 65536, supportsVision: true, supportsTools: true },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", provider: "Google", description: "Stable Flash", contextWindow: 1000000, maxTokens: 8192, supportsVision: true, supportsTools: true },
  { id: "llama-4-maverick", name: "Llama 4 Maverick", provider: "Meta", description: "Open-weight flagship", contextWindow: 1000000, maxTokens: 32768, supportsVision: true, supportsTools: true },
  { id: "llama-4-scout", name: "Llama 4 Scout", provider: "Meta", description: "Efficient open model", contextWindow: 10000000, maxTokens: 32768, supportsVision: true, supportsTools: true },
  { id: "llama-3.3-70b", name: "Llama 3.3 70B", provider: "Meta", description: "Previous gen large", contextWindow: 128000, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "mistral-large", name: "Mistral Large", provider: "Mistral", description: "Flagship Mistral", contextWindow: 128000, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "mistral-medium", name: "Mistral Medium", provider: "Mistral", description: "Balanced model", contextWindow: 32000, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "codestral", name: "Codestral", provider: "Mistral", description: "Code specialist", contextWindow: 256000, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "deepseek-v3", name: "DeepSeek V3", provider: "DeepSeek", description: "Open MoE model", contextWindow: 128000, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "deepseek-r1", name: "DeepSeek R1", provider: "DeepSeek", description: "Reasoning model", contextWindow: 128000, maxTokens: 16384, supportsVision: false, supportsTools: true },
  { id: "grok-3", name: "Grok 3", provider: "xAI", description: "Latest Grok", contextWindow: 131072, maxTokens: 8192, supportsVision: true, supportsTools: true },
  { id: "grok-3-mini", name: "Grok 3 Mini", provider: "xAI", description: "Fast Grok", contextWindow: 131072, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "qwen3-235b", name: "Qwen 3 235B", provider: "Alibaba", description: "Large Qwen model", contextWindow: 131072, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "qwen3-32b", name: "Qwen 3 32B", provider: "Alibaba", description: "Mid-size Qwen", contextWindow: 131072, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "qwen2.5-coder-32b", name: "Qwen 2.5 Coder", provider: "Alibaba", description: "Code specialist", contextWindow: 131072, maxTokens: 8192, supportsVision: false, supportsTools: true },
  { id: "command-r-plus", name: "Command R+", provider: "Cohere", description: "Enterprise RAG", contextWindow: 128000, maxTokens: 4096, supportsVision: false, supportsTools: true },
  { id: "command-r", name: "Command R", provider: "Cohere", description: "Efficient RAG", contextWindow: 128000, maxTokens: 4096, supportsVision: false, supportsTools: true },
  { id: "phi-4", name: "Phi-4", provider: "Microsoft", description: "Small but mighty", contextWindow: 16384, maxTokens: 4096, supportsVision: true, supportsTools: true },
  { id: "phi-4-mini", name: "Phi-4 Mini", provider: "Microsoft", description: "Tiny but capable", contextWindow: 128000, maxTokens: 4096, supportsVision: false, supportsTools: true },
]

export const APEX_TOOLS: ApexTool[] = [
  { id: "file-read", name: "File Read", category: "File", description: "Read file contents", agent: "coder", status: "active" },
  { id: "file-write", name: "File Write", category: "File", description: "Write content to files", agent: "coder", status: "active" },
  { id: "file-edit", name: "File Edit", category: "File", description: "Edit file with diff", agent: "coder", status: "active" },
  { id: "file-search", name: "File Search", category: "File", description: "Search across files", agent: "coder", status: "active" },
  { id: "file-delete", name: "File Delete", category: "File", description: "Delete files", agent: "coder", status: "active" },
  { id: "dir-list", name: "Dir List", category: "File", description: "List directory contents", agent: "coder", status: "active" },
  { id: "dir-create", name: "Dir Create", category: "File", description: "Create directories", agent: "coder", status: "active" },
  { id: "code-search", name: "Code Search", category: "Code", description: "Semantic code search", agent: "coder", status: "active" },
  { id: "code-lint", name: "Code Lint", category: "Code", description: "Lint code files", agent: "reviewer", status: "active" },
  { id: "code-format", name: "Code Format", category: "Code", description: "Format code files", agent: "coder", status: "active" },
  { id: "code-refactor", name: "Code Refactor", category: "Code", description: "Refactor code", agent: "coder", status: "active" },
  { id: "code-test-gen", name: "Test Generator", category: "Code", description: "Generate unit tests", agent: "coder", status: "active" },
  { id: "shell-exec", name: "Shell Exec", category: "Shell", description: "Execute shell commands", agent: "coder", status: "active" },
  { id: "shell-bg", name: "Shell Background", category: "Shell", description: "Run background process", agent: "devops", status: "active" },
  { id: "git-status", name: "Git Status", category: "Git", description: "Check repository status", agent: "coder", status: "active" },
  { id: "git-diff", name: "Git Diff", category: "Git", description: "View changes", agent: "reviewer", status: "active" },
  { id: "git-commit", name: "Git Commit", category: "Git", description: "Create commits", agent: "coder", status: "active" },
  { id: "git-log", name: "Git Log", category: "Git", description: "View commit history", agent: "reviewer", status: "active" },
  { id: "git-branch", name: "Git Branch", category: "Git", description: "Manage branches", agent: "coder", status: "active" },
  { id: "web-search", name: "Web Search", category: "Web", description: "Search the internet", agent: "analyst", status: "active" },
  { id: "web-fetch", name: "Web Fetch", category: "Web", description: "Fetch web pages", agent: "analyst", status: "active" },
  { id: "db-query", name: "DB Query", category: "Database", description: "Execute SQL queries", agent: "analyst", status: "active" },
  { id: "db-migrate", name: "DB Migrate", category: "Database", description: "Run migrations", agent: "devops", status: "active" },
  { id: "docker-build", name: "Docker Build", category: "Docker", description: "Build images", agent: "devops", status: "active" },
  { id: "docker-run", name: "Docker Run", category: "Docker", description: "Run containers", agent: "devops", status: "active" },
  { id: "sec-scan", name: "Security Scan", category: "Security", description: "Scan for vulnerabilities", agent: "reviewer", status: "active" },
  { id: "sec-audit", name: "Security Audit", category: "Security", description: "Audit dependencies", agent: "reviewer", status: "active" },
  { id: "analyze-deps", name: "Dependency Analysis", category: "Analysis", description: "Analyze dependencies", agent: "analyst", status: "active" },
  { id: "analyze-perf", name: "Performance Analysis", category: "Analysis", description: "Analyze performance", agent: "analyst", status: "active" },
  { id: "cloud-aws", name: "AWS CLI", category: "Cloud", description: "AWS operations", agent: "devops", status: "active" },
  { id: "cloud-gcp", name: "GCP CLI", category: "Cloud", description: "GCP operations", agent: "devops", status: "active" },
  { id: "k8s-deploy", name: "K8s Deploy", category: "K8s", description: "Deploy to Kubernetes", agent: "devops", status: "active" },
  { id: "k8s-pods", name: "K8s Pods", category: "K8s", description: "List pods", agent: "devops", status: "active" },
  { id: "lsp-definition", name: "LSP Definition", category: "LSP", description: "Go to definition", agent: "coder", status: "active" },
  { id: "lsp-references", name: "LSP References", category: "LSP", description: "Find references", agent: "coder", status: "active" },
]

export const APEX_KEYBINDINGS = [
  { key: "Tab", action: "Switch agent", category: "Navigation" },
  { key: "Ctrl+K", action: "Model selector", category: "Navigation" },
  { key: "Ctrl+L", action: "Clear chat", category: "Chat" },
  { key: "Ctrl+O", action: "Toggle sidebar", category: "View" },
  { key: "Ctrl+T", action: "Toggle tools", category: "View" },
  { key: "Enter", action: "Send message", category: "Chat" },
  { key: "Ctrl+C", action: "Cancel generation", category: "Chat" },
  { key: "Escape", action: "Close overlay", category: "Navigation" },
  { key: "?", action: "Help panel", category: "Navigation" },
  { key: "Ctrl+Q", action: "Quit APEX", category: "Navigation" },
] as const