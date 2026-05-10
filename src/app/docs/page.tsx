'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Zap, Shield, Bot, Copy, Check, ArrowRight,
  Github, Cpu, Wrench, Users, BookOpen, Box, Settings,
  Puzzle, AlertCircle, Layers, Code2, Hash, Menu, X,
  ChevronRight, Activity, GitBranch, Lock
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
            <a href="/install" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Install</a>
            <a href="/docs" className="text-sm text-apex-cyan transition-colors">Docs</a>
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
      {open && <div className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border px-4 py-4 space-y-3">{[{ href: '/', label: 'Home' }, { href: '/install', label: 'Install' }, { href: '/docs', label: 'Docs' }, { href: '/agents', label: 'Agents' }, { href: '/models', label: 'Models' }, { href: '/tools', label: 'Tools' }, { href: '/activity', label: 'Activity' }, { href: '/roadmap', label: 'Roadmap' }, { href: '/contribute', label: 'Contribute' }].map(l => <a key={l.href} href={l.href} className="block text-sm text-muted-foreground hover:text-foreground py-1">{l.label}</a>)}</div>}
    </nav>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border py-8 mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-xs text-muted-foreground font-mono">MIT License. Built in Gabon 🇬🇦 by <a href="https://github.com/Ggboykxz" target="_blank" className="text-apex-cyan hover:underline">Ggboykxz</a></p>
        <div className="flex items-center gap-6">
          <a href="/docs" className="text-xs text-muted-foreground hover:text-foreground">Docs</a>
          <a href="/install" className="text-xs text-muted-foreground hover:text-foreground">Install</a>
          <a href="/agents" className="text-xs text-muted-foreground hover:text-foreground">Agents</a>
          <a href="/models" className="text-xs text-muted-foreground hover:text-foreground">Models</a>
          <a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a>
        </div>
      </div>
    </footer>
  )
}

/* ──── HELPERS ──── */
function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="relative group my-4 rounded-lg border border-border/50 bg-[#0a0e14] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30">
        <span className="text-xs text-muted-foreground font-mono">{language}</span>
        <button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">{copied ? <Check className="w-3.5 h-3.5 text-apex-green" /> : <Copy className="w-3.5 h-3.5" />}</button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono leading-6 text-muted-foreground"><code>{code}</code></pre>
    </div>
  )
}

function DocsTable({ rows, headers }: { rows: string[][]; headers: string[] }) {
  return (
    <div className="my-4 overflow-x-auto rounded-lg border border-border/50">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-border/50 bg-card/50">{headers.map((h, i) => <th key={i} className="text-left p-3 font-mono text-muted-foreground">{h}</th>)}</tr></thead>
        <tbody>{rows.map((row, i) => <tr key={i} className={`border-b border-border/30 ${i % 2 === 0 ? 'bg-card/20' : ''}`}>{row.map((cell, j) => <td key={j} className="p-3 font-mono text-muted-foreground">{cell.startsWith('`') ? <code className="text-apex-cyan">{cell.replace(/`/g, '')}</code> : cell.startsWith('✅') ? <span className="text-apex-green">{cell}</span> : cell.startsWith('❌') ? <span className="text-apex-red">{cell}</span> : cell}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}

function DocsHeading({ children, id }: { children: React.ReactNode; id?: string }) {
  return <h3 id={id} className="text-xl font-bold font-mono mt-10 mb-4 flex items-center gap-2 group scroll-mt-20">{children}{id && <Hash className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />}</h3>
}

/* ──── DOC SECTIONS ──── */
type DocSection = 'overview' | 'quickstart' | 'configuration' | 'commands' | 'advanced' | 'plugins' | 'api' | 'troubleshooting'

const DOC_NAV: { id: DocSection; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: BookOpen },
  { id: 'quickstart', label: 'Quick Start', icon: Zap },
  { id: 'configuration', label: 'Configuration', icon: Settings },
  { id: 'commands', label: 'Commands', icon: Terminal },
  { id: 'advanced', label: 'Advanced', icon: Layers },
  { id: 'plugins', label: 'Plugins', icon: Puzzle },
  { id: 'api', label: 'API Reference', icon: Code2 },
  { id: 'troubleshooting', label: 'Troubleshooting', icon: AlertCircle },
]

function DocOverview() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2 animated-gradient-text">APEX Documentation</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Built in Gabon 🇬🇦 for the world. APEX is a production-grade, terminal-native AI coding agent that works with <strong className="text-foreground">any LLM</strong> via a unified interface powered by litellm.</p>
      <DocsHeading id="features">Features</DocsHeading>
      <div className="grid sm:grid-cols-2 gap-3">
        {[['100+ Models', 'Claude, GPT-4, Gemini, Grok, DeepSeek, Qwen, Llama, Mistral, and more'], ['Multi-Agent System', 'Build, Plan, Explore, General, YOLO with permission controls'], ['75+ Tools', 'File ops, git, web, sandbox, MCP, LSP, refactoring, Docker, DB'], ['Rich Terminal UI', 'Syntax highlighting, markdown rendering, panels, command palette'], ['Session Persistence', 'Save and load conversations, bookmark positions, share links'], ['Token Cost Tracking', 'Monitor usage and estimated costs in real-time'], ['Plugin System', 'Extensible with custom tools and hooks'], ['Undo/Redo', 'Revert and reapply changes with full history'], ['LSP Integration', 'Go to definition, references, hover, diagnostics'], ['Security System', 'Permission rulesets, rate limiting, shell security, API key management']].map(([title, desc]) => (
          <div key={title} className="p-3 rounded-lg border border-border/50 bg-card/30"><span className="text-apex-cyan font-mono font-bold text-sm">{title}</span><p className="text-muted-foreground text-xs mt-1">{desc}</p></div>
        ))}
      </div>
      <DocsHeading id="comparison">Why APEX?</DocsHeading>
      <DocsTable headers={['Feature', 'APEX', 'OpenCode', 'Claude Code', 'Aider']} rows={[['All models via one CLI', '✅', '⚠️', '❌', '⚠️'], ['No cloud lock-in', '✅', '❌', '❌', '✅'], ['Offline (Ollama)', '✅', '❌', '❌', '✅'], ['Rich syntax UI', '✅', '✅', '✅', '❌'], ['Session persistence', '✅', '❌', '✅', '❌'], ['Plugin system', '✅', '❌', '❌', '❌'], ['Model switch mid-session', '✅', '❌', '❌', '⚠️'], ['Token cost tracking', '✅', '❌', '❌', '✅'], ['French/multilingual UI', '✅', '❌', '❌', '❌']]} />
      <DocsHeading id="philosophy">Philosophy</DocsHeading>
      <p className="text-muted-foreground leading-relaxed">APEX is built by a Gabonese developer for the world. Every developer deserves a world-class coding agent — regardless of which model they can afford. The core principles are: <strong className="text-foreground">complete code, no truncation</strong>, <strong className="text-foreground">production-ready</strong> with full error handling, tests, and type hints, <strong className="text-foreground">language-agnostic</strong> support for Python, JavaScript, Rust, Go, and more, and a <strong className="text-foreground">senior developer mindset</strong> that is opinionated but effective.</p>
      <div className="mt-8 grid sm:grid-cols-3 gap-4">
        {[{ href: '/agents', title: 'Agents Guide', desc: '5 specialized agents with permissions' }, { href: '/models', title: 'Models Guide', desc: '100+ models from every provider' }, { href: '/tools', title: 'Tools Reference', desc: '75+ built-in tools catalog' }].map(l => (
          <a key={l.href} href={l.href} className="group p-4 rounded-lg border border-border/50 bg-card/30 hover:border-apex-cyan/30 transition-all"><h4 className="font-mono font-bold text-apex-cyan mb-1">{l.title}</h4><p className="text-xs text-muted-foreground">{l.desc}</p><ArrowRight className="w-4 h-4 mt-2 text-muted-foreground group-hover:text-apex-cyan transition-colors" /></a>
        ))}
      </div>
    </div>
  )
}

function DocQuickstart() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Quick Start</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Get up and running with APEX in 5 minutes.</p>
      <DocsHeading id="step1">Step 1: Installation</DocsHeading>
      <CodeBlock code="pip install apex-agent" />
      <p className="text-muted-foreground text-sm">Or use pipx for isolated installation: <code className="text-apex-cyan">pipx install apex-agent</code></p>
      <DocsHeading id="step2">Step 2: Configure API Keys</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Create <code className="text-apex-cyan">~/.apex/.env</code> with your API keys:</p>
      <CodeBlock code={`# At least one of these:\nANTHROPIC_API_KEY=sk-ant-...    # For Claude models\nOPENAI_API_KEY=sk-...          # For GPT models\nDEEPSEEK_API_KEY=...           # For DeepSeek models\nGEMINI_API_KEY=...             # For Gemini models`} />
      <div className="p-3 rounded-lg border border-apex-yellow/20 bg-apex-yellow/5 text-sm text-muted-foreground my-4">💡 <strong className="text-foreground">Tip:</strong> Start with a free model like <code className="text-apex-cyan">deepseek-chat</code> or <code className="text-apex-cyan">gpt-4o-mini</code></div>
      <DocsHeading id="step3">Step 3: First Launch</DocsHeading>
      <CodeBlock code="apex" />
      <DocsHeading id="step4">Step 4: Try Your First Command</DocsHeading>
      <CodeBlock language="text" code={`› What is the current directory?\n› Read the file main.py\n› Create a hello.py file that prints "Hello World"`} />
      <DocsHeading id="workflow">Basic Workflow</DocsHeading>
      <CodeBlock language="text" code={`# Switch models mid-session\n› /model gpt-4o\n\n# Check git status\n› /git\n\n# Analyze project\n› /map\n\n# Save your session\n› /save my-project`} />
      <DocsHeading id="common-commands">Common Commands</DocsHeading>
      <DocsTable headers={['Command', 'What it does']} rows={[['/help', 'Show all commands'], ['/models', 'List available models'], ['/agent build', 'Switch to build agent'], ['/agent plan', 'Switch to plan (read-only) agent'], ['@filename', 'Include file in context'], ['/clear', 'Clear conversation history'], ['/exit', 'Exit APEX']]} />
    </div>
  )
}

function DocConfiguration() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Configuration</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Customize APEX to fit your workflow.</p>
      <DocsHeading id="config-file">Config File</DocsHeading>
      <CodeBlock language="json" code={`{\n  "model": "claude-sonnet",\n  "cwd": "/home/user/projects",\n  "theme": "monokai",\n  "max_tool_rounds": 20,\n  "auto_commit": false\n}`} />
      <DocsHeading id="settings">Settings</DocsHeading>
      <DocsTable headers={['Setting', 'Default', 'Description']} rows={[['model', 'claude-sonnet', 'Default model alias'], ['cwd', 'current directory', 'Working directory'], ['theme', 'monokai', 'Syntax highlighting theme'], ['max_tool_rounds', '20', 'Max tool calls per message'], ['auto_commit', 'false', 'Auto git commit after changes']]} />
      <DocsHeading id="cli-options">CLI Options</DocsHeading>
      <CodeBlock code={`apex --model gpt-4o          # Use specific model\napex --cwd /path/to/project  # Set working directory\napex --stream                # Enable streaming\napex --auto-commit           # Auto commit changes\napex --list-models           # List available models`} />
      <DocsHeading id="env-vars">Environment Variables</DocsHeading>
      <DocsTable headers={['Variable', 'Description']} rows={[['ANTHROPIC_API_KEY', 'Anthropic/Claude API key'], ['OPENAI_API_KEY', 'OpenAI API key'], ['GROQ_API_KEY', 'Groq API key'], ['MISTRAL_API_KEY', 'Mistral API key'], ['DEEPSEEK_API_KEY', 'DeepSeek API key'], ['GEMINI_API_KEY', 'Google Gemini API key'], ['COHERE_API_KEY', 'Cohere API key']]} />
    </div>
  )
}

function DocCommands() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Commands</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">APEX provides slash commands, keyboard shortcuts, and @mentions for powerful interaction.</p>
      <DocsHeading id="agent-cmds">Agent Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[['/agent [name]', 'Switch to a different agent'], ['/agents', 'List all available agents'], ['/subagents', 'List all subagents']]} />
      <DocsHeading id="model-cmds">Model Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[['/model &lt;alias&gt;', 'Switch to a different model'], ['/models', 'List all available models']]} />
      <DocsHeading id="session-cmds">Session Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[['/save [name]', 'Save current session'], ['/load &lt;name&gt;', 'Load a previous session'], ['/sessions', 'List saved sessions'], ['/share', 'Generate share link'], ['/clear', 'Clear conversation history'], ['/history', 'Show conversation history'], ['/cost', 'Show token usage and cost']]} />
      <DocsHeading id="git-cmds">Git Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[['/git', 'Show git status'], ['/branch', 'Show current branch'], ['/branches', 'List all branches'], ['/checkout &lt;branch&gt;', 'Switch to branch'], ['/commit &lt;message&gt;', 'Commit changes']]} />
      <DocsHeading id="analysis-cmds">Analysis Commands</DocsHeading>
      <DocsTable headers={['Command', 'Description']} rows={[['/map', 'Show repository map'], ['/stats', 'Show language statistics'], ['/analyze', 'Analyze project structure']]} />
      <DocsHeading id="memory-cmds">Memory Commands</DocsHeading>
      <CodeBlock code={`# Add a fact\n/memory add "Project uses FastAPI" python,fastapi\n\n# Search memory\n/memory search python\n\n# Clear memory\n/memory clear`} />
      <DocsHeading id="mentions">@Mentions</DocsHeading>
      <DocsTable headers={['Syntax', 'Description']} rows={[['@README.md', 'Read and include file content'], ['@src/main.py', 'Include specific file'], ['@*.json', 'Include all JSON files'], ['@explore "Find all API endpoints"', 'Invoke explore subagent'], ['@general "Search for auth logic"', 'Invoke general subagent']]} />
      <DocsHeading id="shortcuts">Keyboard Shortcuts</DocsHeading>
      <DocsTable headers={['Shortcut', 'Action']} rows={[['Tab', 'Cycle through agents'], ['Ctrl+C', 'Cancel current operation'], ['Ctrl+L', 'Clear screen'], ['Ctrl+D', 'Exit APEX'], ['Up/Down', 'Navigate command history']]} />
    </div>
  )
}

function DocAdvanced() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Advanced</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">MCP, custom tools, workspace awareness, context management, and more.</p>
      <DocsHeading id="mcp">MCP (Model Context Protocol)</DocsHeading>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nmcp_servers:\n  filesystem:\n    command: npx\n    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]\n    enabled: true\n  github:\n    command: npx\n    args: ["-y", "@modelcontextprotocol/server-github"]\n    env:\n      GITHUB_TOKEN: your_token_here\n    enabled: true`} />
      <DocsHeading id="lsp">LSP Integration</DocsHeading>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\nlsp_servers:\n  python:\n    command: ["pylsp"]\n    enabled: true\n  typescript:\n    command: ["typescript-language-server", "--stdio"]\n    enabled: true\n  go:\n    command: ["gopls"]\n    enabled: true\n  rust:\n    command: ["rust-analyzer"]\n    enabled: true`} />
      <DocsHeading id="custom-tools">Custom Tools</DocsHeading>
      <CodeBlock language="yaml" code={`# .apex/config.yaml\ncustom_tools:\n  deploy:\n    description: Deploy to production\n    enabled: true\n    command: "kubectl apply -f {manifest}"`} />
      <DocsHeading id="sandbox">Sandbox Execution</DocsHeading>
      <p className="text-muted-foreground text-sm mb-2">Run code safely in isolated environments. Supports Python, JavaScript, Bash, Ruby, Go, and Rust.</p>
      <CodeBlock language="python" code={`from apex.sandbox import sandbox\nresult = sandbox.run_code("print('hello')", "python")`} />
      <DocsHeading id="context-management">Context Management</DocsHeading>
      <CodeBlock language="python" code={`from apex.context_manager import ContextWindow\ncw = ContextWindow(\n    max_tokens=100000,\n    compress_threshold=0.8,\n    summary_messages=50\n)`} />
    </div>
  )
}

function DocPlugins() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Plugins</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Extend APEX with custom plugins and hooks.</p>
      <DocsHeading id="built-in">Built-in Plugins</DocsHeading>
      <div className="space-y-4 mb-8">
        <div className="p-4 rounded-lg border border-border/50 bg-card/30"><h4 className="font-bold font-mono text-apex-cyan mb-2">Logger Plugin</h4><p className="text-muted-foreground text-sm">Logs all tool calls and agent messages for debugging.</p></div>
        <div className="p-4 rounded-lg border border-border/50 bg-card/30"><h4 className="font-bold font-mono text-apex-green mb-2">Security Scanner Plugin</h4><p className="text-muted-foreground text-sm">Scans code for security vulnerabilities before execution.</p></div>
      </div>
      <DocsHeading id="custom-plugins">Custom Plugins</DocsHeading>
      <CodeBlock language="python" code={`from apex.plugins import PluginBase, PluginInfo, PluginManager\n\nclass MyPlugin(PluginBase):\n    info = PluginInfo(\n        name="my-plugin",\n        version="0.1.0",\n        description="My custom plugin"\n    )\n    def initialize(self, app):\n        self.app = app\n        app.plugin_manager.register_hook("tool_call", self.on_tool_call)\n    def on_tool_call(self, tool_name, args):\n        print(f"Tool called: {tool_name}")`} />
      <DocsHeading id="hooks">Hooks</DocsHeading>
      <DocsTable headers={['Hook', 'Description', 'Parameters']} rows={[['agent_start', 'Agent initialized', 'model, agent'], ['agent_message', 'New message', 'message'], ['tool_call', 'Tool about to run', 'tool_name, args'], ['tool_result', 'Tool completed', 'tool_name, result'], ['before_tool_call', 'Before tool execution', 'tool_name, args'], ['error', 'Error occurred', 'error_type, message']]} />
    </div>
  )
}

function DocAPI() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">API Reference</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Core modules and their public APIs.</p>
      <DocsHeading id="agent-api">apex.agent</DocsHeading>
      <CodeBlock language="python" code={`from apex.agent import Agent\nagent = Agent(\n    model="claude-4-sonnet",\n    cwd="/path/to/project",\n    max_rounds=20,\n    temperature=0.3,\n)`} />
      <DocsTable headers={['Method', 'Description']} rows={[['run(message)', 'Run agent with user message'], ['run_stream(message)', 'Run with streaming response'], ['execute(tool, args)', 'Execute a specific tool'], ['add_tool(tool)', 'Add custom tool'], ['clear_history()', 'Clear conversation history'], ['save_session(name)', 'Save session to disk'], ['load_session(name)', 'Load session from disk'], ['set_agent(name)', 'Switch to different agent']]} />
      <DocsHeading id="tools-api">apex.tools</DocsHeading>
      <CodeBlock language="python" code={`from apex.tools import ToolExecutor\nexecutor = ToolExecutor(cwd="/project")\nresult = executor.execute("read_file", {"path": "main.py"})`} />
      <DocsHeading id="mcp-api">apex.mcp</DocsHeading>
      <CodeBlock language="python" code={`from apex.mcp import MCPClient\nclient = MCPClient(name="myserver", command="npx", args=["-y", "server-package"])\nawait client.connect()\ntools = await client.list_tools()\nresult = await client.call_tool("tool_name", args)\nawait client.close()`} />
      <DocsHeading id="workspace-api">apex.workspace</DocsHeading>
      <CodeBlock language="python" code={`from apex.workspace import Workspace\nws = Workspace(cwd="/project")\nws.is_git_repo       # bool\nws.current_branch    # str\nws.language          # str | None\nws.package_manager   # str | None`} />
    </div>
  )
}

function DocTroubleshooting() {
  return (
    <div>
      <h1 className="text-3xl font-bold font-mono mb-2">Troubleshooting</h1>
      <p className="text-muted-foreground text-lg mb-8 leading-relaxed">Common issues and solutions.</p>
      <DocsHeading id="install-issues">Installation Issues</DocsHeading>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4"><h4 className="font-bold font-mono text-apex-red mb-2">&quot;command not found: apex&quot;</h4><CodeBlock code={`pip show apex-agent\npip install --upgrade apex-agent\n# Or use: python -m apex.main --version`} /></div>
      <DocsHeading id="api-issues">API Key Issues</DocsHeading>
      <div className="p-4 rounded-lg border border-border/50 bg-card/30 mb-4"><h4 className="font-bold font-mono text-apex-yellow mb-2">&quot;Authentication failed&quot;</h4><CodeBlock code={`echo $ANTHROPIC_API_KEY\nexport ANTHROPIC_API_KEY="sk-ant-..."`} /></div>
      <DocsHeading id="perf-issues">Performance Issues</DocsHeading>
      <ul className="list-disc list-inside text-muted-foreground space-y-2">
        <li>Use smaller models: <code className="text-apex-cyan">/model gpt-4o-mini</code></li>
        <li>Use streaming: <code className="text-apex-cyan">apex --stream</code></li>
        <li>Reduce history: <code className="text-apex-cyan">/clear</code></li>
      </ul>
      <DocsHeading id="getting-help">Getting Help</DocsHeading>
      <CodeBlock code={`apex --verbose "your prompt"\nls ~/.apex/logs/`} />
    </div>
  )
}

const DOC_CONTENT: Record<DocSection, React.ReactNode> = {
  overview: <DocOverview />, quickstart: <DocQuickstart />, configuration: <DocConfiguration />, commands: <DocCommands />, advanced: <DocAdvanced />, plugins: <DocPlugins />, api: <DocAPI />, troubleshooting: <DocTroubleshooting />,
}

/* ──── MAIN ──── */
export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState<DocSection>('overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />
      <div className="flex flex-1 pt-16">
        <aside className={`fixed md:sticky top-16 left-0 bottom-0 z-40 w-64 shrink-0 border-r border-border bg-background overflow-y-auto transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
          <div className="p-4">
            <h3 className="text-xs font-mono font-bold text-muted-foreground uppercase tracking-wider mb-3">Documentation</h3>
            <nav className="space-y-1">
              {DOC_NAV.map(item => (
                <button key={item.id} onClick={() => { setActiveDoc(item.id); setSidebarOpen(false); window.scrollTo(0, 0) }} className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-mono transition-all ${activeDoc === item.id ? 'bg-apex-cyan/10 text-apex-cyan border border-apex-cyan/20' : 'text-muted-foreground hover:text-foreground hover:bg-card'}`}>
                  <item.icon className="w-4 h-4 shrink-0" />{item.label}
                </button>
              ))}
            </nav>
            <div className="mt-6 pt-4 border-t border-border/50">
              <h3 className="text-xs font-mono font-bold text-muted-foreground uppercase tracking-wider mb-3">Detailed Guides</h3>
              <nav className="space-y-1">
                {[{ href: '/install', label: 'Installation Guide', icon: Box }, { href: '/agents', label: 'Agents', icon: Bot }, { href: '/models', label: 'Models', icon: Cpu }, { href: '/tools', label: 'Tools', icon: Wrench }, { href: '/security', label: 'Security', icon: Shield }].map(l => (
                  <a key={l.href} href={l.href} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-mono text-muted-foreground hover:text-foreground hover:bg-card transition-all"><l.icon className="w-4 h-4 shrink-0" />{l.label}</a>
                ))}
              </nav>
            </div>
          </div>
        </aside>
        {sidebarOpen && <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setSidebarOpen(false)} />}
        <main className="flex-1 min-w-0 px-4 sm:px-8 md:px-12 lg:px-16 py-8">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="md:hidden flex items-center gap-2 text-sm text-muted-foreground mb-6 hover:text-foreground"><Menu className="w-4 h-4" /> Navigation</button>
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-6">
              <a href="/" className="hover:text-foreground transition-colors">APEX</a><ChevronRight className="w-3 h-3" /><span>Docs</span><ChevronRight className="w-3 h-3" /><span className="text-apex-cyan">{DOC_NAV.find(d => d.id === activeDoc)?.label}</span>
            </div>
            <motion.div key={activeDoc} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              {DOC_CONTENT[activeDoc]}
            </motion.div>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}
