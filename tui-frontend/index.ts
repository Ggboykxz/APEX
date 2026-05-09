/**
 * APEX TUI - Premium Terminal UI
 * Built with OpenTUI - The same core that powers OpenCode
 */

import { createCliRenderer, Box, Text, Input, ScrollBox, Code, Diff, Select, TabSelect } from "@opentui/core"
import type { CliRenderer } from "@opentui/core"

interface APEXMessage {
  type: string
  content?: string
  name?: string
  args?: Record<string, unknown>
  result?: string
  model?: string
}

let renderer: CliRenderer

const colors = {
  bg: "#0d1117",
  elevated: "#161b22", 
  surface: "#21262d",
  border: "#30363d",
  text: "#e6edf3",
  muted: "#7d8590",
  cyan: "#58a6ff",
  cyanBright: "#79c0ff",
  purple: "#a371f7",
  green: "#3fb950",
  orange: "#d29922",
  red: "#f85149",
  yellow: "#e3b341",
  pink: "#f778ba",
}

const modelName = "claude-sonnet-4-20250514"
const cwd = "/workspaces/APEX"
const tokens = 1247
const cost = 0.0023

function createHeader() {
  return Box(
    {
      flexDirection: "row",
      height: 3,
      backgroundColor: colors.elevated,
      borderBottom: true,
      borderColor: colors.cyan,
      alignItems: "center",
      paddingX: 2,
    },
    Box({ flexDirection: "row", gap: 1 },
      Text({ content: "◆", fg: colors.purple, textStyle: "bold" }),
      Text({ content: "APEX", fg: colors.text, textStyle: "bold" }),
      Text({ content: "AI Coding Assistant", fg: colors.muted }),
    ),
    Box({ flexGrow: 1 }),
    Box({ flexDirection: "row", gap: 2, alignItems: "center" },
      Text({ content: "▶", fg: colors.green, textStyle: "bold" }),
      Text({ content: "build", fg: colors.green }),
      Text({ content: "│", fg: colors.muted }),
      Text({ content: "▶", fg: colors.cyan, textStyle: "bold" }),
      Text({ content: modelName, fg: colors.cyan, textStyle: "bold" }),
      Text({ content: "│", fg: colors.muted }),
      Text({ content: "📁", fg: colors.muted }),
      Text({ content: cwd, fg: colors.text, textStyle: "bold" }),
      Text({ content: "│", fg: colors.muted }),
      Text({ content: "●", fg: colors.orange, textStyle: "bold" }),
      Text({ content: `${tokens}k`, fg: colors.orange }),
      Text({ content: "│", fg: colors.muted }),
      Text({ content: `$${cost}`, fg: colors.muted }),
    ),
  )
}

function createFileTree() {
  const tree = Box({ flexDirection: "column", padding: 1, gap: 0 })
  
  tree.add(Text({ content: "EXPLORER", fg: colors.muted, textStyle: "bold" }))
  tree.add(Text({ content: "", fg: colors.text }))
  
  const items = [
    { icon: "📂", name: "APEX", color: colors.cyan },
    { icon: "  ├", name: "📁 .git", color: colors.muted },
    { icon: "  ├", name: "📁 .github", color: colors.muted },
    { icon: "  ├", name: "📁 apex", color: colors.text },
    { icon: "  ├", name: "📁 tests", color: colors.text },
    { icon: "  ├", name: "📁 docs", color: colors.text },
    { icon: "  └", name: "📄 README.md", color: colors.text },
  ]
  
  for (const item of items) {
    tree.add(Box({ flexDirection: "row" },
      Text({ content: item.icon, fg: item.color }),
      Text({ content: " " + item.name, fg: item.color }),
    ))
  }
  
  return tree
}

function createToolLog() {
  const log = Box({ flexDirection: "column", padding: 1, flexGrow: 1 })
  
  log.add(Text({ content: "", fg: colors.text }))
  log.add(Text({ content: "TOOL LOG", fg: colors.muted, textStyle: "bold" }))
  log.add(Text({ content: "", fg: colors.text }))
  
  const tools = [
    { status: "✓", color: colors.green, name: "read_file", file: "main.py" },
    { status: "✓", color: colors.green, name: "edit_file", file: "agent.py:45" },
    { status: "⟳", color: colors.cyan, name: "run_command", file: "pytest..." },
  ]
  
  for (const tool of tools) {
    log.add(Box({ flexDirection: "row", gap: 1 },
      Text({ content: tool.status, fg: tool.color }),
      Text({ content: tool.name, fg: colors.text }),
      Text({ content: tool.file, fg: colors.muted }),
    ))
  }
  
  return log
}

function createSidebar() {
  return Box(
    {
      width: 28,
      backgroundColor: colors.elevated,
      borderRight: true,
      borderColor: colors.border,
      flexDirection: "column",
    },
    Box(
      {
        flexDirection: "column",
        borderBottom: true,
        borderColor: colors.border,
        flexGrow: 1,
      },
      createFileTree(),
      createToolLog(),
    ),
  )
}

function createMessage(role: string, content: string, timestamp: string) {
  const isUser = role === "You"
  const borderColor = isUser ? colors.surface : colors.cyan
  
  return Box(
    {
      flexDirection: "column",
      marginY: 1,
      padding: 1,
      border: true,
      borderColor: borderColor,
      borderLeft: true,
      backgroundColor: isUser ? colors.surface : colors.elevated,
    },
    Box({ flexDirection: "row", justifyContent: "space-between", marginBottom: 1 },
      Text({ content: role, fg: isUser ? colors.text : colors.cyan, textStyle: "bold" }),
      Text({ content: timestamp, fg: colors.muted }),
    ),
    Text({ content: content, fg: colors.text, textStyle: isUser ? "none" : "none" }),
  )
}

function createCodeBlock(language: string, code: string) {
  return Box(
    {
      backgroundColor: colors.bg,
      border: true,
      borderColor: colors.border,
      padding: 1,
      marginY: 1,
    },
    Text({ content: language, fg: colors.muted, textStyle: "italic" }),
    Code({ content: code, filetype: language, width: "100%" }),
  )
}

function createToolCard(name: string, cmd: string, status: "pending" | "running" | "success" | "error", duration?: string) {
  const statusColors = {
    pending: colors.orange,
    running: colors.cyan,
    success: colors.green,
    error: colors.red,
  }
  const statusIcons = {
    pending: "○",
    running: "⟳",
    success: "✓",
    error: "✗",
  }
  const statusColor = statusColors[status]
  const statusIcon = statusIcons[status]
  
  return Box(
    {
      flexDirection: "column",
      padding: 1,
      marginY: 1,
      border: true,
      borderColor: statusColor,
      borderLeft: true,
      backgroundColor: colors.bg,
    },
    Box({ flexDirection: "row", justifyContent: "space-between" },
      Box({ flexDirection: "row", gap: 1 },
        Text({ content: statusIcon, fg: statusColor, textStyle: "bold" }),
        Text({ content: name, fg: statusColor, textStyle: "bold" }),
      ),
      duration ? Text({ content: duration, fg: colors.muted }) : null,
    ),
    Text({ content: cmd, fg: colors.text, backgroundColor: colors.surface }),
  )
}

function createChatArea() {
  const chat = Box({ flexDirection: "column", flexGrow: 1, padding: 2, overflow: "hidden" })
  
  chat.add(Text({ content: "Session: main · 4 messages", fg: colors.muted }))
  chat.add(Text({ content: "", fg: colors.text }))
  
  chat.add(createMessage("You", "Fix the authentication bug in auth.py - users can't log in", "14:31"))
  chat.add(createMessage("APEX", "I'll analyze the auth.py file and fix the login issue.", "14:31"))
  chat.add(createToolCard("read_file", "auth.py", "success", "0.3s"))
  chat.add(createToolCard("run_command", "pytest tests/test_auth.py -v", "running"))
  
  return chat
}

function createInputBar() {
  const inputContainer = Box(
    {
      flexDirection: "row",
      height: 4,
      backgroundColor: colors.surface,
      borderTop: true,
      borderColor: colors.border,
      alignItems: "center",
      paddingX: 2,
    },
    Text({ content: "›", fg: colors.green, textStyle: "bold" }),
    Input({
      placeholder: "Message APEX... (Enter to send, Shift+Enter for newline)",
      width: "100%",
      backgroundColor: colors.surface,
      textColor: colors.text,
      placeholderColor: colors.muted,
      onSubmit: (value: string) => {
        if (value.trim()) {
          console.log("User input:", value)
        }
      },
    }),
  )
  return inputContainer
}

function createStatusBar() {
  return Box(
    {
      flexDirection: "row",
      height: 2,
      backgroundColor: colors.elevated,
      borderTop: true,
      borderColor: colors.border,
      alignItems: "center",
      paddingX: 2,
    },
    Text({ content: "●", fg: colors.green }),
    Text({ content: " Ready ", fg: colors.muted }),
    Text({ content: "│", fg: colors.muted }),
    Text({ content: "Enter", fg: colors.text, textStyle: "bold" }),
    Text({ content: " Envoyer ", fg: colors.muted }),
    Text({ content: "│", fg: colors.muted }),
    Text({ content: "↑↓", fg: colors.text, textStyle: "bold" }),
    Text({ content: " Historique ", fg: colors.muted }),
    Text({ content: "│", fg: colors.muted }),
    Text({ content: "Ctrl+K", fg: colors.text, textStyle: "bold" }),
    Text({ content: " Commands ", fg: colors.muted }),
    Text({ content: "│", fg: colors.muted }),
    Text({ content: "Tab", fg: colors.text, textStyle: "bold" }),
    Text({ content: " Agent ", fg: colors.muted }),
    Text({ content: "│", fg: colors.muted }),
    Text({ content: "Ctrl+T", fg: colors.text, textStyle: "bold" }),
    Text({ content: " Theme ", fg: colors.muted }),
  )
}

function createCommandPalette() {
  const palette = Box({
    position: "absolute",
    left: "25%",
    top: "15%",
    width: "50%",
    backgroundColor: colors.elevated,
    border: true,
    borderStyle: "rounded",
    borderColor: colors.cyan,
    flexDirection: "column",
    padding: 1,
    zIndex: 100,
  })
  
  palette.add(Text({ content: "⌘ Commands", fg: colors.cyan, textStyle: "bold" }))
  palette.add(Text({ content: "", fg: colors.text }))
  
  const commands = [
    { cmd: "/model", desc: "Switch AI model" },
    { cmd: "/models", desc: "List available models" },
    { cmd: "/clear", desc: "Clear conversation" },
    { cmd: "/save", desc: "Save session" },
    { cmd: "/load", desc: "Load session" },
    { cmd: "/cwd", desc: "Change directory" },
    { cmd: "/help", desc: "Show help" },
    { cmd: "/exit", desc: "Exit APEX" },
  ]
  
  for (const c of commands) {
    palette.add(Box({ flexDirection: "row", gap: 1 },
      Text({ content: c.cmd, fg: colors.cyan }),
      Text({ content: " - " + c.desc, fg: colors.muted }),
    ))
  }
  
  return palette
}

async function main() {
  renderer = await createCliRenderer({
    exitOnCtrlC: false,
    targetFps: 60,
    backgroundColor: colors.bg,
  })

  const mainLayout = Box(
    { flexDirection: "row", flexGrow: 1 },
    createSidebar(),
    createChatArea(),
  )

  const appLayout = Box(
    { flexDirection: "column", flexGrow: 1 },
    createHeader(),
    mainLayout,
    createInputBar(),
    createStatusBar(),
  )

  renderer.root.add(appLayout)

  renderer.on("key", (key: string) => {
    if (key === "ctrl+c") {
      renderer.destroy()
      process.exit(0)
    }
    if (key === "ctrl+k") {
      console.log("Command palette triggered")
    }
  })

  process.stdin.setEncoding("utf8")
  process.stdin.on("data", (chunk: string) => {
    const lines = chunk.split("\n").filter((line) => line.trim())
    for (const line of lines) {
      try {
        const msg: APEXMessage = JSON.parse(line)
        console.log("Received:", msg)
      } catch {
        // Not JSON
      }
    }
  })
  
  console.log("APEX TUI initialized - Press Ctrl+C to exit")
}

main().catch(console.error)