'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ArrowRight,
  Bot, Code2, Eye, Search, Layers, Zap, Shield, Cpu,
  Wrench, BookOpen, Activity, GitBranch, Users, Hash
} from 'lucide-react'

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg><span className="font-mono font-bold text-lg">APEX</span></a>
          <div className="hidden md:flex items-center gap-5"><a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-apex-cyan">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() { return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>) }

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (<div className="relative group my-3 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden"><div className="flex items-center justify-between px-4 py-2 border-b border-border/30"><span className="text-xs text-muted-foreground font-mono">{language}</span><button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button></div><pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre></div>)
}

const AGENTS = [
  {
    name: 'Build', mode: 'Primary', color: '#00e5ff', icon: Code2,
    access: 'Full (read/edit/bash/web)', default: true,
    desc: 'Your primary coding agent. Reads, writes, executes, and browses — the full stack. It handles file operations, code editing, command execution, web searches, and package management.',
    capabilities: ['Write, edit, and delete files', 'Run shell commands and tests', 'Search and analyze code', 'Install packages and format code', 'Browse the web for documentation', 'Create git commits and PRs'],
    switch: '/agent build  or press Tab',
    workflow: 'Use the Build agent for everyday coding tasks — fixing bugs, adding features, refactoring code, and running tests. It has full access to all tools.',
  },
  {
    name: 'Plan', mode: 'Primary', color: '#ffaa00', icon: Eye,
    access: 'Read-only (analysis & planning)', default: false,
    desc: 'Analyzes your codebase and creates detailed implementation plans before any code is written. Perfect for complex features that need careful thought before execution.',
    capabilities: ['Read and analyze all files', 'Search code patterns', 'Create detailed implementation plans', 'Suggest improvements and refactoring', 'Identify potential issues', 'Map project dependencies'],
    switch: '/agent plan',
    workflow: 'Switch to Plan when you need to understand a codebase before making changes. It will read files, analyze patterns, and produce a step-by-step plan.',
  },
  {
    name: 'Explore', mode: 'Subagent', color: '#00ff88', icon: Search,
    access: 'Read-only (fast exploration)', default: false,
    desc: 'Quickly navigates and searches your codebase to find answers. Optimized for speed — it finds files, searches patterns, and returns results fast.',
    capabilities: ['Find files by name pattern', 'Search code for keywords and regex', 'Show directory structure', 'Analyze git history', 'Read specific files quickly', 'Locate function and class definitions'],
    switch: '@explore "your search query"',
    workflow: 'Invoke Explore as a subagent when you need quick answers: "Find all TODO comments", "Where is the authentication logic?", "Show me all Python files in src/".',
  },
  {
    name: 'General', mode: 'Subagent', color: '#d946ef', icon: Layers,
    access: 'Full (complex multi-step)', default: false,
    desc: 'Handles complex multi-step tasks that need careful orchestration. Perfect for tasks requiring coordination across multiple files and tools.',
    capabilities: ['Coordinate multi-file operations', 'Execute complex workflows', 'Research and analyze code', 'Implement changes across the codebase', 'Run and fix test suites', 'Handle long-running tasks'],
    switch: '@general "your complex task"',
    workflow: 'Use General for complex tasks: "Refactor the entire auth module", "Add logging to all API endpoints", "Set up the test infrastructure".',
  },
  {
    name: 'YOLO', mode: 'Primary', color: '#ff4444', icon: Zap,
    access: 'Full + auto-approve', default: false,
    desc: 'Autonomous mode with auto-approve enabled. It moves fast and doesn\'t ask for confirmation — perfect for tasks you trust the AI to handle independently.',
    capabilities: ['All Build agent capabilities', 'Auto-approve all tool calls', 'No confirmation prompts', 'Maximum execution speed', 'Autonomous bug fixing', 'Batch operations without interruption'],
    switch: '/agent yolo',
    workflow: 'Use YOLO when you want APEX to work autonomously: "Fix all linting errors", "Update all dependencies", "Run the full test suite and fix failures".',
  },
]

const PERMISSION_MATRIX = [
  { tool: 'read', tools: 'read_file, list_files, search_in_files, glob_search', build: 'allow', plan: 'allow', explore: 'allow', general: 'allow', yolo: 'allow' },
  { tool: 'edit', tools: 'write_file, edit_file, delete_file', build: 'allow', plan: 'deny', explore: 'deny', general: 'allow', yolo: 'allow' },
  { tool: 'bash', tools: 'run_command', build: 'ask', plan: 'deny', explore: 'deny', general: 'ask', yolo: 'allow' },
  { tool: 'websearch', tools: 'web_search, fetch_url', build: 'ask', plan: 'allow', explore: 'deny', general: 'allow', yolo: 'allow' },
  { tool: 'task', tools: 'subagent invocation', build: 'ask', plan: 'deny', explore: 'deny', general: 'ask', yolo: 'allow' },
]

export default function AgentsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="absolute inset-0 radial-gradient" />
          <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Multi-Agent System</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4"><span className="animated-gradient-text">5 Specialized</span> Agents</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Each agent is configured for specific tasks with granular permission controls. Switch agents mid-session or invoke subagents inline.</p>
            </motion.div>
          </div>
        </section>

        {/* Agent Cards */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-8">
            {AGENTS.map((agent, i) => (
              <motion.div key={agent.name} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}>
                <div className="p-6 md:p-8 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: agent.color, borderLeftWidth: 4 }}>
                  <div className="flex flex-col md:flex-row md:items-start gap-6">
                    <div className="shrink-0">
                      <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${agent.color}15`, border: `1px solid ${agent.color}30` }}>
                        <agent.icon className="w-7 h-7" style={{ color: agent.color }} />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-3 mb-2">
                        <h3 className="text-2xl font-bold font-mono" style={{ color: agent.color }}>{agent.name} Agent</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-mono ${agent.mode === 'Primary' ? 'bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20' : 'bg-apex-magenta/10 text-apex-magenta border border-apex-magenta/20'}`}>{agent.mode}</span>
                        {agent.default && <span className="px-2 py-0.5 rounded text-xs font-mono bg-apex-green/10 text-apex-green border border-apex-green/20">Default</span>}
                      </div>
                      <p className="text-muted-foreground text-sm mb-1"><strong className="text-foreground">Access:</strong> {agent.access}</p>
                      <p className="text-muted-foreground text-sm leading-relaxed mb-4">{agent.desc}</p>

                      <div className="grid sm:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-bold font-mono text-sm mb-2" style={{ color: agent.color }}>Capabilities</h4>
                          <ul className="space-y-1.5">
                            {agent.capabilities.map(c => (
                              <li key={c} className="flex items-start gap-2 text-sm text-muted-foreground"><ArrowRight className="w-3 h-3 shrink-0 mt-1.5" style={{ color: agent.color }} />{c}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <h4 className="font-bold font-mono text-sm mb-2" style={{ color: agent.color }}>How to Use</h4>
                          <CodeBlock code={agent.switch} />
                          <h4 className="font-bold font-mono text-sm mb-2 mt-4" style={{ color: agent.color }}>Workflow</h4>
                          <p className="text-sm text-muted-foreground leading-relaxed">{agent.workflow}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Permission Matrix */}
        <section className="py-12 bg-card/30">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Shield className="w-6 h-6 text-apex-cyan" /> Permission Matrix</h2>
            <p className="text-muted-foreground mb-6">Each agent has different permission levels for each tool category. Values: <code className="text-apex-green">allow</code> (always permit), <code className="text-apex-yellow">ask</code> (prompt user), <code className="text-apex-red">deny</code> (block).</p>
            <div className="overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 bg-card/50">
                    <th className="text-left p-3 font-mono text-muted-foreground">Permission</th>
                    <th className="text-left p-3 font-mono text-muted-foreground">Tools</th>
                    <th className="text-center p-3 font-mono text-muted-foreground">Build</th>
                    <th className="text-center p-3 font-mono text-muted-foreground">Plan</th>
                    <th className="text-center p-3 font-mono text-muted-foreground">Explore</th>
                    <th className="text-center p-3 font-mono text-muted-foreground">General</th>
                    <th className="text-center p-3 font-mono text-muted-foreground">YOLO</th>
                  </tr>
                </thead>
                <tbody>
                  {PERMISSION_MATRIX.map((row, i) => (
                    <tr key={row.tool} className={`border-b border-border/30 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
                      <td className="p-3 font-mono font-bold text-foreground">{row.tool}</td>
                      <td className="p-3 font-mono text-muted-foreground text-xs">{row.tools}</td>
                      {[row.build, row.plan, row.explore, row.general, row.yolo].map((val, j) => (
                        <td key={j} className="p-3 text-center font-mono"><span className={`px-2 py-0.5 rounded text-xs ${val === 'allow' ? 'bg-apex-green/10 text-apex-green' : val === 'ask' ? 'bg-apex-yellow/10 text-apex-yellow' : 'bg-apex-red/10 text-apex-red'}`}>{val}</span></td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Switching Methods */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Zap className="w-6 h-6 text-apex-cyan" /> Switching Methods</h2>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">Slash Command</h3>
                <CodeBlock code="/agent build\n/agent plan\n/agent yolo" />
                <p className="text-sm text-muted-foreground mt-2">Type <code className="text-apex-cyan">/agent</code> followed by the agent name.</p>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">Tab Key</h3>
                <CodeBlock language="text" code="Press Tab to cycle\nthrough primary agents" />
                <p className="text-sm text-muted-foreground mt-2">Quickly cycle between Build, Plan, and YOLO.</p>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">@Mention</h3>
                <CodeBlock code='@explore "find TODO comments"\n@general "refactor auth"' />
                <p className="text-sm text-muted-foreground mt-2">Invoke subagents inline with @mention.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Custom Agent Creation */}
        <section className="py-12 bg-card/30">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Bot className="w-6 h-6 text-apex-cyan" /> Custom Agent Creation</h2>
            <p className="text-muted-foreground mb-6">Create custom agents with specific permissions and system prompts in your configuration file.</p>
            <CodeBlock language="yaml" code={`# .apex/config.yaml\nagents:\n  # Code Reviewer - read-only, focused on security\n  reviewer:\n    description: Code review agent focused on security\n    mode: subagent\n    permission:\n      read: allow\n      edit: deny\n      bash: deny\n      websearch: allow\n    prompt: |\n      You are a code reviewer focused on security vulnerabilities.\n      Always check for: SQL injection, XSS, CSRF, auth issues.\n      Provide specific line numbers and fixes.\n\n  # Test Writer - can write test files only\n  test-writer:\n    description: Writes comprehensive test suites\n    mode: subagent\n    permission:\n      read: allow\n      edit: allow      # Can write test files\n      bash: allow      # Can run tests\n      websearch: deny\n    prompt: |\n      You are a test writing specialist.\n      Write comprehensive pytest test suites.\n      Aim for 90%+ coverage on all new code.\n      Use fixtures, parametrize, and mocking.\n\n  # DevOps Agent - handles infrastructure\n  devops:\n    description: DevOps and deployment agent\n    mode: primary\n    permission:\n      read: allow\n      edit: ask\n      bash: ask\n      websearch: allow\n    prompt: |\n      You are a DevOps specialist.\n      Help with CI/CD, Docker, Kubernetes, and cloud deployments.\n      Always explain what each command does before running.`} />
          </div>
        </section>

        {/* Best Practices */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><BookOpen className="w-6 h-6 text-apex-cyan" /> Best Practices</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { title: 'Plan Before Building', desc: 'Use the Plan agent first for complex features. It analyzes your codebase and creates a step-by-step plan before any code is written.' },
                { title: 'Use YOLO Sparingly', desc: 'YOLO mode is powerful but risky. Use it for well-defined, trusted tasks like fixing lint errors or running test suites.' },
                { title: 'Leverage Subagents', desc: 'Use @explore for quick lookups and @general for complex research. This keeps your main conversation focused.' },
                { title: 'Configure Permissions', desc: 'Customize the permission matrix for your security needs. Use "ask" mode for sensitive operations and "deny" for destructive ones.' },
                { title: 'Switch Contextually', desc: 'Switch to Plan for analysis, Build for implementation, and Explore for research. Each agent is optimized for its domain.' },
                { title: 'Create Custom Agents', desc: 'Define custom agents for repeated workflows. A "reviewer" agent or "test-writer" agent saves time on common tasks.' },
              ].map(bp => (
                <div key={bp.title} className="p-4 rounded-lg border border-border/50 bg-card/30">
                  <h4 className="font-bold font-mono text-apex-cyan mb-1">{bp.title}</h4>
                  <p className="text-sm text-muted-foreground">{bp.desc}</p>
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
