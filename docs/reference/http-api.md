# HTTP API Reference

APEX provides a comprehensive HTTP API with **56 endpoints** for programmatic access.

## Base URL

```
http://127.0.0.1:8080
```

## Authentication

```http
Authorization: Bearer YOUR_API_KEY
# or
X-API-Key: YOUR_API_KEY
# or
?api_key=YOUR_API_KEY
```

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send message (non-streaming) |
| `POST` | `/chat/stream` | Send message (SSE streaming) |
| `GET` | `/stream` | SSE stream endpoint |

### Models

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/models` | List available models |
| `POST` | `/api/v1/models/refresh` | Refresh model cache |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session/save` | Save current session |
| `POST` | `/session/load` | Load a session |
| `GET` | `/api/v1/sessions` | List all sessions |
| `DELETE` | `/api/v1/sessions/{id}` | Delete a session |

### Config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/config` | Get current config (sanitized) |
| `POST` | `/api/v1/config` | Update config |

### Agents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/agents` | List all agents |
| `GET` | `/api/v1/agents/{name}` | Get agent details |

### Share

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/share` | Share current session |
| `POST` | `/api/v1/unshare/{share_id}` | Unshare a session |
| `GET` | `/api/v1/shares` | List shared sessions |

### Themes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/themes` | List available themes |
| `POST` | `/api/v1/themes` | Set active theme |

### Stats

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/stats` | Get usage statistics |
| `GET` | `/metrics` | Get session metrics |
| `GET` | `/rate-limit/status` | Rate limit status |

### Formatters

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/formatters` | List available formatters |
| `POST` | `/api/v1/format` | Format file or code snippet |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | Add/update provider API key |
| `POST` | `/api/v1/auth/logout` | Remove provider API key |
| `GET` | `/api/v1/auth/status` | Check provider configuration status |

### Commands

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/commands` | List custom commands |
| `POST` | `/api/v1/commands/execute` | Execute a custom command |

### Undo/Redo

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/undo` | Undo last action |
| `POST` | `/api/v1/redo` | Redo last undone action |

### Init

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/init` | Initialize project (AGENTS.md) |
| `POST` | `/api/v1/compact` | Compact session context |

### Export/Import

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/export/{session_id}` | Export session as JSON |
| `POST` | `/api/v1/import` | Import session from JSON |

### Providers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/providers` | List configured providers |

## Rate Limiting

All endpoints are rate-limited. Rate limit info returned in response:

```json
{
  "rate_limit": {
    "remaining_minute": 58,
    "remaining_hour": 950,
    "remaining_day": 4500
  }
}
```

## Error Responses

```json
{
  "error": "Authentication required",
  "code": "AUTH_REQUIRED"
}
```

```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMITED",
  "retry_after": 45
}
```
