export const PROVIDERS = [
  { id: "anthropic", name: "Anthropic", color: "#FF6B35" },
  { id: "openai", name: "OpenAI", color: "#10A37F" },
  { id: "google", name: "Google", color: "#4285F4" },
  { id: "xai", name: "xAI", color: "#9D00FF" },
  { id: "meta", name: "Meta", color: "#1877F2" },
  { id: "deepseek", name: "DeepSeek", color: "#0066FF" },
  { id: "alibaba", name: "Alibaba", color: "#FF6600" },
  { id: "mistral", name: "Mistral", color: "#EB298D" },
  { id: "groq", name: "Groq", color: "#FF4500" },
  { id: "cohere", name: "Cohere", color: "#00C4B4" },
  { id: "local", name: "Local", color: "#6B7280" },
];

export interface ModelEntry {
  alias: string;
  provider: string;
  name: string;
  description: string;
}

export const MODELS: ModelEntry[] = [
  { alias: "claude-3.5-sonnet", provider: "anthropic", name: "Claude 3.5 Sonnet", description: "Latest Claude with enhanced coding" },
  { alias: "claude-3-opus", provider: "anthropic", name: "Claude 3 Opus", description: "Most capable Claude for complex tasks" },
  { alias: "claude-3-sonnet", provider: "anthropic", name: "Claude 3 Sonnet", description: "Balanced speed and capability" },
  { alias: "claude-3-haiku", provider: "anthropic", name: "Claude 3 Haiku", description: "Fast and efficient" },
  { alias: "claude-4-sonnet", provider: "anthropic", name: "Claude 4 Sonnet", description: "Claude 4 Sonnet 2025" },
  { alias: "claude-4-opus", provider: "anthropic", name: "Claude 4 Opus", description: "Claude 4 Opus 2025" },
  { alias: "gpt-4o", provider: "openai", name: "GPT-4o", description: "Most capable OpenAI model" },
  { alias: "gpt-4o-mini", provider: "openai", name: "GPT-4o Mini", description: "Fast and cost-effective" },
  { alias: "gpt-4-turbo", provider: "openai", name: "GPT-4 Turbo", description: "Fast GPT-4 with 128k context" },
  { alias: "gpt-4", provider: "openai", name: "GPT-4", description: "Original GPT-4" },
  { alias: "o1-preview", provider: "openai", name: "o1 Preview", description: "OpenAI reasoning model" },
  { alias: "o1-mini", provider: "openai", name: "o1 Mini", description: "Fast reasoning model" },
  { alias: "gemini-2-flash", provider: "google", name: "Gemini 2.0 Flash", description: "Fast multimodal Google model" },
  { alias: "gemini-2-flash-lite", provider: "google", name: "Gemini 2.0 Flash Lite", description: "Ultra fast, low cost" },
  { alias: "gemini-1.5-pro", provider: "google", name: "Gemini 1.5 Pro", description: "2M token context" },
  { alias: "gemini-1.5-flash", provider: "google", name: "Gemini 1.5 Flash", description: "Fast multimodal" },
  { alias: "gemini-1.5-flash-8b", provider: "google", name: "Gemini 1.5 Flash 8B", description: "Very fast, 8B params" },
  { alias: "grok-2", provider: "xai", name: "Grok 2", description: "xAI Grok 2" },
  { alias: "grok-2-mini", provider: "xai", name: "Grok 2 Mini", description: "Fast Grok 2" },
  { alias: "grok-1", provider: "xai", name: "Grok 1", description: "Original Grok model" },
  { alias: "llama-3.3-70b", provider: "meta", name: "Llama 3.3 70B", description: "Meta's top open model" },
  { alias: "llama-3.1-70b", provider: "meta", name: "Llama 3.1 70B", description: "Llama 3.1 70B Instruct" },
  { alias: "llama-3.1-8b", provider: "meta", name: "Llama 3.1 8B", description: "Fast open model" },
  { alias: "llama-3-70b", provider: "meta", name: "Llama 3 70B", description: "Llama 3 70B Instruct" },
  { alias: "llama-3-8b", provider: "meta", name: "Llama 3 8B", description: "Llama 3 8B Instruct" },
  { alias: "deepseek-chat", provider: "deepseek", name: "DeepSeek V3", description: "DeepSeek Chat model" },
  { alias: "deepseek-coder", provider: "deepseek", name: "DeepSeek Coder", description: "Specialized for code" },
  { alias: "qwen-2.5", provider: "alibaba", name: "Qwen 2.5", description: "Alibaba Qwen 2.5" },
  { alias: "qwen-2", provider: "alibaba", name: "Qwen 2", description: "Alibaba Qwen 2" },
  { alias: "pixtral", provider: "mistral", name: "Pixtral", description: "Mistral vision model" },
  { alias: "mistral-large", provider: "mistral", name: "Mistral Large", description: "Mistral's top model" },
  { alias: "mistral-medium", provider: "mistral", name: "Mistral Medium", description: "Balanced Mistral" },
  { alias: "mixtral-8x7b", provider: "mistral", name: "Mixtral 8x7B", description: "MoE model" },
  { alias: "groq-70b", provider: "groq", name: "Llama 3.3 70B (Groq)", description: "Fast inference via Groq" },
  { alias: "groq-8b", provider: "groq", name: "Llama 3.1 8B (Groq)", description: "Very fast via Groq" },
  { alias: "command-r-plus", provider: "cohere", name: "Command R+", description: "Cohere's top model" },
  { alias: "command-r", provider: "cohere", name: "Command R", description: "Cohere's efficient model" },
];

export const AGENTS = [
  { id: "coder", name: "Coder", icon: "⌨", description: "Full access for coding tasks", color: "#10A37F" },
  { id: "architect", name: "Architect", icon: "🏗", description: "Read-only planning and design", color: "#4285F4" },
  { id: "reviewer", name: "Reviewer", icon: "🔍", description: "Code review and analysis", color: "#9D00FF" },
  { id: "devops", name: "DevOps", icon: "🚀", description: "Deployment and infrastructure", color: "#FF6B35" },
  { id: "analyst", name: "Analyst", icon: "📊", description: "Data analysis and insights", color: "#FF6600" },
];

export const THEMES = [
  { id: "apex", name: "APEX Dark", bg: "#0D1117", accent: "#FF6B35" },
  { id: "dracula", name: "Dracula", bg: "#282A36", accent: "#BD93F9" },
  { id: "nord", name: "Nord", bg: "#2E3440", accent: "#88C0D0" },
  { id: "tokyonight", name: "Tokyo Night", bg: "#1A1B26", accent: "#7AA2F7" },
  { id: "gruvbox", name: "Gruvbox", bg: "#282828", accent: "#FABD2F" },
  { id: "github", name: "GitHub Dark", bg: "#0D1117", accent: "#58A6FF" },
];

export function getProviderColor(providerId: string): string {
  return PROVIDERS.find(p => p.id === providerId)?.color || "#6B7280";
}