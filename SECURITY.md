# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.3.x | ✅ |
| 1.2.x | ✅ |
| < 1.2 | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** create a public GitHub issue
2. **DO** email the maintainer directly (if available)
3. **OR** use GitHub's private vulnerability reporting

## Security Best Practices

### API Keys

- Never commit API keys to version control
- Use `~/.apex/.env` for local development
- Rotate keys regularly

### File Operations

- APEX has full file system access — be careful with destructive commands
- Always verify before running `/delete` or `/rm` commands

### Code Execution

- The sandbox feature executes code — always review before running
- Use `/approve` and `/reject` for plan-based execution

### Network Operations

- APEX can make HTTP requests — be cautious with sensitive data
- Review web requests in tool calls

## Known Limitations

- No sandboxed file system isolation by default
- No built-in firewall for API calls
- Session files may contain sensitive data — secure `~/.apex/sessions/`

## Best Practices for Teams

1. Use environment variables for API keys, not hardcoded values
2. Review `/save` output for sensitive data before sharing
3. Use `/model` to switch to cheaper models for simple tasks
4. Enable audit logging in production deployments

---

*Security is everyone's responsibility. Thank you for helping keep APEX safe!*