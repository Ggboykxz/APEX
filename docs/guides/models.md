# Supported Models

APEX supports over 100 language models from every major provider, giving you the freedom to choose the best model for each task. Whether you need the reasoning power of frontier models, the cost-efficiency of smaller variants, or the privacy of fully local inference, APEX has you covered with seamless provider switching and unified tool access across all models.

## OpenAI

All GPT-4 and GPT-4o family models are supported, including `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, and `o1-preview`. APEX leverages structured outputs and function calling where available, and falls back to prompt-based tool use for older models. Streaming is supported across the entire OpenAI lineup.

## Anthropic

Claude models are first-class citizens in APEX. The `claude-sonnet-4-20250514`, `claude-3-5-sonnet`, and `claude-3-opus` families all support APEX's full tool suite via the Anthropic Messages API with tool use. APEX handles Claude-specific prompt formatting automatically, including the correct placement of system messages and tool results.

## Google

Google Gemini models — `gemini-2.5-pro`, `gemini-2.0-flash`, and `gemini-1.5-pro` — are available through the Generative AI API. APEX maps its tool schema to Google's function declaration format so that all 75+ tools work without manual adaptation.

## Ollama (Local Models)

For privacy-sensitive workflows or air-gapped environments, APEX integrates with Ollama to run models locally. Any Ollama-compatible model (Llama 3, Mistral, DeepSeek Coder, Qwen, etc.) can be selected with the `ollama/` prefix. APEX auto-discovers installed models and presents them alongside cloud models in the model selector (`Ctrl+K`). Ensure the Ollama daemon is running at `http://localhost:11434` or configure a custom host via the `OLLAMA_HOST` environment variable.

## Other Providers

APEX also supports models from Groq, Mistral AI, Together AI, Fireworks AI, and any OpenAI-compatible endpoint. Set the `base_url` in your provider config to point APEX at a custom API server, and it will treat it as a standard OpenAI-compatible backend. This makes it easy to integrate with self-hosted inference servers like vLLM or TGI.
