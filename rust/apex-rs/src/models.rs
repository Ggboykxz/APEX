//! Model alias tables — port of `MODELS` and `MODEL_PROVIDERS` from
//! `apex/config.py`. Backs `GET /models`, `POST /api/v1/models/refresh`
//! and `GET /api/v1/providers`.

use serde_json::json;

/// `MODELS` in `apex/config.py`: alias → full model id, in declaration order.
pub const MODELS: &[(&str, &str)] = &[
    // ── Anthropic Claude (2024-2026) ──
    ("claude-3.5-haiku", "anthropic/claude-3-5-haiku-20241022"),
    ("claude-3.5-sonnet", "anthropic/claude-3-5-sonnet-20241022"),
    ("claude-3.7-sonnet", "anthropic/claude-3-7-sonnet-20250219"),
    ("claude-sonnet-4", "anthropic/claude-sonnet-4-20250514"),
    ("claude-opus-4", "anthropic/claude-opus-4-20250514"),
    ("claude-sonnet-4.5", "anthropic/claude-sonnet-4-5"),
    ("claude-opus-4.5", "anthropic/claude-opus-4-5"),
    ("claude-haiku-4.5", "anthropic/claude-haiku-4-5"),
    ("claude-opus-4.7", "anthropic/claude-opus-4-7"),
    ("claude-sonnet-4.6", "anthropic/claude-sonnet-4-6"),
    // ── OpenAI GPT / o-series (2020-2025) ──
    ("gpt-4o", "openai/gpt-4o"),
    ("gpt-4o-mini", "openai/gpt-4o-mini"),
    ("gpt-4-turbo", "openai/gpt-4-turbo"),
    ("gpt-4.1", "openai/gpt-4.1"),
    ("gpt-4.1-mini", "openai/gpt-4.1-mini"),
    ("gpt-4.1-nano", "openai/gpt-4.1-nano"),
    ("gpt-5", "openai/gpt-5"),
    ("gpt-5-mini", "openai/gpt-5-mini"),
    ("gpt-5-nano", "openai/gpt-5-nano"),
    ("gpt-5-pro", "openai/gpt-5-pro"),
    ("o1", "openai/o1"),
    ("o1-mini", "openai/o1-mini"),
    ("o3", "openai/o3"),
    ("o3-mini", "openai/o3-mini"),
    ("o3-pro", "openai/o3-pro"),
    ("o4-mini", "openai/o4-mini"),
    // ── Google DeepMind Gemini / Gemma (2023-2025) ──
    ("gemini-1.5-flash", "google/gemini-1.5-flash"),
    ("gemini-1.5-pro", "google/gemini-1.5-pro"),
    ("gemini-2.0-flash", "google/gemini-2.0-flash"),
    ("gemini-2.0-flash-lite", "google/gemini-2.0-flash-lite"),
    ("gemini-2.5-flash", "google/gemini-2.5-flash"),
    ("gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite"),
    ("gemini-2.5-pro", "google/gemini-2.5-pro"),
    ("gemini-3-flash", "google/gemini-3-flash-preview"),
    ("gemini-3-pro", "google/gemini-3-pro-preview"),
    ("gemma-3-4b", "google/gemma-3-4b-it"),
    ("gemma-3-12b", "google/gemma-3-12b-it"),
    ("gemma-3-27b", "google/gemma-3-27b-it"),
    ("gemma-4-26b", "google/gemma-4-26b-a4b-it"),
    ("gemma-4-31b", "google/gemma-4-31b-it"),
    // ── xAI Grok (2023-2025) ──
    ("grok-2", "xai/grok-2"),
    ("grok-3", "xai/grok-3"),
    ("grok-3-mini", "xai/grok-3-mini"),
    ("grok-4", "xai/grok-4"),
    ("grok-4-fast", "xai/grok-4-fast"),
    // ── DeepSeek (2024-2025) ──
    ("deepseek-chat", "deepseek/deepseek-chat"),
    ("deepseek-reasoner", "deepseek/deepseek-reasoner"),
    ("deepseek-v4-flash", "deepseek/deepseek-v4-flash"),
    ("deepseek-v4-pro", "deepseek/deepseek-v4-pro"),
    // ── Mistral AI (2023-2025) ──
    ("mistral-small-latest", "mistral/mistral-small-latest"),
    ("mistral-medium-latest", "mistral/mistral-medium-latest"),
    ("mistral-large-latest", "mistral/mistral-large-latest"),
    ("codestral", "mistral/codestral-latest"),
    ("devstral", "mistral/devstral-medium-latest"),
    ("devstral-small", "mistral/devstral-small-2507"),
    ("ministral-8b", "mistral/ministral-8b-latest"),
    ("ministral-3b", "mistral/ministral-3b-latest"),
    ("mixtral-8x7b", "mistral/open-mixtral-8x7b"),
    ("mixtral-8x22b", "mistral/open-mixtral-8x22b"),
    ("mistral-7b", "mistral/open-mistral-7b"),
    ("magistral-medium", "mistral/magistral-medium-latest"),
    ("magistral-small", "mistral/magistral-small"),
    ("pixtral-large", "mistral/pixtral-large-latest"),
    ("pixtral-12b", "mistral/pixtral-12b"),
    // ── Alibaba Qwen (2024-2025) ──
    ("qwen-max", "alibaba/qwen-max"),
    ("qwen-plus", "alibaba/qwen-plus"),
    ("qwen-turbo", "alibaba/qwen-turbo"),
    ("qwen3-8b", "alibaba/qwen3-8b"),
    ("qwen3-32b", "alibaba/qwen3-32b"),
    ("qwen3-235b", "alibaba/qwen3-235b-a22b"),
    ("qwen3-coder-plus", "alibaba/qwen3-coder-plus"),
    ("qwen3-coder-flash", "alibaba/qwen3-coder-flash"),
    ("qwen3-max", "alibaba/qwen3-max"),
    ("qwen3.5-plus", "alibaba/qwen3.5-plus"),
    ("qwen3.6-plus", "alibaba/qwen3.6-plus"),
    ("qwq-plus", "alibaba/qwq-plus"),
    // ── Meta Llama (2023-2025) — Llama API ──
    ("llama-3.3-70b", "llama/llama-3.3-70b-instruct"),
    ("llama-3.3-8b", "llama/llama-3.3-8b-instruct"),
    ("llama-4-scout", "llama/llama-4-scout-17b-16e-instruct-fp8"),
    (
        "llama-4-maverick",
        "llama/llama-4-maverick-17b-128e-instruct-fp8",
    ),
    // ── Amazon Bedrock Nova (2024-2025) ──
    ("nova-micro", "bedrock/amazon.nova-micro-v1:0"),
    ("nova-lite", "bedrock/amazon.nova-lite-v1:0"),
    ("nova-pro", "bedrock/amazon.nova-pro-v1:0"),
    ("nova-2-lite", "bedrock/amazon.nova-2-lite-v1:0"),
    // ── Microsoft Phi (2023-2025) ──
    ("phi-3-mini", "microsoft/phi-3-mini-128k-instruct"),
    ("phi-3-small", "microsoft/phi-3-small-128k-instruct"),
    ("phi-3-medium", "microsoft/phi-3-medium-128k-instruct"),
    ("phi-3.5-mini", "microsoft/phi-3.5-mini-instruct"),
    ("phi-3.5-moe", "microsoft/phi-3.5-moe-instruct"),
    ("phi-4", "microsoft/phi-4"),
    ("phi-4-mini", "microsoft/phi-4-mini-instruct"),
    ("phi-4-reasoning", "microsoft/phi-4-reasoning"),
    ("phi-4-multimodal", "microsoft/phi-4-multimodal-instruct"),
    // ── Cohere (2023-2025) ──
    ("command-r", "cohere/command-r-08-2024"),
    ("command-r-plus", "cohere/command-r-plus-08-2024"),
    ("command-a", "cohere/command-a-03-2025"),
    ("command-a-reasoning", "cohere/command-a-reasoning-08-2025"),
    ("command-r7b", "cohere/command-r7b-12-2024"),
    // ── Groq hosted models ──
    ("llama-groq-3.3-70b", "groq/llama-3.3-70b-versatile"),
    ("llama-groq-3.1-8b", "groq/llama-3.1-8b-instant"),
    (
        "llama-groq-4-scout",
        "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    ),
    (
        "llama-groq-4-maverick",
        "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    ),
    ("mixtral-groq-8x7b", "groq/mixtral-8x7b-32768"),
    ("gemma2-groq-9b", "groq/gemma2-9b-it"),
    ("qwq-groq-32b", "groq/qwen-qwq-32b"),
    ("deepseek-r1-groq-70b", "groq/deepseek-r1-distill-llama-70b"),
    ("qwen3-groq-32b", "groq/qwen/qwen3-32b"),
    // ── Ollama local models (no API key needed) ──
    ("ollama-llama3", "ollama/llama3"),
    ("ollama-llama3.1", "ollama/llama3.1"),
    ("ollama-llama3.2", "ollama/llama3.2"),
    ("ollama-llama3.3", "ollama/llama3.3"),
    ("ollama-codellama", "ollama/codellama"),
    ("ollama-deepseek-coder", "ollama/deepseek-coder"),
    ("ollama-deepseek-r1", "ollama/deepseek-r1"),
    ("ollama-qwen2.5", "ollama/qwen2.5"),
    ("ollama-qwen2.5-coder", "ollama/qwen2.5-coder"),
    ("ollama-mistral", "ollama/mistral"),
    ("ollama-gemma2", "ollama/gemma2"),
    ("ollama-phi3", "ollama/phi3"),
    ("ollama-phi4", "ollama/phi4"),
    // ── OpenRouter (use OPENROUTER_API_KEY) ──
    ("or-gpt4o", "openrouter/openai/gpt-4o"),
    ("or-gpt4o-mini", "openrouter/openai/gpt-4o-mini"),
    ("or-claude", "openrouter/anthropic/claude-sonnet-4"),
    ("or-deepseek", "openrouter/deepseek/deepseek-chat"),
    ("or-llama", "openrouter/meta-llama/llama-3.3-70b-instruct"),
    ("or-gemini", "openrouter/google/gemini-2.5-pro-preview"),
    ("or-mistral", "openrouter/mistralai/mistral-large-latest"),
    ("free-router", "openrouter/openrouter/free"),
    ("deepseek-r1-free", "openrouter/deepseek/deepseek-r1:free"),
    (
        "llama-3.1-8b-free",
        "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    ),
    (
        "qwen-2.5-7b-free",
        "openrouter/qwen/qwen2.5-7b-instruct:free",
    ),
    // ── APEX Free (ALL OpenRouter free coding models) ──
    ("free-or-router", "openrouter/openrouter/free"),
    ("free-or-qwen3-235b", "openrouter/qwen/qwen3-235b-a22b:free"),
    ("free-or-qwen3-coder", "openrouter/qwen/qwen3-coder:free"),
    (
        "free-or-qwen3-next-80b",
        "openrouter/qwen/qwen3-next-80b-a3b-instruct:free",
    ),
    (
        "free-or-nemotron-super",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    ),
    (
        "free-or-nemotron-nano",
        "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
    ),
    (
        "free-or-gemma-4-26b",
        "openrouter/google/gemma-4-26b-a4b-it:free",
    ),
    (
        "free-or-gemma-4-31b",
        "openrouter/google/gemma-4-31b-it:free",
    ),
    (
        "free-or-ring-2.6",
        "openrouter/inclusionai/ring-2.6-1t:free",
    ),
    (
        "free-or-deepseek-v3.2",
        "openrouter/deepseek/deepseek-chat-v3.2:free",
    ),
    (
        "free-or-deepseek-r1",
        "openrouter/deepseek/deepseek-r1:free",
    ),
    (
        "free-or-llama-3.3-70b",
        "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    ),
    (
        "free-or-minimax-m2.5",
        "openrouter/minimax/minimax-m2.5:free",
    ),
    ("free-or-glm-4.6", "openrouter/z-ai/glm-4.6:free"),
    (
        "free-or-poolside-laguna-m",
        "openrouter/poolside/laguna-m.1:free",
    ),
    (
        "free-or-poolside-laguna-xs",
        "openrouter/poolside/laguna-xs.2:free",
    ),
    (
        "free-or-gpt-oss-120b",
        "openrouter/openai/gpt-oss-120b:free",
    ),
    ("free-or-gpt-oss-20b", "openrouter/openai/gpt-oss-20b:free"),
    (
        "free-or-liquid-thinking",
        "openrouter/liquid/lfm-2.5-1.2b-thinking:free",
    ),
    // ── Cerebras (ultra-fast inference) ──
    ("cerebras-llama3.1-8b", "cerebras/llama3.1-8b"),
    (
        "cerebras-qwen3-235b",
        "cerebras/qwen-3-235b-a22b-instruct-2507",
    ),
    ("cerebras-gpt-oss-120b", "cerebras/gpt-oss-120b"),
    // ── Fireworks AI ──
    (
        "fireworks-deepseek-v3.1",
        "fireworks/accounts/fireworks/models/deepseek-v3p1",
    ),
    (
        "fireworks-deepseek-v3.2",
        "fireworks/accounts/fireworks/models/deepseek-v3p2",
    ),
    (
        "fireworks-deepseek-v4-pro",
        "fireworks/accounts/fireworks/models/deepseek-v4-pro",
    ),
    (
        "fireworks-qwen3.6-plus",
        "fireworks/accounts/fireworks/models/qwen3p6-plus",
    ),
    (
        "fireworks-kimi-k2",
        "fireworks/accounts/fireworks/models/kimi-k2-instruct",
    ),
    (
        "fireworks-glm-5",
        "fireworks/accounts/fireworks/models/glm-5",
    ),
    (
        "fireworks-gpt-oss-120b",
        "fireworks/accounts/fireworks/models/gpt-oss-120b",
    ),
    // ── Together AI ──
    (
        "together-deepseek-v3",
        "together_ai/deepseek-ai/DeepSeek-V3",
    ),
    (
        "together-deepseek-r1",
        "together_ai/deepseek-ai/DeepSeek-R1",
    ),
    (
        "together-deepseek-v4-pro",
        "together_ai/deepseek-ai/DeepSeek-V4-Pro",
    ),
    (
        "together-llama-3.3-70b",
        "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    ),
    (
        "together-qwen3-coder",
        "together_ai/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8",
    ),
    (
        "together-qwen3.5-397b",
        "together_ai/Qwen/Qwen3.5-397B-A17B",
    ),
    ("together-gemma-4-31b", "together_ai/google/gemma-4-31B-it"),
    // ── Hugging Face ──
    ("hf-deepseek-r1", "huggingface/deepseek-ai/DeepSeek-R1-0528"),
    ("hf-deepseek-v3.2", "huggingface/deepseek-ai/DeepSeek-V3.2"),
    (
        "hf-qwen3-coder",
        "huggingface/Qwen/Qwen3-Coder-480B-A35B-Instruct",
    ),
    ("hf-qwen3.5-397b", "huggingface/Qwen/Qwen3.5-397B-A17B"),
    ("hf-glm-5.1", "huggingface/zai-org/GLM-5.1"),
    ("hf-kimi-k2.6", "huggingface/moonshotai/Kimi-K2.6"),
    // ── Perplexity ──
    ("sonar", "perplexity/sonar"),
    ("sonar-pro", "perplexity/sonar-pro"),
    ("sonar-reasoning-pro", "perplexity/sonar-reasoning-pro"),
    ("sonar-deep-research", "perplexity/sonar-deep-research"),
    // ── NVIDIA NIM ──
    ("nvidia-deepseek-r1", "nvidia/deepseek-ai/deepseek-r1"),
    ("nvidia-deepseek-v3.2", "nvidia/deepseek-ai/deepseek-v3.2"),
    ("nvidia-llama-3.3-70b", "nvidia/meta/llama-3.3-70b-instruct"),
    (
        "nvidia-llama-4-scout",
        "nvidia/meta/llama-4-scout-17b-16e-instruct",
    ),
    (
        "nvidia-llama-4-maverick",
        "nvidia/meta/llama-4-maverick-17b-128e-instruct",
    ),
    ("nvidia-qwen3-235b", "nvidia/qwen/qwen3-235b-a22b"),
    ("nvidia-phi-4-mini", "nvidia/microsoft/phi-4-mini-instruct"),
    (
        "nvidia-nemotron-super",
        "nvidia/nvidia/nemotron-3-super-120b-a12b",
    ),
    // ── Cloudflare Workers AI ──
    ("cf-gpt-oss-120b", "cloudflare/@cf/openai/gpt-oss-120b"),
    ("cf-gpt-oss-20b", "cloudflare/@cf/openai/gpt-oss-20b"),
    (
        "cf-llama-4-scout",
        "cloudflare/@cf/meta/llama-4-scout-17b-16e-instruct",
    ),
    ("cf-gemma-4-26b", "cloudflare/@cf/google/gemma-4-26b-a4b-it"),
    ("cf-kimi-k2.5", "cloudflare/@cf/moonshotai/kimi-k2.5"),
    ("cf-glm-4.7-flash", "cloudflare/@cf/zai-org/glm-4.7-flash"),
    // ── APEX Pro (frontier models via OpenRouter — pay-as-you-go) ──
    ("pro-glm-5", "openrouter/z-ai/glm-5"),
    ("pro-glm-5.1", "openrouter/z-ai/glm-5.1"),
    ("pro-kimi-k2.5", "openrouter/moonshotai/kimi-k2.5"),
    ("pro-kimi-k2.6", "openrouter/moonshotai/kimi-k2.6"),
    ("pro-minimax-m2.5", "openrouter/minimax/minimax-m2.5"),
    ("pro-minimax-m2.7", "openrouter/minimax/minimax-m2.7"),
    ("pro-qwen3.5-plus", "openrouter/qwen/qwen3.5-plus"),
    ("pro-qwen3.6-plus", "openrouter/qwen/qwen3.6-plus"),
    ("pro-deepseek-v4-pro", "openrouter/deepseek/deepseek-v4-pro"),
    (
        "pro-deepseek-v4-flash",
        "openrouter/deepseek/deepseek-v4-flash",
    ),
];

/// `MODEL_PROVIDERS` in `apex/config.py`: alias → provider env var
/// (`None` = no key needed, Ollama), in declaration order.
pub const MODEL_PROVIDERS: &[(&str, Option<&str>)] = &[
    ("claude-3.5-haiku", Some("ANTHROPIC_API_KEY")),
    ("claude-3.5-sonnet", Some("ANTHROPIC_API_KEY")),
    ("claude-3.7-sonnet", Some("ANTHROPIC_API_KEY")),
    ("claude-sonnet-4", Some("ANTHROPIC_API_KEY")),
    ("claude-opus-4", Some("ANTHROPIC_API_KEY")),
    ("claude-sonnet-4.5", Some("ANTHROPIC_API_KEY")),
    ("claude-opus-4.5", Some("ANTHROPIC_API_KEY")),
    ("claude-haiku-4.5", Some("ANTHROPIC_API_KEY")),
    ("claude-opus-4.7", Some("ANTHROPIC_API_KEY")),
    ("claude-sonnet-4.6", Some("ANTHROPIC_API_KEY")),
    ("gpt-4o", Some("OPENAI_API_KEY")),
    ("gpt-4o-mini", Some("OPENAI_API_KEY")),
    ("gpt-4-turbo", Some("OPENAI_API_KEY")),
    ("gpt-4.1", Some("OPENAI_API_KEY")),
    ("gpt-4.1-mini", Some("OPENAI_API_KEY")),
    ("gpt-4.1-nano", Some("OPENAI_API_KEY")),
    ("gpt-5", Some("OPENAI_API_KEY")),
    ("gpt-5-mini", Some("OPENAI_API_KEY")),
    ("gpt-5-nano", Some("OPENAI_API_KEY")),
    ("gpt-5-pro", Some("OPENAI_API_KEY")),
    ("o1", Some("OPENAI_API_KEY")),
    ("o1-mini", Some("OPENAI_API_KEY")),
    ("o3", Some("OPENAI_API_KEY")),
    ("o3-mini", Some("OPENAI_API_KEY")),
    ("o3-pro", Some("OPENAI_API_KEY")),
    ("o4-mini", Some("OPENAI_API_KEY")),
    ("gemini-1.5-flash", Some("GEMINI_API_KEY")),
    ("gemini-1.5-pro", Some("GEMINI_API_KEY")),
    ("gemini-2.0-flash", Some("GEMINI_API_KEY")),
    ("gemini-2.0-flash-lite", Some("GEMINI_API_KEY")),
    ("gemini-2.5-flash", Some("GEMINI_API_KEY")),
    ("gemini-2.5-flash-lite", Some("GEMINI_API_KEY")),
    ("gemini-2.5-pro", Some("GEMINI_API_KEY")),
    ("gemini-3-flash", Some("GEMINI_API_KEY")),
    ("gemini-3-pro", Some("GEMINI_API_KEY")),
    ("gemma-3-4b", Some("GEMINI_API_KEY")),
    ("gemma-3-12b", Some("GEMINI_API_KEY")),
    ("gemma-3-27b", Some("GEMINI_API_KEY")),
    ("gemma-4-26b", Some("GEMINI_API_KEY")),
    ("gemma-4-31b", Some("GEMINI_API_KEY")),
    ("grok-2", Some("XAI_API_KEY")),
    ("grok-3", Some("XAI_API_KEY")),
    ("grok-3-mini", Some("XAI_API_KEY")),
    ("grok-4", Some("XAI_API_KEY")),
    ("grok-4-fast", Some("XAI_API_KEY")),
    ("deepseek-chat", Some("DEEPSEEK_API_KEY")),
    ("deepseek-reasoner", Some("DEEPSEEK_API_KEY")),
    ("deepseek-v4-flash", Some("DEEPSEEK_API_KEY")),
    ("deepseek-v4-pro", Some("DEEPSEEK_API_KEY")),
    ("mistral-small-latest", Some("MISTRAL_API_KEY")),
    ("mistral-medium-latest", Some("MISTRAL_API_KEY")),
    ("mistral-large-latest", Some("MISTRAL_API_KEY")),
    ("codestral", Some("MISTRAL_API_KEY")),
    ("devstral", Some("MISTRAL_API_KEY")),
    ("devstral-small", Some("MISTRAL_API_KEY")),
    ("ministral-8b", Some("MISTRAL_API_KEY")),
    ("ministral-3b", Some("MISTRAL_API_KEY")),
    ("mixtral-8x7b", Some("MISTRAL_API_KEY")),
    ("mixtral-8x22b", Some("MISTRAL_API_KEY")),
    ("mistral-7b", Some("MISTRAL_API_KEY")),
    ("magistral-medium", Some("MISTRAL_API_KEY")),
    ("magistral-small", Some("MISTRAL_API_KEY")),
    ("pixtral-large", Some("MISTRAL_API_KEY")),
    ("pixtral-12b", Some("MISTRAL_API_KEY")),
    ("qwen-max", Some("DASHSCOPE_API_KEY")),
    ("qwen-plus", Some("DASHSCOPE_API_KEY")),
    ("qwen-turbo", Some("DASHSCOPE_API_KEY")),
    ("qwen3-8b", Some("DASHSCOPE_API_KEY")),
    ("qwen3-32b", Some("DASHSCOPE_API_KEY")),
    ("qwen3-235b", Some("DASHSCOPE_API_KEY")),
    ("qwen3-coder-plus", Some("DASHSCOPE_API_KEY")),
    ("qwen3-coder-flash", Some("DASHSCOPE_API_KEY")),
    ("qwen3-max", Some("DASHSCOPE_API_KEY")),
    ("qwen3.5-plus", Some("DASHSCOPE_API_KEY")),
    ("qwen3.6-plus", Some("DASHSCOPE_API_KEY")),
    ("qwq-plus", Some("DASHSCOPE_API_KEY")),
    ("llama-3.3-70b", Some("LLAMA_API_KEY")),
    ("llama-3.3-8b", Some("LLAMA_API_KEY")),
    ("llama-4-scout", Some("LLAMA_API_KEY")),
    ("llama-4-maverick", Some("LLAMA_API_KEY")),
    ("nova-micro", Some("AWS_ACCESS_KEY_ID")),
    ("nova-lite", Some("AWS_ACCESS_KEY_ID")),
    ("nova-pro", Some("AWS_ACCESS_KEY_ID")),
    ("nova-2-lite", Some("AWS_ACCESS_KEY_ID")),
    ("phi-3-mini", Some("GITHUB_TOKEN")),
    ("phi-3-small", Some("GITHUB_TOKEN")),
    ("phi-3-medium", Some("GITHUB_TOKEN")),
    ("phi-3.5-mini", Some("GITHUB_TOKEN")),
    ("phi-3.5-moe", Some("GITHUB_TOKEN")),
    ("phi-4", Some("GITHUB_TOKEN")),
    ("phi-4-mini", Some("GITHUB_TOKEN")),
    ("phi-4-reasoning", Some("GITHUB_TOKEN")),
    ("phi-4-multimodal", Some("GITHUB_TOKEN")),
    ("command-r", Some("COHERE_API_KEY")),
    ("command-r-plus", Some("COHERE_API_KEY")),
    ("command-a", Some("COHERE_API_KEY")),
    ("command-a-reasoning", Some("COHERE_API_KEY")),
    ("command-r7b", Some("COHERE_API_KEY")),
    ("llama-groq-3.3-70b", Some("GROQ_API_KEY")),
    ("llama-groq-3.1-8b", Some("GROQ_API_KEY")),
    ("llama-groq-4-scout", Some("GROQ_API_KEY")),
    ("llama-groq-4-maverick", Some("GROQ_API_KEY")),
    ("mixtral-groq-8x7b", Some("GROQ_API_KEY")),
    ("gemma2-groq-9b", Some("GROQ_API_KEY")),
    ("qwq-groq-32b", Some("GROQ_API_KEY")),
    ("deepseek-r1-groq-70b", Some("GROQ_API_KEY")),
    ("qwen3-groq-32b", Some("GROQ_API_KEY")),
    ("ollama-llama3", None),
    ("ollama-llama3.1", None),
    ("ollama-llama3.2", None),
    ("ollama-llama3.3", None),
    ("ollama-codellama", None),
    ("ollama-deepseek-coder", None),
    ("ollama-deepseek-r1", None),
    ("ollama-qwen2.5", None),
    ("ollama-qwen2.5-coder", None),
    ("ollama-mistral", None),
    ("ollama-gemma2", None),
    ("ollama-phi3", None),
    ("ollama-phi4", None),
    ("or-gpt4o", Some("OPENROUTER_API_KEY")),
    ("or-gpt4o-mini", Some("OPENROUTER_API_KEY")),
    ("or-claude", Some("OPENROUTER_API_KEY")),
    ("or-deepseek", Some("OPENROUTER_API_KEY")),
    ("or-llama", Some("OPENROUTER_API_KEY")),
    ("or-gemini", Some("OPENROUTER_API_KEY")),
    ("or-mistral", Some("OPENROUTER_API_KEY")),
    ("free-router", Some("OPENROUTER_API_KEY")),
    ("deepseek-r1-free", Some("OPENROUTER_API_KEY")),
    ("llama-3.1-8b-free", Some("OPENROUTER_API_KEY")),
    ("qwen-2.5-7b-free", Some("OPENROUTER_API_KEY")),
    ("free-or-router", Some("OPENROUTER_API_KEY")),
    ("free-or-qwen3-235b", Some("OPENROUTER_API_KEY")),
    ("free-or-qwen3-coder", Some("OPENROUTER_API_KEY")),
    ("free-or-qwen3-next-80b", Some("OPENROUTER_API_KEY")),
    ("free-or-nemotron-super", Some("OPENROUTER_API_KEY")),
    ("free-or-nemotron-nano", Some("OPENROUTER_API_KEY")),
    ("free-or-gemma-4-26b", Some("OPENROUTER_API_KEY")),
    ("free-or-gemma-4-31b", Some("OPENROUTER_API_KEY")),
    ("free-or-ring-2.6", Some("OPENROUTER_API_KEY")),
    ("free-or-deepseek-v3.2", Some("OPENROUTER_API_KEY")),
    ("free-or-deepseek-r1", Some("OPENROUTER_API_KEY")),
    ("free-or-llama-3.3-70b", Some("OPENROUTER_API_KEY")),
    ("free-or-minimax-m2.5", Some("OPENROUTER_API_KEY")),
    ("free-or-glm-4.6", Some("OPENROUTER_API_KEY")),
    ("free-or-poolside-laguna-m", Some("OPENROUTER_API_KEY")),
    ("free-or-poolside-laguna-xs", Some("OPENROUTER_API_KEY")),
    ("free-or-gpt-oss-120b", Some("OPENROUTER_API_KEY")),
    ("free-or-gpt-oss-20b", Some("OPENROUTER_API_KEY")),
    ("free-or-liquid-thinking", Some("OPENROUTER_API_KEY")),
    ("pro-glm-5", Some("OPENROUTER_API_KEY")),
    ("pro-glm-5.1", Some("OPENROUTER_API_KEY")),
    ("pro-kimi-k2.5", Some("OPENROUTER_API_KEY")),
    ("pro-kimi-k2.6", Some("OPENROUTER_API_KEY")),
    ("pro-minimax-m2.5", Some("OPENROUTER_API_KEY")),
    ("pro-minimax-m2.7", Some("OPENROUTER_API_KEY")),
    ("pro-qwen3.5-plus", Some("OPENROUTER_API_KEY")),
    ("pro-qwen3.6-plus", Some("OPENROUTER_API_KEY")),
    ("pro-deepseek-v4-pro", Some("OPENROUTER_API_KEY")),
    ("pro-deepseek-v4-flash", Some("OPENROUTER_API_KEY")),
    ("cerebras-llama3.1-8b", Some("CEREBRAS_API_KEY")),
    ("cerebras-qwen3-235b", Some("CEREBRAS_API_KEY")),
    ("cerebras-gpt-oss-120b", Some("CEREBRAS_API_KEY")),
    ("fireworks-deepseek-v3.1", Some("FIREWORKS_API_KEY")),
    ("fireworks-deepseek-v3.2", Some("FIREWORKS_API_KEY")),
    ("fireworks-deepseek-v4-pro", Some("FIREWORKS_API_KEY")),
    ("fireworks-qwen3.6-plus", Some("FIREWORKS_API_KEY")),
    ("fireworks-kimi-k2", Some("FIREWORKS_API_KEY")),
    ("fireworks-glm-5", Some("FIREWORKS_API_KEY")),
    ("fireworks-gpt-oss-120b", Some("FIREWORKS_API_KEY")),
    ("together-deepseek-v3", Some("TOGETHER_API_KEY")),
    ("together-deepseek-r1", Some("TOGETHER_API_KEY")),
    ("together-deepseek-v4-pro", Some("TOGETHER_API_KEY")),
    ("together-llama-3.3-70b", Some("TOGETHER_API_KEY")),
    ("together-qwen3-coder", Some("TOGETHER_API_KEY")),
    ("together-qwen3.5-397b", Some("TOGETHER_API_KEY")),
    ("together-gemma-4-31b", Some("TOGETHER_API_KEY")),
    ("hf-deepseek-r1", Some("HF_TOKEN")),
    ("hf-deepseek-v3.2", Some("HF_TOKEN")),
    ("hf-qwen3-coder", Some("HF_TOKEN")),
    ("hf-qwen3.5-397b", Some("HF_TOKEN")),
    ("hf-glm-5.1", Some("HF_TOKEN")),
    ("hf-kimi-k2.6", Some("HF_TOKEN")),
    ("sonar", Some("PERPLEXITY_API_KEY")),
    ("sonar-pro", Some("PERPLEXITY_API_KEY")),
    ("sonar-reasoning-pro", Some("PERPLEXITY_API_KEY")),
    ("sonar-deep-research", Some("PERPLEXITY_API_KEY")),
    ("nvidia-deepseek-r1", Some("NVIDIA_API_KEY")),
    ("nvidia-deepseek-v3.2", Some("NVIDIA_API_KEY")),
    ("nvidia-llama-3.3-70b", Some("NVIDIA_API_KEY")),
    ("nvidia-llama-4-scout", Some("NVIDIA_API_KEY")),
    ("nvidia-llama-4-maverick", Some("NVIDIA_API_KEY")),
    ("nvidia-qwen3-235b", Some("NVIDIA_API_KEY")),
    ("nvidia-phi-4-mini", Some("NVIDIA_API_KEY")),
    ("nvidia-nemotron-super", Some("NVIDIA_API_KEY")),
    ("cf-gpt-oss-120b", Some("CLOUDFLARE_API_KEY")),
    ("cf-gpt-oss-20b", Some("CLOUDFLARE_API_KEY")),
    ("cf-llama-4-scout", Some("CLOUDFLARE_API_KEY")),
    ("cf-gemma-4-26b", Some("CLOUDFLARE_API_KEY")),
    ("cf-kimi-k2.5", Some("CLOUDFLARE_API_KEY")),
    ("cf-glm-4.7-flash", Some("CLOUDFLARE_API_KEY")),
];

/// Python's `str.title()` over the env var name: `"ANTHROPIC_API_KEY"`
/// becomes `"Anthropic"`, `"AWS_ACCESS_KEY_ID"` becomes `"Aws Access Key Id"`.
fn provider_display_name(env_var: &str) -> String {
    let stripped = env_var
        .replace("_API_KEY", "")
        .replace("_TOKEN", "")
        .replace('_', " ");
    let mut out = String::new();
    for word in stripped.split(' ') {
        if word.is_empty() {
            continue;
        }
        let mut chars = word.chars();
        if let Some(first) = chars.next() {
            out.extend(first.to_uppercase());
            out.extend(chars.flat_map(|c| c.to_lowercase()));
        }
        out.push(' ');
    }
    out.pop();
    out
}

/// `{"alias": …, "model": …}` pairs in `MODELS` order
/// (Python's `list_models` / `api_models_refresh`).
pub fn models_list() -> Vec<serde_json::Value> {
    MODELS
        .iter()
        .map(|(alias, model_id)| json!({"alias": alias, "model": model_id}))
        .collect()
}

/// `GET /api/v1/providers` body: one entry per env var, first-seen order of
/// `MODELS`, `models` in `MODEL_PROVIDERS` order (Python's
/// `_get_configured_providers`).
pub fn configured_providers() -> Vec<serde_json::Value> {
    let mut out: Vec<serde_json::Value> = Vec::new();
    for (alias, _model_id) in MODELS {
        let env_key = MODEL_PROVIDERS
            .iter()
            .find(|(a, _)| a == alias)
            .and_then(|(_, e)| *e);
        let Some(env_key) = env_key else {
            continue;
        };
        if out.iter().any(|p| p["env_var"] == env_key) {
            continue;
        }
        let models: Vec<&str> = MODEL_PROVIDERS
            .iter()
            .filter(|(_, e)| *e == Some(env_key))
            .map(|(a, _)| *a)
            .collect();
        let configured =
            std::env::var(env_key).is_ok() || std::env::var(env_key.to_lowercase()).is_ok();
        out.push(json!({
            "name": provider_display_name(env_key),
            "env_var": env_key,
            "configured": configured,
            "models": models,
        }));
    }
    out
}
