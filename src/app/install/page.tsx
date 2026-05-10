'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Zap, Github, Copy, Check, ArrowRight,
  Box, Menu, X, ChevronRight, Apple, Monitor, Container,
  Download, Key, AlertTriangle, RefreshCw, Cpu, Wrench, Bot, Activity, GitBranch, Users
} from 'lucide-react'

/* ──── SHARED NAV ──── */
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
            <a href="/#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="/install" className="text-sm text-apex-cyan transition-colors">Install</a>
            <a href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Docs</a>
            <a href="/agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Agents</a>
            <a href="/models" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Models</a>
            <a href="/tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Tools</a>
            <a href="/activity" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Activity</a>
            <a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Roadmap</a>
            <a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Contribute</a>
            <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-foreground transition-colors"><Github className="w-4 h-4" /></a>
          </div>
          <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-muted-foreground">{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
        </div>
      </div>
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border py-8 mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p>
        <div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="/install" className="text-xs text-muted-foreground hover:text-foreground">Install</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
      </div>
    </footer>
  )
}

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="relative group my-4 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30"><span className="text-xs text-muted-foreground font-mono">{language}</span><button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button></div>
      <pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre>
    </div>
  )
}

/* ──── INSTALL METHODS ──── */
const INSTALL_METHODS = [
  { id: 'curl', label: 'curl', icon: Terminal, platform: 'macOS / Linux', cmd: 'curl -fsSL https://apex-agent.dev/install.sh | bash', desc: 'One-line installer for macOS and Linux. Downloads and runs the official install script.' },
  { id: 'pipx', label: 'pipx', icon: Box, platform: 'All', cmd: 'pipx install apex-agent', desc: 'Recommended method. pipx creates an isolated environment, preventing dependency conflicts with other Python packages.' },
  { id: 'pip', label: 'pip', icon: Download, platform: 'All', cmd: 'pip install apex-agent', desc: 'Standard Python package installer. Works on all platforms with Python 3.11+.' },
  { id: 'brew', label: 'brew', icon: Apple, platform: 'macOS / Linux', cmd: 'brew install apex-agent', desc: 'Homebrew formula for macOS and Linux. Automatically manages dependencies.' },
  { id: 'docker', label: 'docker', icon: Container, platform: 'All', cmd: 'docker run -it ghcr.io/ggboykxz/apex', desc: 'Run APEX in a Docker container. Great for isolated environments and CI/CD.' },
  { id: 'cargo', label: 'cargo', icon: Terminal, platform: 'All', cmd: 'cargo install apex-agent', desc: 'Install via Rust cargo. Requires Rust toolchain installed.' },
  { id: 'npm', label: 'npm', icon: Box, platform: 'All', cmd: 'npm install -g apex-agent', desc: 'Install via Node.js npm package manager. Requires Node.js 18+.' },
  { id: 'nix', label: 'nix', icon: Terminal, platform: 'Linux / macOS', cmd: 'nix profile install github:Ggboykxz/APEX', desc: 'Nix package manager for reproducible builds and deployments.' },
  { id: 'aur', label: 'AUR', icon: Terminal, platform: 'Arch Linux', cmd: 'yay -S apex-agent', desc: 'Arch User Repository package. Use your favorite AUR helper.' },
  { id: 'scoop', label: 'scoop', icon: Terminal, platform: 'Windows', cmd: 'scoop install apex-agent', desc: 'Scoop package manager for Windows command-line apps.' },
  { id: 'choco', label: 'choco', icon: Terminal, platform: 'Windows', cmd: 'choco install apex-agent', desc: 'Chocolatey package manager for Windows.' },
  { id: 'winget', label: 'winget', icon: Terminal, platform: 'Windows', cmd: 'winget install Ggboykxz.ApexAgent', desc: 'Windows Package Manager (winget) — built into Windows 11.' },
  { id: 'npx', label: 'npx', icon: Box, platform: 'All', cmd: 'npx apex-agent', desc: 'Run APEX directly without installing. Uses npx to download and execute on the fly.' },
  { id: 'source', label: 'source', icon: Github, platform: 'All', cmd: 'git clone https://github.com/Ggboykxz/APEX.git\ncd APEX\npip install -e .', desc: 'Install from source for development. Clone the repo and install in editable mode.' },
]

const API_KEYS = [
  { provider: 'Anthropic', env: 'ANTHROPIC_API_KEY', prefix: 'sk-ant-', models: 'Claude 4 Sonnet, Opus 4, 3.5 Haiku', link: 'https://console.anthropic.com/' },
  { provider: 'OpenAI', env: 'OPENAI_API_KEY', prefix: 'sk-', models: 'GPT-4o, o1, o3, GPT-4.5, o4-mini', link: 'https://platform.openai.com/api-keys' },
  { provider: 'Google', env: 'GEMINI_API_KEY', prefix: 'AI', models: 'Gemini 2.5 Pro, Gemini 2.0 Flash', link: 'https://aistudio.google.com/apikey' },
  { provider: 'xAI', env: 'XAI_API_KEY', prefix: 'xai-', models: 'Grok 3, Grok 3 Mini', link: 'https://console.x.ai/' },
  { provider: 'Groq', env: 'GROQ_API_KEY', prefix: 'gsk_', models: 'Llama Groq, Mixtral Groq', link: 'https://console.groq.com/' },
  { provider: 'Mistral', env: 'MISTRAL_API_KEY', prefix: '', models: 'Mistral Large, Codestral', link: 'https://console.mistral.ai/' },
  { provider: 'DeepSeek', env: 'DEEPSEEK_API_KEY', prefix: '', models: 'DeepSeek V3, DeepSeek R1', link: 'https://platform.deepseek.com/' },
  { provider: 'Cohere', env: 'COHERE_API_KEY', prefix: '', models: 'Command R, Command R Plus', link: 'https://dashboard.cohere.com/' },
]

/* ──── MAIN ──── */
export default function InstallPage() {
  const [activeMethod, setActiveMethod] = useState('pipx')

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
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />Installation
              </div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Install <span className="animated-gradient-text">APEX</span></h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">14 installation methods for every platform. Get started in under a minute.</p>
            </motion.div>
          </div>
        </section>

        {/* System Requirements */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Monitor className="w-6 h-6 text-apex-cyan" /> System Requirements</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-3">Minimum</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-cyan" /> Python 3.11 or later</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-cyan" /> At least one API key (or Ollama for free local models)</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-cyan" /> Terminal with 256-color support</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-cyan" /> 100 MB disk space</li>
                </ul>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-green mb-3">Recommended</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-green" /> Python 3.12+</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-green" /> pipx for isolated install</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-green" /> Git for version control integration</li>
                  <li className="flex items-center gap-2"><ChevronRight className="w-3 h-3 text-apex-green" /> Ollama for free local models</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Install Methods */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Download className="w-6 h-6 text-apex-cyan" /> Installation Methods</h2>
            <div className="grid lg:grid-cols-[280px_1fr] gap-6">
              {/* Method selector */}
              <div className="space-y-1 max-h-[600px] overflow-y-auto">
                {INSTALL_METHODS.map(m => (
                  <button key={m.id} onClick={() => setActiveMethod(m.id)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-mono transition-all text-left ${activeMethod === m.id ? 'bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20' : 'text-muted-foreground hover:text-foreground hover:bg-card'}`}>
                    <m.icon className="w-4 h-4 shrink-0" />
                    <div><div className="font-bold">{m.label}</div><div className="text-xs opacity-60">{m.platform}</div></div>
                  </button>
                ))}
              </div>
              {/* Method detail */}
              <div>
                {INSTALL_METHODS.filter(m => m.id === activeMethod).map(m => (
                  <motion.div key={m.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-xl border border-border/50 bg-card/30">
                    <div className="flex items-center gap-3 mb-4"><m.icon className="w-6 h-6 text-apex-cyan" /><div><h3 className="font-bold font-mono text-lg">{m.label}</h3><span className="text-xs text-muted-foreground font-mono">{m.platform}</span></div></div>
                    <p className="text-sm text-muted-foreground mb-4 leading-relaxed">{m.desc}</p>
                    <CodeBlock code={m.cmd} />
                    {m.id === 'docker' && <div className="mt-4 p-3 rounded-lg border border-apex-yellow/20 bg-apex-yellow/5 text-sm text-muted-foreground">💡 Mount your project directory: <code className="text-apex-cyan">docker run -it -v $(pwd):/workspace ghcr.io/ggboykxz/apex</code></div>}
                    {m.id === 'source' && <div className="mt-4 p-3 rounded-lg border border-apex-cyan/20 bg-apex-cyan/5 text-sm text-muted-foreground">💡 For dev dependencies: <code className="text-apex-cyan">pip install -e &quot;.[dev]&quot;</code></div>}
                    <div className="mt-4"><CodeBlock code="apex --version" language="Verify" /></div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* API Key Setup */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Key className="w-6 h-6 text-apex-cyan" /> API Key Setup</h2>
            <p className="text-muted-foreground mb-6">APEX needs API keys for cloud models. Set them in <code className="text-apex-cyan">~/.apex/.env</code> (recommended), <code className="text-apex-cyan">./.env</code>, or <code className="text-apex-cyan">~/.env</code>.</p>
            <CodeBlock code={`# ~/.apex/.env\nANTHROPIC_API_KEY=sk-ant-...\nOPENAI_API_KEY=sk-...\nGROQ_API_KEY=gsk_...\nMISTRAL_API_KEY=...\nDEEPSEEK_API_KEY=...\nGEMINI_API_KEY=...\nCOHERE_API_KEY=...`} />
            <div className="mt-8 grid gap-4">
              {API_KEYS.map(k => (
                <div key={k.provider} className="p-4 rounded-lg border border-border/50 bg-card/30">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h4 className="font-bold font-mono text-apex-cyan">{k.provider}</h4>
                      <p className="text-xs text-muted-foreground">Models: {k.models}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <code className="text-xs font-mono text-muted-foreground bg-card px-2 py-1 rounded">{k.env}</code>
                      <a href={k.link} target="_blank" rel="noopener noreferrer" className="text-xs text-apex-cyan hover:underline flex items-center gap-1">Get Key <ArrowRight className="w-3 h-3" /></a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 p-4 rounded-lg border border-apex-green/20 bg-apex-green/5 text-sm text-muted-foreground">
              🏠 <strong className="text-foreground">Local Models (Free):</strong> No API key needed! Install <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer" className="text-apex-cyan hover:underline">Ollama</a>, run <code className="text-apex-cyan">ollama pull llama3</code>, then use <code className="text-apex-cyan">apex --model ollama/llama3</code>
            </div>
          </div>
        </section>

        {/* Platform Notes */}
        <section className="py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Apple className="w-6 h-6 text-apex-cyan" /> Platform Notes</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#00e5ff', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#00e5ff] mb-3">macOS</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Best with Homebrew: <code className="text-apex-cyan">brew install apex-agent</code></li>
                  <li>• Or curl installer: <code className="text-apex-cyan">curl -fsSL ... | bash</code></li>
                  <li>• pipx recommended over pip</li>
                  <li>• Terminal.app, iTerm2, Warp, Kitty all supported</li>
                </ul>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#00ff88', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#00ff88] mb-3">Linux</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• curl installer works on all distros</li>
                  <li>• Arch: AUR package available</li>
                  <li>• Nix: nix profile install</li>
                  <li>• Docker for isolated environments</li>
                </ul>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#ffaa00', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#ffaa00] mb-3">Windows</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• winget: <code className="text-apex-cyan">winget install Ggboykxz.ApexAgent</code></li>
                  <li>• scoop: <code className="text-apex-cyan">scoop install apex-agent</code></li>
                  <li>• choco: <code className="text-apex-cyan">choco install apex-agent</code></li>
                  <li>• WSL2 recommended for best TUI experience</li>
                </ul>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30" style={{ borderLeftColor: '#d946ef', borderLeftWidth: 3 }}>
                <h3 className="font-bold font-mono text-[#d946ef] mb-3">FreeBSD</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Install via pip or pipx</li>
                  <li>• Python 3.11+ from ports or pkg</li>
                  <li>• CLI mode fully supported</li>
                  <li>• TUI may require xterm compatibility</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Upgrade & Troubleshooting */}
        <section className="py-12 bg-card/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><RefreshCw className="w-6 h-6 text-apex-cyan" /> Upgrade & Troubleshooting</h2>
            <div className="grid sm:grid-cols-2 gap-6">
              <div>
                <h3 className="font-bold font-mono text-apex-cyan mb-4">Upgrade</h3>
                <CodeBlock code={`# pip\npip install --upgrade apex-agent\n\n# pipx\npipx upgrade apex-agent\n\n# brew\nbrew upgrade apex-agent\n\n# Check version\napex --version`} />
              </div>
              <div>
                <h3 className="font-bold font-mono text-apex-yellow mb-4 flex items-center gap-2"><AlertTriangle className="w-5 h-5" /> Common Issues</h3>
                <div className="space-y-4">
                  <div className="p-3 rounded-lg border border-border/50 bg-card/30">
                    <h4 className="font-bold text-sm font-mono mb-1">&quot;command not found: apex&quot;</h4>
                    <p className="text-xs text-muted-foreground">Ensure Python bin directory is in your PATH. Try: <code className="text-apex-cyan">python -m apex.main</code></p>
                  </div>
                  <div className="p-3 rounded-lg border border-border/50 bg-card/30">
                    <h4 className="font-bold text-sm font-mono mb-1">&quot;Authentication failed&quot;</h4>
                    <p className="text-xs text-muted-foreground">Check your API key in <code className="text-apex-cyan">~/.apex/.env</code>. Run <code className="text-apex-cyan">echo $ANTHROPIC_API_KEY</code></p>
                  </div>
                  <div className="p-3 rounded-lg border border-border/50 bg-card/30">
                    <h4 className="font-bold text-sm font-mono mb-1">Import errors on startup</h4>
                    <p className="text-xs text-muted-foreground">Reinstall: <code className="text-apex-cyan">pip install --force-reinstall apex-agent</code></p>
                  </div>
                  <div className="p-3 rounded-lg border border-border/50 bg-card/30">
                    <h4 className="font-bold text-sm font-mono mb-1">Python version mismatch</h4>
                    <p className="text-xs text-muted-foreground">Requires Python 3.11+. Check: <code className="text-apex-cyan">python --version</code></p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
