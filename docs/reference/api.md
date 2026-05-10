# HTTP API Reference

APEX exposes an optional HTTP API that allows external applications, scripts, and integrations to interact with the AI agent programmatically. The API follows REST conventions and returns JSON responses. It is designed to be compatible with the OpenAI Chat Completions API format while adding APEX-specific extensions for tools, agents, and session management.

## Starting the API Server

Launch the API server with:

```bash
apex serve --port 8080
```

This starts a FastAPI-based HTTP server on the specified port. The API is also available when the TUI or web UI is running — APEX listens on the same port and routes requests accordingly.

## Authentication

All API endpoints require an API key passed via the `Authorization` header:

```
Authorization: Bearer apex-your-api-key-here
```

Generate an API key by running `apex config api-key generate`. Keys can be scoped to specific permissions (read-only, tool-execution, admin) for secure integration with third-party services.

## Endpoints

### `POST /v1/chat/completions`

Send a chat completion request. This endpoint mirrors the OpenAI API format with additional APEX extensions.

**Request body:**

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "Refactor the auth module to use JWT."}
  ],
  "stream": false,
  "tools": ["file_read", "file_write", "shell_exec"],
  "agent": "coder",
  "auto_approve": false
}
```

**Response:**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'll start by reading the current auth module...",
        "tool_calls": []
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 256,
    "completion_tokens": 128,
    "total_tokens": 384
  }
}
```

### `GET /v1/models`

List all available models. Returns model names, providers, and capability metadata.

### `GET /v1/tools`

List all available tools with their descriptions, parameter schemas, and current enabled status.

### `GET /v1/sessions`

List all active sessions with their IDs, creation timestamps, and message counts.

### `GET /v1/sessions/{session_id}`

Retrieve the full conversation history for a specific session.

### `POST /v1/sessions/{session_id}/cancel`

Cancel an in-progress agent execution within a session.

### `GET /v1/health`

Health check endpoint. Returns `{"status": "ok"}` with version information.

## Streaming

Set `"stream": true` in the request body to receive Server-Sent Events (SSE) instead of a single JSON response. Each event contains a delta chunk compatible with the OpenAI streaming format, plus optional APEX-specific fields for tool execution updates.

## Rate Limiting

The API enforces configurable rate limits per API key. Default limits are 60 requests per minute and 1,000,000 tokens per day. Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are included in every response.
