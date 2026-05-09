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

## Security Best Practices

When using APEX:

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` files (already in `.gitignore`)
3. **Sandbox**: Use the sandbox feature for untrusted code
4. **Permissions**: Review agent permissions before running

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | ✅ Current         |
| < 1.3   | ❌ Not supported   |

---

*Built with ❤️ in Gabon 🇬🇦*