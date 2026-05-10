'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ArrowRight,
  Cpu, Bot, Wrench, BookOpen, Activity, GitBranch, Users,
  Shield, DollarSign, Zap, Globe, Home
} from 'lucide-react'

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg><span className="font-mono font-bold text-lg">APEX</span></a>
          <div className="hidden md:flex items-center gap-5"><a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-apex-cyan">Models</a><a href="/tools" className="text-sm text-muted-foreground hover:text-foreground">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
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

const PROVIDERS = [
  {
    name: 'Anthropic', icon: '🧠', color: '#d4a574',
    models: [
      { alias: 'claude-sonnet', model: 'anthropic/claude-sonnet-4-20250514', desc: 'Best balance of speed and intelligence', use: 'General coding, debugging, refactoring' },
      { alias: 'claude-opus', model: 'anthropic/claude-opus-4-20250514', desc: 'Most capable model for complex reasoning', use: 'Complex architecture, multi-file refactoring' },
      { alias: 'claude-flash', model: 'anthropic/claude-3-5-haiku-20241022', desc: 'Fastest Claude model, cost-effective', use: 'Quick edits, simple queries, chat' },
    ]
  },
  {
    name: 'OpenAI', icon: '🔮', color: '#10a37f',
    models: [
      { alias: 'gpt-4o', model: 'openai/gpt-4o', desc: 'Flagship multimodal model', use: 'General coding, analysis, complex tasks' },
      { alias: 'gpt-4o-mini', model: 'openai/gpt-4o-mini', desc: 'Fast and affordable', use: 'Quick edits, simple queries, cost-effective' },
      { alias: 'gpt-4.5', model: 'openai/gpt-4.5-preview', desc: 'Latest GPT model with enhanced reasoning', use: 'Complex reasoning, creative coding' },
      { alias: 'o1', model: 'openai/o1', desc: 'Reasoning model for complex problems', use: 'Complex algorithm design, math, logic' },
      { alias: 'o3', model: 'openai/o3', desc: 'Advanced reasoning model', use: 'Complex reasoning, research tasks' },
      { alias: 'o3-mini', model: 'openai/o3-mini', desc: 'Cost-effective reasoning', use: 'Structured problem-solving on a budget' },
      { alias: 'o4-mini', model: 'openai/o4-mini', desc: 'Efficient reasoning model', use: 'Fast reasoning tasks, code analysis' },
    ]
  },
  {
    name: 'Google', icon: '💎', color: '#4285f4',
    models: [
      { alias: 'gemini-2.5-pro', model: 'google/gemini-2.5-pro-preview-05-06', desc: 'Most capable Gemini model', use: 'Complex coding, long context, analysis' },
      { alias: 'gemini-flash', model: 'google/gemini-2.0-flash-001', desc: 'Fast and efficient Gemini', use: 'Quick tasks, real-time coding, chat' },
    ]
  },
  {
    name: 'xAI', icon: '⚡', color: '#ff6b35',
    models: [
      { alias: 'grok-3', model: 'xai/grok-3', desc: 'Latest Grok model', use: 'General coding with real-time knowledge' },
      { alias: 'grok-3-mini', model: 'xai/grok-3-mini', desc: 'Cost-effective Grok', use: 'Quick queries, simple coding tasks' },
    ]
  },
  {
    name: 'Meta', icon: '🦙', color: '#0668E1',
    models: [
      { alias: 'llama4-maverick', model: 'meta_llama/llama-4-maverick', desc: 'Latest Llama with MoE architecture', use: 'Open-weight coding, research' },
      { alias: 'llama4-scout', model: 'meta_llama/llama-4-scout', desc: 'Efficient Llama variant', use: 'Fast open-weight coding tasks' },
      { alias: 'llama3.3-70b', model: 'meta_llama/llama-3.3-70b-instruct', desc: 'Llama 3.3 70B instruct', use: 'General coding with open weights' },
    ]
  },
  {
    name: 'DeepSeek', icon: '🔍', color: '#4d6bfe',
    models: [
      { alias: 'deepseek', model: 'deepseek/deepseek-chat', desc: 'DeepSeek V3 general chat', use: 'Cost-effective coding, Chinese + English' },
      { alias: 'deepseek-r1', model: 'deepseek/deepseek-reasoner', desc: 'DeepSeek R1 reasoning model', use: 'Complex reasoning, math, algorithm design' },
      { alias: 'deepseek-coder', model: 'deepseek/deepseek-coder', desc: 'Specialized for code generation', use: 'Code generation, completion, review' },
    ]
  },
  {
    name: 'Alibaba', icon: '🌐', color: '#ff6a00',
    models: [
      { alias: 'qwen3-235b', model: 'alibaba/qwen3-235b-a22b', desc: 'Qwen 3 with 235B parameters', use: 'Complex reasoning, multilingual coding' },
      { alias: 'qwen2.5-coder', model: 'alibaba/qwen2.5-coder-32b-instruct', desc: 'Specialized for code', use: 'Code generation, debugging, review' },
    ]
  },
  {
    name: 'Mistral', icon: '🌪️', color: '#f70000',
    models: [
      { alias: 'mistral-large', model: 'mistral/mistral-large-latest', desc: 'Most capable Mistral model', use: 'Complex coding, enterprise tasks' },
      { alias: 'codestral', model: 'mistral/codestral-latest', desc: 'Specialized for code generation', use: 'Code completion, generation, review' },
    ]
  },
  {
    name: 'Groq', icon: '🚀', color: '#f55036',
    models: [
      { alias: 'llama-groq', model: 'groq/llama-3.3-70b-versatile', desc: 'Ultra-fast Llama on Groq', use: 'Real-time coding, instant responses' },
      { alias: 'mixtral-groq', model: 'groq/mixtral-8x7b-32768', desc: 'Fast Mixtral on Groq', use: 'Fast multi-task coding, long context' },
    ]
  },
  {
    name: 'Cohere', icon: '🟠', color: '#39594d',
    models: [
      { alias: 'command-r', model: 'cohere/command-r', desc: 'Balanced performance model', use: 'RAG, tool use, general coding' },
      { alias: 'command-r-plus', model: 'cohere/command-r-plus', desc: 'Most capable Cohere model', use: 'Complex reasoning, enterprise tasks' },
    ]
  },
  {
    name: 'Local (Ollama / LM Studio / llama.cpp)', icon: '🏠', color: '#00ff88',
    models: [
      { alias: 'ollama-llama3', model: 'ollama/llama3', desc: 'Llama 3 via Ollama (local)', use: 'Free, offline, private coding' },
      { alias: 'ollama-llama3.1', model: 'ollama/llama3.1', desc: 'Llama 3.1 via Ollama', use: 'Free, offline with better reasoning' },
      { alias: 'ollama-codellama', model: 'ollama/codellama', desc: 'Code Llama via Ollama', use: 'Free, offline code generation' },
      { alias: 'ollama-deepseek', model: 'ollama/deepseek-coder-v2', desc: 'DeepSeek Coder via Ollama', use: 'Free, offline code specialist' },
      { alias: 'ollama-qwen2.5', model: 'ollama/qwen2.5-coder', desc: 'Qwen Coder via Ollama', use: 'Free, offline coding assistant' },
      { alias: 'lm-studio', model: 'lm_studio/your-model', desc: 'Any model via LM Studio', use: 'Free, offline, any GGUF model' },
      { alias: 'llama.cpp', model: 'llama.cpp/your-model', desc: 'Any model via llama.cpp server', use: 'Free, offline, maximum control' },
    ]
  },
]

const COST_COMPARISON = [
  { model: 'GPT-4o', input: '$2.50', output: '$10.00', speed: 'Fast', best: 'General coding' },
  { model: 'GPT-4o-mini', input: '$0.15', output: '$0.60', speed: 'Very Fast', best: 'Budget coding' },
  { model: 'Claude 4 Sonnet', input: '$3.00', output: '$15.00', speed: 'Fast', best: 'Code quality' },
  { model: 'Claude Opus 4', input: '$15.00', output: '$75.00', speed: 'Medium', best: 'Complex tasks' },
  { model: 'Claude 3.5 Haiku', input: '$0.80', output: '$4.00', speed: 'Very Fast', best: 'Quick edits' },
  { model: 'Gemini 2.5 Pro', input: '$1.25', output: '$10.00', speed: 'Fast', best: 'Long context' },
  { model: 'DeepSeek V3', input: '$0.27', output: '$1.10', speed: 'Fast', best: 'Best value' },
  { model: 'DeepSeek R1', input: '$0.55', output: '$2.19', speed: 'Medium', best: 'Reasoning' },
  { model: 'Ollama (Local)', input: 'Free', output: 'Free', speed: 'Varies', best: 'Privacy/offline' },
]

export default function ModelsPage() {
  const [expandedProvider, setExpandedProvider] = useState<string | null>('Anthropic')

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />100+ Models</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Every <span className="animated-gradient-text">Model</span>, One CLI</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Use any LLM from any provider. Switch models mid-session without losing context. All via litellm.</p>
            </motion.div>
          </div>
        </section>

        {/* Model Switching Guide */}
        <section className="py-8">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="p-6 rounded-xl border border-apex-cyan/20 bg-apex-cyan/5">
              <h3 className="font-bold font-mono text-apex-cyan mb-3 flex items-center gap-2"><Zap className="w-5 h-5" /> Switch Models Mid-Session</h3>
              <div className="grid sm:grid-cols-3 gap-4">
                <div><CodeBlock code="/model gpt-4o" /><p className="text-xs text-muted-foreground mt-1">Switch in-session</p></div>
                <div><CodeBlock code="/models" /><p className="text-xs text-muted-foreground mt-1">List all models</p></div>
                <div><CodeBlock code='apex --model gpt-4o "prompt"' /><p className="text-xs text-muted-foreground mt-1">Specify on launch</p></div>
              </div>
            </div>
          </div>
        </section>

        {/* Provider Cards */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-4">
            {PROVIDERS.map((provider, i) => (
              <motion.div key={provider.name} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.05 }}>
                <div className="rounded-xl border border-border/50 bg-card/30 overflow-hidden">
                  <button onClick={() => setExpandedProvider(expandedProvider === provider.name ? null : provider.name)} className="w-full flex items-center justify-between p-5 hover:bg-card/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{provider.icon}</span>
                      <div className="text-left"><h3 className="font-bold font-mono text-lg" style={{ color: provider.color }}>{provider.name}</h3><span className="text-xs text-muted-foreground font-mono">{provider.models.length} model{provider.models.length > 1 ? 's' : ''}</span></div>
                    </div>
                    <ArrowRight className={`w-5 h-5 text-muted-foreground transition-transform ${expandedProvider === provider.name ? 'rotate-90' : ''}`} />
                  </button>
                  {expandedProvider === provider.name && (
                    <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} className="border-t border-border/50">
                      <div className="p-5 space-y-4">
                        {provider.models.map(m => (
                          <div key={m.alias} className="p-4 rounded-lg border border-border/30 bg-card/20">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                              <div><code className="text-sm font-mono font-bold text-apex-cyan">{m.alias}</code></div>
                              <code className="text-xs font-mono text-muted-foreground bg-card px-2 py-1 rounded break-all">{m.model}</code>
                            </div>
                            <p className="text-sm text-muted-foreground mb-1">{m.desc}</p>
                            <p className="text-xs text-muted-foreground"><strong className="text-foreground">Best for:</strong> {m.use}</p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Cost Comparison */}
        <section className="py-12 bg-card/30">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><DollarSign className="w-6 h-6 text-apex-cyan" /> Cost Comparison</h2>
            <p className="text-muted-foreground mb-6">Approximate pricing per 1M tokens. Prices vary by provider and may change.</p>
            <div className="overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-border/50 bg-card/50"><th className="text-left p-3 font-mono text-muted-foreground">Model</th><th className="text-left p-3 font-mono text-muted-foreground">Input/1M</th><th className="text-left p-3 font-mono text-muted-foreground">Output/1M</th><th className="text-left p-3 font-mono text-muted-foreground">Speed</th><th className="text-left p-3 font-mono text-muted-foreground">Best For</th></tr></thead>
                <tbody>{COST_COMPARISON.map((row, i) => (
                  <tr key={row.model} className={`border-b border-border/30 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
                    <td className="p-3 font-mono font-bold text-foreground">{row.model}</td>
                    <td className="p-3 font-mono text-muted-foreground">{row.input}</td>
                    <td className="p-3 font-mono text-muted-foreground">{row.output}</td>
                    <td className="p-3 font-mono text-muted-foreground">{row.speed}</td>
                    <td className="p-3 font-mono text-muted-foreground">{row.best}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Performance Tips */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Zap className="w-6 h-6 text-apex-cyan" /> Performance Optimization</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { title: 'Use Fast Models for Edits', desc: 'Switch to gpt-4o-mini or claude-3.5-haiku for quick edits and simple queries. Save expensive models for complex tasks.' },
                { title: 'Clear Context Regularly', desc: 'Use /clear to free up context window. Long conversations consume tokens even for small requests.' },
                { title: 'Use Streaming Mode', desc: 'Enable streaming with apex --stream for real-time output. Reduces perceived latency significantly.' },
                { title: 'Leverage Local Models', desc: 'Use Ollama for privacy-sensitive code or when offline. Zero cost, zero data leaving your machine.' },
                { title: 'Monitor Costs', desc: 'Use /cost to check token usage and estimated costs in real-time. Set budget alerts in your config.' },
                { title: 'Choose the Right Model', desc: 'Reasoning tasks → o1/deepseek-r1. Code gen → gpt-4o/claude-sonnet. Budget → gpt-4o-mini/deepseek-chat.' },
              ].map(tip => (
                <div key={tip.title} className="p-4 rounded-lg border border-border/50 bg-card/30">
                  <h4 className="font-bold font-mono text-apex-cyan mb-1">{tip.title}</h4>
                  <p className="text-sm text-muted-foreground">{tip.desc}</p>
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
