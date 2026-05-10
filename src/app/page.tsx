'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import {
  Terminal, Zap, Shield, Bot, Copy, Check, ArrowRight,
  Github, Cpu, Wrench, Users, Star, Lock,
  Activity, Radio, Loader2, Menu, X, Code2, Eye, Search, Layers,
  GitBranch, Globe, FileCode, Play, Command, Clock, Sparkles, BookOpen,
  CircleDot, GitPullRequest, Tag, Box
} from 'lucide-react'

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

const STATS = [
  { value: '100+', label: 'Models Supported', icon: Cpu },
  { value: '75+', label: 'Built-in Tools', icon: Wrench },
  { value: '5', label: 'Specialized Agents', icon: Bot },
  { value: '1,148', label: 'Tests Passing', icon: Check },
  { value: '20+', label: 'Slash Commands', icon: Terminal },
  { value: '14', label: 'Install Methods', icon: Box },
]

const PAGE_LINKS = [
  { href: '/agents', icon: Bot, title: 'Agents', desc: '5 specialized agents with permission controls', color: 'text-apex-cyan' },
  { href: '/models', icon: Cpu, title: 'Models', desc: '100+ models from every major provider', color: 'text-apex-green' },
  { href: '/tools', icon: Wrench, title: 'Tools', desc: '75+ built-in tools for every workflow', color: 'text-apex-yellow' },
  { href: '/install', icon: Box, title: 'Install', desc: '14 installation methods for every platform', color: 'text-apex-cyan' },
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
  return <span ref={ref} className="animated-gradient-text font-bold">{prefix}{count}{suffix}</span>
}

function NavBar({ scrolled, mobileMenuOpen, setMobileMenuOpen, apiStatus }: {
  scrolled: boolean; mobileMenuOpen: boolean; setMobileMenuOpen: (v: boolean) => void; apiStatus: 'online' | 'offline' | 'loading'
}) {
  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-background/80 backdrop-blur-xl border-b border-border' : 'bg-transparent'}`}>
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
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className={`w-1.5 h-1.5 rounded-full pulse-dot ${apiStatus === 'online' ? 'bg-apex-green' : apiStatus === 'offline' ? 'bg-apex-red' : 'bg-apex-yellow'}`} />
              <span className={apiStatus === 'online' ? 'text-apex-green' : apiStatus === 'offline' ? 'text-apex-red' : 'text-apex-yellow'}>API · {apiStatus === 'online' ? 'Online' : apiStatus === 'offline' ? 'Offline' : 'Sync'}</span>
            </div>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"><Github className="w-4 h-4" /> GitHub</a>
            <a href="#install" className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-apex-cyan text-background text-sm font-medium hover:bg-apex-cyan/90 transition-colors"><ArrowRight className="w-3.5 h-3.5" /> Install</a>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <span className={`w-1.5 h-1.5 rounded-full pulse-dot ${apiStatus === 'online' ? 'bg-apex-green' : apiStatus === 'offline' ? 'bg-apex-red' : 'bg-apex-yellow'}`} />
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

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar scrolled={scrolled} mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} apiStatus={apiStatus} />

      {/* LIVE TICKER */}
      <div className="relative pt-16">
        <div className="bg-card/80 border-b border-border/50 overflow-hidden">
          <div className="flex items-center">
            <div className="shrink-0 px-3 py-2 bg-apex-cyan/10 border-r border-border/50 flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-apex-cyan" /><span className="text-xs font-mono font-bold text-apex-cyan uppercase">Live</span>
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
              <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />v1.3.0 — Security System Released
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold font-mono leading-tight mb-6">
              The Universal <span className="animated-gradient-text">AI Coding</span><br />Agent
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Every model. One terminal. APEX runs in your terminal with 100+ models, 75+ tools, and 5 built-in agents. Switch models mid-session. Never leave your terminal.
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
                <span className="flex items-center gap-1.5"><Star className="w-3.5 h-3.5 text-apex-yellow" /> MIT Licensed</span>
                <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5 text-apex-cyan" /> Built in Africa 🇬🇦</span>
                <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-apex-green" /> Security First</span>
              </div>
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
              <div className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground font-mono"><span className="text-apex-cyan">build</span><span className="text-muted-foreground">•</span><span>claude-4-sonnet</span></div>
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
                <div className="text-2xl font-bold font-mono"><AnimatedCounter value={stat.value} /></div>
                <div className="text-xs text-muted-foreground font-mono mt-1">{stat.label}</div>
              </motion.div>
            ))}
          </div>
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
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">APEX combines the power of 100+ models, 75+ tools, and 5 specialized agents in one terminal-native experience.</p>
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

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
            <h2 className="text-3xl md:text-5xl font-bold font-mono mb-6">Ready to <span className="animated-gradient-text">APEX</span>?</h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-xl mx-auto leading-relaxed">The last coding agent you&apos;ll ever need. Install in 30 seconds and start coding with any model.</p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <a href="/install" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-apex-cyan text-background font-medium hover:bg-apex-cyan/90 transition-colors"><Zap className="w-4 h-4" /> Install Now</a>
              <a href="/docs" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><BookOpen className="w-4 h-4" /> Read the Docs</a>
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><Github className="w-4 h-4" /> View Source</a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-border py-8 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-5 h-5"><defs><linearGradient id="footer-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#footer-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#footer-grad)"/></svg>
              <span className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></span>
            </div>
            <div className="flex items-center gap-6">
              <a href="/docs" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Docs</a>
              <a href="/install" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Install</a>
              <a href="/agents" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Agents</a>
              <a href="/models" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Models</a>
              <a href="/tools" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Tools</a>
              <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
