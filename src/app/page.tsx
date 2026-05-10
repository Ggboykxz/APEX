'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import {
  Terminal, Zap, Shield, Bot, Copy, Check, ArrowRight,
  Github, Cpu, Wrench, Users, Star, Lock,
  Activity, Radio, Loader2, Menu, X, Code2, Eye, Search, Layers,
  GitBranch, Globe, FileCode, Play, Command, Clock, Sparkles, BookOpen,
  CircleDot, GitPullRequest, Tag, Box, MessageSquare, Heart, ExternalLink,
  ChevronRight
} from 'lucide-react'
import { PROVIDER_ICONS, PROVIDER_LIST, AnthropicIcon } from '@/components/ProviderIcons'

/* ──── TYPES ──── */
interface GitHubRepoData {
  stargazers_count: number
  forks_count: number
  open_issues_count: number
  subscribers_count: number
  contributors: number
  latest_release: { tag_name: string; published_at: string } | null
}
interface GitHubIssue {
  number: number; title: string; state: 'open' | 'closed'; created_at: string; user: { login: string }; labels: { name: string; color: string }[]
}
interface GitHubPullRequest {
  number: number; title: string; state: 'open' | 'closed'; merged_at: string | null; created_at: string; user: { login: string }; labels: { name: string; color: string }[]
}
interface GitHubRelease {
  tag_name: string; name: string; published_at: string; body: string
}
interface GitHubData {
  repo: GitHubRepoData | null; issues: GitHubIssue[]; pullRequests: GitHubPullRequest[]; releases: GitHubRelease[]
}

/* ──── HELPERS ──── */
function timeAgo(dateString: string): string {
  const diff = Date.now() - new Date(dateString).getTime()
  const s = Math.floor(diff / 1000), m = Math.floor(s / 60), h = Math.floor(m / 60), d = Math.floor(h / 24), w = Math.floor(d / 7), mo = Math.floor(d / 30)
  if (s < 60) return `${s}s ago`; if (m < 60) return `${m}m ago`; if (h < 24) return `${h}h ago`; if (d < 7) return `${d}d ago`; if (w < 5) return `${w}w ago`; return `${mo}mo ago`
}

/* ──── CONSTANTS ──── */
const INSTALL_COMMANDS: Record<string, { label: string; cmd: string }> = {
  curl: { label: 'curl', cmd: 'curl -fsSL https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.sh | bash' },
  pipx: { label: 'pipx', cmd: 'pipx install apex-ai' },
  pip: { label: 'pip', cmd: 'pip install apex-ai' },
  uv: { label: 'uv', cmd: 'uv tool install apex-ai' },
  docker: { label: 'docker', cmd: 'docker run -it ghcr.io/ggboykxz/apex' },
}

const FEATURES = [
  { icon: Cpu, title: '100+ Models', description: 'Use any LLM from any provider. Claude, GPT-4o, Gemini, Grok, Llama, DeepSeek, Qwen, and 95+ more models via litellm.', color: 'text-apex-cyan', glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]' },
  { icon: Bot, title: '5 Specialized Agents', description: 'Coder, Architect, Planner, Reviewer, and Shell agents with per-tool permission systems.', color: 'text-apex-green', glow: 'group-hover:shadow-[0_0_30px_rgba(0,255,136,0.15)]' },
  { icon: Wrench, title: '75+ Tools', description: 'File ops, search, git, web, LSP, code generation, sandboxed execution, clipboard, skills, and more — all built in and ready.', color: 'text-apex-yellow', glow: 'group-hover:shadow-[0_0_30px_rgba(255,170,0,0.15)]' },
  { icon: Shield, title: 'Security System', description: 'Shell command analysis, permission rulesets (ALLOW/DENY/ASK), rate limiting, API key management, billing system, and path traversal protection.', color: 'text-apex-red', glow: 'group-hover:shadow-[0_0_30px_rgba(255,68,68,0.15)]' },
  { icon: Zap, title: 'Switch Models Live', description: 'Switch between any model mid-session without restarting. Compare outputs, optimize costs, and never lose context.', color: 'text-apex-magenta', glow: 'group-hover:shadow-[0_0_30px_rgba(217,70,239,0.15)]' },
  { icon: Terminal, title: '3 TUI Modes + 6 Themes', description: 'Rich CLI, full Textual TUI with sidebar, or the new OpenTUI frontend with routes, command palette, and 6 built-in themes (opencode, dracula, nord, tokyonight, gruvbox, github).', color: 'text-apex-cyan', glow: 'group-hover:shadow-[0_0_30px_rgba(0,229,255,0.15)]' },
  { icon: Layers, title: 'Snapshots & Undo/Redo', description: 'Git-based snapshot system creates automatic backups before every destructive action. Undo/redo with full diff computation. Never lose work again.', color: 'text-apex-green', glow: 'group-hover:shadow-[0_0_30px_rgba(0,255,136,0.15)]' },
  { icon: Command, title: 'Custom Commands + Event Bus', description: 'Create user: and project: commands with template variables. 25+ typed events on the Event Bus for real-time UI updates. Session sharing via apex:// links.', color: 'text-apex-magenta', glow: 'group-hover:shadow-[0_0_30px_rgba(217,70,239,0.15)]' },
]

const STATS = [
  { value: '100+', label: 'Models Supported', icon: Cpu },
  { value: '75+', label: 'Built-in Tools', icon: Wrench },
  { value: '5', label: 'Specialized Agents', icon: Bot },
  { value: '1,148+', label: 'Tests Passing', icon: Check },
  { value: '6', label: 'Built-in Themes', icon: Sparkles },
  { value: '6+', label: 'Install Methods', icon: Box },
]

const PAGE_LINKS = [
  { href: '/agents', icon: Bot, title: 'Agents', desc: '5 specialized agents for every workflow', color: 'text-apex-cyan' },
  { href: '/models', icon: Cpu, title: 'Models', desc: '100+ models from every major provider', color: 'text-apex-green' },
  { href: '/tools', icon: Wrench, title: 'Tools', desc: '75+ built-in tools for every workflow', color: 'text-apex-yellow' },
  { href: '/install', icon: Box, title: 'Install', desc: '6 installation methods for every platform', color: 'text-apex-cyan' },
  { href: '/security', icon: Shield, title: 'Security', desc: 'Permissions, rate limiting, and shell security', color: 'text-apex-red' },
  { href: '/activity', icon: Activity, title: 'Activity', desc: 'Live issues, PRs, and releases feed', color: 'text-apex-green' },
  { href: '/roadmap', icon: GitBranch, title: 'Roadmap', desc: 'From Foundation to Enterprise', color: 'text-apex-magenta' },
  { href: '/contribute', icon: Users, title: 'Contribute', desc: 'Development setup and guidelines', color: 'text-apex-yellow' },
]

/* ──── COMPONENTS ──── */
function AnimatedCounter({ value, suffix = '' }: { value: string; suffix?: string }) {
  const numericPart = value.replace(/[^0-9]/g, '')
  const prefix = value.substring(0, value.indexOf(numericPart))
  const num = parseInt(numericPart)
  const [count, setCount] = useState(0)
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  useEffect(() => {
    if (!inView) return
    const startTime = Date.now()
    const step = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / 2000, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.floor(eased * num))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [inView, num])
  return <span ref={ref} className="animated-gradient-text font-bold tabular-nums">{prefix}{count}{suffix}</span>
}

/* ──── Edition date helper ──── */
function getEditionDate(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function NavBar({ scrolled, mobileMenuOpen, setMobileMenuOpen, apiStatus }: {
  scrolled: boolean; mobileMenuOpen: boolean; setMobileMenuOpen: (v: boolean) => void; apiStatus: 'online' | 'offline' | 'loading'
}) {
  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border' : 'bg-transparent'}`}>
      {/* Edition Bar — top row */}
      <div className="bg-card/80 backdrop-blur border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between py-1.5">
          <span className="text-xs font-mono text-muted-foreground">Edition {getEditionDate()}</span>
          <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
            <span>apex-ai.dev</span>
            <span className="text-border">·</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full pulse-dot ${apiStatus === 'online' ? 'bg-apex-green' : apiStatus === 'offline' ? 'bg-apex-red' : 'bg-apex-yellow'}`} />
              <span className={apiStatus === 'online' ? 'text-apex-green' : apiStatus === 'offline' ? 'text-apex-red' : 'text-apex-yellow'}>API · {apiStatus === 'online' ? 'Online' : apiStatus === 'offline' ? 'Offline' : 'Sync'}</span>
            </div>
          </div>
        </div>
      </div>
      {/* Main nav — bottom row */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7">
              <defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs>
              <polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/>
              <circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/>
            </svg>
            <span className="font-mono font-bold text-lg">APEX</span>
          </a>
          <div className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="/install" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Install</a>
            <a href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"><BookOpen className="w-4 h-4" /> Docs</a>
            <a href="/agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a>
            <a href="/models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a>
            <a href="/tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Tools</a>
            <a href="/activity" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"><Activity className="w-3.5 h-3.5" /> Activity</a>
            <a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"><GitBranch className="w-3.5 h-3.5" /> Roadmap</a>
            <a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Contribute</a>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"><Github className="w-4 h-4" /> GitHub</a>
            <a href="#install" className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-apex-cyan text-background text-sm font-medium hover:bg-apex-cyan/90 transition-colors"><ArrowRight className="w-3.5 h-3.5" /> Install</a>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 text-muted-foreground hover:text-foreground">{mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
          </div>
        </div>
      </div>
      {mobileMenuOpen && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border">
          <div className="px-4 py-4 space-y-3">
            {[{ href: '#features', label: 'Features' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }, { href: '/activity', label: 'Activity' }, { href: '/roadmap', label: 'Roadmap' }, { href: '/contribute', label: 'Contribute' }, { href: 'https://github.com/Ggboykxz/APEX', label: 'GitHub' }].map(link => (
              <a key={link.href + link.label} href={link.href} onClick={() => setMobileMenuOpen(false)} target={link.href.startsWith('http') ? '_blank' : undefined} rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined} className="block text-sm text-muted-foreground hover:text-foreground transition-colors py-1">{link.label}</a>
            ))}
          </div>
        </motion.div>
      )}
    </nav>
  )
}

/* ──── MAIN ──── */
export default function Home() {
  const [activeTab, setActiveTab] = useState<keyof typeof INSTALL_COMMANDS>('curl')
  const [copied, setCopied] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [githubData, setGithubData] = useState<GitHubData | null>(null)
  const [githubLoading, setGithubLoading] = useState(true)
  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'loading'>('loading')

  useEffect(() => {
    let isMounted = true
    const fetchGithub = async () => {
      try {
        setGithubLoading(true)
        const res = await fetch('/api/github')
        if (!res.ok) throw new Error('Failed')
        const data: GitHubData = await res.json()
        if (isMounted) { setGithubData(data); setApiStatus('online'); setGithubLoading(false) }
      } catch { if (isMounted) { setApiStatus('offline'); setGithubLoading(false) } }
    }
    fetchGithub()
    const interval = setInterval(fetchGithub, 300000)
    return () => { isMounted = false; clearInterval(interval) }
  }, [])

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleCopy = (text: string) => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }

  /* ──── Dispatch helpers ──── */
  const dispatchHighlights = githubData ? [
    ...githubData.releases.slice(0, 2).map(r => ({ type: 'release' as const, title: r.tag_name, desc: r.name || 'New release', number: 0 })),
    ...githubData.pullRequests.filter(p => p.merged_at).slice(0, 2).map(p => ({ type: 'merged' as const, title: p.title, desc: `PR #${p.number} by ${p.user.login}`, number: p.number })),
    ...githubData.issues.filter(i => i.state === 'open').slice(0, 2).map(i => ({ type: 'open' as const, title: i.title, desc: `Issue #${i.number}`, number: i.number })),
  ].slice(0, 5) : []

  const dispatchMovers = githubData ? [
    ...githubData.issues.slice(0, 3).map(i => ({ number: i.number, title: i.title })),
    ...githubData.pullRequests.slice(0, 2).map(p => ({ number: p.number, title: p.title })),
  ] : []

  const recentActivity = githubData ? [
    ...githubData.issues.slice(0, 3).map(i => ({ type: 'Issue' as const, number: i.number, time: timeAgo(i.created_at), title: i.title, state: i.state, author: i.user.login })),
    ...githubData.pullRequests.slice(0, 2).map(p => ({ type: 'Pull' as const, number: p.number, time: timeAgo(p.created_at), title: p.title, state: p.merged_at ? 'merged' : p.state, author: p.user.login })),
  ].sort((a, b) => a.time.localeCompare(b.time)).slice(0, 5) : []

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar scrolled={scrolled} mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} apiStatus={apiStatus} />

      {/* LIVE TICKER */}
      <div className="relative pt-[6.5rem]">
        <div className="bg-card/80 border-b border-border/50 overflow-hidden">
          <div className="flex items-center">
            <div className="shrink-0 px-3 py-2 ticker-label-dark flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-apex-cyan" /><span className="text-xs font-mono font-bold text-apex-cyan uppercase tracking-wider">Live</span>
            </div>
            <div className="overflow-hidden flex-1">
              {githubLoading ? (
                <div className="flex items-center gap-2 px-4 py-2"><Loader2 className="w-3 h-3 text-muted-foreground animate-spin" /><span className="text-xs text-muted-foreground font-mono">Loading activity...</span></div>
              ) : githubData ? (
                <div className="ticker-track">
                  {[...githubData.issues.slice(0, 5), ...githubData.pullRequests.slice(0, 5), ...githubData.releases.slice(0, 3), ...githubData.issues.slice(0, 5), ...githubData.pullRequests.slice(0, 5), ...githubData.releases.slice(0, 3)].map((item, i) => {
                    const isIssue = 'state' in item && !('merged_at' in item)
                    const isPR = 'merged_at' in item
                    const isRelease = 'tag_name' in item && 'body' in item
                    return (
                      <a key={i} href={isRelease ? `https://github.com/Ggboykxz/APEX/releases/tag/${(item as GitHubRelease).tag_name}` : `https://github.com/Ggboykxz/APEX/issues/${(item as GitHubIssue | GitHubPullRequest).number}`} target="_blank" rel="noopener noreferrer" className="shrink-0 flex items-center gap-2 px-4 py-2 hover:bg-card transition-colors border-r border-border/30">
                        {isIssue && <><CircleDot className={`w-3 h-3 ${(item as GitHubIssue).state === 'open' ? 'text-apex-green' : 'text-apex-red'}`} /><span className="text-xs font-mono text-muted-foreground">ISS #{(item as GitHubIssue).number}</span><span className="text-xs text-foreground truncate max-w-[200px]">{(item as GitHubIssue).title}</span><span className="text-xs text-muted-foreground">{timeAgo((item as GitHubIssue).created_at)}</span></>}
                        {isPR && <><GitPullRequest className={`w-3 h-3 ${(item as GitHubPullRequest).merged_at ? 'text-apex-magenta' : (item as GitHubPullRequest).state === 'open' ? 'text-apex-green' : 'text-apex-red'}`} /><span className="text-xs font-mono text-muted-foreground">PR #{(item as GitHubPullRequest).number}</span><span className="text-xs text-foreground truncate max-w-[200px]">{(item as GitHubPullRequest).title}</span><span className="text-xs text-muted-foreground">{timeAgo((item as GitHubPullRequest).created_at)}</span></>}
                        {isRelease && <><Tag className="w-3 h-3 text-apex-cyan" /><span className="text-xs font-mono text-apex-cyan">{(item as GitHubRelease).tag_name}</span><span className="text-xs text-foreground truncate max-w-[200px]">{(item as GitHubRelease).name || 'Release'}</span><span className="text-xs text-muted-foreground">{timeAgo((item as GitHubRelease).published_at)}</span></>}
                      </a>
                    )
                  })}
                </div>
              ) : <div className="px-4 py-2 text-xs text-muted-foreground font-mono">Unable to load activity feed</div>}
            </div>
          </div>
        </div>
      </div>

      {/* HERO */}
      <section className="relative pt-20 pb-20 overflow-hidden">
        <div className="absolute inset-0 grid-pattern" />
        <div className="absolute inset-0 radial-gradient" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-apex-cyan/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-apex-green/5 rounded-full blur-3xl" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }} className="text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />v1.1.0 — TUI & Agent Update
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold font-mono leading-tight mb-6">
              The Universal <span className="animated-gradient-text">AI Coding</span><br />Agent
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Every model. One terminal. APEX runs in your terminal with 100+ models, 75+ tools, and 5 specialized agents. Switch models mid-session. Snapshots, custom commands, and event bus built in.
            </p>

            {/* Install Tabs */}
            <div id="install" className="max-w-2xl mx-auto">
              <div className="rounded-xl border border-border bg-card overflow-hidden">
                <div className="flex items-center border-b border-border overflow-x-auto">
                  {Object.entries(INSTALL_COMMANDS).map(([key, { label }]) => (
                    <button key={key} onClick={() => setActiveTab(key as keyof typeof INSTALL_COMMANDS)} className={`relative px-4 py-3 text-sm font-mono whitespace-nowrap transition-colors ${activeTab === key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                      {label}
                      {activeTab === key && <motion.div layoutId="tab-indicator" className="absolute bottom-0 left-0 right-0 h-0.5 bg-apex-cyan" transition={{ type: 'spring', stiffness: 400, damping: 30 }} />}
                    </button>
                  ))}
                </div>
                <div className="flex items-center justify-between px-4 py-4 gap-4">
                  <code className="text-sm font-mono text-muted-foreground break-all"><span className="text-apex-cyan/60">$</span> {INSTALL_COMMANDS[activeTab].cmd}</code>
                  <button onClick={() => handleCopy(INSTALL_COMMANDS[activeTab].cmd)} className="shrink-0 p-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors" aria-label="Copy command">
                    {copied ? <Check className="w-4 h-4 text-apex-green" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5"><Star className="w-3.5 h-3.5 text-apex-yellow" /> Proprietary License</span>
                <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5 text-apex-cyan" /> Built in Africa 🇬🇦</span>
                <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-apex-green" /> Security First</span>
              </div>
            </div>

            {/* CTA + Support link */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <a href="/install" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-apex-cyan text-background font-medium hover:bg-apex-cyan/90 transition-colors"><Zap className="w-4 h-4" /> Install Now</a>
              <a href="/docs" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><BookOpen className="w-4 h-4" /> Read the Docs</a>
              <a href="https://buymeacoffee.com/ggboykxz" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><Heart className="w-4 h-4 text-apex-pink" /> Support ↗</a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* TERMINAL DEMO */}
      <section className="relative py-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7 }} className="rounded-xl border border-border overflow-hidden glow-cyan">
            <div className="flex items-center gap-2 px-4 py-3 bg-card border-b border-border">
              <div className="flex gap-1.5"><div className="w-3 h-3 rounded-full bg-apex-red/80" /><div className="w-3 h-3 rounded-full bg-apex-yellow/80" /><div className="w-3 h-3 rounded-full bg-apex-green/80" /></div>
              <span className="text-xs text-muted-foreground font-mono ml-2">apex — ~/my-project</span>
              <div className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground font-mono"><span className="text-apex-cyan">coder</span><span className="text-muted-foreground">•</span><span className="flex items-center gap-1"><AnthropicIcon size={12} /><span>claude-4-sonnet</span></span></div>
            </div>
            <div className="bg-[#0a0e14] p-6 font-mono text-sm leading-7 min-h-[320px]">
              <div className="text-muted-foreground"><span className="text-apex-cyan">◆</span> APEX v1.1.0 — Ready</div>
              <div className="mt-2"><span className="text-apex-green">user</span><span className="text-muted-foreground">@apex</span><span className="text-apex-cyan"> ~ </span><span className="text-foreground">Fix the authentication bug in auth.py</span></div>
              <div className="mt-3 text-muted-foreground"><span className="text-apex-cyan">◆</span> Using <span className="text-foreground">coder</span> agent with <span className="text-apex-cyan">claude-4-sonnet</span></div>
              <div className="mt-2 space-y-1.5">
                <div className="flex items-center gap-2"><span className="text-apex-yellow">▸</span><span className="text-muted-foreground">read_file</span><span className="text-foreground">auth.py</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-yellow">▸</span><span className="text-muted-foreground">search_in_files</span><span className="text-foreground">"authenticate" in src/</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-green">✓</span><span className="text-muted-foreground">edit_file</span><span className="text-foreground">auth.py:42 — Fixed token validation</span></div>
                <div className="flex items-center gap-2"><span className="text-apex-green">✓</span><span className="text-muted-foreground">run_test</span><span className="text-foreground">test_auth.py — 8/8 passed</span></div>
              </div>
              <div className="mt-3"><span className="text-apex-cyan">◆</span> <span className="text-foreground">Fixed the token validation bug. The issue was a missing expiration check on line 42. All tests pass.</span></div>
              <div className="mt-4"><span className="text-apex-green">user</span><span className="text-muted-foreground">@apex</span><span className="text-apex-cyan"> ~ </span><span className="text-foreground cursor-blink">▊</span></div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* STATS */}
      <section className="py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {STATS.map((stat, i) => (
              <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }} className="text-center">
                <stat.icon className="w-5 h-5 mx-auto mb-2 text-apex-cyan" />
                <div className="text-2xl font-bold font-mono tabular-nums"><AnimatedCounter value={stat.value} /></div>
                <div className="text-xs text-muted-foreground font-mono mt-1">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── SUPPORTED PROVIDERS ──── */}
      <section className="py-12 border-t border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }} className="text-center">
            <p className="eyebrow mb-6">Supported Providers</p>
            <div className="flex flex-wrap items-center justify-center gap-6 md:gap-8">
              {PROVIDER_LIST.map(p => {
                const IconComp = PROVIDER_ICONS[p.iconKey]
                return (
                  <a key={p.iconKey} href="/models" className="group flex flex-col items-center gap-2 transition-all duration-300 hover:scale-110" title={p.name}>
                    <div className="w-14 h-14 rounded-xl flex items-center justify-center border border-border/50 bg-card/30 group-hover:border-border group-hover:bg-card/60 transition-all duration-300" style={{ boxShadow: `0 0 0 0 ${p.color}00`, transition: 'box-shadow 0.3s' }} onMouseEnter={e => (e.currentTarget.style.boxShadow = `0 0 20px ${p.color}20`)} onMouseLeave={e => (e.currentTarget.style.boxShadow = `0 0 0 0 ${p.color}00`)}>
                      {IconComp && <IconComp size={28} />}
                    </div>
                    <span className="text-[0.65rem] font-mono text-muted-foreground group-hover:text-foreground transition-colors">{p.name}</span>
                  </a>
                )
              })}
            </div>
            <p className="text-xs text-muted-foreground font-mono mt-6">+ 90 more models via litellm · <a href="/models" className="text-apex-cyan hover:underline">View all models →</a></p>
          </motion.div>
        </div>
      </section>

      {/* ──── TODAY'S DISPATCH ──── */}
      <section className="py-16 border-t border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl md:text-3xl font-bold font-mono">Today&apos;s Dispatch</h2>
                <p className="text-sm text-muted-foreground font-mono mt-1">{getEditionDate()}</p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">Curated by apex · 5min cron</span>
            </div>

            {githubLoading ? (
              <div className="grid md:grid-cols-12 gap-8">
                <div className="md:col-span-7 space-y-4">
                  {[...Array(4)].map((_, i) => <div key={i} className="h-12 rounded-lg bg-card/50 animate-pulse" />)}
                </div>
                <div className="md:col-span-5 space-y-3">
                  {[...Array(5)].map((_, i) => <div key={i} className="h-10 rounded-lg bg-card/50 animate-pulse" />)}
                </div>
              </div>
            ) : githubData ? (
              <div className="grid md:grid-cols-12 gap-8">
                {/* Left column — Main dispatch */}
                <div className="md:col-span-7">
                  {/* Headline */}
                  <h3 className="text-xl font-bold font-mono mb-3">
                    {githubData.releases.length > 0 ? `${githubData.releases[0].tag_name} released` : 'Latest updates merged'}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                    {githubData.releases.length > 0
                      ? `${githubData.releases[0].name || 'New release'} — ${githubData.pullRequests.filter(p => p.merged_at).length} PRs merged, ${githubData.issues.filter(i => i.state === 'open').length} issues open. Activity continues across the project.`
                      : `${githubData.pullRequests.length} pull requests and ${githubData.issues.length} issues tracked. Development is active.`}
                  </p>

                  {/* Highlights */}
                  <div className="mb-6">
                    <h4 className="eyebrow mb-3">Highlights</h4>
                    <div className="space-y-2">
                      {dispatchHighlights.map((h, i) => (
                        <a key={i} href={h.number ? `https://github.com/Ggboykxz/APEX/issues/${h.number}` : `https://github.com/Ggboykxz/APEX/releases`} target="_blank" rel="noopener noreferrer" className="flex items-start gap-3 p-2 rounded-lg hover:bg-card/50 transition-colors group">
                          <span className={`shrink-0 mt-0.5 ${h.type === 'release' ? 'pill-hot' : h.type === 'merged' ? 'pill-jade' : 'pill-ghost'}`}>{h.type}</span>
                          <div className="min-w-0">
                            <span className="text-sm font-medium group-hover:text-apex-cyan transition-colors">{h.title}</span>
                            <span className="text-xs text-muted-foreground ml-2">{h.desc}</span>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>

                  {/* Movers */}
                  {dispatchMovers.length > 0 && (
                    <div>
                      <h4 className="eyebrow mb-3">Movers</h4>
                      <div className="space-y-1.5">
                        {dispatchMovers.map((m, i) => (
                          <a key={i} href={`https://github.com/Ggboykxz/APEX/issues/${m.number}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm hover:text-apex-cyan transition-colors">
                            <span className="text-xs font-mono text-muted-foreground">#{m.number}</span>
                            <span className="truncate">{m.title}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right column — Recent Activity sidebar */}
                <div className="md:col-span-5">
                  <div className="rounded-xl border border-border/50 bg-card/30 overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-3 bg-card/80 border-b border-border/50">
                      <h4 className="text-sm font-bold font-mono">Latest Activity</h4>
                      <a href="/activity" className="text-xs text-muted-foreground hover:text-apex-cyan transition-colors flex items-center gap-1">All <ChevronRight className="w-3 h-3" /></a>
                    </div>
                    <div className="divide-y divide-border/30">
                      {recentActivity.map((item, i) => (
                        <a key={i} href={`https://github.com/Ggboykxz/APEX/issues/${item.number}`} target="_blank" rel="noopener noreferrer" className="flex items-start gap-3 px-4 py-3 hover:bg-card/50 transition-colors">
                          <span className={`shrink-0 text-[0.6rem] font-mono font-bold uppercase mt-0.5 ${item.type === 'Pull' ? 'text-apex-magenta' : 'text-apex-green'}`}>{item.type}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-0.5">
                              <span>#{item.number}</span>
                              <span>·</span>
                              <span>{item.time}</span>
                            </div>
                            <p className="text-sm truncate">{item.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className={`pill-ghost text-[0.55rem]`}>{item.state}</span>
                              <span className="text-xs text-muted-foreground">{item.author}</span>
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground font-mono text-sm">Unable to load dispatch</div>
            )}
          </motion.div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }} className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Features
            </div>
            <h2 className="text-3xl md:text-4xl font-bold mb-4 font-mono">Everything You Need</h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">APEX combines the power of 100+ models, 75+ tools, 5 specialized agents, and OpenCode architecture in one terminal-native experience.</p>
          </motion.div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }} className={`group p-6 rounded-xl border border-border/50 bg-card/30 transition-all duration-300 ${feature.glow} hover:border-border`}>
                <feature.icon className={`w-8 h-8 mb-4 ${feature.color}`} />
                <h3 className="text-lg font-bold font-mono mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── WHAT IT ACTUALLY IS ──── */}
      <section className="py-20 bg-card/30 border-t border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <div className="flex items-center gap-3 mb-12">
              <span className="seal">△</span>
              <h2 className="text-3xl md:text-4xl font-bold font-mono">What it actually is</h2>
            </div>
            <div className="grid md:grid-cols-3 col-rule">
              <div className="md:pr-8">
                <p className="eyebrow mb-2">01 · Terminal Agent</p>
                <h3 className="text-lg font-bold font-mono mb-3">A coding agent, not a chat box</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">Same loop as Claude Code or Codex CLI. It reads, edits, runs tests, reports back.</p>
              </div>
              <div className="md:px-8 pt-6 md:pt-0">
                <p className="eyebrow mb-2">02 · Sandbox Protection</p>
                <h3 className="text-lg font-bold font-mono mb-3">Five agents, one approval system</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">Coder asks, Architect reads, Planner observes. Sandboxed via landlock (Linux), seatbelt (macOS), restricted tokens (Windows).</p>
              </div>
              <div className="md:pl-8 pt-6 md:pt-0">
                <p className="eyebrow mb-2">03 · Model Freedom</p>
                <h3 className="text-lg font-bold font-mono mb-3">100+ models by default</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">Use any LLM from any provider. Swap with /model command mid-session. Structured messages with Parts, snapshots with undo/redo, and custom commands.</p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ──── HOW IT WORKS ──── */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <div className="flex items-center gap-3 mb-12">
              <span className="seal">△</span>
              <h2 className="text-3xl md:text-4xl font-bold font-mono">How it works</h2>
            </div>
            <div className="rounded-xl border border-border/50 bg-card/30 p-6 md:p-10 overflow-x-auto">
              {/* Architecture Diagram SVG */}
              <svg viewBox="0 0 900 380" className="w-full max-w-4xl mx-auto" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ minWidth: '600px' }}>
                {/* ── Arrows ── */}
                {/* You type → Engine */}
                <line x1="220" y1="70" x2="370" y2="70" stroke="#00e5ff" strokeWidth="2" markerEnd="url(#arrowCyan)" />
                <text x="295" y="62" textAnchor="middle" fill="#7d8590" fontSize="11" fontFamily="monospace">input</text>

                {/* Engine → LLM API */}
                <line x1="520" y1="50" x2="640" y2="50" stroke="#00e5ff" strokeWidth="2" markerEnd="url(#arrowCyan)" />
                <text x="580" y="42" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">HTTPS / SSE</text>

                {/* Engine → Tools */}
                <line x1="520" y1="90" x2="640" y2="150" stroke="#00e5ff" strokeWidth="2" markerEnd="url(#arrowCyan)" />
                <text x="570" y="118" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">tool call</text>

                {/* Tools → Approval */}
                <line x1="810" y1="170" x2="810" y2="230" stroke="#00e5ff" strokeWidth="2" markerEnd="url(#arrowCyan)" />
                <text x="838" y="205" fill="#7d8590" fontSize="10" fontFamily="monospace">confirm</text>

                {/* Approval → Engine (loop back) */}
                <path d="M810 280 L810 310 L445 310 L445 100" stroke="#00ff88" strokeWidth="2" fill="none" strokeDasharray="6 3" markerEnd="url(#arrowGreen)" />
                <text x="628" y="328" textAnchor="middle" fill="#00ff88" fontSize="10" fontFamily="monospace">Y/N → loop</text>

                {/* Tools → Sandbox */}
                <line x1="720" y1="195" x2="720" y2="260" stroke="#ffaa00" strokeWidth="2" markerEnd="url(#arrowYellow)" />
                <text x="738" y="232" fill="#7d8590" fontSize="10" fontFamily="monospace">exec</text>

                {/* ── Arrow markers ── */}
                <defs>
                  <marker id="arrowCyan" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#00e5ff" /></marker>
                  <marker id="arrowGreen" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#00ff88" /></marker>
                  <marker id="arrowYellow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#ffaa00" /></marker>
                </defs>

                {/* ── Nodes ── */}
                {/* You type */}
                <rect x="40" y="45" width="180" height="50" rx="8" fill="#161b22" stroke="#30363d" strokeWidth="1.5" />
                <text x="130" y="65" textAnchor="middle" fill="#e6edf3" fontSize="13" fontWeight="bold" fontFamily="monospace">You type</text>
                <text x="130" y="82" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">TUI · Terminal</text>

                {/* Engine */}
                <rect x="370" y="35" width="150" height="70" rx="8" fill="#161b22" stroke="#00e5ff" strokeWidth="2" />
                <text x="445" y="65" textAnchor="middle" fill="#00e5ff" fontSize="13" fontWeight="bold" fontFamily="monospace">Engine</text>
                <text x="445" y="82" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">turn loop + tools</text>

                {/* LLM API */}
                <rect x="640" y="25" width="200" height="50" rx="8" fill="#161b22" stroke="#30363d" strokeWidth="1.5" />
                <text x="740" y="46" textAnchor="middle" fill="#e6edf3" fontSize="13" fontWeight="bold" fontFamily="monospace">LLM API</text>
                <text x="740" y="62" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">100+ models</text>

                {/* Tools */}
                <rect x="640" y="120" width="200" height="75" rx="8" fill="#161b22" stroke="#30363d" strokeWidth="1.5" />
                <text x="740" y="145" textAnchor="middle" fill="#e6edf3" fontSize="13" fontWeight="bold" fontFamily="monospace">Tools</text>
                <text x="740" y="162" textAnchor="middle" fill="#7d8590" fontSize="9" fontFamily="monospace">read_file · edit_file</text>
                <text x="740" y="176" textAnchor="middle" fill="#7d8590" fontSize="9" fontFamily="monospace">grep · exec_shell · mcp_server</text>

                {/* Approval */}
                <rect x="740" y="230" width="140" height="50" rx="8" fill="#161b22" stroke="#ffaa00" strokeWidth="1.5" />
                <text x="810" y="252" textAnchor="middle" fill="#ffaa00" fontSize="13" fontWeight="bold" fontFamily="monospace">Approval</text>
                <text x="810" y="268" textAnchor="middle" fill="#7d8590" fontSize="10" fontFamily="monospace">Y / N</text>

                {/* Sandbox */}
                <rect x="600" y="260" width="220" height="50" rx="8" fill="#161b22" stroke="#ff4444" strokeWidth="1.5" />
                <text x="710" y="282" textAnchor="middle" fill="#ff4444" fontSize="12" fontWeight="bold" fontFamily="monospace">Sandbox</text>
                <text x="710" y="298" textAnchor="middle" fill="#7d8590" fontSize="9" fontFamily="monospace">seatbelt · landlock · win32</text>
              </svg>
              <p className="text-center text-xs text-muted-foreground font-mono mt-6">Rendered with APEX architecture standard syntax.</p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* PAGE LINKS */}
      <section className="py-20 bg-card/30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }} className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 font-mono">Explore APEX</h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">Dive deeper into every aspect of APEX — from agents and models to tools and security.</p>
          </motion.div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {PAGE_LINKS.map((link, i) => (
              <motion.a key={link.href} href={link.href} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.05 }} className="group p-5 rounded-xl border border-border/50 bg-card/30 hover:border-border hover:bg-card/50 transition-all duration-300">
                <link.icon className={`w-6 h-6 mb-3 ${link.color}`} />
                <h3 className="font-bold font-mono mb-1">{link.title}</h3>
                <p className="text-sm text-muted-foreground">{link.desc}</p>
                <ArrowRight className="w-4 h-4 mt-3 text-muted-foreground group-hover:text-apex-cyan transition-colors" />
              </motion.a>
            ))}
          </div>
        </div>
      </section>

      {/* ──── JOIN IN CTA ──── */}
      <section className="py-20 bg-[#0a0e14]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <div className="grid md:grid-cols-12 gap-10 md:gap-12">
              {/* Left */}
              <div className="md:col-span-5">
                <p className="eyebrow text-apex-cyan mb-4">Join in</p>
                <h2 className="text-3xl md:text-4xl font-bold font-mono mb-4">This is a small project.<br />Your patch matters.</h2>
                <p className="text-muted-foreground leading-relaxed">No CLA. No sponsor lockouts. The maintainer reads everything personally. Issues triaged in the open. Releases cut from main.</p>
              </div>
              {/* Right — 3 cards */}
              <div className="md:col-span-7">
                <div className="grid sm:grid-cols-3 gap-px bg-border/20 rounded-xl overflow-hidden">
                  <a href="https://github.com/Ggboykxz/APEX/issues" target="_blank" rel="noopener noreferrer" className="group p-6 bg-card/80 hover:bg-apex-cyan/10 transition-colors duration-300">
                    <h3 className="font-bold font-mono mb-2 group-hover:text-apex-cyan transition-colors">Open an issue</h3>
                    <p className="text-sm text-muted-foreground mb-4">Bug, feature, or just a sharp question.</p>
                    <span className="text-xs font-mono text-muted-foreground group-hover:text-apex-cyan transition-colors flex items-center gap-1">GitHub Issues <ExternalLink className="w-3 h-3" /></span>
                  </a>
                  <a href="/contribute" className="group p-6 bg-card/80 hover:bg-apex-cyan/10 transition-colors duration-300">
                    <h3 className="font-bold font-mono mb-2 group-hover:text-apex-cyan transition-colors">Send a PR</h3>
                    <p className="text-sm text-muted-foreground mb-4">Fork, branch, conventional commit, open PR.</p>
                    <span className="text-xs font-mono text-muted-foreground group-hover:text-apex-cyan transition-colors flex items-center gap-1">Contribute <ArrowRight className="w-3 h-3" /></span>
                  </a>
                  <a href="https://github.com/Ggboykxz/APEX/discussions" target="_blank" rel="noopener noreferrer" className="group p-6 bg-card/80 hover:bg-apex-cyan/10 transition-colors duration-300">
                    <h3 className="font-bold font-mono mb-2 group-hover:text-apex-cyan transition-colors">Start a discussion</h3>
                    <p className="text-sm text-muted-foreground mb-4">Roadmap, design, anything that&apos;s not a bug.</p>
                    <span className="text-xs font-mono text-muted-foreground group-hover:text-apex-cyan transition-colors flex items-center gap-1">GitHub Discussions <ExternalLink className="w-3 h-3" /></span>
                  </a>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ──── RICH 5-COLUMN FOOTER ──── */}
      <footer className="border-t border-border bg-card/30 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
          <div className="grid grid-cols-2 md:grid-cols-12 gap-8 md:gap-6">
            {/* Brand column */}
            <div className="col-span-2 md:col-span-4">
              <div className="flex items-center gap-3 mb-4">
                <span className="seal">△</span>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-5 h-5"><defs><linearGradient id="footer-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#footer-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#footer-grad)"/></svg>
                <span className="font-mono font-bold text-lg">APEX</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed mb-3">Universal AI coding agent. Proprietary licensed. Maintained from Gabon. Pull requests welcome.</p>
              <p className="text-xs text-muted-foreground font-mono">Made with care · Built in Africa 🇬🇦</p>
            </div>

            {/* Product */}
            <div className="md:col-span-2">
              <h4 className="font-bold font-mono text-sm mb-4">Product</h4>
              <ul className="space-y-2.5">
                <li><a href="/install" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Install</a></li>
                <li><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Documentation</a></li>
                <li><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Roadmap</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/releases" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Releases</a></li>
              </ul>
            </div>

            {/* Community */}
            <div className="md:col-span-2">
              <h4 className="font-bold font-mono text-sm mb-4">Community</h4>
              <ul className="space-y-2.5">
                <li><a href="https://github.com/Ggboykxz/APEX/issues" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Issues</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/pulls" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Pull Requests</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/discussions" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Discussions</a></li>
                <li><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Contribute</a></li>
                <li><a href="https://buymeacoffee.com/ggboykxz" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">Support APEX <Heart className="w-3 h-3 text-apex-pink" /></a></li>
              </ul>
            </div>

            {/* Resources */}
            <div className="md:col-span-2">
              <h4 className="font-bold font-mono text-sm mb-4">Resources</h4>
              <ul className="space-y-2.5">
                <li><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Activity Feed</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/CODE_OF_CONDUCT.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Code of Conduct</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/SECURITY.md" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Security</a></li>
                <li><a href="https://github.com/Ggboykxz/APEX/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors">License (Proprietary)</a></li>
              </ul>
            </div>

            {/* Social / Connect */}
            <div className="md:col-span-2">
              <h4 className="font-bold font-mono text-sm mb-4">Connect</h4>
              <ul className="space-y-2.5">
                <li><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5"><Github className="w-3.5 h-3.5" /> GitHub</a></li>
                <li><a href="https://buymeacoffee.com/ggboykxz" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5"><Heart className="w-3.5 h-3.5 text-apex-pink" /> Sponsor</a></li>
              </ul>
            </div>
          </div>
        </div>
        {/* Bottom bar */}
        <div className="border-t border-border/50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground font-mono">© 2026 · APEX · Ggboykxz</span>
            <span className="text-xs text-muted-foreground font-mono">Maintained with APEX</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
