'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ChevronRight,
  Code2, Users, BookOpen, GitBranch, Cpu, Wrench, Bot,
  Shield, Activity, Layers, FileCode, TestTube, Heart
} from 'lucide-react'

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg><span className="font-mono font-bold text-lg">APEX</span></a>
          <div className="hidden md:flex items-center gap-5"><a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-apex-cyan">Contribute</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }, { href: '/contribute', label: 'Contribute' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() { return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>) }

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (<div className="relative group my-4 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden"><div className="flex items-center justify-between px-4 py-2 border-b border-border/30"><span className="text-xs text-muted-foreground font-mono">{language}</span><button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button></div><pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre></div>)
}

const PROJECT_TREE = `APEX/
├── apex/
│   ├── agent/            # Agent implementations
│   │   ├── coder.py      # Coder agent (default)
│   │   ├── architect.py   # Architect agent (read-only)
│   │   ├── reviewer.py    # Reviewer subagent
│   │   ├── devops.py      # DevOps agent
│   │   └── analyst.py     # Analyst subagent
│   ├── tools/            # 75+ built-in tools
│   │   ├── file_ops.py   # File operations
│   │   ├── git_tools.py  # Git integration
│   │   ├── search.py     # Search & navigation
│   │   ├── lsp.py        # LSP integration
│   │   ├── web.py        # Web search & fetch
│   │   ├── sandbox.py    # Sandbox execution
│   │   └── ...
│   ├── config/           # Configuration management
│   ├── mcp/              # MCP client support
│   ├── security/         # Permission & rate limiting
│   ├── plugins/          # Plugin system
│   ├── tui/              # Textual TUI frontend
│   ├── cli/              # CLI interface
│   └── utils/            # Shared utilities
├── tests/                # 1,148+ tests
│   ├── test_agents/
│   ├── test_tools/
│   ├── test_security/
│   └── ...
├── docs/                 # Documentation
├── pyproject.toml        # Project config
└── README.md`

const PR_STEPS = [
  { step: 1, title: 'Fork & Clone', desc: 'Fork the repository on GitHub and clone your fork locally.' },
  { step: 2, title: 'Create Branch', desc: 'Create a feature branch from main: git checkout -b feature/my-feature' },
  { step: 3, title: 'Make Changes', desc: 'Write your code following the style guide. Add tests for new functionality.' },
  { step: 4, title: 'Run Tests', desc: 'Run pytest to ensure all tests pass. Add new tests for your changes.' },
  { step: 5, title: 'Lint & Format', desc: 'Run ruff to check code style. Fix any linting issues.' },
  { step: 6, title: 'Commit & Push', desc: 'Write clear commit messages. Push to your fork.' },
  { step: 7, title: 'Open PR', desc: 'Open a pull request with a clear description of your changes.' },
]

const ISSUE_TYPES = [
  { type: 'Bug', color: '#ff4444', icon: '🐛', desc: 'Something is broken. Include steps to reproduce, expected behavior, and actual behavior.' },
  { type: 'Feature', color: '#00e5ff', icon: '✨', desc: 'A new capability. Describe the use case and proposed solution.' },
  { type: 'Documentation', color: '#00ff88', icon: '📝', desc: 'Improvements to docs. Typos, missing info, new guides, or clearer explanations.' },
  { type: 'Refactoring', color: '#ffaa00', icon: '🔧', desc: 'Code improvement without changing behavior. Better structure, performance, or readability.' },
]

export default function ContributePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Open Source</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Contribute to <span className="animated-gradient-text">APEX</span></h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">APEX is built by the community. Every contribution matters — from bug reports to major features.</p>
            </motion.div>
          </div>
        </section>

        {/* Development Setup */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Code2 className="w-6 h-6 text-apex-cyan" /> Development Setup</h2>
            <div className="p-6 rounded-xl border border-border/50 bg-card/30">
              <h3 className="font-bold font-mono text-apex-cyan mb-4">1. Clone & Install</h3>
              <CodeBlock code={`git clone https://github.com/Ggboykxz/APEX.git\ncd APEX\npip install -e ".[dev]"`} />
              <h3 className="font-bold font-mono text-apex-cyan mb-4 mt-6">2. Run Tests</h3>
              <CodeBlock code={`# Run all tests\npytest\n\n# Run specific test file\npytest tests/test_tools/test_file_ops.py\n\n# Run with coverage\npytest --cov=apex --cov-report=html`} />
              <h3 className="font-bold font-mono text-apex-cyan mb-4 mt-6">3. Run Linter</h3>
              <CodeBlock code={`# Check style\nruff check .\n\n# Auto-fix issues\nruff check --fix .\n\n# Format code\nruff format .`} />
            </div>
          </div>
        </section>

        {/* Code Style Guide */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><FileCode className="w-6 h-6 text-apex-cyan" /> Code Style Guide</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { title: 'Python 3.11+', desc: 'All code must be compatible with Python 3.11 and above. Use modern type hints.' },
                { title: 'Ruff Linter', desc: 'Use ruff for linting and formatting. Configuration in pyproject.toml.' },
                { title: '100 Char Lines', desc: 'Maximum line length of 100 characters. Docstrings follow Google style.' },
                { title: 'Type Hints', desc: 'All public functions must have type hints. Use Pydantic for data validation.' },
                { title: 'No Truncation', desc: 'Never use "...rest of file..." or similar. Always provide complete code.' },
                { title: 'Error Handling', desc: 'All functions must handle errors gracefully. Use proper exception types.' },
              ].map(s => (
                <div key={s.title} className="p-4 rounded-lg border border-border/50 bg-card/30">
                  <h4 className="font-bold font-mono text-apex-cyan mb-1">{s.title}</h4>
                  <p className="text-sm text-muted-foreground">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Testing */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><TestTube className="w-6 h-6 text-apex-cyan" /> Testing Guidelines</h2>
            <div className="p-6 rounded-xl border border-border/50 bg-card/30">
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> Use <strong className="text-foreground">pytest</strong> for all tests. Follow the existing test structure.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> All new features <strong className="text-foreground">must</strong> include tests. Aim for 80%+ coverage on new code.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> Use <strong className="text-foreground">fixtures</strong> for common test data. Keep tests isolated and deterministic.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> Follow the <strong className="text-foreground">refactoring pattern</strong>: write failing test → implement → make test pass → refactor.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> Mock external dependencies (API calls, file system) using <code className="text-apex-cyan">unittest.mock</code>.</li>
                <li className="flex items-start gap-2"><ChevronRight className="w-4 h-4 text-apex-cyan shrink-0 mt-0.5" /> Run <code className="text-apex-cyan">pytest --cov</code> before submitting PRs to ensure coverage.</li>
              </ul>
            </div>
          </div>
        </section>

        {/* PR Process */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><GitBranch className="w-6 h-6 text-apex-cyan" /> Pull Request Process</h2>
            <div className="space-y-4">
              {PR_STEPS.map(s => (
                <div key={s.step} className="flex items-start gap-4 p-4 rounded-lg border border-border/50 bg-card/30">
                  <div className="w-8 h-8 rounded-full bg-apex-cyan/10 border border-apex-cyan/20 flex items-center justify-center text-sm font-mono font-bold text-apex-cyan shrink-0">{s.step}</div>
                  <div><h4 className="font-bold font-mono text-foreground mb-1">{s.title}</h4><p className="text-sm text-muted-foreground">{s.desc}</p></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Issue Types */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Layers className="w-6 h-6 text-apex-cyan" /> Issue Types</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {ISSUE_TYPES.map(t => (
                <div key={t.type} className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: t.color, borderLeftWidth: 3 }}>
                  <div className="flex items-center gap-2 mb-2"><span className="text-xl">{t.icon}</span><h4 className="font-bold font-mono" style={{ color: t.color }}>{t.type}</h4></div>
                  <p className="text-sm text-muted-foreground">{t.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Project Structure */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Layers className="w-6 h-6 text-apex-cyan" /> Project Structure</h2>
            <CodeBlock language="text" code={PROJECT_TREE} />
          </div>
        </section>

        {/* Key Dependencies */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Cpu className="w-6 h-6 text-apex-cyan" /> Key Dependencies</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { name: 'litellm', desc: 'Unified interface for 100+ LLM providers' },
                { name: 'prompt_toolkit', desc: 'Rich CLI input with autocomplete and history' },
                { name: 'textual', desc: 'Full-featured TUI framework' },
                { name: 'pydantic', desc: 'Data validation and settings management' },
                { name: 'pytest', desc: 'Testing framework with 1,148+ tests' },
                { name: 'ruff', desc: 'Fast Python linter and formatter' },
                { name: 'rich', desc: 'Beautiful terminal formatting and markdown' },
                { name: 'click', desc: 'CLI argument parsing and commands' },
              ].map(d => (
                <div key={d.name} className="p-3 rounded-lg border border-border/50 bg-card/30 flex items-center gap-3">
                  <code className="text-sm font-mono text-apex-cyan font-bold">{d.name}</code>
                  <span className="text-sm text-muted-foreground">— {d.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Code of Conduct */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
            <Heart className="w-8 h-8 text-apex-red mx-auto mb-4" />
            <h2 className="text-2xl font-bold font-mono mb-4">Code of Conduct</h2>
            <p className="text-muted-foreground max-w-xl mx-auto mb-6">We are committed to providing a welcoming and inclusive experience for everyone. Please read our <a href="https://github.com/Ggboykxz/APEX/blob/main/CODE_OF_CONDUCT.md" target="_blank" rel="noopener noreferrer" className="text-apex-cyan hover:underline">Code of Conduct</a> before contributing.</p>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-apex-cyan text-background font-medium hover:bg-apex-cyan/90 transition-colors"><Github className="w-4 h-4" /> Start Contributing</a>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
