'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ArrowRight,
  Cpu, Bot, Wrench, BookOpen, Activity, GitBranch, Users,
  Shield, DollarSign, Zap, Globe, Home
} from 'lucide-react'
import { PROVIDER_ICONS } from '@/components/ProviderIcons'

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

function Footer() { return (<footer className="border-t border-border py-8 mt-auto"><div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4"><p className="text-xs text-muted-foreground font-mono">Proprietary License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p><div className="flex items-center gap-6"><a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div></div></footer>) }

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (<div className="relative group my-3 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden"><div className="flex items-center justify-between px-4 py-2 border-b border-border/30"><span className="text-xs text-muted-foreground font-mono">{language}</span><button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button></div><pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre></div>)
}

const PROVIDERS = [
  {
    name: 'Anthropic', iconKey: 'anthropic', color: '#d4a574',
    models: [
      { alias: 'claude-sonnet-4.6', model: 'anthropic/claude-sonnet-4-6', desc: 'Claude Sonnet 4.6 — 1M context, extended thinking', use: 'General coding, debugging, refactoring' },
      { alias: 'claude-opus-4.7', model: 'anthropic/claude-opus-4-7', desc: 'Claude Opus 4.7 — 1M context, most capable', use: 'Complex architecture, multi-file refactoring' },
      { alias: 'claude-sonnet-4.5', model: 'anthropic/claude-sonnet-4-5', desc: 'Claude Sonnet 4.5 — latest reasoning', use: 'Advanced coding, complex reasoning' },
      { alias: 'claude-opus-4.5', model: 'anthropic/claude-opus-4-5', desc: 'Claude Opus 4.5 — premium reasoning', use: 'Complex tasks, deep analysis' },
      { alias: 'claude-haiku-4.5', model: 'anthropic/claude-haiku-4-5', desc: 'Claude Haiku 4.5 — fast & affordable', use: 'Quick edits, simple queries, chat' },
      { alias: 'claude-3.7-sonnet', model: 'anthropic/claude-3-7-sonnet-20250219', desc: 'Claude 3.7 Sonnet — enhanced coding', use: 'Advanced coding, complex reasoning' },
      { alias: 'claude-3.5-haiku', model: 'anthropic/claude-3-5-haiku-20241022', desc: 'Claude 3.5 Haiku — fastest Claude', use: 'Quick edits, simple queries, cost-effective' },
    ]
  },
  {
    name: 'OpenAI', iconKey: 'openai', color: '#10a37f',
    models: [
      { alias: 'gpt-5', model: 'openai/gpt-5', desc: 'GPT-5 — latest flagship model', use: 'General coding, analysis, complex tasks' },
      { alias: 'gpt-5-mini', model: 'openai/gpt-5-mini', desc: 'GPT-5 Mini — fast and affordable', use: 'Quick edits, simple queries, cost-effective' },
      { alias: 'gpt-5-nano', model: 'openai/gpt-5-nano', desc: 'GPT-5 Nano — ultra-affordable', use: 'Bulk processing, simple tasks' },
      { alias: 'gpt-5-pro', model: 'openai/gpt-5-pro', desc: 'GPT-5 Pro — premium reasoning', use: 'Complex reasoning, creative coding' },
      { alias: 'gpt-4o', model: 'openai/gpt-4o', desc: 'GPT-4o — multimodal flagship', use: 'General coding, analysis, complex tasks' },
      { alias: 'gpt-4o-mini', model: 'openai/gpt-4o-mini', desc: 'GPT-4o Mini — fast and affordable', use: 'Quick edits, simple queries, cost-effective' },
      { alias: 'gpt-4.1', model: 'openai/gpt-4.1', desc: 'GPT-4.1 — 1M context window', use: 'Long context coding, large codebases' },
      { alias: 'gpt-4.1-mini', model: 'openai/gpt-4.1-mini', desc: 'GPT-4.1 Mini — 1M context, affordable', use: 'Long context, budget coding' },
      { alias: 'o3', model: 'openai/o3', desc: 'o3 — advanced reasoning model', use: 'Complex reasoning, research tasks' },
      { alias: 'o3-mini', model: 'openai/o3-mini', desc: 'o3 Mini — cost-effective reasoning', use: 'Structured problem-solving on a budget' },
      { alias: 'o4-mini', model: 'openai/o4-mini', desc: 'o4 Mini — efficient reasoning', use: 'Fast reasoning tasks, code analysis' },
    ]
  },
  {
    name: 'Google', iconKey: 'google', color: '#4285f4',
    models: [
      { alias: 'gemini-3-pro', model: 'google/gemini-3-pro-preview', desc: 'Gemini 3 Pro — most capable Gemini', use: 'Complex coding, long context, analysis' },
      { alias: 'gemini-3-flash', model: 'google/gemini-3-flash-preview', desc: 'Gemini 3 Flash — fast & capable', use: 'Quick tasks, real-time coding, chat' },
      { alias: 'gemini-2.5-pro', model: 'google/gemini-2.5-pro', desc: 'Gemini 2.5 Pro — 1M context, reasoning', use: 'Complex coding, long context, analysis' },
      { alias: 'gemini-2.5-flash', model: 'google/gemini-2.5-flash', desc: 'Gemini 2.5 Flash — fast and efficient', use: 'Quick tasks, real-time coding, chat' },
      { alias: 'gemini-2.5-flash-lite', model: 'google/gemini-2.5-flash-lite', desc: 'Gemini 2.5 Flash Lite — ultra-affordable', use: 'Budget coding, bulk processing' },
      { alias: 'gemma-4-31b', model: 'google/gemma-4-31b-it', desc: 'Gemma 4 31B — open weights', use: 'Open-weight coding, research' },
    ]
  },
  {
    name: 'xAI', iconKey: 'xai', color: '#ff6b35',
    models: [
      { alias: 'grok-4', model: 'xai/grok-4', desc: 'Grok 4 — latest Grok model', use: 'General coding with real-time knowledge' },
      { alias: 'grok-4-fast', model: 'xai/grok-4-fast', desc: 'Grok 4 Fast — fast reasoning', use: 'Quick queries, fast coding tasks' },
      { alias: 'grok-3', model: 'xai/grok-3', desc: 'Grok 3 — capable Grok model', use: 'General coding, analysis' },
      { alias: 'grok-3-mini', model: 'xai/grok-3-mini', desc: 'Grok 3 Mini — cost-effective Grok', use: 'Quick queries, simple coding tasks' },
    ]
  },
  {
    name: 'DeepSeek', iconKey: 'deepseek', color: '#4d6bfe',
    models: [
      { alias: 'deepseek-v4-pro', model: 'deepseek/deepseek-v4-pro', desc: 'DeepSeek V4 Pro — most capable', use: 'Complex reasoning, code generation' },
      { alias: 'deepseek-v4-flash', model: 'deepseek/deepseek-v4-flash', desc: 'DeepSeek V4 Flash — fast & cheap', use: 'Cost-effective coding, fast responses' },
      { alias: 'deepseek-chat', model: 'deepseek/deepseek-chat', desc: 'DeepSeek V3 general chat', use: 'Cost-effective coding, Chinese + English' },
      { alias: 'deepseek-reasoner', model: 'deepseek/deepseek-reasoner', desc: 'DeepSeek R1 reasoning model', use: 'Complex reasoning, math, algorithm design' },
    ]
  },
  {
    name: 'Mistral', iconKey: 'mistral', color: '#f70000',
    models: [
      { alias: 'mistral-large', model: 'mistral/mistral-large-latest', desc: 'Mistral Large 3 — most capable', use: 'Complex coding, enterprise tasks' },
      { alias: 'mistral-medium', model: 'mistral/mistral-medium-latest', desc: 'Mistral Medium — balanced', use: 'Balanced coding and reasoning' },
      { alias: 'mistral-small', model: 'mistral/mistral-small-latest', desc: 'Mistral Small — fast & cheap', use: 'Quick edits, budget coding' },
      { alias: 'codestral', model: 'mistral/codestral-latest', desc: 'Codestral — specialized for code', use: 'Code completion, generation, review' },
      { alias: 'devstral', model: 'mistral/devstral-medium-latest', desc: 'Devstral 2 — developer-focused', use: 'Code generation, debugging, review' },
      { alias: 'magistral-medium', model: 'mistral/magistral-medium-latest', desc: 'Magistral Medium — reasoning', use: 'Complex reasoning, research' },
    ]
  },
  {
    name: 'Alibaba', iconKey: 'alibaba', color: '#ff6a00',
    models: [
      { alias: 'qwen3-max', model: 'alibaba/qwen3-max', desc: 'Qwen 3 Max — most capable Qwen', use: 'Complex reasoning, multilingual coding' },
      { alias: 'qwen3-coder-plus', model: 'alibaba/qwen3-coder-plus', desc: 'Qwen 3 Coder Plus — 1M context', use: 'Code generation, debugging, review' },
      { alias: 'qwen3.6-plus', model: 'alibaba/qwen3.6-plus', desc: 'Qwen 3.6 Plus — 1M context', use: 'Multilingual coding, long context' },
      { alias: 'qwen3-235b', model: 'alibaba/qwen3-235b-a22b', desc: 'Qwen 3 235B — large MoE model', use: 'Complex reasoning, multilingual coding' },
      { alias: 'qwq-plus', model: 'alibaba/qwq-plus', desc: 'QwQ Plus — reasoning specialist', use: 'Complex reasoning, math, algorithm design' },
      { alias: 'qwen-plus', model: 'alibaba/qwen-plus', desc: 'Qwen Plus — 1M context, balanced', use: 'General coding, balanced cost/perf' },
    ]
  },
  {
    name: 'Meta', iconKey: 'meta', color: '#0668E1',
    models: [
      { alias: 'llama-4-maverick', model: 'llama/llama-4-maverick-17b-128e-instruct-fp8', desc: 'Llama 4 Maverick — MoE 128 experts', use: 'Open-weight coding, research' },
      { alias: 'llama-4-scout', model: 'llama/llama-4-scout-17b-16e-instruct-fp8', desc: 'Llama 4 Scout — efficient MoE', use: 'Fast open-weight coding tasks' },
      { alias: 'llama-3.3-70b', model: 'llama/llama-3.3-70b-instruct', desc: 'Llama 3.3 70B Instruct', use: 'General coding with open weights' },
    ]
  },
  {
    name: 'Cohere', iconKey: 'cohere', color: '#39594d',
    models: [
      { alias: 'command-a', model: 'cohere/command-a-03-2025', desc: 'Command A — most capable Cohere', use: 'Complex reasoning, enterprise tasks' },
      { alias: 'command-a-reasoning', model: 'cohere/command-a-reasoning-08-2025', desc: 'Command A Reasoning — step-by-step', use: 'Complex reasoning, analysis' },
      { alias: 'command-r-plus', model: 'cohere/command-r-plus-08-2024', desc: 'Command R+ — RAG specialist', use: 'RAG, enterprise tasks' },
      { alias: 'command-r', model: 'cohere/command-r-08-2024', desc: 'Command R — balanced model', use: 'RAG, tool use, general coding' },
    ]
  },
  {
    name: 'Groq', iconKey: 'groq', color: '#f55036',
    models: [
      { alias: 'llama-groq-4-maverick', model: 'groq/meta-llama/llama-4-maverick-17b-128e-instruct', desc: 'Llama 4 Maverick on Groq — ultra-fast', use: 'Real-time coding, instant responses' },
      { alias: 'llama-groq-4-scout', model: 'groq/meta-llama/llama-4-scout-17b-16e-instruct', desc: 'Llama 4 Scout on Groq — fast + vision', use: 'Fast coding with vision support' },
      { alias: 'llama-groq-3.3-70b', model: 'groq/llama-3.3-70b-versatile', desc: 'Llama 3.3 70B on Groq', use: 'Fast general coding' },
      { alias: 'deepseek-r1-groq', model: 'groq/deepseek-r1-distill-llama-70b', desc: 'DeepSeek R1 distilled on Groq', use: 'Fast reasoning, budget coding' },
      { alias: 'qwq-groq-32b', model: 'groq/qwen-qwq-32b', desc: 'QwQ 32B on Groq — reasoning', use: 'Fast reasoning tasks' },
    ]
  },
  {
    name: 'Microsoft', iconKey: 'microsoft', color: '#00a4ef',
    models: [
      { alias: 'phi-4', model: 'microsoft/phi-4', desc: 'Phi-4 — small but powerful', use: 'Efficient coding, lightweight tasks' },
      { alias: 'phi-4-reasoning', model: 'microsoft/phi-4-reasoning', desc: 'Phi-4 Reasoning — step-by-step', use: 'Reasoning tasks, analysis' },
      { alias: 'phi-4-mini', model: 'microsoft/phi-4-mini-instruct', desc: 'Phi-4 Mini — ultra-lightweight', use: 'Budget coding, embedded scenarios' },
      { alias: 'phi-4-multimodal', model: 'microsoft/phi-4-multimodal-instruct', desc: 'Phi-4 Multimodal — vision + text', use: 'Vision coding, document analysis' },
    ]
  },
  {
    name: 'Cerebras', iconKey: 'cerebras', color: '#7c3aed',
    models: [
      { alias: 'cerebras-qwen3-235b', model: 'cerebras/qwen-3-235b-a22b-instruct-2507', desc: 'Qwen 3 235B on Cerebras — ultra-fast', use: 'Fastest inference for large models' },
      { alias: 'cerebras-gpt-oss-120b', model: 'cerebras/gpt-oss-120b', desc: 'GPT OSS 120B on Cerebras', use: 'Fast reasoning, large model tasks' },
      { alias: 'cerebras-llama3.1-8b', model: 'cerebras/llama3.1-8b', desc: 'Llama 3.1 8B on Cerebras — instant', use: 'Ultra-fast lightweight coding' },
    ]
  },
  {
    name: 'Fireworks AI', iconKey: 'fireworks', color: '#ff6b6b',
    models: [
      { alias: 'fireworks-deepseek-v4-pro', model: 'fireworks/accounts/fireworks/models/deepseek-v4-pro', desc: 'DeepSeek V4 Pro on Fireworks', use: 'Complex reasoning, 1M context' },
      { alias: 'fireworks-deepseek-v3.2', model: 'fireworks/accounts/fireworks/models/deepseek-v3p2', desc: 'DeepSeek V3.2 on Fireworks', use: 'Cost-effective coding on fast infra' },
      { alias: 'fireworks-qwen3.6-plus', model: 'fireworks/accounts/fireworks/models/qwen3p6-plus', desc: 'Qwen 3.6 Plus on Fireworks', use: 'Multilingual coding, vision' },
      { alias: 'fireworks-glm-5', model: 'fireworks/accounts/fireworks/models/glm-5', desc: 'GLM-5 on Fireworks', use: 'Bilingual coding, reasoning' },
    ]
  },
  {
    name: 'Together AI', iconKey: 'together', color: '#4493f8',
    models: [
      { alias: 'together-deepseek-v4-pro', model: 'together_ai/deepseek-ai/DeepSeek-V4-Pro', desc: 'DeepSeek V4 Pro on Together', use: 'Complex reasoning, 512K context' },
      { alias: 'together-qwen3-coder', model: 'together_ai/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8', desc: 'Qwen 3 Coder on Together', use: 'Code generation, large codebases' },
      { alias: 'together-qwen3.5-397b', model: 'together_ai/Qwen/Qwen3.5-397B-A17B', desc: 'Qwen 3.5 397B on Together', use: 'Complex reasoning, vision coding' },
      { alias: 'together-llama-3.3-70b', model: 'together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo', desc: 'Llama 3.3 70B Turbo on Together', use: 'Fast open-weight coding' },
    ]
  },
  {
    name: 'Hugging Face', iconKey: 'huggingface', color: '#ffd21e',
    models: [
      { alias: 'hf-deepseek-r1', model: 'huggingface/deepseek-ai/DeepSeek-R1-0528', desc: 'DeepSeek R1 on HF Inference', use: 'Reasoning tasks, research' },
      { alias: 'hf-qwen3-coder', model: 'huggingface/Qwen/Qwen3-Coder-480B-A35B-Instruct', desc: 'Qwen 3 Coder on HF Inference', use: 'Code generation, large codebases' },
      { alias: 'hf-glm-5.1', model: 'huggingface/zai-org/GLM-5.1', desc: 'GLM-5.1 on HF Inference', use: 'Bilingual coding, reasoning' },
      { alias: 'hf-kimi-k2.6', model: 'huggingface/moonshotai/Kimi-K2.6', desc: 'Kimi K2.6 on HF Inference', use: 'Vision coding, reasoning' },
    ]
  },
  {
    name: 'Perplexity', iconKey: 'perplexity', color: '#20b8cd',
    models: [
      { alias: 'sonar-pro', model: 'perplexity/sonar-pro', desc: 'Sonar Pro — web-augmented, 200K context', use: 'Research, web-grounded coding' },
      { alias: 'sonar-reasoning-pro', model: 'perplexity/sonar-reasoning-pro', desc: 'Sonar Reasoning Pro — web + reasoning', use: 'Research with step-by-step reasoning' },
      { alias: 'sonar', model: 'perplexity/sonar', desc: 'Sonar — fast web search model', use: 'Quick web-grounded queries' },
      { alias: 'sonar-deep-research', model: 'perplexity/sonar-deep-research', desc: 'Sonar Deep Research — thorough search', use: 'Deep research, comprehensive analysis' },
    ]
  },
  {
    name: 'NVIDIA', iconKey: 'nvidia', color: '#76b900',
    models: [
      { alias: 'nvidia-deepseek-r1', model: 'nvidia/deepseek-ai/deepseek-r1', desc: 'DeepSeek R1 on NVIDIA NIM', use: 'Reasoning on GPU-optimized infra' },
      { alias: 'nvidia-llama-4-scout', model: 'nvidia/meta/llama-4-scout-17b-16e-instruct', desc: 'Llama 4 Scout on NVIDIA NIM', use: 'Fast open-weight with vision' },
      { alias: 'nvidia-nemotron-super', model: 'nvidia/nvidia/nemotron-3-super-120b-a12b', desc: 'Nemotron 3 Super 120B', use: 'NVIDIA\'s flagship model, reasoning' },
      { alias: 'nvidia-phi-4-mini', model: 'nvidia/microsoft/phi-4-mini-instruct', desc: 'Phi-4 Mini on NVIDIA NIM', use: 'Lightweight coding on fast infra' },
    ]
  },
  {
    name: 'Cloudflare Workers AI', iconKey: 'cloudflare', color: '#f48120',
    models: [
      { alias: 'cf-gpt-oss-120b', model: 'cloudflare/@cf/openai/gpt-oss-120b', desc: 'GPT OSS 120B on Cloudflare edge', use: 'Edge inference, serverless coding' },
      { alias: 'cf-llama-4-scout', model: 'cloudflare/@cf/meta/llama-4-scout-17b-16e-instruct', desc: 'Llama 4 Scout on Cloudflare', use: 'Edge coding with vision' },
      { alias: 'cf-gemma-4-26b', model: 'cloudflare/@cf/google/gemma-4-26b-a4b-it', desc: 'Gemma 4 26B on Cloudflare', use: 'Open-weight edge inference' },
      { alias: 'cf-glm-4.7-flash', model: 'cloudflare/@cf/zai-org/glm-4.7-flash', desc: 'GLM-4.7 Flash on Cloudflare', use: 'Fast edge reasoning' },
    ]
  },
  {
    name: 'Amazon Bedrock', iconKey: 'aws', color: '#ff9900',
    models: [
      { alias: 'nova-pro', model: 'bedrock/amazon.nova-pro-v1:0', desc: 'Amazon Nova Pro — capable multimodal', use: 'Enterprise coding, AWS integration' },
      { alias: 'nova-lite', model: 'bedrock/amazon.nova-lite-v1:0', desc: 'Amazon Nova Lite — cost-effective', use: 'Budget coding, AWS native' },
      { alias: 'nova-micro', model: 'bedrock/amazon.nova-micro-v1:0', desc: 'Amazon Nova Micro — ultra-cheap', use: 'Ultra-budget, simple tasks' },
    ]
  },
  {
    name: 'OpenRouter', iconKey: 'openrouter', color: '#6366f1',
    models: [
      { alias: 'or-gpt4o', model: 'openrouter/openai/gpt-4o', desc: 'GPT-4o via OpenRouter', use: 'Multi-model routing, cost optimization' },
      { alias: 'or-claude', model: 'openrouter/anthropic/claude-sonnet-4', desc: 'Claude via OpenRouter', use: 'Claude without direct API key' },
      { alias: 'or-deepseek', model: 'openrouter/deepseek/deepseek-chat', desc: 'DeepSeek via OpenRouter', use: 'Budget coding via router' },
      { alias: 'free-router', model: 'openrouter/openrouter/free', desc: 'Free model router — no credit card', use: 'Free tier, zero cost coding' },
    ]
  },
  {
    name: 'Local (Ollama / LM Studio)', iconKey: 'local', color: '#00ff88',
    models: [
      { alias: 'ollama-llama3.3', model: 'ollama/llama3.3', desc: 'Llama 3.3 via Ollama (local)', use: 'Free, offline, private coding' },
      { alias: 'ollama-deepseek-r1', model: 'ollama/deepseek-r1', desc: 'DeepSeek R1 via Ollama', use: 'Free, offline reasoning' },
      { alias: 'ollama-qwen2.5-coder', model: 'ollama/qwen2.5-coder', desc: 'Qwen 2.5 Coder via Ollama', use: 'Free, offline code specialist' },
      { alias: 'ollama-codellama', model: 'ollama/codellama', desc: 'Code Llama via Ollama', use: 'Free, offline code generation' },
      { alias: 'ollama-phi4', model: 'ollama/phi4', desc: 'Phi-4 via Ollama', use: 'Free, offline lightweight coding' },
      { alias: 'ollama-gemma2', model: 'ollama/gemma2', desc: 'Gemma 2 via Ollama', use: 'Free, offline, Google open weights' },
      { alias: 'lm-studio', model: 'lm_studio/your-model', desc: 'Any model via LM Studio', use: 'Free, offline, any GGUF model' },
    ]
  },
]

const COST_COMPARISON = [
  { model: 'GPT-5', provider: 'openai', input: '$1.25', output: '$10.00', speed: 'Fast', best: 'General coding' },
  { model: 'GPT-5 Mini', provider: 'openai', input: '$0.25', output: '$2.00', speed: 'Very Fast', best: 'Budget coding' },
  { model: 'GPT-5 Nano', provider: 'openai', input: '$0.05', output: '$0.40', speed: 'Very Fast', best: 'Ultra-budget' },
  { model: 'GPT-4o', provider: 'openai', input: '$2.50', output: '$10.00', speed: 'Fast', best: 'General coding' },
  { model: 'GPT-4o Mini', provider: 'openai', input: '$0.15', output: '$0.60', speed: 'Very Fast', best: 'Budget coding' },
  { model: 'Claude Sonnet 4.6', provider: 'anthropic', input: '$3.00', output: '$15.00', speed: 'Fast', best: 'Code quality' },
  { model: 'Claude Opus 4.7', provider: 'anthropic', input: '$5.00', output: '$25.00', speed: 'Medium', best: 'Complex tasks' },
  { model: 'Claude Haiku 4.5', provider: 'anthropic', input: '$1.00', output: '$5.00', speed: 'Very Fast', best: 'Quick edits' },
  { model: 'Gemini 2.5 Pro', provider: 'google', input: '$1.25', output: '$10.00', speed: 'Fast', best: 'Long context' },
  { model: 'Gemini 2.5 Flash', provider: 'google', input: '$0.30', output: '$2.50', speed: 'Very Fast', best: 'Fast coding' },
  { model: 'DeepSeek V4 Flash', provider: 'deepseek', input: '$0.14', output: '$0.28', speed: 'Fast', best: 'Best value' },
  { model: 'DeepSeek V4 Pro', provider: 'deepseek', input: '$1.74', output: '$3.48', speed: 'Medium', best: 'Reasoning' },
  { model: 'Grok 4 Fast', provider: 'xai', input: '$0.20', output: '$0.50', speed: 'Very Fast', best: 'Fast reasoning' },
  { model: 'Mistral Large 3', provider: 'mistral', input: '$0.50', output: '$1.50', speed: 'Fast', best: 'Balanced coding' },
  { model: 'Qwen3 Coder Plus', provider: 'alibaba', input: '$1.00', output: '$5.00', speed: 'Fast', best: 'Code specialist' },
  { model: 'Command A', provider: 'cohere', input: '$2.50', output: '$10.00', speed: 'Fast', best: 'Enterprise RAG' },
  { model: 'Ollama (Local)', provider: 'local', input: 'Free', output: 'Free', speed: 'Varies', best: 'Privacy/offline' },
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
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />170+ Models</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Every <span className="animated-gradient-text">Model</span>, One CLI</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Use any LLM from any provider. Switch models mid-session without losing context. All via litellm.</p>
              {/* Provider Logo Row */}
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                {PROVIDERS.map(p => {
                  const IconComp = PROVIDER_ICONS[p.iconKey]
                  return (
                    <div key={p.iconKey} className="flex flex-col items-center gap-1.5 group" title={p.name}>
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center border border-border/50 bg-card/30 group-hover:bg-card/60 transition-colors">
                        {IconComp && <IconComp size={26} />}
                      </div>
                      <span className="text-[0.6rem] font-mono text-muted-foreground group-hover:text-foreground transition-colors">{p.name.split(' ')[0]}</span>
                    </div>
                  )
                })}
              </div>
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
            {PROVIDERS.map((provider, i) => {
              const IconComp = PROVIDER_ICONS[provider.iconKey]
              return (
                <motion.div key={provider.name} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.05 }}>
                  <div className="rounded-xl border border-border/50 bg-card/30 overflow-hidden">
                    <button onClick={() => setExpandedProvider(expandedProvider === provider.name ? null : provider.name)} className="w-full flex items-center justify-between p-5 hover:bg-card/50 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center border border-border/30 bg-card/50 shrink-0" style={{ borderColor: `${provider.color}30` }}>
                          {IconComp && <IconComp size={24} />}
                        </div>
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
                                <div className="flex items-center gap-2">
                                  <div className="w-6 h-6 rounded flex items-center justify-center" style={{ backgroundColor: `${provider.color}15` }}>
                                    {IconComp && <IconComp size={14} />}
                                  </div>
                                  <code className="text-sm font-mono font-bold text-apex-cyan">{m.alias}</code>
                                </div>
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
              )
            })}
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
                <tbody>{COST_COMPARISON.map((row, i) => {
                  const IconComp = PROVIDER_ICONS[row.provider]
                  return (
                    <tr key={row.model} className={`border-b border-border/30 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>
                      <td className="p-3 font-mono font-bold text-foreground flex items-center gap-2">
                        {IconComp && <span className="shrink-0"><IconComp size={16} /></span>}
                        {row.model}
                      </td>
                      <td className="p-3 font-mono text-muted-foreground">{row.input}</td>
                      <td className="p-3 font-mono text-muted-foreground">{row.output}</td>
                      <td className="p-3 font-mono text-muted-foreground">{row.speed}</td>
                      <td className="p-3 font-mono text-muted-foreground">{row.best}</td>
                    </tr>
                  )
                })}</tbody>
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
