'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, useInView, AnimatePresence } from 'framer-motion'
import {
  Terminal, Zap, Shield, Bot, ChevronDown, Copy, Check, ArrowRight,
  Github, ExternalLink, Code2, Wrench, Users, Star, GitBranch,
  Cpu, Globe, Lock, Eye, FileCode, Search, Play, Command,
  Layers, Sparkles, Box, Activity, Clock, Heart
} from 'lucide-react'

/* ──────────── constants ──────────── */

const INSTALL_COMMANDS: Record<string, { label: string; cmd: string }> = {
  curl: { label: 'curl', cmd: 'curl -fsSL https://apex-agent.dev/install.sh | bash' },
  pipx: { label: 'pipx', cmd: 'pipx install apex-agent' },
  pip: { label: 'pip', cmd: 'pip install apex-agent' },
  brew: { label: 'brew', cmd: 'brew install apex-agent' },
  docker: { label: 'docker', cmd: 'docker run -it ghcr.io/ggboykxz/apex' },
}

const FEATURES = [
  {
    icon: Cpu,
    title: '100+ Models',
    description: 'Use any LLM from any provider. Claude, GPT-4o, Gemini, Grok, Llama, DeepSeek, Qwen, and 95+ more models via litellm.',
    color: 'text-apex-cyan',
    glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]',
  },
  {
    icon: Bot,
    title: '5 Built-in Agents',
    description: 'Build, Plan, Explore, General, and YOLO agents with per-tool permission systems. Switch agents mid-session for different workflows.',
    color: 'text-apex-green',
    glow: 'group-hover:shadow-[0_0_30px_rgba(0,255,136,0.15)]',
  },
  {
    icon: Wrench,
    title: '75+ Tools',
    description: 'File ops, search, git, web, LSP, code generation, sandboxed execution, clipboard, skills, and more — all built in and ready.',
    color: 'text-apex-yellow',
    glow: 'group-hover:shadow-[0_0_30px_rgba(255,170,0,0.15)]',
  },
  {
    icon: Shield,
    title: 'Security System',
    description: 'Permission rulesets, rate limiting, shell security, API key management, path traversal protection, and billing built right in.',
    color: 'text-apex-red',
    glow: 'group-hover:shadow-[0_0_30px_rgba(255,68,68,0.15)]',
  },
  {
    icon: Zap,
    title: 'Switch Models Live',
    description: 'Switch between any model mid-session without restarting. Compare outputs, optimize costs, and never lose context.',
    color: 'text-apex-magenta',
    glow: 'group-hover:shadow-[0_0_30px_rgba(217,70,239,0.15)]',
  },
  {
    icon: Terminal,
    title: 'Beautiful TUI',
    description: 'Rich CLI mode with prompt_toolkit, full Textual TUI with sidebar and command palette, or experimental OpenTUI frontend.',
    color: 'text-apex-cyan',
    glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]',
  },
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
  {
    q: 'How is APEX different from Claude Code or OpenCode?',
    a: 'APEX supports 100+ models (not just one), lets you switch models mid-session, includes 5 specialized agents (not just one), has 75+ built-in tools, and offers a full security system with permissions and rate limiting. It\'s the most feature-rich terminal AI agent available.',
  },
  {
    q: 'Can I use local models with APEX?',
    a: 'Yes! APEX supports Ollama, LM Studio, llama.cpp, and any OpenAI-compatible local server. Run models completely offline with zero data leaving your machine.',
  },
  {
    q: 'What is the YOLO agent?',
    a: 'The YOLO agent is APEX\'s autonomous mode. It has full access (read, write, execute, browse) with auto-approve enabled. It moves fast and doesn\'t ask for confirmation — perfect for tasks you trust the AI to handle independently.',
  },
  {
    q: 'Is APEX free to use?',
    a: 'APEX itself is free and open source (MIT license). You\'ll need API keys for cloud models (Claude, GPT-4, etc.), but local models via Ollama are completely free. APEX also includes cost tracking so you always know your spend.',
  },
  {
    q: 'How does the permission system work?',
    a: 'APEX uses a ruleset-based permission system where each tool can be set to allow, deny, or ask. You can configure permissions per agent, per tool, or per session. Shell commands are analyzed and classified before execution, and path traversal protection is built in.',
  },
  {
    q: 'Can I use APEX in my CI/CD pipeline?',
    a: 'Yes! APEX has an HTTP API server, WebSocket support, and a task queue system. You can integrate it into your CI/CD pipeline for automated code review, testing, and even deployment tasks.',
  },
  {
    q: 'What terminals are supported?',
    a: 'APEX works in any modern terminal. The Rich CLI mode works everywhere. The Textual TUI requires a terminal with 256-color support. We also offer an experimental OpenTUI frontend for an even more premium experience.',
  },
  {
    q: 'How do I contribute to APEX?',
    a: 'Check out our CONTRIBUTING.md and AGENTS.md on GitHub. We welcome bug reports, feature requests, documentation improvements, and code contributions. All PRs are reviewed, and we have a code of conduct to ensure a welcoming community.',
  },
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
    let start = 0
    const duration = 2000
    const startTime = Date.now()
    const step = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      start = Math.floor(eased * num)
      setCount(start)
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


/* ──────────── main page ──────────── */

export default function Home() {
  const [activeTab, setActiveTab] = useState<keyof typeof INSTALL_COMMANDS>('curl')
  const [copied, setCopied] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* ─── NAV ─── */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border' : 'bg-transparent'
      }`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
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
            </div>

            <div className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
              <a href="#agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a>
              <a href="#models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a>
              <a href="#tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Tools</a>
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <Github className="w-4 h-4" />
                GitHub
              </a>
              <a href="https://apex-agent.dev/docs" target="_blank" rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Docs
              </a>
              <a href="#install"
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-apex-cyan text-background text-sm font-medium hover:bg-apex-cyan/90 transition-colors">
                <ArrowRight className="w-3.5 h-3.5" />
                Install
              </a>
            </div>

            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-muted-foreground hover:text-foreground">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d={mobileMenuOpen ? "M5 5L15 15M15 5L5 15" : "M2 6H18M2 10H18M2 14H18"} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="md:hidden overflow-hidden border-t border-border"
              >
                <div className="py-4 flex flex-col gap-3">
                  <a href="#features" className="text-sm text-muted-foreground hover:text-foreground px-2 py-1" onClick={() => setMobileMenuOpen(false)}>Features</a>
                  <a href="#agents" className="text-sm text-muted-foreground hover:text-foreground px-2 py-1" onClick={() => setMobileMenuOpen(false)}>Agents</a>
                  <a href="#models" className="text-sm text-muted-foreground hover:text-foreground px-2 py-1" onClick={() => setMobileMenuOpen(false)}>Models</a>
                  <a href="#tools" className="text-sm text-muted-foreground hover:text-foreground px-2 py-1" onClick={() => setMobileMenuOpen(false)}>Tools</a>
                  <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground px-2 py-1">
                    <Github className="w-4 h-4" /> GitHub
                  </a>
                  <a href="#install" className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md bg-apex-cyan text-background text-sm font-medium"
                    onClick={() => setMobileMenuOpen(false)}>
                    <ArrowRight className="w-3.5 h-3.5" /> Install
                  </a>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 grid-pattern" />
        <div className="absolute inset-0 radial-gradient" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-apex-cyan/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-apex-green/5 rounded-full blur-3xl" />

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="text-center"
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />
              v1.3.0 — Security System Released
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold font-mono leading-tight mb-6">
              The Universal{' '}
              <span className="animated-gradient-text">AI Coding</span>
              <br />
              Agent
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Every model. One terminal. APEX runs in your terminal with 100+ models,
              75+ tools, and 5 built-in agents. Switch models mid-session. Never leave your terminal.
            </p>

            {/* Install Tabs */}
            <div id="install" className="max-w-2xl mx-auto">
              <div className="rounded-xl border border-border bg-card overflow-hidden">
                {/* Tab Bar */}
                <div className="flex items-center border-b border-border overflow-x-auto">
                  {Object.entries(INSTALL_COMMANDS).map(([key, { label }]) => (
                    <button
                      key={key}
                      onClick={() => setActiveTab(key as keyof typeof INSTALL_COMMANDS)}
                      className={`relative px-4 py-3 text-sm font-mono whitespace-nowrap transition-colors ${
                        activeTab === key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {label}
                      {activeTab === key && (
                        <motion.div
                          layoutId="tab-indicator"
                          className="absolute bottom-0 left-0 right-0 h-0.5 bg-apex-cyan"
                          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                        />
                      )}
                    </button>
                  ))}
                </div>

                {/* Command */}
                <div className="flex items-center justify-between px-4 py-4 gap-4">
                  <code className="text-sm font-mono text-muted-foreground break-all">
                    <span className="text-apex-cyan/60">$</span>{' '}
                    {INSTALL_COMMANDS[activeTab].cmd}
                  </code>
                  <button
                    onClick={() => handleCopy(INSTALL_COMMANDS[activeTab].cmd)}
                    className="shrink-0 p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                    aria-label="Copy command"
                  >
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
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.7 }}
            className="rounded-xl border border-border overflow-hidden glow-cyan"
          >
            {/* Terminal Header */}
            <div className="flex items-center gap-2 px-4 py-3 bg-card border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-apex-red/80" />
                <div className="w-3 h-3 rounded-full bg-apex-yellow/80" />
                <div className="w-3 h-3 rounded-full bg-apex-green/80" />
              </div>
              <span className="text-xs text-muted-foreground font-mono ml-2">apex — ~/my-project</span>
              <div className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                <span className="text-apex-cyan">build</span>
                <span className="text-muted-foreground">•</span>
                <span>claude-4-sonnet</span>
              </div>
            </div>

            {/* Terminal Content */}
            <div className="bg-[#0a0e14] p-6 font-mono text-sm leading-7 min-h-[320px]">
              <div className="text-muted-foreground">
                <span className="text-apex-cyan">◆</span> APEX v1.3.0 — Ready
              </div>
              <div className="mt-2">
                <span className="text-apex-green">user</span>
                <span className="text-muted-foreground">@apex</span>
                <span className="text-apex-cyan"> ~ </span>
                <span className="text-foreground">Fix the authentication bug in auth.py</span>
              </div>
              <div className="mt-3 text-muted-foreground">
                <span className="text-apex-cyan">◆</span> Using <span className="text-foreground">build</span> agent with <span className="text-apex-cyan">claude-4-sonnet</span>
              </div>
              <div className="mt-2 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-apex-yellow">▸</span>
                  <span className="text-muted-foreground">read_file</span>
                  <span className="text-foreground">auth.py</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-apex-yellow">▸</span>
                  <span className="text-muted-foreground">search_in_files</span>
                  <span className="text-foreground">"authenticate" in src/</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-apex-green">✓</span>
                  <span className="text-muted-foreground">edit_file</span>
                  <span className="text-foreground">auth.py:42 — Fixed token validation</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-apex-green">✓</span>
                  <span className="text-muted-foreground">run_test</span>
                  <span className="text-foreground">test_auth.py — 8/8 passed</span>
                </div>
              </div>
              <div className="mt-3">
                <span className="text-apex-cyan">◆</span>{' '}
                <span className="text-foreground">Fixed the token validation bug. The issue was a missing expiration check on line 42. All tests pass.</span>
              </div>
              <div className="mt-3">
                <span className="text-apex-green">user</span>
                <span className="text-muted-foreground">@apex</span>
                <span className="text-apex-cyan"> ~ </span>
                <span className="text-foreground">/model gpt-4o<span className="cursor-blink text-foreground">█</span></span>
              </div>
              <div className="text-muted-foreground text-xs mt-1">
                Switching to gpt-4o — context preserved
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── STATS ─── */}
      <section className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="text-center p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all"
              >
                <stat.icon className="w-5 h-5 text-apex-cyan mx-auto mb-2" />
                <div className="text-2xl md:text-3xl font-bold font-mono mb-1">
                  <AnimatedCounter value={stat.value} />
                </div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section id="features" className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader
            badge="FEATURES"
            title="Everything you need to code with AI"
            description="APEX is the most feature-rich terminal AI coding agent. 100+ models, 75+ tools, 5 agents, and a comprehensive security system — all in your terminal."
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`group p-6 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300 ${feature.glow}`}
              >
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
          <SectionHeader
            badge="MULTI-AGENT"
            title="5 Specialized Agents"
            description="Each agent has a unique role, access level, and personality. Switch between agents mid-session or let sub-agents handle specialized tasks automatically."
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {AGENTS.map((agent, i) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="group relative p-5 rounded-xl border border-border/50 bg-card/50 hover:border-border transition-all duration-300"
                style={{ '--agent-color': agent.color } as React.CSSProperties}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: agent.color + '15' }}>
                    <agent.icon className="w-5 h-5" style={{ color: agent.color }} />
                  </div>
                  <div>
                    <h3 className="font-bold font-mono text-lg" style={{ color: agent.color }}>/{agent.name}</h3>
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">{agent.mode}</span>
                  </div>
                </div>
                <p className="text-muted-foreground text-sm leading-relaxed mb-3">{agent.desc}</p>
                <div className="flex items-center gap-1.5 text-xs font-mono">
                  <Lock className="w-3 h-3 text-muted-foreground" />
                  <span className="text-muted-foreground">{agent.access}</span>
                </div>
                {/* Accent line */}
                <div className="absolute bottom-0 left-4 right-4 h-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ backgroundColor: agent.color }} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── MODELS ─── */}
      <section id="models" className="py-20 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader
            badge="MODELS"
            title="100+ Models. Any Provider."
            description="Connect any model from any provider. Cloud, local, or custom endpoints. Switch models mid-session without losing context."
          />

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODELS.map((provider, i) => (
              <motion.div
                key={provider.provider}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300"
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{provider.icon}</span>
                  <span className="font-mono font-bold text-sm">{provider.provider}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {provider.models.map(model => (
                    <span key={model} className="px-2 py-0.5 rounded-md bg-secondary text-xs text-muted-foreground font-mono">
                      {model}
                    </span>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>

          <div className="mt-8 text-center">
            <p className="text-muted-foreground text-sm">
              ...and 95+ more models via <span className="text-apex-cyan font-mono">litellm</span>. Supports OpenRouter, Groq, Cohere, Amazon Nova, and any OpenAI-compatible endpoint.
            </p>
          </div>
        </div>
      </section>

      {/* ─── TOOLS ─── */}
      <section id="tools" className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <SectionHeader
            badge="TOOLS"
            title="75+ Built-in Tools"
            description="File operations, search, git, web, LSP, code execution, session management, and more — all built in. No plugins required for the basics."
          />

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {TOOL_CATEGORIES.map((cat, i) => (
              <motion.div
                key={cat.name}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                className="group p-4 rounded-xl border border-border/50 bg-card/50 hover:border-apex-cyan/20 transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <cat.icon className="w-4 h-4 text-apex-cyan" />
                    <span className="font-mono font-bold text-sm">{cat.name}</span>
                  </div>
                  <span className="text-xs text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded">{cat.count}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {cat.examples.map(ex => (
                    <span key={ex} className="text-xs text-muted-foreground font-mono hover:text-apex-cyan transition-colors cursor-default">
                      {ex}
                    </span>
                  )).reduce<React.ReactNode[]>((acc, el, idx) => idx === 0 ? [el] : [...acc, <span key={`sep-${idx}`} className="text-border">·</span>, el], [])}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── COMPARISON ─── */}
      <section className="py-20 relative">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <SectionHeader
            badge="COMPARISON"
            title="Why APEX?"
            description="See how APEX compares to other AI coding agents. More models, more tools, more agents, more control."
          />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="overflow-x-auto rounded-xl border border-border"
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-card/50">
                  <th className="text-left p-4 font-mono text-muted-foreground">Feature</th>
                  <th className="p-4 font-mono text-center">
                    <span className="animated-gradient-text font-bold">APEX</span>
                  </th>
                  <th className="p-4 font-mono text-muted-foreground text-center">OpenCode</th>
                  <th className="p-4 font-mono text-muted-foreground text-center">Claude Code</th>
                  <th className="p-4 font-mono text-muted-foreground text-center">Aider</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row, i) => (
                  <tr key={row.feature} className={`border-b border-border/50 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
                    <td className="p-4 font-mono text-muted-foreground">{row.feature}</td>
                    <td className="p-4 text-center">
                      {typeof row.apex === 'boolean' ? (
                        row.apex ? <Check className="w-4 h-4 text-apex-green mx-auto" /> : <span className="text-muted-foreground">—</span>
                      ) : (
                        <span className="text-apex-cyan font-mono font-bold">{row.apex}</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.opencode === 'boolean' ? (
                        row.opencode ? <Check className="w-4 h-4 text-apex-green mx-auto" /> : <span className="text-muted-foreground">—</span>
                      ) : (
                        <span className="text-muted-foreground font-mono">{row.opencode}</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.claudecode === 'boolean' ? (
                        row.claudecode ? <Check className="w-4 h-4 text-apex-green mx-auto" /> : <span className="text-muted-foreground">—</span>
                      ) : (
                        <span className="text-muted-foreground font-mono">{row.claudecode}</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.aider === 'boolean' ? (
                        row.aider ? <Check className="w-4 h-4 text-apex-green mx-auto" /> : <span className="text-muted-foreground">—</span>
                      ) : (
                        <span className="text-muted-foreground font-mono">{row.aider}</span>
                      )}
                    </td>
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
          <SectionHeader
            badge="SECURITY v1.3.0"
            title="Security-First Architecture"
            description="APEX v1.3.0 introduces a comprehensive security system. Permission rulesets, rate limiting, shell security, and API key management keep you in control."
          />

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                icon: Shield,
                title: 'Permission Rulesets',
                desc: 'Configure allow/deny/ask rules per tool, per agent, or per session. Fine-grained control over what APEX can do.',
                color: '#00e5ff',
              },
              {
                icon: Activity,
                title: 'Rate Limiting',
                desc: 'Database-backed rate limiting with Memory and SQLite backends. Protect against runaway agents and unexpected costs.',
                color: '#00ff88',
              },
              {
                icon: Terminal,
                title: 'Shell Security',
                desc: 'Shell commands are analyzed and classified before execution. Built-in allowlist and command pattern matching.',
                color: '#ffaa00',
              },
              {
                icon: Lock,
                title: 'API Key Management',
                desc: 'Workspace-based API key management with secure storage. Rotate keys, set budgets, and track usage per workspace.',
                color: '#d946ef',
              },
            ].map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="group p-5 rounded-xl border border-border/50 bg-card/50 hover:border-border transition-all duration-300"
              >
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-4" style={{ backgroundColor: item.color + '15' }}>
                  <item.icon className="w-5 h-5" style={{ color: item.color }} />
                </div>
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
          <SectionHeader
            badge="COMMANDS"
            title="20+ Slash Commands"
            description="Powerful slash commands for every workflow. Model switching, session management, git operations, and more — all from the command line."
          />

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {[
              '/model', '/models', '/agent', '/yolo', '/plan', '/build',
              '/cwd', '/clear', '/history', '/cost', '/save', '/load',
              '/memory', '/map', '/stats', '/git', '/undo', '/redo',
              '/restore', '/skills', '/help',
            ].map((cmd, i) => (
              <motion.div
                key={cmd}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.2, delay: i * 0.02 }}
                className="px-3 py-2 rounded-lg border border-border/50 bg-card/50 font-mono text-sm text-apex-cyan hover:border-apex-cyan/30 hover:bg-apex-cyan/5 transition-all cursor-default text-center"
              >
                {cmd}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="py-20 relative">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <SectionHeader
            badge="FAQ"
            title="Frequently Asked Questions"
            description="Got questions? We have answers."
          />

          <div className="space-y-3">
            {FAQ.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="rounded-xl border border-border/50 bg-card/50 overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left hover:bg-card/80 transition-colors"
                >
                  <span className="font-mono font-bold text-sm pr-4">{item.q}</span>
                  <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform duration-200 ${
                    openFaq === i ? 'rotate-180' : ''
                  }`} />
                </button>
                <AnimatePresence>
                  {openFaq === i && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 text-muted-foreground text-sm leading-relaxed">
                        {item.a}
                      </div>
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
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl md:text-5xl font-bold font-mono mb-6">
              Ready to <span className="animated-gradient-text">code faster</span>?
            </h2>
            <p className="text-muted-foreground text-lg mb-10 leading-relaxed">
              Install APEX in seconds. Connect your API key. Start coding with the most powerful terminal AI agent.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href="#install"
                className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-apex-cyan text-background font-bold font-mono hover:bg-apex-cyan/90 transition-colors glow-cyan">
                <ArrowRight className="w-4 h-4" />
                Install APEX
              </a>
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-border text-foreground font-bold font-mono hover:border-apex-cyan/30 hover:bg-card transition-colors">
                <Github className="w-4 h-4" />
                View on GitHub
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="border-t border-border py-12 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-6 h-6">
                  <defs>
                    <linearGradient id="foot-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stopColor="#00e5ff"/>
                      <stop offset="100%" stopColor="#00ff88"/>
                    </linearGradient>
                  </defs>
                  <polygon points="32,4 60,56 4,56" stroke="url(#foot-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/>
                  <circle cx="32" cy="40" r="4" fill="url(#foot-grad)"/>
                </svg>
                <span className="font-mono font-bold">APEX</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                The universal AI coding agent.<br />
                Every model. One terminal.
              </p>
              <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>Built in Africa</span>
                <span>🇬🇦</span>
                <span>with</span>
                <Heart className="w-3 h-3 text-apex-red inline" />
              </div>
            </div>

            {/* Product */}
            <div>
              <h4 className="font-mono font-bold text-sm mb-4">Product</h4>
              <ul className="space-y-2">
                <li><a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a></li>
                <li><a href="#agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a></li>
                <li><a href="#models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a></li>
                <li><a href="#tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Tools</a></li>
                <li><a href="#install" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Install</a></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="font-mono font-bold text-sm mb-4">Resources</h4>
              <ul className="space-y-2">
                <li><a href="https://apex-agent.dev/docs" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Documentation <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">GitHub <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/CHANGELOG.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Changelog <ExternalLink className="w-3 h-3" /></a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/ROADMAP.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Roadmap <ExternalLink className="w-3 h-3" /></a></li>
              </ul>
            </div>

            {/* Community */}
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
            <p className="text-xs text-muted-foreground">
              MIT License. Built by <a href="https://github.com/Ggboykxz" target="_blank" rel="noopener noreferrer" className="text-apex-cyan hover:underline">Ggboykxz</a>.
            </p>
            <div className="flex items-center gap-4">
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground transition-colors">
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
