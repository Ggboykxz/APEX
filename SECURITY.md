# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in APEX, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email the details to: apex@example.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (critical = 24-72h)

## Security Features

APEX implements multiple layers of security to protect your system:

### Shell Command Analysis

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
print(analysis.safe)  # False for dangerous commands
print(analysis.category)  # CommandCategory.DANGEROUS
print(analysis.warnings)  # List of warnings
```

**Command Categories:**
- `WORKING_DIR` — Safe directory operations (cd, pwd)
- `FILE_READ` — Read-only file operations
- `FILE_WRITE` — File creation/modification
- `FILE_DELETE` — File deletion (requires confirmation)
- `SYSTEM` — System modifications (sudo, chmod)
- `NETWORK` — Network operations (curl, wget)
- `PROCESS` — Process management (kill, ps)
- `GIT` — Git operations
- `BUILD` — Build tools (npm, make)
- `CONTAINER` — Container operations (docker, kubectl)
- `DANGEROUS` — Blocked dangerous commands

**Blocked Patterns:**
- `rm -rf /` — System-wide deletion
- Fork bombs
- Direct disk writes
- Download and execute (`curl | sh`)
- Pipe to shell execution

### Permission System

```python
from apex.permission import permission_manager, PermissionAction

# Add custom rules
permission_manager.add_rule(
    pattern="read_file",
    action=PermissionAction.ALLOW,
    reason="Reading files is safe"
)

# Check tool permission
can_execute, reason = permission_manager.can_execute_tool("run_command")
```

**Actions:** `ALLOW`, `DENY`, `ASK`

### Rate Limiting

```python
from apex.rate_limiter import create_rate_limiter, RateLimitConfig

# Create rate limiter
limiter = create_rate_limiter(
    config=RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000
    ),
    use_sqlite=True  # Persistent storage
)

# Check rate limit
result = limiter.check_rate_limit("user_123")
print(result.allowed)  # True/False
print(result.retry_after)  # Seconds to wait
```

### API Key Management

```python
from apex.api_key import create_key_manager

manager = create_key_manager()

# Create workspace
workspace = manager.create_workspace(
    name="my-project",
    owner_id="user_123"
)

# Create API key
api_key, key_info = manager.create_key(
    workspace_id=workspace.workspace_id,
    name="production-key",
    expires_in=86400 * 30,  # 30 days
    rate_limit_per_minute=100
)

# Validate key
try:
    info = manager.validate_key(api_key)
    print(f"Valid key for workspace: {info.workspace_id}")
except InvalidKeyError:
    print("Invalid key")
```

### Billing & Cost Tracking

```python
from apex.billing import billing_manager, calculate_cost

# Calculate cost
cost = calculate_cost(
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)

# Check quota
can_proceed, msg = billing_manager.check_quota(
    user_id="user_123",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)

# Record usage
billing_manager.record_usage(
    user_id="user_123",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)
```

### HTTP API Security

```python
from apex.http_api import HTTPServer

server = HTTPServer(
    host="127.0.0.1",
    port=8080,
    require_auth=True,  # API key required
)
```

**Endpoints:**
- `POST /chat` — Chat (auth required)
- `GET /stream` — SSE streaming
- `GET /health` — Health check (no auth)
- `GET /metrics` — Usage metrics (auth required)
- `GET /rate-limit/status` — Rate limit status

**Headers:**
- `Authorization: Bearer YOUR_API_KEY`
- `X-API-Key: YOUR_API_KEY`
- `?api_key=YOUR_API_KEY` (query param)

## Best Practices

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` files (already in `.gitignore`)
3. **Sandbox**: Use the sandbox feature for untrusted code
4. **Permissions**: Review agent permissions before running
5. **Rate Limits**: Set appropriate limits per API key
6. **Shell Security**: Dangerous commands are blocked by default

## HTTP API Security

The HTTP API server (`apex.http_api`) includes:

- **Authentication**: Bearer token or API key header
- **Rate Limiting**: Per-key limits (60/min, 1000/hr, 10000/day default)
- **Billing**: Automatic cost tracking per request
- **Shell Security**: Command analysis before execution
- **Permission Checks**: Tool-level access control

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.4.x   | ✅ Current         |
| 1.3.x   | ⚠️ Security only  |
| < 1.3   | ❌ Not supported   |

---

*Built with ❤️ in Gabon 🇬🇦*