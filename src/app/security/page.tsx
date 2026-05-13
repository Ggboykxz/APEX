'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ArrowRight,
  Shield, Cpu, Bot, Wrench, BookOpen, Activity, GitBranch,
  Users, Lock, Eye, Key, DollarSign, AlertTriangle, CheckCircle2,
  FileWarning, Server, Gauge, GitCommit
} from 'lucide-react'

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg><span className="font-mono font-bold text-lg">APEX</span></a>
          <div className="hidden md:flex items-center gap-5"><a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() { return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">Proprietary License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>) }

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (<div className="relative group my-3 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden"><div className="flex items-center justify-between px-4 py-2 border-b border-border/30"><span className="text-xs text-muted-foreground font-mono">{language}</span><button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button></div><pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre></div>)
}

const SECURITY_FEATURES = [
  {
    title: 'Permission System', icon: Lock, color: '#00e5ff',
    desc: 'Ruleset-based permission system where each tool can be set to ALLOW, DENY, or ASK. Supports wildcards and per-agent configuration. Each agent has its own permission profile.',
    details: [
      'Per-tool permission controls (read, edit, bash, websearch, task)',
      'Per-agent permission profiles (Coder, Architect, Planner, Reviewer, Shell)',
      'Three permission levels: ALLOW (always permit), ASK (prompt user), DENY (block completely)',
      'Wildcard pattern support for flexible rule matching',
      'Configurable via .apex/config.yaml or CLI flags',
      'Permission checks happen before every tool execution',
    ],
    code: `# .apex/config.yaml\npermissions:\n  default: ask\n  rules:\n    - tool: read_file\n      action: allow\n    - tool: run_command\n      action: ask\n      patterns:\n        - "rm *"     # Always ask for rm\n        - "sudo *"   # Always ask for sudo\n    - tool: delete_file\n      action: deny  # Never allow file deletion`,
  },
  {
    title: 'Rate Limiting', icon: Gauge, color: '#00ff88',
    desc: 'Prevent excessive API usage and control costs with configurable rate limiting. Supports both Memory and SQLite backends for persistence.',
    details: [
      'Configurable rate limits per model and per session',
      'Memory backend for fast, in-process rate tracking',
      'SQLite backend for persistent rate limiting across sessions',
      'Token-based and request-based limiting',
      'Automatic backoff and retry logic',
      'Cost threshold alerts and budget limits',
    ],
    code: `# .apex/config.yaml\nrate_limiting:\n  enabled: true\n  backend: sqlite  # or "memory"\n  limits:\n    - model: "anthropic/*"\n      requests_per_minute: 60\n      tokens_per_minute: 100000\n    - model: "openai/*"\n      requests_per_minute: 100\n  budget:\n    daily_limit: 10.00    # $10/day\n    monthly_limit: 200.00 # $200/month`,
  },
  {
    title: 'Shell Security', icon: Terminal, color: '#ffaa00',
    desc: 'Every shell command is analyzed and classified before execution. Dangerous patterns are blocked or require explicit approval.',
    details: [
      'Command analysis and classification before execution',
      'Pattern-based dangerous command detection (rm -rf, sudo, chmod 777)',
      'Blocklist of known dangerous commands',
      'Allowlist for trusted command patterns',
      'Shell injection prevention',
      'Command audit logging for compliance',
    ],
    code: `# .apex/config.yaml\nshell_security:\n  enabled: true\n  block_patterns:\n    - "rm -rf /"\n    - "dd if=* of=/dev/*"\n    - ":(){ :|:& };:"\n    - "chmod 777"\n    - "> /dev/sda"\n  ask_patterns:\n    - "sudo *"\n    - "pip install *"\n    - "npm install -g *"\n  allow_patterns:\n    - "git *"\n    - "pytest *"\n    - "ls *"`,
  },
  {
    title: 'API Key Management', icon: Key, color: '#d946ef',
    desc: 'Workspace-based key storage with SHA-256 hashing. Keys are never logged, never included in prompts, and are encrypted at rest.',
    details: [
      'Workspace-based key storage with SHA-256 hashing',
      'Keys never appear in logs or conversation history',
      'Automatic key rotation support',
      'Key validation on startup',
      'Support for multiple keys per provider (load balancing)',
      'Key usage tracking and audit log',
    ],
    code: `# ~/.apex/.env (encrypted at rest)\nANTHROPIC_API_KEY=sk-ant-...\nOPENAI_API_KEY=sk-...\n\n# Key rotation\napex /key rotate anthropic\napex /key validate\napex /key status`,
  },
  {
    title: 'Path Traversal Protection', icon: FileWarning, color: '#ff4444',
    desc: 'Prevents directory traversal attacks. All file operations are restricted to the project workspace and configured safe paths.',
    details: [
      'All file paths resolved against the project root',
      'Symlink resolution and validation',
      'Blocking of ../ traversal patterns',
      'Configurable allowed and denied paths',
      'Protection against absolute path injection',
      'Workspace boundary enforcement',
    ],
    code: `# .apex/config.yaml\npath_security:\n  enabled: true\n  allowed_paths:\n    - "."           # Project root\n    - "/tmp/apex"   # Temp directory\n  denied_paths:\n    - "/etc"\n    - "/root"\n    - "~/.ssh"\n    - "~/.gnupg"\n  resolve_symlinks: true\n  max_path_length: 4096`,
  },
  {
    title: 'Billing & Cost Tracking', icon: DollarSign, color: '#ffaa00',
    desc: 'Real-time cost tracking with model-specific pricing and three plan tiers (Free/Pro/Enterprise). Monitor usage, set budgets, and get alerts when limits are approached.',
    details: [
      'Model-specific pricing with accurate per-token cost calculation',
      'Real-time cost display in TUI and CLI',
      'Session cost tracking with /cost command',
      'Three billing plans: Free, Pro ($200/mo), Enterprise (custom)',
      'Daily and monthly budget limits with alerts',
      'Cost breakdown by model and provider',
      'Export cost reports as CSV or JSON',
    ],
    code: `# Check costs\napex /cost\n\n# Cost output:\n# Session:  $0.42 (1,234 tokens)\n# Today:    $3.21\n# This month: $47.89 / $200.00 budget\n\n# Budget configuration\nbudget:\n  daily: 10.00\n  monthly: 200.00\n  alert_threshold: 0.8  # Alert at 80%`,
  },
  {
    title: 'Sandbox Execution', icon: Server, color: '#00e5ff',
    desc: 'Run code in isolated sandboxed environments. Untrusted code never touches your filesystem or network.',
    details: [
      'Isolated execution environments for untrusted code',
      'Support for Python, JavaScript, Bash, Ruby, Go, Rust',
      'Configurable timeout (default: 30 seconds)',
      'Memory and CPU limits',
      'Network isolation by default',
      'Output capture and return',
    ],
    code: `# Code runs in sandbox\napex "Run this Python code: print('hello')"\n\n# Sandbox config\nsandbox:\n  enabled: true\n  timeout: 30\n  max_memory_mb: 512\n  max_output_chars: 10000\n  network: disabled`,
  },
  {
    title: 'HTTP API Security', icon: Server, color: '#00ff88',
    desc: 'Secure headless agent access with Bearer token or X-API-Key authentication, per-endpoint rate limiting, and automatic cost tracking integrated with the billing system.',
    details: [
      'Bearer token or X-API-Key authentication',
      'Per-endpoint rate limiting',
      'Automatic cost tracking per request',
      'Shell security integration for API-initiated commands',
      'CORS and origin validation',
      'Request logging and audit trail',
    ],
    code: `# Start secure HTTP API server\nfrom apex.http_api import HTTPServer\n\nserver = HTTPServer(\n    host="127.0.0.1",\n    port=8080,\n    require_auth=True,\n)\n\n# API key required for all requests\n# Authorization: Bearer <api-key>\n# or X-API-Key: <api-key>`,
  },
]

const SUPPORTED_VERSIONS = [
  { version: 'v1.0.0', status: 'Active', support: 'Full support, security patches', color: '#00ff88' },
  { version: 'v1.0.0', status: 'Active', support: 'Current production release', color: '#00e5ff' },
]

export default function SecurityPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><Lock className="w-3.5 h-3.5" />Security First</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4"><span className="animated-gradient-text">Security</span> System</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">APEX is built with security at its core. From permission rulesets to sandboxed execution, every layer is designed to keep you safe.</p>
            </motion.div>
          </div>
        </section>

        {/* Security Features */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-8">
            {SECURITY_FEATURES.map((feature, i) => (
              <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}>
                <div className="p-6 md:p-8 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: feature.color, borderLeftWidth: 4 }}>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${feature.color}15`, border: `1px solid ${feature.color}30` }}>
                      <feature.icon className="w-5 h-5" style={{ color: feature.color }} />
                    </div>
                    <h3 className="text-2xl font-bold font-mono" style={{ color: feature.color }}>{feature.title}</h3>
                  </div>
                  <p className="text-muted-foreground leading-relaxed mb-4">{feature.desc}</p>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="font-bold font-mono text-sm mb-3" style={{ color: feature.color }}>Key Features</h4>
                      <ul className="space-y-2">
                        {feature.details.map(d => (
                          <li key={d} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" style={{ color: feature.color }} />
                            {d}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="font-bold font-mono text-sm mb-3" style={{ color: feature.color }}>Configuration</h4>
                      <CodeBlock language="yaml" code={feature.code} />
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Security Reporting */}
        <section className="py-12 bg-card/30">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><AlertTriangle className="w-6 h-6 text-apex-yellow" /> Security Reporting</h2>
            <div className="p-6 rounded-xl border border-apex-yellow/20 bg-apex-yellow/5">
              <h3 className="font-bold font-mono text-apex-yellow mb-3">Found a Security Vulnerability?</h3>
              <p className="text-muted-foreground mb-4 leading-relaxed">We take security seriously. If you discover a vulnerability, please report it responsibly.</p>
              <ol className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2"><span className="text-apex-yellow font-bold">1.</span> Do NOT publicly disclose the vulnerability.</li>
                <li className="flex items-start gap-2"><span className="text-apex-yellow font-bold">2.</span> Email <a href="mailto:security@apex-ai.dev" className="text-apex-cyan hover:underline">security@apex-ai.dev</a> with details.</li>
                <li className="flex items-start gap-2"><span className="text-apex-yellow font-bold">3.</span> Include: affected version, steps to reproduce, potential impact.</li>
                <li className="flex items-start gap-2"><span className="text-apex-yellow font-bold">4.</span> We will acknowledge within 48 hours and provide a fix timeline.</li>
                <li className="flex items-start gap-2"><span className="text-apex-yellow font-bold">5.</span> We will credit you in the security advisory (unless you prefer to remain anonymous).</li>
              </ol>
            </div>
          </div>
        </section>

        {/* Supported Versions */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><GitCommit className="w-6 h-6 text-apex-cyan" /> Supported Versions</h2>
            <div className="space-y-3">
              {SUPPORTED_VERSIONS.map(v => (
                <div key={v.version} className="flex items-center justify-between p-4 rounded-lg border border-border/50 bg-card/30">
                  <div className="flex items-center gap-3">
                    <code className="text-sm font-mono font-bold" style={{ color: v.color }}>{v.version}</code>
                    <span className="px-2 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: `${v.color}15`, color: v.color, border: `1px solid ${v.color}30` }}>{v.status}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">{v.support}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
