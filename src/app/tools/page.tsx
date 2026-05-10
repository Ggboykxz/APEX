'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Terminal, Github, Menu, X, Copy, Check, ArrowRight,
  Cpu, Bot, Wrench, BookOpen, Activity, GitBranch, Users,
  Shield, FileCode, Search, Globe, Play, Code2, Clock,
  Sparkles, Command, Layers, Zap, RotateCcw, Clipboard
} from 'lucide-react'

function NavBar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" className="w-7 h-7"><defs><linearGradient id="nav-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse"><stop offset="0%" stopColor="#00e5ff"/><stop offset="100%" stopColor="#00ff88"/></linearGradient></defs><polygon points="32,4 60,56 4,56" stroke="url(#nav-grad)" strokeWidth="4" fill="none" strokeLinejoin="round"/><circle cx="32" cy="40" r="4" fill="url(#nav-grad)"/></svg><span className="font-mono font-bold text-lg">APEX</span></a>
          <div className="hidden md:flex items-center gap-5"><a href="/#features" className="text-sm text-muted-foreground hover:text-foreground">Features</a><a href="/install" className="text-sm text-muted-foreground hover:text-foreground">Install</a><a href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</a><a href="/agents" className="text-sm text-muted-foreground hover:text-foreground">Agents</a><a href="/models" className="text-sm text-muted-foreground hover:text-foreground">Models</a><a href="/tools" className="text-sm text-apex-cyan">Tools</a><a href="/activity" className="text-sm text-muted-foreground hover:text-foreground">Activity</a><a href="/roadmap" className="text-sm text-muted-foreground hover:text-foreground">Roadmap</a><a href="/contribute" className="text-sm text-muted-foreground hover:text-foreground">Contribute</a><a href="https://github.com/Ggboykxz/APEX" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground"><Github className="w-4 h-4" /></a></div>
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

interface Tool {
  name: string; desc: string; params?: string; example: string
}

interface ToolCategory {
  name: string; icon: React.ElementType; color: string; count: number; tools: Tool[]
}

const TOOL_CATEGORIES: ToolCategory[] = [
  {
    name: 'File Operations', icon: FileCode, color: '#00e5ff', count: 12,
    tools: [
      { name: 'read_file', desc: 'Read a file with line numbers. Returns the full content with line-by-line numbering.', params: 'path: str, start_line?: int, end_line?: int', example: '"Read src/main.py"' },
      { name: 'write_file', desc: 'Create or overwrite a file with the given content. Creates parent directories automatically.', params: 'path: str, content: str', example: '"Create config.json with default settings"' },
      { name: 'edit_file', desc: 'Replace a unique string in a file. Finds the exact match and replaces it. Safer than write_file for targeted changes.', params: 'path: str, old_string: str, new_string: str', example: '"Fix the bug on line 42 in auth.py"' },
      { name: 'delete_file', desc: 'Delete a file or directory. Requires confirmation unless in YOLO mode.', params: 'path: str', example: '"Delete old_file.txt"' },
      { name: 'create_directory', desc: 'Create a directory tree. Creates all parent directories as needed.', params: 'path: str', example: '"Create src/utils/helpers/"' },
      { name: 'list_files', desc: 'List files and directories at the given path. Shows names, types, and sizes.', params: 'path: str, recursive?: bool', example: '"List all files in src/"' },
      { name: 'search_in_files', desc: 'Regex search across files. Returns matching lines with file paths and line numbers.', params: 'pattern: str, path?: str, file_pattern?: str', example: '"Find all TODO comments in the project"' },
      { name: 'glob_search', desc: 'Find files matching a glob pattern. Supports ** for recursive search.', params: 'pattern: str, path?: str', example: '"Find all .py files in src/"' },
      { name: 'apply_patch', desc: 'Apply a unified diff patch to a file. Precise multi-line edits.', params: 'path: str, patch: str', example: '"Apply the formatting patch to main.py"' },
      { name: 'batch_read', desc: 'Read multiple files at once. Efficient for reading several related files.', params: 'paths: list[str]', example: '"Read all config files"' },
      { name: 'get_file_tree', desc: 'Get the complete directory tree structure. Shows the full project hierarchy.', params: 'path?: str, max_depth?: int', example: '"Show the project structure"' },
      { name: 'diff_files', desc: 'Compare two files and show differences. Returns a unified diff.', params: 'path1: str, path2: str', example: '"Compare config.old and config.new"' },
    ]
  },
  {
    name: 'Search & Navigation', icon: Search, color: '#00ff88', count: 8,
    tools: [
      { name: 'search_in_files', desc: 'Regex search across the codebase. Fast full-text search with pattern matching.', params: 'pattern: str, path?: str', example: '"Search for all API endpoints"' },
      { name: 'glob_search', desc: 'Find files by name pattern. Supports wildcards and recursive search.', params: 'pattern: str', example: '"Find all test files (*test*.py)"' },
      { name: 'get_file_tree', desc: 'Show the complete directory tree with file sizes and types.', params: 'path?: str, max_depth?: int', example: '"Show project structure"' },
      { name: 'get_repo_map', desc: 'Generate a semantic map of the repository. Shows classes, functions, and their relationships.', params: 'path?: str', example: '"Map the project architecture"' },
      { name: 'read_image', desc: 'Read and analyze an image file. Returns description and metadata.', params: 'path: str', example: '"Analyze the screenshot in docs/demo.png"' },
    ]
  },
  {
    name: 'Git Integration', icon: GitBranch, color: '#ffaa00', count: 11,
    tools: [
      { name: 'git_status', desc: 'Show git working tree status. Lists modified, staged, and untracked files.', params: 'none', example: '"Show git status"' },
      { name: 'git_log', desc: 'Show recent commit history. Includes author, date, and message.', params: 'count?: int, branch?: str', example: '"Show last 10 commits"' },
      { name: 'git_diff', desc: 'Show changes in working tree or staged files. Displays unified diff output.', params: 'staged?: bool, file?: str', example: '"Show changes in auth.py"' },
      { name: 'git_branch', desc: 'Show current branch info or list all branches.', params: 'action: "list" | "current"', example: '"What branch am I on?"' },
      { name: 'git_remote', desc: 'Show remote repository information including URLs.', params: 'none', example: '"Show git remotes"' },
      { name: 'git_commit', desc: 'Stage all changes and commit with the given message.', params: 'message: str', example: '"Commit: Fix auth bug"' },
      { name: 'git_create_pr', desc: 'Create a pull request on the remote repository.', params: 'title: str, body?: str, base?: str', example: '"Create PR for feature branch"' },
      { name: 'git_checkout', desc: 'Switch to a different branch or restore files.', params: 'branch: str', example: '"Switch to develop branch"' },
      { name: 'git_fetch', desc: 'Fetch changes from the remote without merging.', params: 'remote?: str', example: '"Fetch latest from origin"' },
      { name: 'git_push', desc: 'Push local commits to the remote repository.', params: 'remote?: str, branch?: str', example: '"Push to origin"' },
      { name: 'git_pr', desc: 'View and manage pull requests.', params: 'action: "list" | "view", number?: int', example: '"List open PRs"' },
    ]
  },
  {
    name: 'Web & Network', icon: Globe, color: '#d946ef', count: 4,
    tools: [
      { name: 'web_search', desc: 'Search the web using the configured search engine. Returns relevant results with titles and URLs.', params: 'query: str, count?: int', example: '"Search for Python asyncio tutorial"' },
      { name: 'fetch_url', desc: 'Fetch and extract content from a URL. Returns cleaned text content.', params: 'url: str, max_length?: int', example: '"Read the documentation at https://..."' },
    ]
  },
  {
    name: 'Code Execution', icon: Play, color: '#ff4444', count: 6,
    tools: [
      { name: 'run_command', desc: 'Execute a shell command in the project directory. Subject to permission checks.', params: 'command: str, cwd?: str, timeout?: int', example: '"Run pytest tests/"' },
      { name: 'run_test', desc: 'Run the project test suite with the specified test runner.', params: 'path?: str, args?: str', example: '"Run all tests"' },
      { name: 'run_code', desc: 'Execute code in a sandboxed environment. Supports Python, JavaScript, Bash, Ruby, Go.', params: 'code: str, language: str', example: '"Test this Python snippet"' },
      { name: 'format_file', desc: 'Format a file using the appropriate formatter (black, prettier, etc.).', params: 'path: str', example: '"Format main.py with black"' },
      { name: 'install_package', desc: 'Install a package using the project package manager (pip, npm, cargo, etc.).', params: 'package: str, manager?: str', example: '"Install the requests library"' },
    ]
  },
  {
    name: 'LSP Integration', icon: Code2, color: '#00e5ff', count: 6,
    tools: [
      { name: 'lsp_definition', desc: 'Go to the definition of a symbol. Returns file path and line number.', params: 'file: str, line: int, column: int', example: '"Go to definition of authenticate()"' },
      { name: 'lsp_references', desc: 'Find all references to a symbol across the project.', params: 'file: str, line: int, column: int', example: '"Find all references to User class"' },
      { name: 'lsp_hover', desc: 'Show hover information for a symbol. Type info, docs, signature.', params: 'file: str, line: int, column: int', example: '"What type is this variable?"' },
      { name: 'lsp_diagnostics', desc: 'Get all errors and warnings for a file or the entire project.', params: 'file?: str', example: '"Show all errors in the project"' },
      { name: 'lsp_completion', desc: 'Get completion suggestions at a position.', params: 'file: str, line: int, column: int', example: '"Show completions for os.path."' },
      { name: 'lsp_rename', desc: 'Rename a symbol across the entire project safely.', params: 'file: str, line: int, column: int, new_name: str', example: '"Rename getUser to fetchUser"' },
    ]
  },
  {
    name: 'Session & History', icon: Clock, color: '#00ff88', count: 8,
    tools: [
      { name: 'bookmark_session', desc: 'Bookmark the current conversation position for later reference.', params: 'label?: str', example: '"Bookmark this point in the conversation"' },
      { name: 'search_history', desc: 'Search through previous conversation history.', params: 'query: str', example: '"Find where we discussed the auth module"' },
      { name: 'share_session', desc: 'Generate a shareable link for the current session.', params: 'none', example: '"Share this session with the team"' },
      { name: 'save_session', desc: 'Save the current session to disk for later resumption.', params: 'name: str', example: '"Save session as auth-refactor"' },
      { name: 'load_session', desc: 'Load a previously saved session.', params: 'name: str', example: '"Load the auth-refactor session"' },
    ]
  },
  {
    name: 'Edit & Review', icon: Command, color: '#ffaa00', count: 6,
    tools: [
      { name: 'preview_edit', desc: 'Preview what a file edit would look like before applying. Shows diff.', params: 'path: str, old_string: str, new_string: str', example: '"Preview the fix for auth.py"' },
      { name: 'apply_edit', desc: 'Apply a previously previewed edit to a file.', params: 'edit_id: str', example: '"Apply the previewed edit"' },
      { name: 'apply_patch', desc: 'Apply a unified diff patch to one or more files.', params: 'patch: str', example: '"Apply the diff patch"' },
    ]
  },
  {
    name: 'Analysis', icon: Activity, color: '#d946ef', count: 4,
    tools: [
      { name: 'analyze_code', desc: 'Analyze code structure, complexity, and potential issues.', params: 'path: str', example: '"Analyze the auth module"' },
      { name: 'explain_code', desc: 'Explain what a piece of code does in plain language.', params: 'path: str, start_line?: int, end_line?: int', example: '"Explain the middleware function"' },
      { name: 'generate_tests', desc: 'Generate test cases for the specified code.', params: 'path: str, framework?: str', example: '"Generate tests for auth.py"' },
    ]
  },
  {
    name: 'Undo & Redo', icon: RotateCcw, color: '#ff4444', count: 4,
    tools: [
      { name: 'undo', desc: 'Undo the last file modification. Restores the previous file state.', params: 'none', example: '"Undo the last change"' },
      { name: 'redo', desc: 'Redo the last undone action. Re-applies the change.', params: 'none', example: '"Redo the last undone change"' },
      { name: 'undo_info', desc: 'Show what can be undone. Displays the pending undo operation.', params: 'none', example: '"What was the last change?"' },
      { name: 'redo_info', desc: 'Show what can be redone. Displays the pending redo operation.', params: 'none', example: '"What can be redone?"' },
    ]
  },
  {
    name: 'Skills & Plugins', icon: Sparkles, color: '#00e5ff', count: 3,
    tools: [
      { name: 'list_skills', desc: 'List all available skills (built-in and custom).', params: 'none', example: '"Show available skills"' },
      { name: 'use_skill', desc: 'Execute a specific skill by name with the given arguments.', params: 'skill: str, args?: dict', example: '"Run the deploy skill"' },
    ]
  },
  {
    name: 'Clipboard', icon: Clipboard, color: '#00ff88', count: 2,
    tools: [
      { name: 'clipboard_read', desc: 'Read the current contents of the system clipboard.', params: 'none', example: '"Read what\'s on my clipboard"' },
      { name: 'clipboard_write', desc: 'Write content to the system clipboard.', params: 'content: str', example: '"Copy the API key to clipboard"' },
    ]
  },
  {
    name: 'MCP & Custom Tools', icon: Layers, color: '#ffaa00', count: 3,
    tools: [
      { name: 'mcp_tool', desc: 'Call a tool from a connected MCP (Model Context Protocol) server.', params: 'server: str, tool: str, args?: dict', example: '"Use the filesystem MCP tool"' },
      { name: 'list_commands', desc: 'List all available custom commands from the config.', params: 'none', example: '"Show custom commands"' },
      { name: 'run_command_custom', desc: 'Run a custom command defined in the configuration.', params: 'command: str, args?: dict', example: '"Run the deploy command"' },
    ]
  },
  {
    name: 'OpenCode Architecture', icon: Cpu, color: '#8b5cf6', count: 9,
    tools: [
      { name: 'snapshot_create', desc: 'Create a Git-based snapshot before modifications. Captures the current state of the workspace for safe rollback.', params: 'label?: str', example: '"Create a snapshot before refactoring"' },
      { name: 'snapshot_restore', desc: 'Restore a previously created snapshot. Reverts the workspace to the captured state.', params: 'snapshot_id: str', example: '"Restore snapshot before-refactor"' },
      { name: 'snapshot_diff', desc: 'Compute diff between snapshot states. Shows what changed between two snapshots.', params: 'snapshot_id_1: str, snapshot_id_2: str', example: '"Diff snapshot v1 and v2"' },
      { name: 'undo', desc: 'Undo the last AI action. Reverts the most recent modification made by the agent.', params: 'none', example: '"Undo the last change"' },
      { name: 'redo', desc: 'Redo an undone action. Re-applies the change that was previously undone.', params: 'none', example: '"Redo the undone change"' },
      { name: 'command_run', desc: 'Execute a custom user: or project: command. Runs predefined command templates with variable substitution.', params: 'command: str, args?: dict', example: '"Run user:deploy command"' },
      { name: 'command_create', desc: 'Create a new custom command with template variables. Define reusable command templates with $variable placeholders.', params: 'name: str, template: str, description?: str', example: '"Create a deploy command template"' },
      { name: 'session_share', desc: 'Generate a shareable apex:// link for the current session. Allows others to resume from this point.', params: 'none', example: '"Share this session with the team"' },
      { name: 'session_load_shared', desc: 'Load a session from a shared link. Resumes a session that was shared via an apex:// link.', params: 'link: str', example: '"Load session from apex:// link"' },
    ]
  },
]

export default function ToolsPage() {
  const [expandedCat, setExpandedCat] = useState<string | null>('File Operations')

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <NavBar />

      <main className="flex-1 pt-16">
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 grid-pattern" />
          <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-apex-cyan/20 bg-apex-cyan/5 text-apex-cyan text-sm font-mono mb-6"><span className="w-1.5 h-1.5 rounded-full bg-apex-cyan pulse-dot" />75+ Tools</div>
              <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">Built-in <span className="animated-gradient-text">Tools</span> Catalog</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">Every tool at your disposal, organized by category. Tools are automatically selected by the AI based on your requests.</p>
            </motion.div>
          </div>
        </section>

        {/* Quick Stats */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {TOOL_CATEGORIES.map(cat => (
              <div key={cat.name} onClick={() => setExpandedCat(expandedCat === cat.name ? null : cat.name)} className={`cursor-pointer p-3 rounded-lg border transition-all text-center ${expandedCat === cat.name ? 'border-apex-cyan/30 bg-apex-cyan/5' : 'border-border/50 bg-card/30 hover:border-border'}`}>
                <cat.icon className="w-5 h-5 mx-auto mb-1" style={{ color: cat.color }} />
                <div className="text-lg font-bold font-mono">{cat.count}</div>
                <div className="text-xs text-muted-foreground font-mono truncate">{cat.name}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Tool Categories Detail */}
        <section className="py-8">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-4">
            {TOOL_CATEGORIES.map((cat, i) => (
              <motion.div key={cat.name} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.3, delay: i * 0.03 }}>
                <div className="rounded-xl border border-border/50 bg-card/30 overflow-hidden">
                  <button onClick={() => setExpandedCat(expandedCat === cat.name ? null : cat.name)} className="w-full flex items-center justify-between p-5 hover:bg-card/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${cat.color}15`, border: `1px solid ${cat.color}30` }}><cat.icon className="w-5 h-5" style={{ color: cat.color }} /></div>
                      <div className="text-left"><h3 className="font-bold font-mono text-lg" style={{ color: cat.color }}>{cat.name}</h3><span className="text-xs text-muted-foreground font-mono">{cat.count} tools</span></div>
                    </div>
                    <ArrowRight className={`w-5 h-5 text-muted-foreground transition-transform ${expandedCat === cat.name ? 'rotate-90' : ''}`} />
                  </button>
                  {expandedCat === cat.name && (
                    <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} className="border-t border-border/50">
                      <div className="p-5 space-y-3">
                        {cat.tools.map(tool => (
                          <div key={tool.name} className="p-4 rounded-lg border border-border/30 bg-card/20">
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                              <div>
                                <code className="text-sm font-mono font-bold" style={{ color: cat.color }}>{tool.name}</code>
                                {tool.params && <code className="text-xs font-mono text-muted-foreground ml-3">({tool.params})</code>}
                              </div>
                            </div>
                            <p className="text-sm text-muted-foreground mb-2">{tool.desc}</p>
                            <div className="flex items-center gap-2"><span className="text-xs text-muted-foreground">Example:</span><code className="text-xs font-mono text-apex-cyan bg-card px-2 py-0.5 rounded">{tool.example}</code></div>
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

        {/* How Tools Work */}
        <section className="py-12 bg-card/30">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <h2 className="text-2xl font-bold font-mono mb-6 flex items-center gap-2"><Zap className="w-6 h-6 text-apex-cyan" /> How Tools Work</h2>
            <div className="grid sm:grid-cols-3 gap-6">
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">1. You Ask</h3>
                <p className="text-sm text-muted-foreground">Type your request in natural language. APEX understands what you need and selects the right tools.</p>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">2. Agent Selects</h3>
                <p className="text-sm text-muted-foreground">The current agent analyzes your request, checks permissions, and calls the appropriate tool with the right parameters.</p>
              </div>
              <div className="p-5 rounded-xl border border-border/50 bg-card/30">
                <h3 className="font-bold font-mono text-apex-cyan mb-2">3. Tool Executes</h3>
                <p className="text-sm text-muted-foreground">The tool executes safely, returns results, and the agent uses them to continue the conversation or take further action.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
