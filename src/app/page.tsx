'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, useInView, AnimatePresence } from 'framer-motion'
import {
  Terminal, Zap, Shield, Bot, ChevronDown, Copy, Check, ArrowRight,
  Github, ExternalLink, Code2, Wrench, Users, Star, GitBranch,
  Cpu, Globe, Lock, Eye, FileCode, Search, Play, Command,
  Layers, Sparkles, Box, Activity, Clock, Heart, BookOpen,
  Menu, X, ChevronRight, HomeIcon, Settings, Puzzle, AlertCircle,
  ArrowLeft, Hash
} from 'lucide-react'

/* ──────────── NAV STATE ──────────── */
type PageView = 'landing' | 'docs'
type DocSection = 'overview' | 'installation' | 'quickstart' | 'configuration' | 'agents' | 'models' | 'commands' | 'tools' | 'advanced' | 'plugins' | 'api' | 'troubleshooting'

const DOC_NAV: { id: DocSection; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: BookOpen },
  { id: 'installation', label: 'Installation', icon: Box },
  { id: 'quickstart', label: 'Quick Start', icon: Zap },
  { id: 'configuration', label: 'Configuration', icon: Settings },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'models', label: 'Models', icon: Cpu },
  { id: 'commands', label: 'Commands', icon: Terminal },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'advanced', label: 'Advanced', icon: Layers },
  { id: 'plugins', label: 'Plugins', icon: Puzzle },
  { id: 'api', label: 'API Reference', icon: Code2 },
  { id: 'troubleshooting', label: 'Troubleshooting', icon: AlertCircle },
]

/* ──────────── LANDING PAGE CONSTANTS ──────────── */

const INSTALL_COMMANDS: Record<string, { label: string; cmd: string }> = {
  curl: { label: 'curl', cmd: 'curl -fsSL https://apex-agent.dev/install.sh | bash' },
  pipx: { label: 'pipx', cmd: 'pipx install apex-agent' },
  pip: { label: 'pip', cmd: 'pip install apex-agent' },
  brew: { label: 'brew', cmd: 'brew install apex-agent' },
  docker: { label: 'docker', cmd: 'docker run -it ghcr.io/ggboykxz/apex' },
}

const FEATURES = [
  { icon: Cpu, title: '100+ Models', description: 'Use any LLM from any provider. Claude, GPT-4o, Gemini, Grok, Llama, DeepSeek, Qwen, and 95+ more models via litellm.', color: 'text-apex-cyan', glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]' },
  { icon: Bot, title: '5 Built-in Agents', description: 'Build, Plan, Explore, General, and YOLO agents with per-tool permission systems. Switch agents mid-session for different workflows.', color: 'text-apex-green', glow: 'group-hover:shadow-[0_0_30px_rgba(0,255,136,0.15)]' },
  { icon: Wrench, title: '75+ Tools', description: 'File ops, search, git, web, LSP, code generation, sandboxed execution, clipboard, skills, and more — all built in and ready.', color: 'text-apex-yellow', glow: 'group-hover:shadow-[0_0_30px_rgba(255,170,0,0.15)]' },
  { icon: Shield, title: 'Security System', description: 'Permission rulesets, rate limiting, shell security, API key management, path traversal protection, and billing built right in.', color: 'text-apex-red', glow: 'group-hover:shadow-[0_0_30px_rgba(255,68,68,0.15)]' },
  { icon: Zap, title: 'Switch Models Live', description: 'Switch between any model mid-session without restarting. Compare outputs, optimize costs, and never lose context.', color: 'text-apex-magenta', glow: 'group-hover:shadow-[0_0_30px_rgba(217,70,239,0.15)]' },
  { icon: Terminal, title: 'Beautiful TUI', description: 'Rich CLI mode with prompt_toolkit, full Textual TUI with sidebar and command palette, or experimental OpenTUI frontend.', color: 'text-apex-cyan', glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]' },
]

const AGENTS = [
  { name: 'build', mode: 'primary', access: 'Full (read/edit/bash/web)', color: '#00e5ff', icon: Code2, desc: 'Your primary coding agent. Reads, writes, executes, and browses — the full stack.' },
  { name: 'plan', mode: 'primary', access: 'Read-only (analysis & planning)', color: '#ffaa00', icon: Eye, desc: 'Analyzes your codebase and creates detailed plans before execution.' },
  { name: 'explore', mode: 'subagent', access: 'Read-only (fast exploration)', color: '#00ff88', icon: Search, desc: 'Quickly navigates and searches your codebase to find answers.' },
  { name: 'general', mode: 'subagent', access: 'Full (complex multi-step)', color: '#d946ef', icon: Layers, desc: 'Handles complex multi-step tasks that need careful orchestration.' },
  { name: 'yolo', mode: 'primary', access: 'Full + auto-approve', color: '#ff4444', icon: Zap, desc: 'Autonomous mode with auto-approve. Moves fast, asks no questions.' },
]

const MODELS = [
  { provider: 'Anthropic', models: ['Claude 4 Sonnet', 'Claude 3.5 Haiku', 'Claude Opus 4'], icon: '🧠' },
  { provider: 'OpenAI', models: ['GPT-4o', 'o1', 'o3', 'GPT-4.5'], icon: '🔮' },
  { provider: 'Google', models: ['Gemini 2.5 Pro', 'Gemini 2.0 Flash'], icon: '💎' },
  { provider: 'xAI', models: ['Grok 3', 'Grok 3 Mini'], icon: '⚡' },
  { provider: 'Meta', models: ['Llama 4 Maverick', 'Llama 3.3 70B'], icon: '🦙' },
  { provider: 'DeepSeek', models: ['DeepSeek V3', 'DeepSeek R1'], icon: '🔍' },
  { provider: 'Alibaba', models: ['Qwen 3 235B', 'Qwen 2.5 Coder'], icon: '🌐' },
  { provider: 'Mistral', models: ['Mistral Large', 'Codestral'], icon: '🌪️' },
  { provider: 'Local', models: ['Ollama', 'LM Studio', 'llama.cpp'], icon: '🏠' },
]

const TOOL_CATEGORIES = [
  { name: 'File Operations', count: 12, icon: FileCode, examples: ['read_file', 'write_file', 'edit_file', 'batch_read'] },
  { name: 'Search & Navigation', count: 8, icon: Search, examples: ['search_in_files', 'glob_search', 'get_file_tree', 'get_repo_map'] },
  { name: 'Git Integration', count: 11, icon: GitBranch, examples: ['git_status', 'git_commit', 'git_create_pr', 'git_diff'] },
  { name: 'Web & Network', count: 4, icon: Globe, examples: ['web_search', 'fetch_url'] },
  { name: 'Code Execution', count: 6, icon: Play, examples: ['run_command', 'run_test', 'run_code', 'format_file'] },
  { name: 'LSP Integration', count: 6, icon: Code2, examples: ['lsp_definition', 'lsp_references', 'lsp_diagnostics'] },
  { name: 'Session & History', count: 8, icon: Clock, examples: ['bookmark_session', 'search_history', 'share_session'] },
  { name: 'Edit & Review', count: 6, icon: Command, examples: ['preview_edit', 'apply_edit', 'apply_patch'] },
  { name: 'Analysis', count: 4, icon: Activity, examples: ['analyze_code', 'explain_code', 'generate_tests'] },
  { name: 'Undo & Redo', count: 4, icon: Layers, examples: ['undo', 'redo', 'undo_info'] },
  { name: 'Skills & Plugins', count: 3, icon: Sparkles, examples: ['list_skills', 'use_skill'] },
  { name: 'Clipboard', count: 2, icon: Copy, examples: ['clipboard_read', 'clipboard_write'] },
]

const FAQ = [
  { q: 'How is APEX different from Claude Code or OpenCode?', a: 'APEX supports 100+ models (not just one), lets you switch models mid-session, includes 5 specialized agents (not just one), has 75+ built-in tools, and offers a full security system with permissions and rate limiting. It\'s the most feature-rich terminal AI agent available.' },
  { q: 'Can I use local models with APEX?', a: 'Yes! APEX supports Ollama, LM Studio, llama.cpp, and any OpenAI-compatible local server. Run models completely offline with zero data leaving your machine.' },
  { q: 'What is the YOLO agent?', a: 'The YOLO agent is APEX\'s autonomous mode. It has full access (read, write, execute, browse) with auto-approve enabled. It moves fast and doesn\'t ask for confirmation — perfect for tasks you trust the AI to handle independently.' },
  { q: 'Is APEX free to use?', a: 'APEX itself is free and open source (MIT license). You\'ll need API keys for cloud models (Claude, GPT-4, etc.), but local models via Ollama are completely free. APEX also includes cost tracking so you always know your spend.' },
  { q: 'How does the permission system work?', a: 'APEX uses a ruleset-based permission system where each tool can be set to allow, deny, or ask. You can configure permissions per agent, per tool, or per session. Shell commands are analyzed and classified before execution, and path traversal protection is built in.' },
  { q: 'Can I use APEX in my CI/CD pipeline?', a: 'Yes! APEX has an HTTP API server, WebSocket support, and a task queue system. You can integrate it into your CI/CD pipeline for automated code review, testing, and even deployment tasks.' },
  { q: 'What terminals are supported?', a: 'APEX works in any modern terminal. The Rich CLI mode works everywhere. The Textual TUI requires a terminal with 256-color support. We also offer an experimental OpenTUI frontend for an even more premium experience.' },
  { q: 'How do I contribute to APEX?', a: 'Check out our CONTRIBUTING.md and AGENTS.md on GitHub. We welcome bug reports, feature requests, documentation improvements, and code contributions. All PRs are reviewed, and we have a code of conduct to ensure a welcoming community.' },
]

const STATS = [
  { value: '100+', label: 'Models Supported', icon: Cpu },
  { value: '75+', label: 'Built-in Tools', icon: Wrench },
  { value: '5', label: 'Specialized Agents', icon: Bot },
  { value: '1,148', label: 'Tests Passing', icon: Check },
  { value: '20+', label: 'Slash Commands', icon: Terminal },
  { value: '14', label: 'Install Methods', icon: Box },
]

const COMPARISON = [
  { feature: 'Models Supported', apex: '100+', opencode: '75+ providers', claudecode: 'Claude only', aider: '20+' },
  { feature: 'Switch Models Mid-Session', apex: true, opencode: true, claudecode: false, aider: false },
  { feature: 'Multi-Agent System', apex: '5 agents', opencode: false, claudecode: false, aider: false },
  { feature: 'Built-in Tools', apex: '75+', opencode: '~30', claudecode: '~20', aider: '~15' },
  { feature: 'Permission System', apex: true, opencode: false, claudecode: true, aider: false },
  { feature: 'Rate Limiting', apex: true, opencode: false, claudecode: false, aider: false },
  { feature: 'Full TUI', apex: true, opencode: true, claudecode: false, aider: false },
  { feature: 'Command Palette', apex: true, opencode: true, claudecode: false, aider: false },
  { feature: 'LSP Integration', apex: true, opencode: true, claudecode: false, aider: false },
  { feature: 'Git Undo/Redo', apex: true, opencode: false, claudecode: false, aider: false },
  { feature: 'Local Model Support', apex: true, opencode: true, claudecode: false, aider: true },
  { feature: 'Session Sharing', apex: true, opencode: true, claudecode: false, aider: false },
  { feature: 'Plugin System', apex: true, opencode: false, claudecode: false, aider: false },
  { feature: 'Open Source', apex: true, opencode: true, claudecode: false, aider: true },
]


/* ──────────── helper components ──────────── */

function SectionHeader({ badge, title, description }: { badge: string; title: string; description: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5 }}
      className="text-center mb-16"
    >
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6">
        <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />
        {badge}
      </div>
      <h2 className="text-3xl md:text-4xl font-bold mb-4 font-mono">{title}</h2>
      <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">{description}</p>
    </motion.div>
  )
}

function AnimatedCounter({ value, suffix = '' }: { value: string; suffix?: string }) {
  const numericPart = value.replace(/[^0-9]/g, '')
  const prefix = value.substring(0, value.indexOf(numericPart))
  const num = parseInt(numericPart)
  const [count, setCount] = useState(0)
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })

  useEffect(() => {
    if (!inView) return
    const duration = 2000
    const startTime = Date.now()
    const step = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.floor(eased * num))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [inView, num])

  return (
    <span ref={ref} className="animated-gradient-text font-bold">
      {prefix}{count}{suffix}
    </span>
  )
}

/* ─── Code block for docs ─── */
function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="relative group my-4 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30">
        <span className="text-xs text-muted-foreground font-mono">{language}</span>
        <button onClick={handleCopy} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
          {copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground">
        <code>{code}</code>
      </pre>
    </div>
  )
}

/* ─── Docs table ─── */
function DocsTable({ rows, headers }: { rows: string[][]; headers: string[] }) {
  return (
    <div className="my-4 overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border/50 bg-card/50">
            {headers.map((h, i) => (
              <th key={i} className="text-left p-3 font-mono text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={`border-b border-border/30 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
              {row.map((cell, j) => (
                <td key={j} className="p-3 font-mono text-muted-foreground">
                  {cell.startsWith('`') ? <code className="text-apex-cyan">{cell.replace(/`/g, '')}</code> : cell.startsWith('✅') ? <span className="text-apex-green">{cell}</span> : cell.startsWith('❌') ? <span className="text-apex-red">{cell}</span> : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DocsHeading({ children, id }: { children: React.ReactNode; id?: string }) {
  return (
    <h3 id={id} className="text-xl font-bold font-mono mt-10 mb-4 flex items-center gap-2 group scroll-mt-20">
      {children}
      {id && <Hash className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />}
    </h3>
  )
}


/* ──────────── DOCS PAGES ──────────── */

function DocOverview() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2 animated-gradient-text">APEX Documentation</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">
        Built in Gabon 🇬🇦 for the world. APEX is a production-grade, terminal-native AI coding agent that works with <strong className="text-foreground">any LLM</strong> via a unified interface powered by litellm.
      </p>

      <DocsHeading id="features">Features</DocsHeading>
      <div className="grid sm:grid-cols-2 gap-3">
        {[
          ['100+ Models', 'Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more'],
          ['Multi-Agent System', 'Build, Plan, Explore, General, YOLO with permission controls'],
          ['75+ Tools', 'File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB'],
          ['Rich Terminal UI', 'Syntax highlighting, markdown rendering, panels, command palette'],
          ['Session Persistence', 'Save and load conversations, bookmark positions, share links'],
          ['Token Cost Tracking', 'Monitor usage and estimated costs in real-time'],
          ['Plugin System', 'Extensible with custom tools and hooks'],
          ['Undo/Redo', 'Revert and reapply changes with full history'],
          ['LSP Integration', 'Go to definition, references, hover, diagnostics'],
          ['Security System', 'Permission rulesets, rate limiting, shell security, API key management'],
        ].map(([title, desc]) => (
          <div key={title} className="p-3 rounded-lg border border-border/50 bg-card/30">
            <span className="text-apex-cyan font-mono font-bold text-sm">{title}</span>
            <p className="text-muted-foreground text-xs mt-1">{desc}</p>
          </div>
        ))}
      </div>

      <DocsHeading id="comparison">Why APEX?</DocsHeading>
      <DocsTable
        headers={['Feature', 'APEX', 'OpenCode', 'Claude Code', 'Aider']}
        rows={[
          ['All models via one CLI', '✅', '⚠️', '❌', '⚠️'],
          ['No cloud lock-in', '✅', '❌', '❌', '✅'],
          ['Offline (Ollama)', '✅', '❌', '❌', '✅'],
          ['Rich syntax UI', '✅', '✅', '✅', '❌'],
          ['Session persistence', '✅', '❌', '✅', '❌'],
          ['Plugin system', '✅', '❌', '❌', '❌'],
          ['Model switch mid-session', '✅', '❌', '❌', '⚠️'],
          ['Token cost tracking', '✅', '❌', '❌', '✅'],
          ['French/multilingual UI', '✅', '❌', '❌', '❌'],
        ]}
      />

      <DocsHeading id="philosophy">Philosophy</DocsHeading>
      <p className="text-muted-foreground leading-relaxed">
        APEX is built by a Gabonese developer for the world. Every developer deserves a world-class coding agent — regardless of which model they can afford. The core principles are: <strong className="text-foreground">complete code, no truncation</strong> (never use <code className="text-apex-cyan">...rest of file...</code>), <strong className="text-foreground">production-ready</strong> with full error handling, tests, and type hints, <strong className="text-foreground">language-agnostic</strong> support for Python, JavaScript, Rust, Go, and more, and a <strong className="text-foreground">senior developer mindset</strong> that is opinionated but effective. With 1,148 tests passing and growing, APEX is built to be reliable and testable by default.
      </p>
    </div>
  )
}

function DocInstallation() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Installation</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Get APEX installed on your system in under a minute.</p>

      <DocsHeading id="requirements">Requirements</DocsHeading>
      <ul className="list-disc list-inside text-muted-foreground space-y-1 mb-6">
        <li>Python 3.11+</li>
        <li>API keys for your chosen model(s) — or use Ollama for free local models</li>
      </ul>

      <DocsHeading id="pip">Install via pip</DocsHeading>
      <CodeBlock code="pip install apex-agent" />

      <DocsHeading id="pipx">Install via pipx (recommended)</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">pipx provides an isolated environment, preventing dependency conflicts with other Python packages.</p>
      <CodeBlock code="pipx install apex-agent" />

      <DocsHeading id="source">Install from source</DocsHeading>
      <CodeBlock code={`git clone https://github.com/Ggboykxz/APEX.git\ncd APEX\npip install -e .\n# or with dev dependencies\npip install -e ".[dev]"`} />

      <DocsHeading id="verify">Verify installation</DocsHeading>
      <CodeBlock code={`apex --version\napex --list-models`} />

      <DocsHeading id="api-keys">API Keys</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">APEX requires API keys for the models you want to use. Set them in one of these locations:</p>
      <ol className="list-decimal list-inside text-muted-foreground text-sm space-y-1 mb-4">
        <li><code className="text-apex-cyan">~/.apex/.env</code> (recommended)</li>
        <li><code className="text-apex-cyan">./.env</code> (project root)</li>
        <li><code className="text-apex-cyan">~/.env</code></li>
      </ol>
      <CodeBlock code={`# ~/.apex/.env\nANTHROPIC_API_KEY=sk-ant-...\nOPENAI_API_KEY=sk-...\nGROQ_API_KEY=gsk_...\nMISTRAL_API_KEY=...\nDEEPSEEK_API_KEY=...\nGEMINI_API_KEY=...\nCOHERE_API_KEY=...`} />
      <p className="text-muted-foreground text-sm">For local models (Ollama), no API key needed.</p>

      <DocsHeading id="upgrade">Upgrade</DocsHeading>
      <CodeBlock code="pip install --upgrade apex-agent" />
    </div>
  )
}

function DocQuickstart() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Quick Start</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Get up and running with APEX in 5 minutes.</p>

      <DocsHeading id="step1">Step 1: Installation</DocsHeading>
      <CodeBlock code="pip install apex-agent" />
      <p className="text-muted-foreground text-sm">Or use pipx for isolated installation: <code className="text-apex-cyan">pipx install apex-agent</code></p>

      <DocsHeading id="step2">Step 2: Configure API Keys</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Create <code className="text-apex-cyan">~/.apex/.env</code> with your API keys:</p>
      <CodeBlock code={`# At least one of these:\nANTHROPIC_API_KEY=sk-ant-...    # For Claude models\nOPENAI_API_KEY=sk-...          # For GPT models\nDEEPSEEK_API_KEY=...           # For DeepSeek models\nGEMINI_API_KEY=...             # For Gemini models\nGROQ_API_KEY=gsk_...            # For Groq models`} />
      <div className="p-3 rounded-lg border border-apex-yellow/20 bg-apex-yellow/5 text-sm text-muted-foreground my-4">
        💡 <strong className="text-foreground">Tip:</strong> Start with a free model like <code className="text-apex-cyan">deepseek-chat</code> or <code className="text-apex-cyan">gpt-4o-mini</code>
      </div>

      <DocsHeading id="step3">Step 3: First Launch</DocsHeading>
      <CodeBlock code="apex" />
      <p className="text-muted-foreground text-sm mb-2">You should see the banner:</p>
      <CodeBlock language="text" code={`╔═══════════════════════════════════════════════════════╗\n║   APEX — Agent for Programming EXecution             ║\n║   The last coding agent you'll ever need             ║\n╚═══════════════════════════════════════════════════════╝\n\nAgent: build  Model: gpt-4o-mini  CWD: /home/user\n›`} />

      <DocsHeading id="step4">Step 4: Try Your First Command</DocsHeading>
      <CodeBlock language="text" code={`› What is the current directory?\n› Read the file main.py\n› Create a hello.py file that prints "Hello World"`} />

      <DocsHeading id="workflow">Basic Workflow</DocsHeading>
      <CodeBlock language="text" code={`# Switch models mid-session\n› /model gpt-4o\n\n# Check git status\n› /git\n\n# Analyze project\n› /map\n\n# Save your session\n› /save my-project\n\n# Load a previous session\n› /load my-project`} />

      <DocsHeading id="common-commands">Common Commands</DocsHeading>
      <DocsTable
        headers={['Command', 'What it does']}
        rows={[
          ['/help', 'Show all commands'],
          ['/models', 'List available models'],
          ['/agent build', 'Switch to build agent'],
          ['/agent plan', 'Switch to plan (read-only) agent'],
          ['@filename', 'Include file in context'],
          ['/clear', 'Clear conversation history'],
          ['/exit', 'Exit APEX'],
        ]}
      />

      <DocsHeading id="next-steps">Next Steps</DocsHeading>
      <ul className="space-y-2">
        {[
          ['Commands Guide', 'Learn all available commands', 'commands'],
          ['Configuration', 'Customize your setup', 'configuration'],
          ['Models', 'See all supported models', 'models'],
          ['Tools', 'Learn about built-in tools', 'tools'],
        ].map(([title, desc, id]) => (
          <li key={id} className="flex items-center gap-2 text-muted-foreground">
            <ChevronRight className="w-4 h-4 text-apex-cyan" />
            <strong className="text-foreground">{title}</strong> — {desc}
          </li>
        ))}
      </ul>
    </div>
  )
}

function DocConfiguration() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Configuration</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Customize APEX to fit your workflow.</p>

      <DocsHeading id="config-file">Config File</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">APEX stores configuration in <code className="text-apex-cyan">~/.apex/config.json</code>:</p>
      <CodeBlock language="json" code={`{\n  "model": "claude-sonnet",\n  "cwd": "/home/user/projects",\n  "theme": "monokai",\n  "max_tool_rounds": 20,\n  "auto_commit": false\n}`} />

      <DocsHeading id="settings">Settings</DocsHeading>
      <DocsTable
        headers={['Setting', 'Default', 'Description']}
        rows={[
          ['model', 'claude-sonnet', 'Default model alias'],
          ['cwd', 'current directory', 'Working directory'],
          ['theme', 'monokai', 'Syntax highlighting theme'],
          ['max_tool_rounds', '20', 'Max tool calls per message'],
          ['auto_commit', 'false', 'Auto git commit after changes'],
        ]}
      />

      <DocsHeading id="cli-options">CLI Options</DocsHeading>
      <CodeBlock code={`apex --model gpt-4o          # Use specific model\napex --cwd /path/to/project  # Set working directory\napex --stream                # Enable streaming\napex --auto-commit           # Auto commit changes\napex --list-models           # List available models`} />

      <DocsHeading id="env-vars">Environment Variables</DocsHeading>
      <DocsTable
        headers={['Variable', 'Description']}
        rows={[
          ['ANTHROPIC_API_KEY', 'Anthropic/Claude API key'],
          ['OPENAI_API_KEY', 'OpenAI API key'],
          ['GROQ_API_KEY', 'Groq API key'],
          ['MISTRAL_API_KEY', 'Mistral API key'],
          ['DEEPSEEK_API_KEY', 'DeepSeek API key'],
          ['GEMINI_API_KEY', 'Google Gemini API key'],
          ['COHERE_API_KEY', 'Cohere API key'],
        ]}
      />
      <p className="text-muted-foreground text-sm mt-4">No API key needed for Ollama (local models).</p>
    </div>
  )
}

function DocAgents() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Agents</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">APEX includes a powerful multi-agent system. Agents are specialized AI assistants configured for specific tasks.</p>

      <DocsHeading id="primary">Primary Agents</DocsHeading>
      <p className="text-muted-foreground text-sm mb-4">Primary agents handle your main conversation. Switch between them using <code className="text-apex-cyan">Tab</code> key or <code className="text-apex-cyan">/agent</code> command.</p>

      <div className="space-y-6 mb-8">
        <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#00e5ff', borderLeftWidth: 3 }}>
          <h4 className="font-bold font-mono text-lg text-[#00e5ff] mb-2">Build Agent (Default)</h4>
          <p className="text-muted-foreground text-sm mb-2">The default agent with full tool access for development work. It can write, edit, and delete files, run commands and tests, search and analyze code, install packages, and format code.</p>
          <CodeBlock code="apex /agent build\n# or press Tab" />
        </div>
        <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#ffaa00', borderLeftWidth: 3 }}>
          <h4 className="font-bold font-mono text-lg text-[#ffaa00] mb-2">Plan Agent</h4>
          <p className="text-muted-foreground text-sm mb-2">A restricted agent for planning and analysis. It can analyze code structure, suggest improvements, and create implementation plans, but cannot modify files or run commands.</p>
          <CodeBlock code="apex /agent plan" />
        </div>
      </div>

      <DocsHeading id="subagents">Subagents</DocsHeading>
      <p className="text-muted-foreground text-sm mb-4">Subagents are specialized assistants invoked with <code className="text-apex-cyan">@mention</code>:</p>

      <div className="space-y-4 mb-8">
        <div className="p-4 rounded-lg border border-border/50 bg-card/30" style={{ borderLeftColor: '#00ff88', borderLeftWidth: 3 }}>
          <h4 className="font-bold font-mono text-[#00ff88] mb-1">Explore Agent</h4>
          <p className="text-muted-foreground text-sm mb-2">Fast, read-only agent for exploring codebases. Find files by pattern, search code for keywords, show directory structure, analyze git history.</p>
          <CodeBlock code='apex @explore find all TODO comments' />
        </div>
        <div className="p-4 rounded-lg border border-border/50 bg-card/30" style={{ borderLeftColor: '#d946ef', borderLeftWidth: 3 }}>
          <h4 className="font-bold font-mono text-[#d946ef] mb-1">General Agent</h4>
          <p className="text-muted-foreground text-sm mb-2">General-purpose subagent for complex multi-step tasks. Research complex questions, execute multi-step workflows, coordinate file operations.</p>
          <CodeBlock code='apex @general research error handling patterns' />
        </div>
      </div>

      <DocsHeading id="permissions">Agent Permissions</DocsHeading>
      <DocsTable
        headers={['Permission', 'Tools Controlled']}
        rows={[
          ['read', 'read_file, list_files, search_in_files, glob_search'],
          ['edit', 'write_file, edit_file, delete_file'],
          ['bash', 'run_command'],
          ['websearch', 'web_search, fetch_url'],
          ['task', 'task (subagent invocation)'],
        ]}
      />
      <p className="text-muted-foreground text-sm mt-2">Permission values: <code className="text-apex-green">allow</code> (always permit), <code className="text-apex-yellow">ask</code> (prompt for confirmation), <code className="text-apex-red">deny</code> (block completely)</p>

      <DocsHeading id="custom-agents">Custom Agents</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Create custom agents in your config:</p>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nagents:\n  reviewer:\n    description: Code review agent\n    mode: subagent\n    permission:\n      edit: deny\n      bash: deny\n    prompt: "You are a code reviewer focused on security..."`} />
    </div>
  )
}

function DocModels() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Models</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">APEX supports 100+ models via litellm. Switch anytime with <code className="text-apex-cyan">/model</code>.</p>

      <DocsHeading id="anthropic">Anthropic</DocsHeading>
      <DocsTable headers={['Alias', 'Model String']} rows={[
        ['claude-sonnet', 'anthropic/claude-sonnet-4-20250514'],
        ['claude-opus', 'anthropic/claude-opus-4-20250514'],
        ['claude-flash', 'anthropic/claude-3-5-haiku-20241022'],
      ]} />

      <DocsHeading id="openai">OpenAI</DocsHeading>
      <DocsTable headers={['Alias', 'Model String']} rows={[
        ['gpt-4o', 'openai/gpt-4o'],
        ['gpt-4o-mini', 'openai/gpt-4o-mini'],
        ['o1', 'openai/o1'],
        ['o3-mini', 'openai/o3-mini'],
      ]} />

      <DocsHeading id="google">Google</DocsHeading>
      <DocsTable headers={['Alias', 'Model String']} rows={[
        ['gemini-2', 'google/gemini-2.0-flash-exp'],
        ['gemini-flash', 'google/gemini-1.5-flash'],
      ]} />

      <DocsHeading id="deepseek">DeepSeek</DocsHeading>
      <DocsTable headers={['Alias', 'Model String']} rows={[
        ['deepseek', 'deepseek/deepseek-chat'],
        ['deepseek-r1', 'deepseek/deepseek-reasoner'],
      ]} />

      <DocsHeading id="ollama">Ollama (Local)</DocsHeading>
      <DocsTable headers={['Alias', 'Model String']} rows={[
        ['ollama-llama3', 'ollama/llama3'],
        ['ollama-llama3.1', 'ollama/llama3.1'],
        ['ollama-codellama', 'ollama/codellama'],
        ['ollama-deepseek', 'ollama/deepseek-coder'],
      ]} />

      <DocsHeading id="switching">Switching Models</DocsHeading>
      <CodeBlock code={`apex> /model gpt-4o\napex> /models`} />
      <p className="text-muted-foreground text-sm mt-2">Or use CLI: <code className="text-apex-cyan">apex --model gpt-4o &quot;your prompt&quot;</code></p>
    </div>
  )
}

function DocCommands() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Commands</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">APEX provides slash commands, keyboard shortcuts, and @mentions for powerful interaction.</p>

      <DocsHeading id="agent-cmds">Agent Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[
        ['/agent [name]', 'Switch to a different agent (build/plan/explore/general)'],
        ['/agents', 'List all available agents'],
        ['/subagents', 'List all subagents'],
      ]} />

      <DocsHeading id="model-cmds">Model Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[
        ['/model &lt;alias&gt;', 'Switch to a different model'],
        ['/models', 'List all available models'],
      ]} />

      <DocsHeading id="session-cmds">Session Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[
        ['/save [name]', 'Save current session'],
        ['/load &lt;name&gt;', 'Load a previous session'],
        ['/sessions', 'List saved sessions'],
        ['/share', 'Generate share link for current session'],
        ['/clear', 'Clear conversation history'],
        ['/history', 'Show conversation history'],
        ['/cost', 'Show token usage and estimated cost'],
      ]} />

      <DocsHeading id="git-cmds">Git Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[
        ['/git', 'Show git status'],
        ['/branch', 'Show current branch'],
        ['/branches', 'List all branches'],
        ['/checkout &lt;branch&gt;', 'Switch to branch'],
        ['/commit &lt;message&gt;', 'Commit changes'],
      ]} />

      <DocsHeading id="analysis-cmds">Analysis Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[
        ['/map', 'Show repository map'],
        ['/stats', 'Show language statistics'],
        ['/analyze', 'Analyze project structure'],
      ]} />

      <DocsHeading id="memory-cmds">Memory Commands</DocsHeading>
      <CodeBlock code={`# Add a fact\n/memory add "Project uses FastAPI" python,fastapi\n/memory add "Database is PostgreSQL" database,postgres\n\n# Search memory\n/memory search python\n/memory search database\n\n# Clear memory\n/memory clear`} />

      <DocsHeading id="mentions">@Mentions</DocsHeading>
      <DocsTable headers={['Syntax', 'Description']} rows={[
        ['@README.md', 'Read and include file content'],
        ['@src/main.py', 'Include specific file'],
        ['@*.json', 'Include all JSON files'],
        ['@explore "Find all API endpoints"', 'Invoke explore subagent'],
        ['@general "Search for auth logic"', 'Invoke general subagent'],
      ]} />

      <DocsHeading id="shortcuts">Keyboard Shortcuts</DocsHeading>
      <DocsTable headers={['Shortcut', 'Action']} rows={[
        ['Tab', 'Cycle through agents'],
        ['Ctrl+C', 'Cancel current operation'],
        ['Ctrl+L', 'Clear screen'],
        ['Ctrl+D', 'Exit APEX'],
        ['Up/Down', 'Navigate command history'],
      ]} />
    </div>
  )
}

function DocTools() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Tools</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">APEX provides 75+ built-in tools for file operations, git, web, testing, LSP, and more. These tools are automatically selected by the AI based on your requests.</p>

      <DocsHeading id="file-ops">File Operations</DocsHeading>
      <DocsTable headers={['Tool', 'Description', 'Example']} rows={[
        ['read_file', 'Read file with line numbers', '"Read src/main.py"'],
        ['write_file', 'Create or overwrite file', '"Create config.json"'],
        ['edit_file', 'Replace unique string in file', '"Fix the bug on line 42"'],
        ['delete_file', 'Delete file or directory', '"Delete old_file.txt"'],
        ['create_directory', 'Create directory tree', '"Create src/utils/"'],
        ['search_in_files', 'Regex search', '"Find all TODO comments"'],
        ['glob_search', 'Find by pattern', '"Find all .py files"'],
      ]} />

      <DocsHeading id="git-tools">Git Tools</DocsHeading>
      <DocsTable headers={['Tool', 'Description', 'Example']} rows={[
        ['get_git_status', 'Git status output', '"Show git status"'],
        ['get_git_log', 'Recent commits', '"Show recent commits"'],
        ['git_diff', 'Working tree diff', '"Show changes"'],
        ['git_branch', 'Branch info', '"Current branch?"'],
      ]} />

      <DocsHeading id="web-tools">Web Tools</DocsHeading>
      <DocsTable headers={['Tool', 'Description', 'Example']} rows={[
        ['web_search', 'Search the web', '"Search for Python asyncio"'],
        ['fetch_url', 'Fetch webpage content', '"Read this documentation"'],
      ]} />

      <DocsHeading id="lsp-tools">LSP Tools</DocsHeading>
      <DocsTable headers={['Tool', 'Description', 'Example']} rows={[
        ['lsp_definition', 'Go to definition', '"Go to definition of function"'],
        ['lsp_references', 'Find references', '"Find all references"'],
        ['lsp_hover', 'Show hover info', '"What\'s this function?"'],
        ['lsp_diagnostics', 'Get errors/warnings', '"Show all errors"'],
      ]} />

      <DocsHeading id="dev-tools">Development Tools</DocsHeading>
      <DocsTable headers={['Tool', 'Description', 'Example']} rows={[
        ['run_command', 'Execute shell command', '"Run pytest"'],
        ['run_test', 'Run test suite', '"Run all tests"'],
        ['format_file', 'Format code', '"Format this file"'],
        ['install_package', 'Install dependency', '"Install requests"'],
        ['run_code', 'Run code in sandbox', '"Test this snippet"'],
      ]} />

      <DocsHeading id="undo-redo">Undo/Redo</DocsHeading>
      <DocsTable headers={['Tool', 'Description']} rows={[
        ['undo', 'Undo last file modification'],
        ['redo', 'Redo last undone action'],
        ['undo_info', 'Show what can be undone'],
        ['redo_info', 'Show what can be redone'],
      ]} />

      <DocsHeading id="how-tools-work">How Tools Work</DocsHeading>
      <p className="text-muted-foreground leading-relaxed">APEX automatically selects and uses tools based on your natural language requests. The agent analyzes your request and selects the appropriate tool: file operations for reading/writing/editing, git tools for version control, LSP tools for code navigation, web tools for online content, and development tools for running commands. If a tool fails, APEX will show the error, try an alternative approach, or ask for clarification.</p>
    </div>
  )
}

function DocAdvanced() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Advanced</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">MCP, custom tools, workspace awareness, context management, and more.</p>

      <DocsHeading id="mcp">MCP (Model Context Protocol)</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Connect to external tools and services via MCP:</p>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nmcp_servers:\n  filesystem:\n    command: npx\n    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]\n    enabled: true\n  github:\n    command: npx\n    args: ["-y", "@modelcontextprotocol/server-github"]\n    env:\n      GITHUB_TOKEN: your_token_here\n    enabled: true`} />

      <DocsHeading id="lsp">LSP Integration</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Connect to Language Server Protocol servers for code intelligence:</p>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nlsp_servers:\n  python:\n    command: ["pylsp"]\n    enabled: true\n  typescript:\n    command: ["typescript-language-server", "--stdio"]\n    enabled: true\n  go:\n    command: ["gopls"]\n    enabled: true\n  rust:\n    command: ["rust-analyzer"]\n    enabled: true`} />

      <DocsHeading id="custom-tools">Custom Tools</DocsHeading>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\ncustom_tools:\n  deploy:\n    description: Deploy application to production\n    enabled: true\n    command: "kubectl apply -f {manifest}"\n    cwd: /path/to/project\n  run_tests:\n    description: Run test suite\n    enabled: true\n    command: "npm test -- --reporter=json"`} />

      <DocsHeading id="sandbox">Sandbox Execution</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Run code safely in isolated environments. Supports Python, JavaScript, Bash, Ruby, Go, and Rust. Default timeout is 30 seconds, configurable up to any limit.</p>
      <CodeBlock language="python" code={`from apex.sandbox import sandbox\n\n# Python\nresult = sandbox.run_code("print('hello')", "python")\n\n# JavaScript\nresult = sandbox.run_code("console.log('hello')", "javascript")`} />

      <DocsHeading id="context-management">Context Management</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">APEX automatically compresses long conversations when approaching token limits. You can configure custom thresholds and use manual bookmarks for important conversation points.</p>
      <CodeBlock language="python" code={`from apex.context_manager import ContextWindow\n\ncw = ContextWindow(\n    max_tokens=100000,      # Max context size\n    compress_threshold=0.8,  # Compress at 80%\n    summary_messages=50     # Summarize every 50 messages\n)`} />

      <DocsHeading id="performance">Performance Optimization</DocsHeading>
      <DocsTable
        headers={['Use Case', 'Recommended Model']}
        rows={[
          ['Code generation', 'gpt-4o, claude-4-opus'],
          ['Fast editing', 'gpt-4o-mini, claude-3.5-haiku'],
          ['Complex reasoning', 'o3, deepseek-r1'],
          ['Cost-effective', 'gpt-4o-mini, qwen2.5'],
          ['Local/offline', 'ollama-llama3'],
        ]}
      />
    </div>
  )
}

function DocPlugins() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Plugins</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Extend APEX with custom plugins and hooks.</p>

      <DocsHeading id="built-in">Built-in Plugins</DocsHeading>
      <div className="space-y-4 mb-8">
        <div className="p-4 rounded-lg border border-border/50 bg-card/30">
          <h4 className="font-bold font-mono text-apex-cyan mb-2">Logger Plugin</h4>
          <p className="text-muted-foreground text-sm">Logs all tool calls and agent messages for debugging. Enables automatically when loaded via config.</p>
        </div>
        <div className="p-4 rounded-lg border border-border/50 bg-card/30">
          <h4 className="font-bold font-mono text-apex-green mb-2">Security Scanner Plugin</h4>
          <p className="text-muted-foreground text-sm">Scans code for security vulnerabilities before execution. Checks for: use of eval() or exec(), shell=True in subprocess calls, hardcoded passwords or API keys, use of os.system, and dangerous pickle operations.</p>
        </div>
      </div>

      <DocsHeading id="custom-plugins">Custom Plugins</DocsHeading>
      <CodeBlock language="python" code={`from apex.plugins import PluginBase, PluginInfo, PluginManager\n\nclass MyPlugin(PluginBase):\n    info = PluginInfo(\n        name="my-plugin",\n        version="0.1.0",\n        description="My custom plugin"\n    )\n\n    def initialize(self, app):\n        self.app = app\n        app.plugin_manager.register_hook("tool_call", self.on_tool_call)\n\n    def cleanup(self):\n        pass\n\n    def on_tool_call(self, tool_name, args):\n        print(f"Tool called: {tool_name}")`} />

      <DocsHeading id="hooks">Hooks</DocsHeading>
      <DocsTable headers={['Hook', 'Description', 'Parameters']} rows={[
        ['agent_start', 'Agent initialized', 'model, agent'],
        ['agent_message', 'New message', 'message'],
        ['tool_call', 'Tool about to run', 'tool_name, args'],
        ['tool_result', 'Tool completed', 'tool_name, result'],
        ['before_tool_call', 'Before tool execution', 'tool_name, args'],
        ['error', 'Error occurred', 'error_type, message'],
      ]} />

      <DocsHeading id="plugin-config">Plugin Configuration</DocsHeading>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nplugin_dirs:\n  - ~/.apex/plugins\n\nplugins:\n  logger:\n    enabled: true\n  security_scanner:\n    enabled: true`} />

      <DocsHeading id="example-linter">Example: Custom Linter Plugin</DocsHeading>
      <CodeBlock language="python" code={`import re\nfrom apex.plugins import PluginBase, PluginInfo\n\nclass LinterPlugin(PluginBase):\n    info = PluginInfo(\n        name="linter",\n        version="0.1.0",\n        description="Code linting plugin"\n    )\n\n    def initialize(self, app):\n        self.app = app\n        app.plugin_manager.register_hook("before_tool_call", self.lint_code)\n\n    def lint_code(self, tool_name, args):\n        if tool_name in ("write_file", "edit_file"):\n            code = args.get("content", "") or args.get("new_string", "")\n            issues = self._lint(code)\n            if issues:\n                print(f"[LINTER] Issues found: {issues}")\n\n    def _lint(self, code):\n        issues = []\n        if "TODO" in code:\n            issues.append("TODO comment found")\n        if len(code.splitlines()) > 500:\n            issues.append("File exceeds 500 lines")\n        return issues`} />
    </div>
  )
}

function DocAPI() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">API Reference</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Core modules and their public APIs.</p>

      <DocsHeading id="agent-api">apex.agent</DocsHeading>
      <CodeBlock language="python" code={`from apex.agent import Agent\n\nagent = Agent(\n    model="claude-4-sonnet",      # Model name\n    cwd="/path/to/project",       # Working directory\n    system_prompt=None,           # Custom system prompt\n    max_rounds=20,                # Max tool call rounds\n    temperature=0.3,             # Model temperature\n)`} />
      <DocsTable headers={['Method', 'Description']} rows={[
        ['run(message)', 'Run agent with user message'],
        ['run_stream(message)', 'Run with streaming response'],
        ['execute(tool, args)', 'Execute a specific tool'],
        ['add_tool(tool)', 'Add custom tool'],
        ['clear_history()', 'Clear conversation history'],
        ['save_session(name)', 'Save session to disk'],
        ['load_session(name)', 'Load session from disk'],
        ['set_agent(name)', 'Switch to different agent'],
      ]} />

      <DocsHeading id="config-api">apex.config</DocsHeading>
      <CodeBlock language="python" code={`from apex.config import Config\n\nconfig = Config.load()  # Load from ~/.apex/config.yaml\n\n# Access settings\nconfig.model           # Default model\nconfig.max_rounds      # Max tool rounds\nconfig.get_model_info("gpt-4o")`} />

      <DocsHeading id="tools-api">apex.tools</DocsHeading>
      <CodeBlock language="python" code={`from apex.tools import ToolExecutor\n\nexecutor = ToolExecutor(cwd="/project", max_output_chars=10000)\n\n# Execute tool\nresult = executor.execute("read_file", {"path": "main.py"})`} />

      <DocsHeading id="async-tools">AsyncToolExecutor</DocsHeading>
      <CodeBlock language="python" code={`from apex.tools import AsyncToolExecutor\n\nexecutor = AsyncToolExecutor(cwd="/project")\n\n# Async execution\nresult = await executor.execute("read_file", {"path": "main.py"})\n\n# Parallel execution\nresults = await executor.execute_all([\n    ("read_file", {"path": "a.py"}),\n    ("read_file", {"path": "b.py"}),\n])`} />

      <DocsHeading id="mcp-api">apex.mcp</DocsHeading>
      <CodeBlock language="python" code={`from apex.mcp import MCPClient\n\nclient = MCPClient(\n    name="myserver",\n    command="npx",\n    args=["-y", "server-package"],\n    env={"KEY": "value"},\n)\n\n# Connect and use tools\nawait client.connect()\ntools = await client.list_tools()\nresult = await client.call_tool("tool_name", args)\nawait client.close()`} />

      <DocsHeading id="workspace-api">apex.workspace</DocsHeading>
      <CodeBlock language="python" code={`from apex.workspace import Workspace\n\nws = Workspace(cwd="/project")\n\n# Git info\nws.is_git_repo          # bool\nws.current_branch       # str\nws.remote_url           # str | None\nws.is_dirty             # bool\n\n# Project detection\nws.language             # str | None\nws.package_manager      # str | None\nws.test_framework       # str | None`} />

      <DocsHeading id="telemetry-api">apex.telemetry</DocsHeading>
      <CodeBlock language="python" code={`from apex.telemetry import logger, perf_monitor\n\n# Automatically logs:\nlogger.log_agent_start(model, agent)\nlogger.log_tool_call(tool_name, args)\nlogger.log_tool_result(tool_name, result, duration_ms)\n\n# Get stats\nstats = logger.get_stats()\nlogger.print_summary()\n\n# Performance monitoring\nperf_monitor.record("tool_execution", duration_ms)\nstats = perf_monitor.get_all_stats()`} />
    </div>
  )
}

function DocTroubleshooting() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Troubleshooting</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Common issues and solutions for APEX.</p>

      <DocsHeading id="install-issues">Installation Issues</DocsHeading>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4">
        <h4 className="font-bold font-mono text-apex-red mb-2">&quot;command not found: apex&quot; after pip install</h4>
        <CodeBlock code={`# Check if installed\npip show apex-agent\n\n# Reinstall\npip uninstall apex-agent\npip install apex-agent\n\n# Or use python module\npython -m apex.main --version`} />
      </div>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4">
        <h4 className="font-bold font-mono text-apex-red mb-2">Import errors</h4>
        <CodeBlock code={`# Ensure Python 3.11+\npython --version\n\n# Upgrade pip\npip install --upgrade pip\n\n# Reinstall dependencies\npip install -r requirements.txt`} />
      </div>

      <DocsHeading id="api-issues">API Key Issues</DocsHeading>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4">
        <h4 className="font-bold font-mono text-apex-yellow mb-2">&quot;Authentication failed&quot;</h4>
        <CodeBlock code={`# Test with echo\necho $ANTHROPIC_API_KEY\n\n# Or set explicitly\nexport ANTHROPIC_API_KEY="sk-ant-..."`} />
      </div>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4">
        <h4 className="font-bold font-mono text-apex-yellow mb-2">&quot;Rate limit exceeded&quot;</h4>
        <CodeBlock code={`# Switch to a faster model\n/model gpt-4o-mini`} />
      </div>

      <DocsHeading id="model-issues">Model Issues</DocsHeading>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4">
        <h4 className="font-bold font-mono text-apex-cyan mb-2">Model not found</h4>
        <CodeBlock code={`# List available models\napex --list-models\n\n# Use exact model name\napex --model gpt-4o "hello"`} />
      </div>

      <DocsHeading id="perf-issues">Performance Issues</DocsHeading>
      <ul className="list-disc list-inside text-muted-foreground space-y-2 mb-6">
        <li>Use smaller models: <code className="text-apex-cyan">/model gpt-4o-mini</code></li>
        <li>Use streaming: <code className="text-apex-cyan">apex --stream &quot;prompt&quot;</code></li>
        <li>Reduce history: <code className="text-apex-cyan">/clear</code></li>
        <li>Clear conversation history periodically to free context window</li>
      </ul>

      <DocsHeading id="getting-help">Getting Help</DocsHeading>
      <CodeBlock code={`# Run with verbose output\napex --verbose "your prompt"\n\n# View session logs\nls ~/.apex/logs/\n\n# Session summary\napex /cost`} />
      <p className="text-muted-foreground text-sm mt-4">When reporting issues, include: APEX version (<code className="text-apex-cyan">apex --version</code>), Python version, error message, and steps to reproduce.</p>
    </div>
  )
}

const DOC_CONTENT: Record<DocSection, React.ReactNode> = {
  overview: <DocOverview />,
  installation: <DocInstallation />,
  quickstart: <DocQuickstart />,
  configuration: <DocConfiguration />,
  agents: <DocAgents />,
  models: <DocModels />,
  commands: <DocCommands />,
  tools: <DocTools />,
  advanced: <DocAdvanced />,
  plugins: <DocPlugins />,
  api: <DocAPI />,
  troubleshooting: <DocTroubleshooting />,
}


/* ──────────── SHARED NAV COMPONENT ──────────── */

function NavBar({ pageView, setPageView, scrolled, mobileMenuOpen, setMobileMenuOpen }: {
  pageView: PageView
  setPageView: (v: PageView) => void
  scrolled: boolean
  mobileMenuOpen: boolean
  setMobileMenuOpen: (v: boolean) => void
}) {
  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border' : 'bg-transparent'
    }`}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <button onClick={() => setPageView('landing')} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7">
              <defs>
                <linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#00e5ff"/>
                  <stop offset="100%" stopColor="#00ff88"/>
                </linearGradient>
              </defs>
              <polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/>
              <circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/>
            </svg>
            <span className="font-mono font-bold text-lg">APEX</span>
          </button>

          <div className="hidden md:flex items-center gap-6">
            {pageView === 'landing' ? (
              <>
                <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
                <a href="#agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a>
                <a href="#models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a>
                <a href="#tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Tools</a>
                <button onClick={() => setPageView('docs')} className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
                  <BookOpen className="w-4 h-4" /> Docs
                </button>
              </>
            ) : (
              <button onClick={() => setPageView('landing')} className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
                <HomeIcon className="w-4 h-4" /> Home
              </button>
            )}
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <Github className="w-4 h-4" /> GitHub
            </a>
            {pageView === 'landing' && (
              <a href="#install"
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-apex-cyan text-background text-sm font-medium hover:bg-apex-cyan/90 transition-colors">
                <ArrowRight className="w-3.5 h-3.5" /> Install
              </a>
            )}
          </div>

          <div className="flex items-center gap-2 md:hidden">
            {pageView === 'landing' && (
              <button onClick={() => setPageView('docs')} className="p-2 text-muted-foreground hover:text-foreground">
                <BookOpen className="w-5 h-5" />
              </button>
            )}
            {pageView === 'docs' && (
              <button onClick={() => setPageView('landing')} className="p-2 text-muted-foreground hover:text-foreground">
                <HomeIcon className="w-5 h-5" />
              </button>
            )}
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 text-muted-foreground hover:text-foreground">
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

/* ──────────── MAIN PAGE ──────────── */

export default function Home() {
  const [pageView, setPageView] = useState<PageView>('landing')
  const [activeDoc, setActiveDoc] = useState<DocSection>('overview')
  const [activeTab, setActiveTab] = useState<keyof typeof INSTALL_COMMANDS>('curl')
  const [copied, setCopied] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const [scrolled, setScrolled] = useState(false)
  const [docsSidebarOpen, setDocsSidebarOpen] = useState(false)
  const docContentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Scroll to top when switching docs
  useEffect(() => {
    if (pageView === 'docs' && docContentRef.current) {
      docContentRef.current.scrollTop = 0
    }
    window.scrollTo(0, 0)
  }, [activeDoc, pageView])

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  /* ─── DOCS VIEW ─── */
  if (pageView === 'docs') {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <NavBar pageView={pageView} setPageView={setPageView} scrolled={scrolled} mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} />
        <div className="flex flex-1 pt-16">
          {/* Sidebar */}
          <aside className={`fixed md:sticky top-16 left-0 bottom-0 z-40 w-64 shrink-0 border-r border-border bg-background overflow-y-auto transition-transform duration-200 ${
            docsSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}>
            <div className="p-4">
              <h3 className="text-xs font-mono font-bold text-muted-foreground uppercase tracking-wider mb-3">Documentation</h3>
              <nav className="space-y-1">
                {DOC_NAV.map(item => (
                  <button
                    key={item.id}
                    onClick={() => { setActiveDoc(item.id); setDocsSidebarOpen(false) }}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-mono transition-all ${
                      activeDoc === item.id
                        ? 'bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20'
                        : 'text-muted-foreground hover:text-foreground hover:bg-card'
                    }`}
                  >
                    <item.icon className="w-4 h-4 shrink-0" />
                    {item.label}
                  </button>
                ))}
              </nav>
            </div>
          </aside>

          {/* Overlay for mobile sidebar */}
          {docsSidebarOpen && (
            <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setDocsSidebarOpen(false)} />
          )}

          {/* Content */}
          <main ref={docContentRef} className="flex-1 min-w-0 px-4 sm:px-8 md:px-12 lg:px-16 py-8">
            {/* Mobile sidebar toggle */}
            <button
              onClick={() => setDocsSidebarOpen(!docsSidebarOpen)}
              className="md:hidden flex items-center gap-2 text-sm text-muted-foreground mb-6 hover:text-foreground"
            >
              <Menu className="w-4 h-4" />
              Navigation
            </button>

            <div className="max-w-3xl">
              {/* Breadcrumb */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-6">
                <button onClick={() => setPageView('landing')} className="hover:text-foreground transition-colors">APEX</button>
                <ChevronRight className="w-3 h-3" />
                <span>Docs</span>
                <ChevronRight className="w-3 h-3" />
                <span className="text-apex-cyan">{DOC_NAV.find(d => d.id === activeDoc)?.label}</span>
              </div>

              {DOC_CONTENT[activeDoc]}
            </div>
          </main>
        </div>

        {/* Footer */}
        <footer className="border-t border-border py-8 mt-auto">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between">
            <p className="text-xs text-muted-foreground">MIT License. Built by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a>
          </div>
        </footer>
      </div>
    )
  }


  /* ─── LANDING VIEW ─── */
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar pageView={pageView} setPageView={setPageView} scrolled={scrolled} mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} />

      {/* ─── HERO ─── */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 grid-pattern" />
        <div className="absolute inset-0 radial-gradient" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-apex-cyan/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-apex-green/5 rounded-full blur-3xl" />

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }} className="text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />
              v1.3.0 — Security System Released
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold font-mono leading-tight mb-6">
              The Universal{' '}<span className="animated-gradient-text">AI Coding</span><br />Agent
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Every model. One terminal. APEX runs in your terminal with 100+ models,
              75+ tools, and 5 built-in agents. Switch models mid-session. Never leave your terminal.
            </p>

            {/* Install Tabs */}
            <div id="install" className="max-w-2xl mx-auto">
              <div className="rounded-xl border border-border bg-card overflow-hidden">
                <div className="flex items-center border-b border-border overflow-x-auto">
                  {Object.entries(INSTALL_COMMANDS).map(([key, { label }]) => (
                    <button key={key} onClick={() => setActiveTab(key as keyof typeof INSTALL_COMMANDS)}
                      className={`relative px-4 py-3 text-sm font-mono whitespace-nowrap transition-colors ${activeTab === key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                      {label}
                      {activeTab === key && (
                        <motion.div layoutId="tab-indicator" className="absolute bottom-0 left-0 right-0 h-0.5 bg-apex-cyan" transition={{ type: 'spring', stiffness: 400, damping: 30 }} />
                      )}
                    </button>
                  ))}
                </div>
                <div className="flex items-center justify-between px-4 py-4 gap-4">
                  <code className="text-sm font-mono text-muted-foreground break-all">
                    <span className="text-apex-cyan/60">$</span>{' '}{INSTALL_COMMANDS[activeTab].cmd}
                  </code>
                  <button onClick={() => handleCopy(INSTALL_COMMANDS[activeTab].cmd)}
                    className="shrink-0 p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors" aria-label="Copy command">
                    {copied ? <Check className="w-4 h-4 text-apex-green" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5"><Star className="w-3.5 h-3.5 text-apex-yellow" /> MIT Licensed</span>
                <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5 text-apex-cyan" /> Built in Africa 🇬🇦</span>
                <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-apex-green" /> Security First</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── TERMINAL DEMO ─── */}
      <section className="relative py-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-50px' }} transition={{ duration: 0.7 }}
            className="rounded-xl border border-border overflow-hidden glow-cyan">
            <div className="flex items-center gap-2 px-4 py-3 bg-card border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-apex-red/80" />
                <div className="w-3 h-3 rounded-full bg-apex-yellow/80" />
                <div className="w-3 h-3 rounded-full bg-apex-green/80" />
              </div>
              <span className="text-xs text-muted-foreground font-mono ml-2">apex — ~/my-project</span>
              <div className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                <span className="text-apex-cyan">build</span><span className="text-muted-foreground">•</span><span>claude-4-sonnet</span>
              </div>
            </div>
            <div className="bg-[#0a0e14] p-6 font-mono text-sm leading-7 min-h-[320px]">
              <div className="text-muted-foreground"><span className="text-apex-cyan">◆</span> APEX v1.3.0 — Ready</div>
              <div className="mt-2"><span className="text-apex-green">user</span><span className="text-muted-foreground">@apex</span><span className="text-apex-cyan"> ~ </span><span className="text-foreground">Fix the authentication bug in auth.py</span></div>
              <div className="mt-3 text-muted-foreground"><span className="text-apex-cyan">◆</span> Using <span className="text-foreground">build</span> agent with <span className="text-apex-cyan">claude-4-sonnet</span></div>
              <div className="mt-2 space-y-1.5">
                <div className="flex items-center gap-2"><span className="text-apex-yellow">▸</span><span className="text-muted-foreground">read_file</span><span className="text-foreground">auth.py</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-yellow">▸</span><span className="text-muted-foreground">search_in_files</span><span className="text-foreground">"authenticate" in src/</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-green">✓</span><span className="text-muted-foreground">edit_file</span><span className="text-foreground">auth.py:42 — Fixed token validation</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-green">✓</span><span className="text-muted-foreground">run_test</span><span className="text-foreground">test_auth.py — 8/8 passed</span></div>
              </div>
              <div className="mt-3"><span className="text-apex-cyan">◆</span>{' '}<span className="text-foreground">Fixed the token validation bug. The issue was a missing expiration check on line 42. All tests pass.</span></div>
              <div className="mt-3"><span className="text-apex-green">user</span><span className="text-muted-foreground">@apex</span><span className="text-apex-cyan"> ~ </span><span className="text-foreground">/model gpt-4o<span className="cursor-blink text-foreground">█</span></span></div>
              <div className="text-muted-foreground text-xs mt-1">Switching to gpt-4o — context preserved</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── STATS ─── */}
      <section className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {STATS.map((stat, i) => (
              <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.1 }}
                className="text-center p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all">
                <stat.icon className="w-5 h-5 text-apex-cyan mx-auto mb-2" />
                <div className="text-2xl md:text-3xl font-bold font-mono mb-1"><AnimatedCounter value={stat.value} /></div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section id="features" className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="FEATURES" title="Everything you need to code with AI" description="APEX is the most feature-rich terminal AI coding agent. 100+ models, 75+ tools, 5 agents, and a comprehensive security system — all in your terminal." />
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`group p-6 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300 ${feature.glow}`}>
                <feature.icon className={`w-8 h-8 ${feature.color} mb-4`} />
                <h3 className="text-lg font-bold font-mono mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── AGENTS ─── */}
      <section id="agents" className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="MULTI-AGENT" title="5 Specialized Agents" description="Each agent has a unique role, access level, and personality. Switch between agents mid-session or let sub-agents handle specialized tasks automatically." />
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {AGENTS.map((agent, i) => (
              <motion.div key={agent.name} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}
                className="group relative p-5 rounded-xl border border-border/50 bg-card/50 hover:border-border transition-all duration-300" style={{ '--agent-color': agent.color } as React.CSSProperties}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: agent.color + '15' }}><agent.icon className="w-5 h-5" style={{ color: agent.color }} /></div>
                  <div>
                    <h3 className="font-bold font-mono text-lg" style={{ color: agent.color }}>/{agent.name}</h3>
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">{agent.mode}</span>
                  </div>
                </div>
                <p className="text-muted-foreground text-sm leading-relaxed mb-3">{agent.desc}</p>
                <div className="flex items-center gap-1.5 text-xs font-mono"><Lock className="w-3 h-3 text-muted-foreground" /><span className="text-muted-foreground">{agent.access}</span></div>
                <div className="absolute bottom-0 left-4 right-4 h-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" style={{ backgroundColor: agent.color }} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── MODELS ─── */}
      <section id="models" className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="MODELS" title="100+ Models. Any Provider." description="Connect any model from any provider. Cloud, local, or custom endpoints. Switch models mid-session without losing context." />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODELS.map((provider, i) => (
              <motion.div key={provider.provider} initial={{ opacity: 0, y: 15 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.05 }}
                className="p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300">
                <div className="flex items-center gap-2 mb-3"><span className="text-lg">{provider.icon}</span><span className="font-mono font-bold text-sm">{provider.provider}</span></div>
                <div className="flex flex-wrap gap-1.5">
                  {provider.models.map(model => (<span key={model} className="px-2 py-0.5 rounded-md bg-secondary text-xs text-muted-foreground font-mono">{model}</span>))}
                </div>
              </motion.div>
            ))}
          </div>
          <div className="mt-8 text-center"><p className="text-muted-foreground text-sm">...and 95+ more models via <span className="text-apex-cyan font-mono">litellm</span></p></div>
        </div>
      </section>

      {/* ─── TOOLS ─── */}
      <section id="tools" className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="TOOLS" title="75+ Built-in Tools" description="File operations, search, git, web, LSP, code execution, session management, and more — all built in." />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {TOOL_CATEGORIES.map((cat, i) => (
              <motion.div key={cat.name} initial={{ opacity: 0, y: 15 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.04 }}
                className="group p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><cat.icon className="w-4 h-4 text-apex-cyan" /><span className="font-mono font-bold text-sm">{cat.name}</span></div>
                  <span className="text-xs text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded">{cat.count}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {cat.examples.map(ex => (<span key={ex} className="text-xs text-muted-foreground font-mono hover:text-apex-cyan transition-colors cursor-default">{ex}</span>)).reduce<React.ReactNode[]>((acc, el, idx) => idx === 0 ? [el] : [...acc, <span key={`sep-${idx}`} className="text-border">·</span>, el], [])}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── COMPARISON ─── */}
      <section className="py-20 relative">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="COMPARISON" title="Why APEX?" description="See how APEX compares to other AI coding agents." />
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }} className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-card/50">
                  <th className="text-left p-4 font-mono text-muted-foreground">Feature</th>
                  <th className="p-4 font-mono text-center"><span className="animated-gradient-text font-bold">APEX</span></th>
                  <th className="p-4 font-mono text-muted-foreground text-center">OpenCode</th>
                  <th className="p-4 font-mono text-muted-foreground text-center">Claude Code</th>
                  <th className="p-4 font-mono text-muted-foreground text-center">Aider</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row, i) => (
                  <tr key={row.feature} className={`border-b border-border/50 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
                    <td className="p-4 font-mono text-muted-foreground">{row.feature}</td>
                    {(['apex', 'opencode', 'claudecode', 'aider'] as const).map(col => (
                      <td key={col} className="p-4 text-center">
                        {typeof row[col] === 'boolean' ? (row[col] ? <Check className="w-4 h-4 text-apex-green mx-auto" /> : <span className="text-muted-foreground">—</span>)
                          : col === 'apex' ? <span className="text-apex-cyan font-mono font-bold">{row[col] as string}</span>
                          : <span className="text-muted-foreground font-mono">{row[col] as string}</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        </div>
      </section>

      {/* ─── SECURITY ─── */}
      <section className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-30" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="SECURITY v1.3.0" title="Security-First Architecture" description="APEX v1.3.0 introduces a comprehensive security system with permissions, rate limiting, and shell security." />
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: Shield, title: 'Permission Rulesets', desc: 'Configure allow/deny/ask rules per tool, per agent, or per session.', color: '#00e5ff' },
              { icon: Activity, title: 'Rate Limiting', desc: 'Database-backed rate limiting with Memory and SQLite backends.', color: '#00ff88' },
              { icon: Terminal, title: 'Shell Security', desc: 'Shell commands analyzed and classified before execution.', color: '#ffaa00' },
              { icon: Lock, title: 'API Key Management', desc: 'Workspace-based API key management with secure storage.', color: '#d946ef' },
            ].map((item, i) => (
              <motion.div key={item.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.1 }}
                className="group p-5 rounded-xl border border-border/50 bg-card/50 hover:border-border transition-all duration-300">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style={{ backgroundColor: item.color + '15' }}><item.icon className="w-5 h-5" style={{ color: item.color }} /></div>
                <h3 className="font-bold font-mono mb-2" style={{ color: item.color }}>{item.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── SLASH COMMANDS ─── */}
      <section className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="COMMANDS" title="20+ Slash Commands" description="Powerful slash commands for every workflow." />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {['/model', '/models', '/agent', '/yolo', '/plan', '/build', '/cwd', '/clear', '/history', '/cost', '/save', '/load', '/memory', '/map', '/stats', '/git', '/undo', '/redo', '/restore', '/skills', '/help'].map((cmd, i) => (
              <motion.div key={cmd} initial={{ opacity: 0, scale: 0.95 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ duration: 0.2, delay: i * 0.02 }}
                className="px-3 py-2 rounded-lg border border-border/50 bg-card/50 font-mono text-sm text-apex-cyan hover:border-apex-cyan/30 hover:bg-apex-cyan/5 transition-all cursor-default text-center">{cmd}</motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="py-20 relative">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <SectionHeader badge="FAQ" title="Frequently Asked Questions" description="Got questions? We have answers." />
          <div className="space-y-3">
            {FAQ.map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.05 }}
                className="rounded-xl border border-border/50 bg-card/50 overflow-hidden">
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)} className="w-full flex items-center justify-between p-5 text-left hover:bg-card/80 transition-colors">
                  <span className="font-mono font-bold text-sm pr-4">{item.q}</span>
                  <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform duration-200 ${openFaq === i ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {openFaq === i && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                      <div className="px-5 pb-5 text-muted-foreground text-sm leading-relaxed">{item.a}</div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 radial-gradient" />
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <h2 className="text-3xl md:text-5xl font-bold font-mono mb-6">Ready to <span className="animated-gradient-text">code faster</span>?</h2>
            <p className="text-muted-foreground text-lg mb-10 leading-relaxed">Install APEX in seconds. Connect your API key. Start coding with the most powerful terminal AI agent.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href="#install" className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-apex-cyan text-background font-bold font-mono hover:bg-apex-cyan/90 transition-colors glow-cyan">
                <ArrowRight className="w-4 h-4" /> Install APEX
              </a>
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-border text-foreground font-bold font-mono hover:border-apex-cyan/30 hover:bg-card transition-colors">
                <Github className="w-4 h-4" /> View on GitHub
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="border-t border-border py-12 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-6 h-6">
                  <defs><linearGradient id="foot-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs>
                  <polygon points="32,4 60,56 4,56" stroke="url(#foot-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#foot-grad)"/>
                </svg>
                <span className="font-mono font-bold">APEX</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">The universal AI coding agent.<br />Every model. One terminal.</p>
              <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground"><span>Built in Africa</span><span>🇬🇦</span><span>with</span><Heart className="w-3 h-3 text-apex-red inline" /></div>
            </div>
            <div>
              <h4 className="font-mono font-bold text-sm mb-4">Product</h4>
              <ul className="space-y-2">
                <li><a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a></li>
                <li><a href="#agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a></li>
                <li><a href="#models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a></li>
                <li><button onClick={() => setPageView('docs')} className="text-sm text-muted-foreground hover:text-foreground transition-colors">Documentation</button></li>
              </ul>
            </div>
            <div>
              <h4 className="font-mono font-bold text-sm mb-4">Resources</h4>
              <ul className="space-y-2">
                <li><button onClick={() => setPageView('docs')} className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"><BookOpen className="w-3 h-3" /> Docs</button></li>
                <li><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">GitHub <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/CHANGELOG.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Changelog <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/ROADMAP.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Roadmap <ExternalLink className="w-3 h-3" /></a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-mono font-bold text-sm mb-4">Community</h4>
              <ul className="space-y-2">
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Contributing <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/CODE_OF_CONDUCT.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Code of Conduct <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/SECURITY.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Security <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/issues" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Issues <ExternalLink className="w-3 h-3" /></a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">MIT License. Built by <a href="https://github.com/Ggboykxz" target="_blank" rel="noopener noreferrer" className="text-apex-cyan hover:underline">Ggboykxz</a>.</p>
            <div className="flex items-center gap-4">
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground transition-colors"><Github className="w-4 h-4" /></a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
