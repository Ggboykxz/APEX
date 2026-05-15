#!/usr/bin/env python3
"""Generate updated model data for the APEX project from models.dev JSON."""

import json
from pathlib import Path

SRC = Path("/tmp/condensed_models.json")
OUT_DIR = Path("/home/z/my-project/APEX")

data = json.load(open(SRC))

# ═══════════════════════════════════════════════════════════════════
# 1. Python config_models_new.py — MODELS dict + MODEL_PROVIDERS dict
# ═══════════════════════════════════════════════════════════════════

# Curated model selections per provider.
# Each entry: (alias, litellm_model_string, env_key)

MODELS_ENTRIES = [
    # ── Anthropic Claude (2024-2026) ──
    ("claude-3.5-haiku", "anthropic/claude-3-5-haiku-20241022", "ANTHROPIC_API_KEY"),
    ("claude-3.5-sonnet", "anthropic/claude-3-5-sonnet-20241022", "ANTHROPIC_API_KEY"),
    ("claude-3.7-sonnet", "anthropic/claude-3-7-sonnet-20250219", "ANTHROPIC_API_KEY"),
    ("claude-sonnet-4", "anthropic/claude-sonnet-4-20250514", "ANTHROPIC_API_KEY"),
    ("claude-opus-4", "anthropic/claude-opus-4-20250514", "ANTHROPIC_API_KEY"),
    ("claude-sonnet-4.5", "anthropic/claude-sonnet-4-5", "ANTHROPIC_API_KEY"),
    ("claude-opus-4.5", "anthropic/claude-opus-4-5", "ANTHROPIC_API_KEY"),
    ("claude-haiku-4.5", "anthropic/claude-haiku-4-5", "ANTHROPIC_API_KEY"),
    ("claude-opus-4.7", "anthropic/claude-opus-4-7", "ANTHROPIC_API_KEY"),
    ("claude-sonnet-4.6", "anthropic/claude-sonnet-4-6", "ANTHROPIC_API_KEY"),

    # ── OpenAI GPT / o-series (2020-2025) ──
    ("gpt-4o", "openai/gpt-4o", "OPENAI_API_KEY"),
    ("gpt-4o-mini", "openai/gpt-4o-mini", "OPENAI_API_KEY"),
    ("gpt-4-turbo", "openai/gpt-4-turbo", "OPENAI_API_KEY"),
    ("gpt-4.1", "openai/gpt-4.1", "OPENAI_API_KEY"),
    ("gpt-4.1-mini", "openai/gpt-4.1-mini", "OPENAI_API_KEY"),
    ("gpt-4.1-nano", "openai/gpt-4.1-nano", "OPENAI_API_KEY"),
    ("gpt-5", "openai/gpt-5", "OPENAI_API_KEY"),
    ("gpt-5-mini", "openai/gpt-5-mini", "OPENAI_API_KEY"),
    ("gpt-5-nano", "openai/gpt-5-nano", "OPENAI_API_KEY"),
    ("gpt-5-pro", "openai/gpt-5-pro", "OPENAI_API_KEY"),
    ("o1", "openai/o1", "OPENAI_API_KEY"),
    ("o1-mini", "openai/o1-mini", "OPENAI_API_KEY"),
    ("o3", "openai/o3", "OPENAI_API_KEY"),
    ("o3-mini", "openai/o3-mini", "OPENAI_API_KEY"),
    ("o3-pro", "openai/o3-pro", "OPENAI_API_KEY"),
    ("o4-mini", "openai/o4-mini", "OPENAI_API_KEY"),

    # ── Google DeepMind Gemini (2023-2025) ──
    ("gemini-1.5-flash", "google/gemini-1.5-flash", "GEMINI_API_KEY"),
    ("gemini-1.5-pro", "google/gemini-1.5-pro", "GEMINI_API_KEY"),
    ("gemini-2.0-flash", "google/gemini-2.0-flash", "GEMINI_API_KEY"),
    ("gemini-2.0-flash-lite", "google/gemini-2.0-flash-lite", "GEMINI_API_KEY"),
    ("gemini-2.5-flash", "google/gemini-2.5-flash", "GEMINI_API_KEY"),
    ("gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite", "GEMINI_API_KEY"),
    ("gemini-2.5-pro", "google/gemini-2.5-pro", "GEMINI_API_KEY"),
    ("gemini-3-flash", "google/gemini-3-flash-preview", "GEMINI_API_KEY"),
    ("gemini-3-pro", "google/gemini-3-pro-preview", "GEMINI_API_KEY"),

    # ── xAI Grok (2023-2025) ──
    ("grok-2", "xai/grok-2", "XAI_API_KEY"),
    ("grok-3", "xai/grok-3", "XAI_API_KEY"),
    ("grok-3-mini", "xai/grok-3-mini", "XAI_API_KEY"),
    ("grok-4", "xai/grok-4", "XAI_API_KEY"),
    ("grok-4-fast", "xai/grok-4-fast", "XAI_API_KEY"),

    # ── DeepSeek (2024-2025) ──
    ("deepseek-chat", "deepseek/deepseek-chat", "DEEPSEEK_API_KEY"),
    ("deepseek-reasoner", "deepseek/deepseek-reasoner", "DEEPSEEK_API_KEY"),
    ("deepseek-v4-flash", "deepseek/deepseek-v4-flash", "DEEPSEEK_API_KEY"),
    ("deepseek-v4-pro", "deepseek/deepseek-v4-pro", "DEEPSEEK_API_KEY"),

    # ── Mistral AI (2023-2025) ──
    ("mistral-small-latest", "mistral/mistral-small-latest", "MISTRAL_API_KEY"),
    ("mistral-medium-latest", "mistral/mistral-medium-latest", "MISTRAL_API_KEY"),
    ("mistral-large-latest", "mistral/mistral-large-latest", "MISTRAL_API_KEY"),
    ("codestral", "mistral/codestral-latest", "MISTRAL_API_KEY"),
    ("devstral", "mistral/devstral-medium-latest", "MISTRAL_API_KEY"),
    ("devstral-small", "mistral/devstral-small-2507", "MISTRAL_API_KEY"),
    ("ministral-8b", "mistral/ministral-8b-latest", "MISTRAL_API_KEY"),
    ("ministral-3b", "mistral/ministral-3b-latest", "MISTRAL_API_KEY"),
    ("mixtral-8x7b", "mistral/open-mixtral-8x7b", "MISTRAL_API_KEY"),
    ("mixtral-8x22b", "mistral/open-mixtral-8x22b", "MISTRAL_API_KEY"),
    ("mistral-7b", "mistral/open-mistral-7b", "MISTRAL_API_KEY"),
    ("magistral-medium", "mistral/magistral-medium-latest", "MISTRAL_API_KEY"),
    ("magistral-small", "mistral/magistral-small", "MISTRAL_API_KEY"),
    ("pixtral-large", "mistral/pixtral-large-latest", "MISTRAL_API_KEY"),
    ("pixtral-12b", "mistral/pixtral-12b", "MISTRAL_API_KEY"),

    # ── Alibaba Qwen (2024-2025) ──
    ("qwen-max", "alibaba/qwen-max", "DASHSCOPE_API_KEY"),
    ("qwen-plus", "alibaba/qwen-plus", "DASHSCOPE_API_KEY"),
    ("qwen-turbo", "alibaba/qwen-turbo", "DASHSCOPE_API_KEY"),
    ("qwen3-8b", "alibaba/qwen3-8b", "DASHSCOPE_API_KEY"),
    ("qwen3-32b", "alibaba/qwen3-32b", "DASHSCOPE_API_KEY"),
    ("qwen3-235b", "alibaba/qwen3-235b-a22b", "DASHSCOPE_API_KEY"),
    ("qwen3-coder-plus", "alibaba/qwen3-coder-plus", "DASHSCOPE_API_KEY"),
    ("qwen3-coder-flash", "alibaba/qwen3-coder-flash", "DASHSCOPE_API_KEY"),
    ("qwen3-max", "alibaba/qwen3-max", "DASHSCOPE_API_KEY"),
    ("qwen3.5-plus", "alibaba/qwen3.5-plus", "DASHSCOPE_API_KEY"),
    ("qwen3.6-plus", "alibaba/qwen3.6-plus", "DASHSCOPE_API_KEY"),
    ("qwq-plus", "alibaba/qwq-plus", "DASHSCOPE_API_KEY"),

    # ── Meta Llama (2023-2025) via Llama API ──
    ("llama-3.3-70b", "llama/llama-3.3-70b-instruct", "LLAMA_API_KEY"),
    ("llama-3.3-8b", "llama/llama-3.3-8b-instruct", "LLAMA_API_KEY"),
    ("llama-4-scout", "llama/llama-4-scout-17b-16e-instruct-fp8", "LLAMA_API_KEY"),
    ("llama-4-maverick", "llama/llama-4-maverick-17b-128e-instruct-fp8", "LLAMA_API_KEY"),

    # ── Amazon Bedrock Nova (2024-2025) ──
    ("nova-micro", "bedrock/amazon.nova-micro-v1:0", "AWS_ACCESS_KEY_ID"),
    ("nova-lite", "bedrock/amazon.nova-lite-v1:0", "AWS_ACCESS_KEY_ID"),
    ("nova-pro", "bedrock/amazon.nova-pro-v1:0", "AWS_ACCESS_KEY_ID"),
    ("nova-2-lite", "bedrock/amazon.nova-2-lite-v1:0", "AWS_ACCESS_KEY_ID"),

    # ── Microsoft Phi (2023-2025) ──
    ("phi-3-mini", "microsoft/phi-3-mini-128k-instruct", "GITHUB_TOKEN"),
    ("phi-3-small", "microsoft/phi-3-small-128k-instruct", "GITHUB_TOKEN"),
    ("phi-3-medium", "microsoft/phi-3-medium-128k-instruct", "GITHUB_TOKEN"),
    ("phi-3.5-mini", "microsoft/phi-3.5-mini-instruct", "GITHUB_TOKEN"),
    ("phi-3.5-moe", "microsoft/phi-3.5-moe-instruct", "GITHUB_TOKEN"),
    ("phi-4", "microsoft/phi-4", "GITHUB_TOKEN"),
    ("phi-4-mini", "microsoft/phi-4-mini-instruct", "GITHUB_TOKEN"),
    ("phi-4-reasoning", "microsoft/phi-4-reasoning", "GITHUB_TOKEN"),
    ("phi-4-multimodal", "microsoft/phi-4-multimodal-instruct", "GITHUB_TOKEN"),

    # ── Cohere (2023-2025) ──
    ("command-r", "cohere/command-r-08-2024", "COHERE_API_KEY"),
    ("command-r-plus", "cohere/command-r-plus-08-2024", "COHERE_API_KEY"),
    ("command-a", "cohere/command-a-03-2025", "COHERE_API_KEY"),
    ("command-a-reasoning", "cohere/command-a-reasoning-08-2025", "COHERE_API_KEY"),
    ("command-r7b", "cohere/command-r7b-12-2024", "COHERE_API_KEY"),

    # ── Groq hosted models ──
    ("llama-groq-3.3-70b", "groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
    ("llama-groq-3.1-8b", "groq/llama-3.1-8b-instant", "GROQ_API_KEY"),
    ("llama-groq-4-scout", "groq/meta-llama/llama-4-scout-17b-16e-instruct", "GROQ_API_KEY"),
    ("llama-groq-4-maverick", "groq/meta-llama/llama-4-maverick-17b-128e-instruct", "GROQ_API_KEY"),
    ("mixtral-groq-8x7b", "groq/mixtral-8x7b-32768", "GROQ_API_KEY"),
    ("gemma2-groq-9b", "groq/gemma2-9b-it", "GROQ_API_KEY"),
    ("qwq-groq-32b", "groq/qwen-qwq-32b", "GROQ_API_KEY"),
    ("deepseek-r1-groq-70b", "groq/deepseek-r1-distill-llama-70b", "GROQ_API_KEY"),
    ("qwen3-groq-32b", "groq/qwen/qwen3-32b", "GROQ_API_KEY"),

    # ── Ollama local models (no API key needed) ──
    ("ollama-llama3", "ollama/llama3", None),
    ("ollama-llama3.1", "ollama/llama3.1", None),
    ("ollama-llama3.2", "ollama/llama3.2", None),
    ("ollama-llama3.3", "ollama/llama3.3", None),
    ("ollama-codellama", "ollama/codellama", None),
    ("ollama-deepseek-coder", "ollama/deepseek-coder", None),
    ("ollama-deepseek-r1", "ollama/deepseek-r1", None),
    ("ollama-qwen2.5", "ollama/qwen2.5", None),
    ("ollama-qwen2.5-coder", "ollama/qwen2.5-coder", None),
    ("ollama-mistral", "ollama/mistral", None),
    ("ollama-gemma2", "ollama/gemma2", None),
    ("ollama-phi3", "ollama/phi3", None),
    ("ollama-phi4", "ollama/phi4", None),

    # ── OpenRouter (use OPENROUTER_API_KEY) ──
    ("or-gpt4o", "openrouter/openai/gpt-4o", "OPENROUTER_API_KEY"),
    ("or-gpt4o-mini", "openrouter/openai/gpt-4o-mini", "OPENROUTER_API_KEY"),
    ("or-claude", "openrouter/anthropic/claude-sonnet-4", "OPENROUTER_API_KEY"),
    ("or-deepseek", "openrouter/deepseek/deepseek-chat", "OPENROUTER_API_KEY"),
    ("or-llama", "openrouter/meta-llama/llama-3.3-70b-instruct", "OPENROUTER_API_KEY"),
    ("or-gemini", "openrouter/google/gemini-2.5-pro-preview", "OPENROUTER_API_KEY"),
    ("or-mistral", "openrouter/mistralai/mistral-large-latest", "OPENROUTER_API_KEY"),

    # ── OpenRouter FREE models (no credit card required) ──
    ("free-router", "openrouter/openrouter/free", "OPENROUTER_API_KEY"),
    ("deepseek-r1-free", "openrouter/deepseek/deepseek-r1:free", "OPENROUTER_API_KEY"),
    ("llama-3.1-8b-free", "openrouter/meta-llama/llama-3.1-8b-instruct:free", "OPENROUTER_API_KEY"),
    ("qwen-2.5-7b-free", "openrouter/qwen/qwen2.5-7b-instruct:free", "OPENROUTER_API_KEY"),

    # ── Cerebras (ultra-fast inference) ──
    ("cerebras-llama3.1-8b", "cerebras/llama3.1-8b", "CEREBRAS_API_KEY"),
    ("cerebras-qwen3-235b", "cerebras/qwen-3-235b-a22b-instruct-2507", "CEREBRAS_API_KEY"),
    ("cerebras-gpt-oss-120b", "cerebras/gpt-oss-120b", "CEREBRAS_API_KEY"),

    # ── Fireworks AI ──
    ("fireworks-deepseek-v3.1", "fireworks/accounts/fireworks/models/deepseek-v3p1", "FIREWORKS_API_KEY"),
    ("fireworks-deepseek-v3.2", "fireworks/accounts/fireworks/models/deepseek-v3p2", "FIREWORKS_API_KEY"),
    ("fireworks-deepseek-v4-pro", "fireworks/accounts/fireworks/models/deepseek-v4-pro", "FIREWORKS_API_KEY"),
    ("fireworks-qwen3.6-plus", "fireworks/accounts/fireworks/models/qwen3p6-plus", "FIREWORKS_API_KEY"),
    ("fireworks-kimi-k2", "fireworks/accounts/fireworks/models/kimi-k2-instruct", "FIREWORKS_API_KEY"),
    ("fireworks-glm-5", "fireworks/accounts/fireworks/models/glm-5", "FIREWORKS_API_KEY"),
    ("fireworks-gpt-oss-120b", "fireworks/accounts/fireworks/models/gpt-oss-120b", "FIREWORKS_API_KEY"),

    # ── Together AI ──
    ("together-deepseek-v3", "together_ai/deepseek-ai/DeepSeek-V3", "TOGETHER_API_KEY"),
    ("together-deepseek-r1", "together_ai/deepseek-ai/DeepSeek-R1", "TOGETHER_API_KEY"),
    ("together-deepseek-v4-pro", "together_ai/deepseek-ai/DeepSeek-V4-Pro", "TOGETHER_API_KEY"),
    ("together-llama-3.3-70b", "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo", "TOGETHER_API_KEY"),
    ("together-qwen3-coder", "together_ai/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8", "TOGETHER_API_KEY"),
    ("together-qwen3.5-397b", "together_ai/Qwen/Qwen3.5-397B-A17B", "TOGETHER_API_KEY"),
    ("together-gemma-4-31b", "together_ai/google/gemma-4-31B-it", "TOGETHER_API_KEY"),

    # ── Hugging Face ──
    ("hf-deepseek-r1", "huggingface/deepseek-ai/DeepSeek-R1-0528", "HF_TOKEN"),
    ("hf-deepseek-v3.2", "huggingface/deepseek-ai/DeepSeek-V3.2", "HF_TOKEN"),
    ("hf-qwen3-coder", "huggingface/Qwen/Qwen3-Coder-480B-A35B-Instruct", "HF_TOKEN"),
    ("hf-qwen3.5-397b", "huggingface/Qwen/Qwen3.5-397B-A17B", "HF_TOKEN"),
    ("hf-glm-5.1", "huggingface/zai-org/GLM-5.1", "HF_TOKEN"),
    ("hf-kimi-k2.6", "huggingface/moonshotai/Kimi-K2.6", "HF_TOKEN"),

    # ── Perplexity ──
    ("sonar", "perplexity/sonar", "PERPLEXITY_API_KEY"),
    ("sonar-pro", "perplexity/sonar-pro", "PERPLEXITY_API_KEY"),
    ("sonar-reasoning-pro", "perplexity/sonar-reasoning-pro", "PERPLEXITY_API_KEY"),
    ("sonar-deep-research", "perplexity/sonar-deep-research", "PERPLEXITY_API_KEY"),

    # ── NVIDIA NIM ──
    ("nvidia-deepseek-r1", "nvidia/deepseek-ai/deepseek-r1", "NVIDIA_API_KEY"),
    ("nvidia-deepseek-v3.2", "nvidia/deepseek-ai/deepseek-v3.2", "NVIDIA_API_KEY"),
    ("nvidia-llama-3.3-70b", "nvidia/meta/llama-3.3-70b-instruct", "NVIDIA_API_KEY"),
    ("nvidia-llama-4-scout", "nvidia/meta/llama-4-scout-17b-16e-instruct", "NVIDIA_API_KEY"),
    ("nvidia-llama-4-maverick", "nvidia/meta/llama-4-maverick-17b-128e-instruct", "NVIDIA_API_KEY"),
    ("nvidia-qwen3-235b", "nvidia/qwen/qwen3-235b-a22b", "NVIDIA_API_KEY"),
    ("nvidia-phi-4-mini", "nvidia/microsoft/phi-4-mini-instruct", "NVIDIA_API_KEY"),
    ("nvidia-nemotron-super", "nvidia/nvidia/nemotron-3-super-120b-a12b", "NVIDIA_API_KEY"),

    # ── Cloudflare Workers AI ──
    ("cf-gpt-oss-120b", "cloudflare/@cf/openai/gpt-oss-120b", "CLOUDFLARE_API_KEY"),
    ("cf-gpt-oss-20b", "cloudflare/@cf/openai/gpt-oss-20b", "CLOUDFLARE_API_KEY"),
    ("cf-llama-4-scout", "cloudflare/@cf/meta/llama-4-scout-17b-16e-instruct", "CLOUDFLARE_API_KEY"),
    ("cf-gemma-4-26b", "cloudflare/@cf/google/gemma-4-26b-a4b-it", "CLOUDFLARE_API_KEY"),
    ("cf-kimi-k2.5", "cloudflare/@cf/moonshotai/kimi-k2.5", "CLOUDFLARE_API_KEY"),
    ("cf-glm-4.7-flash", "cloudflare/@cf/zai-org/glm-4.7-flash", "CLOUDFLARE_API_KEY"),

    # ── Google Gemma (open weights) ──
    ("gemma-3-4b", "google/gemma-3-4b-it", "GEMINI_API_KEY"),
    ("gemma-3-12b", "google/gemma-3-12b-it", "GEMINI_API_KEY"),
    ("gemma-3-27b", "google/gemma-3-27b-it", "GEMINI_API_KEY"),
    ("gemma-4-26b", "google/gemma-4-26b-a4b-it", "GEMINI_API_KEY"),
    ("gemma-4-31b", "google/gemma-4-31b-it", "GEMINI_API_KEY"),
]


def build_python_config():
    lines = []
    lines.append('"""Auto-generated model configuration for APEX — sourced from models.dev."""')
    lines.append('')
    lines.append('MODELS: dict[str, str] = {')

    provider_comments = {
        "anthropic": "Anthropic Claude (2024-2026)",
        "openai": "OpenAI GPT / o-series (2020-2025)",
        "google": "Google DeepMind Gemini / Gemma (2023-2025)",
        "xai": "xAI Grok (2023-2025)",
        "deepseek": "DeepSeek (2024-2025)",
        "mistral": "Mistral AI (2023-2025)",
        "alibaba": "Alibaba Qwen (2024-2025)",
        "llama": "Meta Llama (2023-2025) — Llama API",
        "bedrock": "Amazon Bedrock Nova (2024-2025)",
        "microsoft": "Microsoft Phi (2023-2025)",
        "cohere": "Cohere (2023-2025)",
        "groq": "Groq hosted models",
        "ollama": "Ollama local models (no API key needed)",
        "openrouter": "OpenRouter (use OPENROUTER_API_KEY)",
        "cerebras": "Cerebras (ultra-fast inference)",
        "fireworks": "Fireworks AI",
        "together": "Together AI",
        "huggingface": "Hugging Face",
        "perplexity": "Perplexity",
        "nvidia": "NVIDIA NIM",
        "cloudflare": "Cloudflare Workers AI",
    }

    provider_map = {
        "anthropic": "anthropic", "openai": "openai", "google": "google",
        "xai": "xai", "deepseek": "deepseek", "mistral": "mistral",
        "alibaba": "alibaba", "llama": "llama", "bedrock": "bedrock",
        "microsoft": "microsoft", "cohere": "cohere", "groq": "groq",
        "ollama": "ollama", "openrouter": "openrouter",
        "cerebras": "cerebras", "fireworks": "fireworks",
        "together_ai": "together", "huggingface": "huggingface",
        "perplexity": "perplexity", "nvidia": "nvidia",
        "cloudflare": "cloudflare",
    }

    current_provider = None
    for alias, model_str, env_key in MODELS_ENTRIES:
        provider_prefix = model_str.split("/")[0]
        provider = provider_map.get(provider_prefix, provider_prefix)

        if provider != current_provider:
            comment = provider_comments.get(provider, provider)
            lines.append(f'    # ── {comment} ──')
            current_provider = provider

        lines.append(f'    "{alias}": "{model_str}",')

    lines.append('}')
    lines.append('')

    # MODEL_PROVIDERS
    lines.append('MODEL_PROVIDERS: dict[str, str | None] = {')
    current_provider = None
    for alias, model_str, env_key in MODELS_ENTRIES:
        provider_prefix = model_str.split("/")[0]
        provider = provider_map.get(provider_prefix, provider_prefix)

        if provider != current_provider:
            comment = provider_comments.get(provider, provider)
            lines.append(f'    # ── {comment} ──')
            current_provider = provider

        val = f'"{env_key}"' if env_key else "None"
        lines.append(f'    "{alias}": {val},')

    lines.append('}')
    return "\n".join(lines)


def build_typescript_providers():
    providers_data = [
        {
            "name": "Anthropic", "iconKey": "anthropic", "color": "#d4a574",
            "models": [
                {"alias": "claude-sonnet-4.6", "model": "anthropic/claude-sonnet-4-6", "desc": "Claude Sonnet 4.6 — 1M context, extended thinking", "use": "General coding, debugging, refactoring"},
                {"alias": "claude-opus-4.7", "model": "anthropic/claude-opus-4-7", "desc": "Claude Opus 4.7 — 1M context, most capable", "use": "Complex architecture, multi-file refactoring"},
                {"alias": "claude-sonnet-4.5", "model": "anthropic/claude-sonnet-4-5", "desc": "Claude Sonnet 4.5 — latest reasoning", "use": "Advanced coding, complex reasoning"},
                {"alias": "claude-opus-4.5", "model": "anthropic/claude-opus-4-5", "desc": "Claude Opus 4.5 — premium reasoning", "use": "Complex tasks, deep analysis"},
                {"alias": "claude-haiku-4.5", "model": "anthropic/claude-haiku-4-5", "desc": "Claude Haiku 4.5 — fast & affordable", "use": "Quick edits, simple queries, chat"},
                {"alias": "claude-3.7-sonnet", "model": "anthropic/claude-3-7-sonnet-20250219", "desc": "Claude 3.7 Sonnet — enhanced coding", "use": "Advanced coding, complex reasoning"},
                {"alias": "claude-3.5-haiku", "model": "anthropic/claude-3-5-haiku-20241022", "desc": "Claude 3.5 Haiku — fastest Claude", "use": "Quick edits, simple queries, cost-effective"},
            ]
        },
        {
            "name": "OpenAI", "iconKey": "openai", "color": "#10a37f",
            "models": [
                {"alias": "gpt-5", "model": "openai/gpt-5", "desc": "GPT-5 — latest flagship model", "use": "General coding, analysis, complex tasks"},
                {"alias": "gpt-5-mini", "model": "openai/gpt-5-mini", "desc": "GPT-5 Mini — fast and affordable", "use": "Quick edits, simple queries, cost-effective"},
                {"alias": "gpt-5-nano", "model": "openai/gpt-5-nano", "desc": "GPT-5 Nano — ultra-affordable", "use": "Bulk processing, simple tasks"},
                {"alias": "gpt-5-pro", "model": "openai/gpt-5-pro", "desc": "GPT-5 Pro — premium reasoning", "use": "Complex reasoning, creative coding"},
                {"alias": "gpt-4o", "model": "openai/gpt-4o", "desc": "GPT-4o — multimodal flagship", "use": "General coding, analysis, complex tasks"},
                {"alias": "gpt-4o-mini", "model": "openai/gpt-4o-mini", "desc": "GPT-4o Mini — fast and affordable", "use": "Quick edits, simple queries, cost-effective"},
                {"alias": "gpt-4.1", "model": "openai/gpt-4.1", "desc": "GPT-4.1 — 1M context window", "use": "Long context coding, large codebases"},
                {"alias": "gpt-4.1-mini", "model": "openai/gpt-4.1-mini", "desc": "GPT-4.1 Mini — 1M context, affordable", "use": "Long context, budget coding"},
                {"alias": "o3", "model": "openai/o3", "desc": "o3 — advanced reasoning model", "use": "Complex reasoning, research tasks"},
                {"alias": "o3-mini", "model": "openai/o3-mini", "desc": "o3 Mini — cost-effective reasoning", "use": "Structured problem-solving on a budget"},
                {"alias": "o4-mini", "model": "openai/o4-mini", "desc": "o4 Mini — efficient reasoning", "use": "Fast reasoning tasks, code analysis"},
            ]
        },
        {
            "name": "Google", "iconKey": "google", "color": "#4285f4",
            "models": [
                {"alias": "gemini-3-pro", "model": "google/gemini-3-pro-preview", "desc": "Gemini 3 Pro — most capable Gemini", "use": "Complex coding, long context, analysis"},
                {"alias": "gemini-3-flash", "model": "google/gemini-3-flash-preview", "desc": "Gemini 3 Flash — fast & capable", "use": "Quick tasks, real-time coding, chat"},
                {"alias": "gemini-2.5-pro", "model": "google/gemini-2.5-pro", "desc": "Gemini 2.5 Pro — 1M context, reasoning", "use": "Complex coding, long context, analysis"},
                {"alias": "gemini-2.5-flash", "model": "google/gemini-2.5-flash", "desc": "Gemini 2.5 Flash — fast and efficient", "use": "Quick tasks, real-time coding, chat"},
                {"alias": "gemini-2.5-flash-lite", "model": "google/gemini-2.5-flash-lite", "desc": "Gemini 2.5 Flash Lite — ultra-affordable", "use": "Budget coding, bulk processing"},
                {"alias": "gemma-4-31b", "model": "google/gemma-4-31b-it", "desc": "Gemma 4 31B — open weights", "use": "Open-weight coding, research"},
            ]
        },
        {
            "name": "xAI", "iconKey": "xai", "color": "#ff6b35",
            "models": [
                {"alias": "grok-4", "model": "xai/grok-4", "desc": "Grok 4 — latest Grok model", "use": "General coding with real-time knowledge"},
                {"alias": "grok-4-fast", "model": "xai/grok-4-fast", "desc": "Grok 4 Fast — fast reasoning", "use": "Quick queries, fast coding tasks"},
                {"alias": "grok-3", "model": "xai/grok-3", "desc": "Grok 3 — capable Grok model", "use": "General coding, analysis"},
                {"alias": "grok-3-mini", "model": "xai/grok-3-mini", "desc": "Grok 3 Mini — cost-effective Grok", "use": "Quick queries, simple coding tasks"},
            ]
        },
        {
            "name": "DeepSeek", "iconKey": "deepseek", "color": "#4d6bfe",
            "models": [
                {"alias": "deepseek-v4-pro", "model": "deepseek/deepseek-v4-pro", "desc": "DeepSeek V4 Pro — most capable", "use": "Complex reasoning, code generation"},
                {"alias": "deepseek-v4-flash", "model": "deepseek/deepseek-v4-flash", "desc": "DeepSeek V4 Flash — fast & cheap", "use": "Cost-effective coding, fast responses"},
                {"alias": "deepseek-chat", "model": "deepseek/deepseek-chat", "desc": "DeepSeek V3 general chat", "use": "Cost-effective coding, Chinese + English"},
                {"alias": "deepseek-reasoner", "model": "deepseek/deepseek-reasoner", "desc": "DeepSeek R1 reasoning model", "use": "Complex reasoning, math, algorithm design"},
            ]
        },
        {
            "name": "Mistral", "iconKey": "mistral", "color": "#f70000",
            "models": [
                {"alias": "mistral-large", "model": "mistral/mistral-large-latest", "desc": "Mistral Large 3 — most capable", "use": "Complex coding, enterprise tasks"},
                {"alias": "mistral-medium", "model": "mistral/mistral-medium-latest", "desc": "Mistral Medium — balanced", "use": "Balanced coding and reasoning"},
                {"alias": "mistral-small", "model": "mistral/mistral-small-latest", "desc": "Mistral Small — fast & cheap", "use": "Quick edits, budget coding"},
                {"alias": "codestral", "model": "mistral/codestral-latest", "desc": "Codestral — specialized for code", "use": "Code completion, generation, review"},
                {"alias": "devstral", "model": "mistral/devstral-medium-latest", "desc": "Devstral 2 — developer-focused", "use": "Code generation, debugging, review"},
                {"alias": "magistral-medium", "model": "mistral/magistral-medium-latest", "desc": "Magistral Medium — reasoning", "use": "Complex reasoning, research"},
            ]
        },
        {
            "name": "Alibaba", "iconKey": "alibaba", "color": "#ff6a00",
            "models": [
                {"alias": "qwen3-max", "model": "alibaba/qwen3-max", "desc": "Qwen 3 Max — most capable Qwen", "use": "Complex reasoning, multilingual coding"},
                {"alias": "qwen3-coder-plus", "model": "alibaba/qwen3-coder-plus", "desc": "Qwen 3 Coder Plus — 1M context", "use": "Code generation, debugging, review"},
                {"alias": "qwen3.6-plus", "model": "alibaba/qwen3.6-plus", "desc": "Qwen 3.6 Plus — 1M context", "use": "Multilingual coding, long context"},
                {"alias": "qwen3-235b", "model": "alibaba/qwen3-235b-a22b", "desc": "Qwen 3 235B — large MoE model", "use": "Complex reasoning, multilingual coding"},
                {"alias": "qwq-plus", "model": "alibaba/qwq-plus", "desc": "QwQ Plus — reasoning specialist", "use": "Complex reasoning, math, algorithm design"},
                {"alias": "qwen-plus", "model": "alibaba/qwen-plus", "desc": "Qwen Plus — 1M context, balanced", "use": "General coding, balanced cost/perf"},
            ]
        },
        {
            "name": "Meta", "iconKey": "meta", "color": "#0668E1",
            "models": [
                {"alias": "llama-4-maverick", "model": "llama/llama-4-maverick-17b-128e-instruct-fp8", "desc": "Llama 4 Maverick — MoE 128 experts", "use": "Open-weight coding, research"},
                {"alias": "llama-4-scout", "model": "llama/llama-4-scout-17b-16e-instruct-fp8", "desc": "Llama 4 Scout — efficient MoE", "use": "Fast open-weight coding tasks"},
                {"alias": "llama-3.3-70b", "model": "llama/llama-3.3-70b-instruct", "desc": "Llama 3.3 70B Instruct", "use": "General coding with open weights"},
            ]
        },
        {
            "name": "Cohere", "iconKey": "cohere", "color": "#39594d",
            "models": [
                {"alias": "command-a", "model": "cohere/command-a-03-2025", "desc": "Command A — most capable Cohere", "use": "Complex reasoning, enterprise tasks"},
                {"alias": "command-a-reasoning", "model": "cohere/command-a-reasoning-08-2025", "desc": "Command A Reasoning — step-by-step", "use": "Complex reasoning, analysis"},
                {"alias": "command-r-plus", "model": "cohere/command-r-plus-08-2024", "desc": "Command R+ — RAG specialist", "use": "RAG, enterprise tasks"},
                {"alias": "command-r", "model": "cohere/command-r-08-2024", "desc": "Command R — balanced model", "use": "RAG, tool use, general coding"},
            ]
        },
        {
            "name": "Groq", "iconKey": "groq", "color": "#f55036",
            "models": [
                {"alias": "llama-groq-4-maverick", "model": "groq/meta-llama/llama-4-maverick-17b-128e-instruct", "desc": "Llama 4 Maverick on Groq — ultra-fast", "use": "Real-time coding, instant responses"},
                {"alias": "llama-groq-4-scout", "model": "groq/meta-llama/llama-4-scout-17b-16e-instruct", "desc": "Llama 4 Scout on Groq — fast + vision", "use": "Fast coding with vision support"},
                {"alias": "llama-groq-3.3-70b", "model": "groq/llama-3.3-70b-versatile", "desc": "Llama 3.3 70B on Groq", "use": "Fast general coding"},
                {"alias": "deepseek-r1-groq", "model": "groq/deepseek-r1-distill-llama-70b", "desc": "DeepSeek R1 distilled on Groq", "use": "Fast reasoning, budget coding"},
                {"alias": "qwq-groq-32b", "model": "groq/qwen-qwq-32b", "desc": "QwQ 32B on Groq — reasoning", "use": "Fast reasoning tasks"},
            ]
        },
        {
            "name": "Microsoft", "iconKey": "microsoft", "color": "#00a4ef",
            "models": [
                {"alias": "phi-4", "model": "microsoft/phi-4", "desc": "Phi-4 — small but powerful", "use": "Efficient coding, lightweight tasks"},
                {"alias": "phi-4-reasoning", "model": "microsoft/phi-4-reasoning", "desc": "Phi-4 Reasoning — step-by-step", "use": "Reasoning tasks, analysis"},
                {"alias": "phi-4-mini", "model": "microsoft/phi-4-mini-instruct", "desc": "Phi-4 Mini — ultra-lightweight", "use": "Budget coding, embedded scenarios"},
                {"alias": "phi-4-multimodal", "model": "microsoft/phi-4-multimodal-instruct", "desc": "Phi-4 Multimodal — vision + text", "use": "Vision coding, document analysis"},
            ]
        },
        {
            "name": "Cerebras", "iconKey": "cerebras", "color": "#7c3aed",
            "models": [
                {"alias": "cerebras-qwen3-235b", "model": "cerebras/qwen-3-235b-a22b-instruct-2507", "desc": "Qwen 3 235B on Cerebras — ultra-fast", "use": "Fastest inference for large models"},
                {"alias": "cerebras-gpt-oss-120b", "model": "cerebras/gpt-oss-120b", "desc": "GPT OSS 120B on Cerebras", "use": "Fast reasoning, large model tasks"},
                {"alias": "cerebras-llama3.1-8b", "model": "cerebras/llama3.1-8b", "desc": "Llama 3.1 8B on Cerebras — instant", "use": "Ultra-fast lightweight coding"},
            ]
        },
        {
            "name": "Fireworks AI", "iconKey": "fireworks", "color": "#ff6b6b",
            "models": [
                {"alias": "fireworks-deepseek-v4-pro", "model": "fireworks/accounts/fireworks/models/deepseek-v4-pro", "desc": "DeepSeek V4 Pro on Fireworks", "use": "Complex reasoning, 1M context"},
                {"alias": "fireworks-deepseek-v3.2", "model": "fireworks/accounts/fireworks/models/deepseek-v3p2", "desc": "DeepSeek V3.2 on Fireworks", "use": "Cost-effective coding on fast infra"},
                {"alias": "fireworks-qwen3.6-plus", "model": "fireworks/accounts/fireworks/models/qwen3p6-plus", "desc": "Qwen 3.6 Plus on Fireworks", "use": "Multilingual coding, vision"},
                {"alias": "fireworks-glm-5", "model": "fireworks/accounts/fireworks/models/glm-5", "desc": "GLM-5 on Fireworks", "use": "Bilingual coding, reasoning"},
            ]
        },
        {
            "name": "Together AI", "iconKey": "together", "color": "#4493f8",
            "models": [
                {"alias": "together-deepseek-v4-pro", "model": "together_ai/deepseek-ai/DeepSeek-V4-Pro", "desc": "DeepSeek V4 Pro on Together", "use": "Complex reasoning, 512K context"},
                {"alias": "together-qwen3-coder", "model": "together_ai/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8", "desc": "Qwen 3 Coder on Together", "use": "Code generation, large codebases"},
                {"alias": "together-qwen3.5-397b", "model": "together_ai/Qwen/Qwen3.5-397B-A17B", "desc": "Qwen 3.5 397B on Together", "use": "Complex reasoning, vision coding"},
                {"alias": "together-llama-3.3-70b", "model": "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo", "desc": "Llama 3.3 70B Turbo on Together", "use": "Fast open-weight coding"},
            ]
        },
        {
            "name": "Hugging Face", "iconKey": "huggingface", "color": "#ffd21e",
            "models": [
                {"alias": "hf-deepseek-r1", "model": "huggingface/deepseek-ai/DeepSeek-R1-0528", "desc": "DeepSeek R1 on HF Inference", "use": "Reasoning tasks, research"},
                {"alias": "hf-qwen3-coder", "model": "huggingface/Qwen/Qwen3-Coder-480B-A35B-Instruct", "desc": "Qwen 3 Coder on HF Inference", "use": "Code generation, large codebases"},
                {"alias": "hf-glm-5.1", "model": "huggingface/zai-org/GLM-5.1", "desc": "GLM-5.1 on HF Inference", "use": "Bilingual coding, reasoning"},
                {"alias": "hf-kimi-k2.6", "model": "huggingface/moonshotai/Kimi-K2.6", "desc": "Kimi K2.6 on HF Inference", "use": "Vision coding, reasoning"},
            ]
        },
        {
            "name": "Perplexity", "iconKey": "perplexity", "color": "#20b8cd",
            "models": [
                {"alias": "sonar-pro", "model": "perplexity/sonar-pro", "desc": "Sonar Pro — web-augmented, 200K context", "use": "Research, web-grounded coding"},
                {"alias": "sonar-reasoning-pro", "model": "perplexity/sonar-reasoning-pro", "desc": "Sonar Reasoning Pro — web + reasoning", "use": "Research with step-by-step reasoning"},
                {"alias": "sonar", "model": "perplexity/sonar", "desc": "Sonar — fast web search model", "use": "Quick web-grounded queries"},
                {"alias": "sonar-deep-research", "model": "perplexity/sonar-deep-research", "desc": "Sonar Deep Research — thorough search", "use": "Deep research, comprehensive analysis"},
            ]
        },
        {
            "name": "NVIDIA", "iconKey": "nvidia", "color": "#76b900",
            "models": [
                {"alias": "nvidia-deepseek-r1", "model": "nvidia/deepseek-ai/deepseek-r1", "desc": "DeepSeek R1 on NVIDIA NIM", "use": "Reasoning on GPU-optimized infra"},
                {"alias": "nvidia-llama-4-scout", "model": "nvidia/meta/llama-4-scout-17b-16e-instruct", "desc": "Llama 4 Scout on NVIDIA NIM", "use": "Fast open-weight with vision"},
                {"alias": "nvidia-nemotron-super", "model": "nvidia/nvidia/nemotron-3-super-120b-a12b", "desc": "Nemotron 3 Super 120B", "use": "NVIDIA's flagship model, reasoning"},
                {"alias": "nvidia-phi-4-mini", "model": "nvidia/microsoft/phi-4-mini-instruct", "desc": "Phi-4 Mini on NVIDIA NIM", "use": "Lightweight coding on fast infra"},
            ]
        },
        {
            "name": "Cloudflare Workers AI", "iconKey": "cloudflare", "color": "#f48120",
            "models": [
                {"alias": "cf-gpt-oss-120b", "model": "cloudflare/@cf/openai/gpt-oss-120b", "desc": "GPT OSS 120B on Cloudflare edge", "use": "Edge inference, serverless coding"},
                {"alias": "cf-llama-4-scout", "model": "cloudflare/@cf/meta/llama-4-scout-17b-16e-instruct", "desc": "Llama 4 Scout on Cloudflare", "use": "Edge coding with vision"},
                {"alias": "cf-gemma-4-26b", "model": "cloudflare/@cf/google/gemma-4-26b-a4b-it", "desc": "Gemma 4 26B on Cloudflare", "use": "Open-weight edge inference"},
                {"alias": "cf-glm-4.7-flash", "model": "cloudflare/@cf/zai-org/glm-4.7-flash", "desc": "GLM-4.7 Flash on Cloudflare", "use": "Fast edge reasoning"},
            ]
        },
        {
            "name": "Amazon Bedrock", "iconKey": "aws", "color": "#ff9900",
            "models": [
                {"alias": "nova-pro", "model": "bedrock/amazon.nova-pro-v1:0", "desc": "Amazon Nova Pro — capable multimodal", "use": "Enterprise coding, AWS integration"},
                {"alias": "nova-lite", "model": "bedrock/amazon.nova-lite-v1:0", "desc": "Amazon Nova Lite — cost-effective", "use": "Budget coding, AWS native"},
                {"alias": "nova-micro", "model": "bedrock/amazon.nova-micro-v1:0", "desc": "Amazon Nova Micro — ultra-cheap", "use": "Ultra-budget, simple tasks"},
            ]
        },
        {
            "name": "OpenRouter", "iconKey": "openrouter", "color": "#6366f1",
            "models": [
                {"alias": "or-gpt4o", "model": "openrouter/openai/gpt-4o", "desc": "GPT-4o via OpenRouter", "use": "Multi-model routing, cost optimization"},
                {"alias": "or-claude", "model": "openrouter/anthropic/claude-sonnet-4", "desc": "Claude via OpenRouter", "use": "Claude without direct API key"},
                {"alias": "or-deepseek", "model": "openrouter/deepseek/deepseek-chat", "desc": "DeepSeek via OpenRouter", "use": "Budget coding via router"},
                {"alias": "free-router", "model": "openrouter/openrouter/free", "desc": "Free model router — no credit card", "use": "Free tier, zero cost coding"},
            ]
        },
        {
            "name": "Local (Ollama / LM Studio)", "iconKey": "local", "color": "#00ff88",
            "models": [
                {"alias": "ollama-llama3.3", "model": "ollama/llama3.3", "desc": "Llama 3.3 via Ollama (local)", "use": "Free, offline, private coding"},
                {"alias": "ollama-deepseek-r1", "model": "ollama/deepseek-r1", "desc": "DeepSeek R1 via Ollama", "use": "Free, offline reasoning"},
                {"alias": "ollama-qwen2.5-coder", "model": "ollama/qwen2.5-coder", "desc": "Qwen 2.5 Coder via Ollama", "use": "Free, offline code specialist"},
                {"alias": "ollama-codellama", "model": "ollama/codellama", "desc": "Code Llama via Ollama", "use": "Free, offline code generation"},
                {"alias": "ollama-phi4", "model": "ollama/phi4", "desc": "Phi-4 via Ollama", "use": "Free, offline lightweight coding"},
                {"alias": "ollama-gemma2", "model": "ollama/gemma2", "desc": "Gemma 2 via Ollama", "use": "Free, offline, Google open weights"},
                {"alias": "lm-studio", "model": "lm_studio/your-model", "desc": "Any model via LM Studio", "use": "Free, offline, any GGUF model"},
            ]
        },
    ]

    cost_data = [
        {"model": "GPT-5", "provider": "openai", "input": "$1.25", "output": "$10.00", "speed": "Fast", "best": "General coding"},
        {"model": "GPT-5 Mini", "provider": "openai", "input": "$0.25", "output": "$2.00", "speed": "Very Fast", "best": "Budget coding"},
        {"model": "GPT-5 Nano", "provider": "openai", "input": "$0.05", "output": "$0.40", "speed": "Very Fast", "best": "Ultra-budget"},
        {"model": "GPT-4o", "provider": "openai", "input": "$2.50", "output": "$10.00", "speed": "Fast", "best": "General coding"},
        {"model": "GPT-4o Mini", "provider": "openai", "input": "$0.15", "output": "$0.60", "speed": "Very Fast", "best": "Budget coding"},
        {"model": "Claude Sonnet 4.6", "provider": "anthropic", "input": "$3.00", "output": "$15.00", "speed": "Fast", "best": "Code quality"},
        {"model": "Claude Opus 4.7", "provider": "anthropic", "input": "$5.00", "output": "$25.00", "speed": "Medium", "best": "Complex tasks"},
        {"model": "Claude Haiku 4.5", "provider": "anthropic", "input": "$1.00", "output": "$5.00", "speed": "Very Fast", "best": "Quick edits"},
        {"model": "Gemini 2.5 Pro", "provider": "google", "input": "$1.25", "output": "$10.00", "speed": "Fast", "best": "Long context"},
        {"model": "Gemini 2.5 Flash", "provider": "google", "input": "$0.30", "output": "$2.50", "speed": "Very Fast", "best": "Fast coding"},
        {"model": "DeepSeek V4 Flash", "provider": "deepseek", "input": "$0.14", "output": "$0.28", "speed": "Fast", "best": "Best value"},
        {"model": "DeepSeek V4 Pro", "provider": "deepseek", "input": "$1.74", "output": "$3.48", "speed": "Medium", "best": "Reasoning"},
        {"model": "Grok 4 Fast", "provider": "xai", "input": "$0.20", "output": "$0.50", "speed": "Very Fast", "best": "Fast reasoning"},
        {"model": "Mistral Large 3", "provider": "mistral", "input": "$0.50", "output": "$1.50", "speed": "Fast", "best": "Balanced coding"},
        {"model": "Qwen3 Coder Plus", "provider": "alibaba", "input": "$1.00", "output": "$5.00", "speed": "Fast", "best": "Code specialist"},
        {"model": "Command A", "provider": "cohere", "input": "$2.50", "output": "$10.00", "speed": "Fast", "best": "Enterprise RAG"},
        {"model": "Ollama (Local)", "provider": "local", "input": "Free", "output": "Free", "speed": "Varies", "best": "Privacy/offline"},
    ]

    lines = []
    lines.append("// Auto-generated PROVIDERS array and COST_COMPARISON for APEX models page")
    lines.append("// Sourced from models.dev data")
    lines.append("")
    lines.append("export const PROVIDERS = [")

    for p in providers_data:
        lines.append("  {")
        lines.append(f"    name: '{p['name']}', iconKey: '{p['iconKey']}', color: '{p['color']}',")
        lines.append("    models: [")
        for m in p["models"]:
            lines.append(f"      {{ alias: '{m['alias']}', model: '{m['model']}', desc: '{m['desc']}', use: '{m['use']}' }},")
        lines.append("    ]")
        lines.append("  },")

    lines.append("]")
    lines.append("")
    lines.append("export const COST_COMPARISON = [")

    for c in cost_data:
        lines.append(f"  {{ model: '{c['model']}', provider: '{c['provider']}', input: '{c['input']}', output: '{c['output']}', speed: '{c['speed']}', best: '{c['best']}' }},")

    lines.append("]")
    return "\n".join(lines)


def build_env_example():
    return """# APEX API Keys Configuration
# Copy this file to ~/.apex/.env or project root .env

# ── Anthropic (Claude) ──
ANTHROPIC_API_KEY=

# ── OpenAI (GPT-4, GPT-5, o1, o3, o4) ──
OPENAI_API_KEY=

# ── Google DeepMind (Gemini, Gemma) ──
GEMINI_API_KEY=
GOOGLE_GENERATIVE_AI_API_KEY=

# ── xAI (Grok) ──
XAI_API_KEY=

# ── DeepSeek ──
DEEPSEEK_API_KEY=

# ── Mistral AI ──
MISTRAL_API_KEY=

# ── Alibaba Cloud (Qwen) ──
DASHSCOPE_API_KEY=

# ── Meta Llama API ──
LLAMA_API_KEY=

# ── Amazon Bedrock (Nova) ──
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_BEARER_TOKEN_BEDROCK=

# ── Microsoft / GitHub Models (Phi) ──
GITHUB_TOKEN=

# ── Cohere ──
COHERE_API_KEY=

# ── Groq ──
GROQ_API_KEY=

# ── OpenRouter ──
OPENROUTER_API_KEY=

# ── Cerebras (ultra-fast inference) ──
CEREBRAS_API_KEY=

# ── Fireworks AI ──
FIREWORKS_API_KEY=

# ── Together AI ──
TOGETHER_API_KEY=

# ── Hugging Face ──
HF_TOKEN=

# ── Perplexity ──
PERPLEXITY_API_KEY=

# ── NVIDIA NIM ──
NVIDIA_API_KEY=

# ── Cloudflare Workers AI ──
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_KEY=

# ── Ollama (local, no key needed) ──
# Just ensure ollama is running on http://localhost:11434
"""


def build_docs_md():
    lines = []
    lines.append("# Models")
    lines.append("")
    lines.append("APEX supports 150+ models from 20+ providers via litellm. Switch anytime with `/model`.")
    lines.append("")

    provider_sections = {
        "Anthropic Claude": [],
        "OpenAI GPT / o-series": [],
        "Google Gemini / Gemma": [],
        "xAI Grok": [],
        "DeepSeek": [],
        "Mistral AI": [],
        "Alibaba Qwen": [],
        "Meta Llama": [],
        "Amazon Bedrock Nova": [],
        "Microsoft Phi": [],
        "Cohere": [],
        "Groq": [],
        "Cerebras": [],
        "Fireworks AI": [],
        "Together AI": [],
        "Hugging Face": [],
        "Perplexity": [],
        "NVIDIA NIM": [],
        "Cloudflare Workers AI": [],
        "OpenRouter": [],
        "Ollama (Local)": [],
    }

    provider_map = {
        "anthropic": "Anthropic Claude",
        "openai": "OpenAI GPT / o-series",
        "google": "Google Gemini / Gemma",
        "xai": "xAI Grok",
        "deepseek": "DeepSeek",
        "mistral": "Mistral AI",
        "alibaba": "Alibaba Qwen",
        "llama": "Meta Llama",
        "bedrock": "Amazon Bedrock Nova",
        "microsoft": "Microsoft Phi",
        "cohere": "Cohere",
        "groq": "Groq",
        "cerebras": "Cerebras",
        "fireworks": "Fireworks AI",
        "together_ai": "Together AI",
        "huggingface": "Hugging Face",
        "perplexity": "Perplexity",
        "nvidia": "NVIDIA NIM",
        "cloudflare": "Cloudflare Workers AI",
        "openrouter": "OpenRouter",
        "ollama": "Ollama (Local)",
    }

    for alias, model_str, env_key in MODELS_ENTRIES:
        prefix = model_str.split("/")[0]
        section = provider_map.get(prefix, prefix)
        if section in provider_sections:
            provider_sections[section].append((alias, model_str, env_key))

    for section_name, entries in provider_sections.items():
        if not entries:
            continue
        lines.append(f"## {section_name}")
        lines.append("")
        lines.append("| Alias | Model String | API Key |")
        lines.append("|-------|-------------|---------|")
        for alias, model_str, env_key in entries:
            key_display = f"`{env_key}`" if env_key else "None (local)"
            lines.append(f"| `{alias}` | `{model_str}` | {key_display} |")
        lines.append("")

    lines.append("## Switching Models")
    lines.append("")
    lines.append("```bash")
    lines.append("apex> /model gpt-4o")
    lines.append("apex> /models")
    lines.append("```")
    lines.append("")
    lines.append("Or use CLI: `apex --model gpt-4o \"your prompt\"`")
    return "\n".join(lines)


def build_icons_description():
    return """# New Provider Icon Components Needed for src/components/ProviderIcons.tsx

## New Icons Required

### 1. CerebrasIcon (iconKey: 'cerebras', color: #7c3aed)
- Description: Cerebras logo — stylized "C" with chip/wafer motif
- SVG: Waffle/chip grid pattern forming a "C" shape, purple (#7c3aed)

### 2. FireworksIcon (iconKey: 'fireworks', color: #ff6b6b)
- Description: Fireworks AI logo — burst/spark pattern
- SVG: Starburst/spark pattern with 5-6 radiating lines, coral red (#ff6b6b)

### 3. TogetherIcon (iconKey: 'together', color: #4493f8)
- Description: Together AI logo — interconnected circles
- SVG: Two overlapping circles representing collaboration, blue (#4493f8)

### 4. HuggingFaceIcon (iconKey: 'huggingface', color: #ffd21e)
- Description: Hugging Face logo — smiley face emoji
- SVG: Simple smiley face with open arms, yellow (#ffd21e) on dark background

### 5. PerplexityIcon (iconKey: 'perplexity', color: #20b8cd)
- Description: Perplexity logo — stylized "P" with search lines
- SVG: Letter "P" with horizontal scan lines, teal (#20b8cd)

### 6. NvidiaIcon (iconKey: 'nvidia', color: #76b900)
- Description: NVIDIA logo — eye/green rectangle
- SVG: Stylized green eye shape, NVIDIA green (#76b900)

### 7. CloudflareIcon (iconKey: 'cloudflare', color: #f48120)
- Description: Cloudflare logo — cloud with arrow
- SVG: Cloud shape with overlapping arcs, orange (#f48120)

### 8. MicrosoftIcon (iconKey: 'microsoft', color: #00a4ef)
- Description: Microsoft/GitHub Models logo — 4-square grid
- SVG: 2x2 grid of squares with rounded corners, Microsoft blue (#00a4ef)

### 9. AwsIcon (iconKey: 'aws', color: #ff9900)
- Description: AWS logo — simplified AWS arrow
- SVG: Orange arrow/chevron shape, AWS orange (#ff9900)

### 10. OpenRouterIcon (iconKey: 'openrouter', color: #6366f1)
- Description: OpenRouter logo — routing/network symbol
- SVG: Central node with branching connections, indigo (#6366f1)

## Updates to PROVIDER_ICONS map

Add these entries to the existing PROVIDER_ICONS record:
```typescript
cerebras: CerebrasIcon,
fireworks: FireworksIcon,
together: TogetherIcon,
huggingface: HuggingFaceIcon,
perplexity: PerplexityIcon,
nvidia: NvidiaIcon,
cloudflare: CloudflareIcon,
microsoft: MicrosoftIcon,
aws: AwsIcon,
openrouter: OpenRouterIcon,
```

## Updates to PROVIDER_LIST

Add these entries to the existing PROVIDER_LIST array:
```typescript
{ name: 'Cerebras', iconKey: 'cerebras', color: '#7c3aed' },
{ name: 'Fireworks AI', iconKey: 'fireworks', color: '#ff6b6b' },
{ name: 'Together AI', iconKey: 'together', color: '#4493f8' },
{ name: 'Hugging Face', iconKey: 'huggingface', color: '#ffd21e' },
{ name: 'Perplexity', iconKey: 'perplexity', color: '#20b8cd' },
{ name: 'NVIDIA', iconKey: 'nvidia', color: '#76b900' },
{ name: 'Cloudflare', iconKey: 'cloudflare', color: '#f48120' },
{ name: 'Microsoft', iconKey: 'microsoft', color: '#00a4ef' },
{ name: 'AWS', iconKey: 'aws', color: '#ff9900' },
{ name: 'OpenRouter', iconKey: 'openrouter', color: '#6366f1' },
```
"""


# ═══════════════════════════════════════════════════════════════════
# Generate all files
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. Python config
    py_content = build_python_config()
    out_path = OUT_DIR / "apex" / "config_models_new.py"
    out_path.write_text(py_content)
    print(f"Written {out_path} ({len(py_content)} bytes)")

    # 2. TypeScript providers
    ts_content = build_typescript_providers()
    out_path = OUT_DIR / "src" / "app" / "models" / "providers_new.ts"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ts_content)
    print(f"Written {out_path} ({len(ts_content)} bytes)")

    # 3. .env.example
    env_content = build_env_example()
    out_path = OUT_DIR / ".env.example"
    out_path.write_text(env_content)
    print(f"Written {out_path} ({len(env_content)} bytes)")

    # 4. docs/models_new.md
    docs_content = build_docs_md()
    out_path = OUT_DIR / "docs" / "models_new.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(docs_content)
    print(f"Written {out_path} ({len(docs_content)} bytes)")

    # 5. Provider icons description
    icons_content = build_icons_description()
    out_path = OUT_DIR / "docs" / "provider_icons_new.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(icons_content)
    print(f"Written {out_path} ({len(icons_content)} bytes)")

    # Summary
    total_models = len(MODELS_ENTRIES)
    providers = set()
    for _, model_str, _ in MODELS_ENTRIES:
        providers.add(model_str.split("/")[0])
    print(f"\nGenerated model data for {total_models} models across {len(providers)} providers")
