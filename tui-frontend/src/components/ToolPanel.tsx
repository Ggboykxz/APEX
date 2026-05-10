import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_TOOLS } from "../data/apex-data.js"

interface ToolPanelProps {
  visible: boolean
  activeAgent?: string
}

const CATEGORY_COLORS: Record<string, string> = {
  File: apexTheme.cyan,
  Code: apexTheme.green,
  Shell: apexTheme.warning,
  Git: "#f97316",
  Web: "#3b82f6",
  Database: "#8b5cf6",
  Docker: "#2496ed",
  K8s: "#326ce5",
  Security: apexTheme.error,
  Analysis: "#ec4899",
  Cloud: "#f59e0b",
}

export function ToolPanel({ visible, activeAgent = "coder" }: ToolPanelProps) {
  if (!visible) return null

  const categories = Array.from(new Set(APEX_TOOLS.map((t) => t.category)))
  const totalTools = APEX_TOOLS.length

  return (
    <box
      id="apex-tools"
      style={{
        width: 28,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.border,
        borderStyle: "single",
      }}
    >
      <box style={{ height: 2, paddingLeft: 1, flexDirection: "column", backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>⚡ Tools</span>
          <span style={{ fg: apexTheme.textMuted }}> </span>
          <span style={{ fg: apexTheme.cyan }}>{totalTools}</span>
          <span style={{ fg: apexTheme.textMuted }}> available</span>
        </text>
        <text style={{ fg: apexTheme.textDim }}>
          File, Code, Git, Shell, Web
        </text>
      </box>

      <scrollbox
        style={{
          flexGrow: 1,
          rootOptions: { backgroundColor: apexTheme.bgSurface },
          contentOptions: { backgroundColor: apexTheme.bgSurface },
          scrollbarOptions: {
            showArrows: false,
            trackOptions: {
              foregroundColor: apexTheme.green,
              backgroundColor: apexTheme.scrollbarTrack,
            },
          },
        }}
      >
        {categories.map((category) => {
          const catTools = APEX_TOOLS.filter((t) => t.category === category).slice(0, 6)
          return (
            <box key={category} style={{ marginBottom: 1, paddingLeft: 1 }}>
              <text>
                <span style={{ fg: CATEGORY_COLORS[category] ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>
                  ─ {category}
                </span>
              </text>
              {catTools.map((tool) => (
                <text key={tool.id}>
                  <span style={{ fg: apexTheme.textMuted }}>  • </span>
                  <span style={{ fg: apexTheme.textDim }}>{tool.name}</span>
                </text>
              ))}
            </box>
          )
        })}
      </scrollbox>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>
          ─ MCP / LSP
        </text>
      </box>

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.green }}>●</span>
          <span style={{ fg: apexTheme.textMuted }}> </span>
          <span style={{ fg: apexTheme.text }}>Servers connected</span>
        </text>
      </box>
      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.textMuted }}>○</span>
          <span style={{ fg: apexTheme.textMuted }}> </span>
          <span style={{ fg: apexTheme.textDim }}>No servers configured</span>
        </text>
      </box>
    </box>
  )
}