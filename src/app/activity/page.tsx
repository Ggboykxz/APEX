'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Activity, Radio, Loader2,
  CircleDot, GitPullRequest, Tag, GitCommit, Star, Users,
  GitBranch, Zap, Clock, MessageSquare, Megaphone, BookOpen,
  Cpu, Wrench, Bot, Shield, Filter
} from 'lucide-react'

interface GitHubRepoData { stargazers_count: number; forks_count: number; open_issues_count: number; subscribers_count: number; contributors: number; latest_release: { tag_name: string; published_at: string } | null }
interface GitHubIssue { number: number; title: string; state: 'open' | 'closed'; created_at: string; user: { login: string }; labels: { name: string; color: string }[] }
interface GitHubPullRequest { number: number; title: string; state: 'open' | 'closed'; merged_at: string | null; created_at: string; user: { login: string }; labels: { name: string; color: string }[] }
interface GitHubRelease { tag_name: string; name: string; published_at: string; body: string }
interface GitHubData { repo: GitHubRepoData | null; issues: GitHubIssue[]; pullRequests: GitHubPullRequest[]; releases: GitHubRelease[] }

function timeAgo(d: string): string {
  const diff = Date.now() - new Date(d).getTime()
  const s = Math.floor(diff / 1000), m = Math.floor(s / 60), h = Math.floor(m / 60), dy = Math.floor(h / 24), w = Math.floor(dy / 7), mo = Math.floor(dy / 30)
  if (s < 60) return `${s}s`; if (m < 60) return `${m}m`; if (h < 24) return `${h}h`; if (dy < 7) return `${dy}d`; if (w < 5) return `${w}w`; return `${mo}mo`
}

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg>
            <span className="font-mono font-bold text-lg">APEX</span>
          </a>
          <div className="hidden md:flex items-center gap-5">
            <a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-apex-cyan">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a>
          </div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }, { href: '/activity', label: 'Activity' }, { href: '/roadmap', label: 'Roadmap' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() {
  return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>)
}

export default function ActivityPage() {
  const [githubData, setGithubData] = useState<GitHubData | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'issues' | 'prs' | 'releases'>('all')

  useEffect(() => {
    let m = true
    const f = async () => { try { const r = await fetch('/api/github'); if (!r.ok) throw new Error(); const d: GitHubData = await r.json(); if (m) { setGithubData(d); setLoading(false) } } catch { if (m) setLoading(false) } }
    f(); const i = setInterval(f, 300000); return () => { m = false; clearInterval(i) }
  }, [])

  const filteredIssues = filter === 'all' || filter === 'issues' ? githubData?.issues ?? [] : []
  const filteredPRs = filter === 'all' || filter === 'prs' ? githubData?.pullRequests ?? [] : []
  const filteredReleases = filter === 'all' || filter === 'releases' ? githubData?.releases ?? [] : []

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        {/* Header */}
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Live Activity</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Project <span className="animated-gradient-text">Activity</span></h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Real-time issues, pull requests, and releases from the APEX repository.</p>
            </motion.div>
          </div>
        </section>

        {/* Live Ticker */}
        <div className="bg-card/80 border-b border-border/50 overflow-hidden">
          <div className="max-w-6xl mx-auto flex items-center">
            <div className="shrink-0 px-3 py-2 bg-apex-cyan/10 border-r border-border/50 flex items-center gap-1.5"><Radio className="w-3 h-3 text-apex-cyan" /><span className="text-xs font-mono font-bold text-apex-cyan uppercase">Live</span></div>
            <div className="overflow-hidden flex-1">
              {loading ? <div className="px-4 py-2"><Loader2 className="w-3 h-3 text-muted-foreground animate-spin inline" /><span className="text-xs text-muted-foreground font-mono ml-2">Syncing...</span></div> : githubData ? (
                <div className="ticker-track">
                  {[...githubData.issues.slice(0, 5), ...githubData.pullRequests.slice(0, 5), ...githubData.releases.slice(0, 3), ...githubData.issues.slice(0, 5), ...githubData.pullRequests.slice(0, 5), ...githubData.releases.slice(0, 3)].map((item, i) => {
                    const isIssue = 'state' in item && !('merged_at' in item)
                    const isPR = 'merged_at' in item
                    const isRelease = 'tag_name' in item && 'body' in item
                    return (
                      <a key={i} href={isRelease ? `https://github.com/Ggboykxz/APEX/releases/tag/${(item as GitHubRelease).tag_name}` : `https://github.com/Ggboykxz/APEX/issues/${(item as GitHubIssue | GitHubPullRequest).number}`} target="_blank" rel="noopener noreferrer" className="shrink-0 flex items-center gap-2 px-4 py-2 hover:bg-card transition-colors border-r border-border/30">
                        {isIssue && <><CircleDot className={`w-3 h-3 ${(item as GitHubIssue).state === 'open' ? 'text-apex-green' : 'text-apex-red'}`} /><span className="text-xs font-mono text-muted-foreground">ISS #{(item as GitHubIssue).number}</span><span className="text-xs text-foreground truncate max-w-[200px]">{(item as GitHubIssue).title}</span></>}
                        {isPR && <><GitPullRequest className={`w-3 h-3 ${(item as GitHubPullRequest).merged_at ? 'text-apex-magenta' : 'text-apex-green'}`} /><span className="text-xs font-mono text-muted-foreground">PR #{(item as GitHubPullRequest).number}</span><span className="text-xs text-foreground truncate max-w-[200px]">{(item as GitHubPullRequest).title}</span></>}
                        {isRelease && <><Tag className="w-3 h-3 text-apex-cyan" /><span className="text-xs font-mono text-apex-cyan">{(item as GitHubRelease).tag_name}</span></>}
                      </a>
                    )
                  })}
                </div>
              ) : <div className="px-4 py-2 text-xs text-muted-foreground font-mono">Unable to load</div>}
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="py-6 border-b border-border/50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {(githubData?.repo ? [
                { icon: Star, label: 'Stars', value: githubData.repo.stargazers_count, color: 'text-apex-yellow' },
                { icon: GitBranch, label: 'Forks', value: githubData.repo.forks_count, color: 'text-apex-cyan' },
                { icon: CircleDot, label: 'Open Issues', value: githubData.repo.open_issues_count, color: 'text-apex-green' },
                { icon: Users, label: 'Subscribers', value: githubData.repo.subscribers_count, color: 'text-apex-magenta' },
              ] : [
                { icon: Star, label: 'Stars', value: '—', color: 'text-apex-yellow' },
                { icon: GitBranch, label: 'Forks', value: '—', color: 'text-apex-cyan' },
                { icon: CircleDot, label: 'Open Issues', value: '—', color: 'text-apex-green' },
                { icon: Users, label: 'Subscribers', value: '—', color: 'text-apex-magenta' },
              ]).map(s => (
                <div key={s.label} className="flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-card/30">
                  <s.icon className={`w-5 h-5 ${s.color}`} />
                  <div><div className="text-lg font-bold font-mono">{s.value}</div><div className="text-xs text-muted-foreground font-mono">{s.label}</div></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Filter */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center gap-2 mb-6">
            <Filter className="w-4 h-4 text-muted-foreground" />
            {(['all', 'issues', 'prs', 'releases'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1.5 rounded-lg text-sm font-mono transition-all ${filter === f ? 'bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20' : 'text-muted-foreground hover:text-foreground hover:bg-card'}`}>
                {f === 'all' ? 'All' : f === 'issues' ? 'Issues' : f === 'prs' ? 'Pull Requests' : 'Releases'}
              </button>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Issues */}
            {(filter === 'all' || filter === 'issues') && (
              <div>
                <h2 className="text-xl font-bold font-mono mb-4 flex items-center gap-2"><CircleDot className="w-5 h-5 text-apex-green" /> Issues <span className="text-sm text-muted-foreground font-normal">({filteredIssues.length})</span></h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {loading ? <div className="text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading...</div> : filteredIssues.map(issue => (
                    <a key={issue.number} href={`https://github.com/Ggboykxz/APEX/issues/${issue.number}`} target="_blank" rel="noopener noreferrer" className="block p-4 rounded-lg border border-border/50 bg-card/30 hover:border-border transition-all">
                      <div className="flex items-center gap-2 mb-2"><CircleDot className={`w-3.5 h-3.5 ${issue.state === 'open' ? 'text-apex-green' : 'text-apex-red'}`} /><span className="text-xs font-mono text-muted-foreground">#{issue.number}</span><span className="text-xs font-mono text-muted-foreground">•</span><span className="text-xs font-mono text-muted-foreground">{timeAgo(issue.created_at)}</span></div>
                      <h3 className="text-sm font-medium leading-snug mb-2">{issue.title}</h3>
                      <div className="flex items-center gap-2"><span className="text-xs text-muted-foreground">by <span className="text-foreground">{issue.user.login}</span></span>{issue.labels.length > 0 && issue.labels.map((l, i) => <span key={i} className="text-xs px-1.5 py-0.5 rounded border border-border/50 font-mono" style={{ borderColor: `#${l.color}40`, color: `#${l.color}` }}>{l.name}</span>)}</div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* PRs */}
            {(filter === 'all' || filter === 'prs') && (
              <div>
                <h2 className="text-xl font-bold font-mono mb-4 flex items-center gap-2"><GitPullRequest className="w-5 h-5 text-apex-magenta" /> Pull Requests <span className="text-sm text-muted-foreground font-normal">({filteredPRs.length})</span></h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {loading ? <div className="text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading...</div> : filteredPRs.map(pr => (
                    <a key={pr.number} href={`https://github.com/Ggboykxz/APEX/pull/${pr.number}`} target="_blank" rel="noopener noreferrer" className="block p-4 rounded-lg border border-border/50 bg-card/30 hover:border-border transition-all">
                      <div className="flex items-center gap-2 mb-2"><GitPullRequest className={`w-3.5 h-3.5 ${pr.merged_at ? 'text-apex-magenta' : pr.state === 'open' ? 'text-apex-green' : 'text-apex-red'}`} /><span className="text-xs font-mono text-muted-foreground">#{pr.number}</span><span className="text-xs font-mono text-muted-foreground">•</span><span className="text-xs font-mono text-muted-foreground">{timeAgo(pr.created_at)}</span>{pr.merged_at && <span className="text-xs font-mono text-apex-magenta">merged</span>}</div>
                      <h3 className="text-sm font-medium leading-snug mb-2">{pr.title}</h3>
                      <span className="text-xs text-muted-foreground">by <span className="text-foreground">{pr.user.login}</span></span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Releases */}
            {(filter === 'all' || filter === 'releases') && (
              <div>
                <h2 className="text-xl font-bold font-mono mb-4 flex items-center gap-2"><Tag className="w-5 h-5 text-apex-cyan" /> Releases <span className="text-sm text-muted-foreground font-normal">({filteredReleases.length})</span></h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {loading ? <div className="text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading...</div> : filteredReleases.map(rel => (
                    <a key={rel.tag_name} href={`https://github.com/Ggboykxz/APEX/releases/tag/${rel.tag_name}`} target="_blank" rel="noopener noreferrer" className="block p-4 rounded-lg border border-border/50 bg-card/30 hover:border-border transition-all">
                      <div className="flex items-center gap-2 mb-2"><Tag className="w-3.5 h-3.5 text-apex-cyan" /><span className="text-sm font-mono font-bold text-apex-cyan">{rel.tag_name}</span><span className="text-xs font-mono text-muted-foreground">•</span><span className="text-xs font-mono text-muted-foreground">{timeAgo(rel.published_at)}</span></div>
                      <h3 className="text-sm font-medium leading-snug mb-2">{rel.name || 'Release'}</h3>
                      <p className="text-xs text-muted-foreground line-clamp-3">{rel.body?.substring(0, 200)}{rel.body && rel.body.length > 200 ? '...' : ''}</p>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Link to GitHub */}
          <div className="mt-12 text-center">
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><Github className="w-4 h-4" /> View on GitHub</a>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
