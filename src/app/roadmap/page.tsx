'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Menu, X, GitBranch, Check, ArrowRight,
  Zap, Shield, Cpu, Eye, Bot, Wrench, BookOpen, Code2,
  Globe, Lock, Activity, Layers, Sparkles, Users
} from 'lucide-react'
import { Github } from "@/components/github-icon"

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
            <a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-apex-cyan">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a>
          </div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }, { href: '/roadmap', label: 'Roadmap' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() {
  return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">Proprietary — All rights reserved. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>)
}

const VERSIONS = [
  {
    version: 'v1.0.0', name: 'First Production Release', status: 'released' as const, progress: 100, color: '#00e5ff',
    desc: 'APEX — the universal AI coding agent built in Gabon 🇬🇦. 170+ models, 75+ tools, 11 specialized agents, Ink TUI, APEX Gateway, and production-ready security.',
    features: [
      { text: '170+ AI Models (Claude, GPT, Gemini, DeepSeek, Qwen, Llama, Mistral...)', done: true },
      { text: 'APEX Free (19 free coding models via OpenRouter — Qwen3 Coder 480B, Ring 2.6 1T, DeepSeek R1...)', done: true },
      { text: 'APEX Pro (10 frontier models — GLM-5.1, Kimi K2.6, MiniMax M2.7, DeepSeek V4 Pro...)', done: true },
      { text: 'APEX Gateway (built-in proxy with auth, rate limits, usage tracking, per-user API keys)', done: true },
      { text: 'Bring Your Own Key (Anthropic, OpenAI, Google, Ollama, or any litellm provider)', done: true },
      { text: 'Ink TUI (command palette Ctrl+P, leader keys Ctrl+X, @ file refs, !bash inline)', done: true },
      { text: '11 Specialized Agents (Build, Plan, Shell + @reviewer, @general, @explore, @scout + system)', done: true },
      { text: '75+ Built-in Tools (file ops, search, git, web, LSP, sandbox, clipboard, skills...)', done: true },
      { text: '12 Built-in Themes (apex, nord, catppuccin, tokyonight, gruvbox, matrix...)', done: true },
      { text: 'Git-based Snapshots with Undo/Redo', done: true },
      { text: 'Hierarchical JSON/JSONC Config (global → custom → project → inline)', done: true },
      { text: '20+ CLI Subcommands (auth, sessions, agents, MCP, plugins, gateway...)', done: true },
      { text: '56 HTTP API Endpoints for remote operation', done: true },
      { text: 'Session Sharing (public URLs with automatic secret sanitization)', done: true },
      { text: 'File Watcher with gitignore-aware patterns', done: true },
      { text: '11 Auto-Formatters (ruff, prettier, gofmt, rustfmt...)', done: true },
      { text: 'Custom Commands via markdown ($ARGUMENTS, !shell, @file)', done: true },
      { text: 'MCP Support (Model Context Protocol)', done: true },
      { text: 'LSP Integration (Language Server Protocol for code intelligence)', done: true },
      { text: 'Shell Command Analysis & Security', done: true },
      { text: 'Permission Ruleset System (ALLOW/DENY/ASK)', done: true },
      { text: 'Rate Limiting + API Key Management + Billing', done: true },
      { text: 'Cross-platform: Linux, macOS, Windows (WSL)', done: true },
    ]
  },
  {
    version: 'v2.0.0', name: 'OpenCode Architecture', status: 'released' as const, progress: 100, color: '#ffaa00',
    desc: 'OpenCode-inspired TUI architecture with WebSocket EventBus, random port binding, 12 bug fixes, TUI audit fixes, and dependency cleanup.',
    features: [
      { text: 'WebSocket EventBus for real-time TUI-backend synchronization', done: true },
      { text: 'Random port binding (no more port 8080 conflicts)', done: true },
      { text: 'State directory with port discovery (~/.apex/state/)', done: true },
      { text: '12 bug fixes (Fernet encryption, symlink race, glob paths, shell security, etc.)', done: true },
      { text: 'TUI audit fixes (8 missing API routes, React 18, Ink subprocess, CORS)', done: true },
      { text: '10 Dependabot PRs merged, 7 dangerous PRs closed', done: true },
      { text: 'All 10 CI workflows passing', done: true },
      { text: 'Node.js 24 in all workflows', done: true },
    ]
  },
  {
    version: 'v2.5.0', name: 'Intelligence', status: 'planned' as const, progress: 10, color: '#ffaa00',
    desc: 'Intelligence features — repo mapping, vision, auto-commit, VS Code extension, MCP server mode.',
    features: [
      { text: 'Repository Map & Code Understanding', done: false },
      { text: 'Vision Model Support (image analysis)', done: false },
      { text: 'Auto-commit with Generated Messages', done: false },
      { text: 'VS Code Extension', done: false },
      { text: 'MCP Server Mode (expose APEX as MCP server)', done: false },
      { text: 'Multi-file Editing with Diff Preview', done: false },
      { text: 'Context Window Optimization', done: false },
      { text: 'Custom Skill Templates', done: false },
    ]
  },
]

export default function RoadmapPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        {/* Header */}
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="absolute inset-0 radial-gradient" />
          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Roadmap</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">From <span className="animated-gradient-text">Foundation</span> to Intelligence</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Our journey from v1.0.0 First Production Release through v2.0.0 OpenCode Architecture to v2.5.0 Intelligence. Every milestone brings APEX closer to being the last coding agent you&apos;ll ever need.</p>
            </motion.div>
          </div>
        </section>

        {/* Timeline */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <div className="space-y-8">
              {VERSIONS.map((v, i) => (
                <motion.div key={v.version} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}>
                  <div className="p-6 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: v.color, borderLeftWidth: 4 }}>
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold font-mono" style={{ color: v.color }}>{v.version}</span>
                        <span className="text-lg font-bold font-mono text-foreground">{v.name}</span>
                        {v.status === 'released' && <span className="px-2 py-0.5 rounded text-xs font-mono bg-apex-green/10 text-apex-green border border-apex-green/20">Released</span>}
                        {v.status === 'next' && <span className="px-2 py-0.5 rounded text-xs font-mono bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20">In Progress</span>}
                        {v.status === 'planned' && <span className="px-2 py-0.5 rounded text-xs font-mono bg-muted/50 text-muted-foreground border border-border">Planned</span>}
                      </div>
                      <span className="text-sm font-mono text-muted-foreground">{v.progress}% complete</span>
                    </div>

                    {/* Progress bar */}
                    <div className="h-2 rounded-full bg-card mb-4 overflow-hidden">
                      <motion.div initial={{ width: 0 }} whileInView={{ width: `${v.progress}%` }} viewport={{ once: true }} transition={{ duration: 1, delay: 0.3 }} className="h-full rounded-full" style={{ backgroundColor: v.color }} />
                    </div>

                    <p className="text-sm text-muted-foreground mb-4 leading-relaxed">{v.desc}</p>

                    {/* Features */}
                    <div className="grid sm:grid-cols-2 gap-2">
                      {v.features.map((f, j) => (
                        <div key={j} className="flex items-start gap-2 text-sm">
                          {f.done ? <Check className="w-4 h-4 text-apex-green shrink-0 mt-0.5" /> : <div className="w-4 h-4 rounded border border-border/50 shrink-0 mt-0.5" />}
                          <span className={f.done ? 'text-foreground' : 'text-muted-foreground'}>{f.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* What's Next Highlight */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Sparkles className="w-6 h-6 text-apex-green" /> What&apos;s Coming Next</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="p-5 rounded-xl border border-apex-green/20 bg-apex-green/5">
                <h3 className="font-bold font-mono text-apex-green mb-2">Streaming Responses</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">See AI responses in real-time as they stream token by token. No more waiting for the full response — start reading and acting immediately.</p>
              </div>
              <div className="p-5 rounded-xl border border-apex-green/20 bg-apex-green/5">
                <h3 className="font-bold font-mono text-apex-green mb-2">Persistent Memory</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">APEX will remember context across sessions. Store project facts, preferences, and decisions that persist between conversations.</p>
              </div>
              <div className="p-5 rounded-xl border border-apex-green/20 bg-apex-green/5">
                <h3 className="font-bold font-mono text-apex-green mb-2">Web Search Integration</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">Search the web and fetch URLs directly from APEX. Look up documentation, find solutions, and browse APIs without leaving the terminal.</p>
              </div>
              <div className="p-5 rounded-xl border border-apex-green/20 bg-apex-green/5">
                <h3 className="font-bold font-mono text-apex-green mb-2">Enhanced Git Tools</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">Create PRs, manage stashes, rebase branches, and resolve merge conflicts — all from within APEX with AI-powered conflict resolution.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Looking Ahead */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Eye className="w-6 h-6 text-apex-cyan" /> Looking Ahead</h2>
            <div className="space-y-4">
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#ffaa00', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#ffaa00] mb-2">v2.5.0 — Intelligence</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">The Intelligence release will bring repo-level understanding, vision model support for analyzing screenshots and diagrams, auto-commit with generated messages, and a VS Code extension that integrates APEX into your IDE workflow. The MCP Server mode will allow other tools to communicate with APEX programmatically.</p>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#d946ef', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#d946ef] mb-2">v3.0.0 — Enterprise</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">The Enterprise release targets organizations with automated test suite generation, native installers for Windows and macOS, SSO integration, and APEX Cloud — a hosted version of APEX that runs in the cloud with team collaboration features, audit logging, and compliance reporting.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Contribute CTA */}
        <section className="py-16 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
            <h2 className="text-2xl font-bold font-mono mb-4">Help Shape the Future</h2>
            <p className="text-muted-foreground mb-6">APEX welcomes contributions. Every contribution moves the roadmap forward — from bug fixes to major features.</p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <a href="/contribute" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-apex-cyan text-background font-medium hover:bg-apex-cyan/90 transition-colors"><Users className="w-4 h-4" /> Contribute</a>
              <a href="https://github.com/Ggboykxz/APEX/blob/main/ROADMAP.md" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><GitBranch className="w-4 h-4" /> View ROADMAP.md</a>
              <a href="https://github.com/Ggboykxz/APEX/issues" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-foreground font-medium hover:bg-card transition-colors"><Github className="w-4 h-4" /> Open an Issue</a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
