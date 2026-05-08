# Models

APEX supports 20+ models via litellm. Switch anytime with `/model`.

## Anthropic

| Alias | Model String |
|-------|---------------|
| `claude-sonnet` | anthropic/claude-sonnet-4-20250514 |
| `claude-opus` | anthropic/claude-opus-4-20250514 |
| `claude-flash` | anthropic/claude-3-5-haiku-20241022 |

## OpenAI

| Alias | Model String |
|-------|---------------|
| `gpt-4o` | openai/gpt-4o |
| `gpt-4o-mini` | openai/gpt-4o-mini |
| `o1` | openai/o1 |
| `o3-mini` | openai/o3-mini |

## Google

| Alias | Model String |
|-------|---------------|
| `gemini-2` | google/gemini-2.0-flash-exp |
| `gemini-flash` | google/gemini-1.5-flash |

## Groq

| Alias | Model String |
|-------|---------------|
| `llama-groq` | groq/llama-3.3-70b-versatile |
| `mixtral-groq` | groq/mixtral-8x7b-32768 |

## Mistral

| Alias | Model String |
|-------|---------------|
| `mistral-large` | mistral/mistral-large-latest |
| `codestral` | mistral/codestral-latest |

## DeepSeek

| Alias | Model String |
|-------|---------------|
| `deepseek` | deepseek/deepseek-chat |
| `deepseek-r1` | deepseek/deepseek-reasoner |

## Ollama (Local)

| Alias | Model String |
|-------|---------------|
| `ollama-llama3` | ollama/llama3 |
| `ollama-llama3.1` | ollama/llama3.1 |
| `ollama-codellama` | ollama/codellama |
| `ollama-deepseek` | ollama/deepseek-coder |

## Cohere

| Alias | Model String |
|-------|---------------|
| `command-r` | cohere/command-r |
| `command-r-plus` | cohere/command-r-plus |

## Switching Models

```bash
apex> /model gpt-4o
apex> /models
```

Or use CLI: `apex --model gpt-4o "your prompt"`