import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_TOOLS } from "../data/apex-data.js"

interface ToolPanelProps {
  visible: boolean
}

export function ToolPanel({ visible }: ToolPanelProps) {
  if (!visible) return null

  const toolCategories = Array.from(new Set(APEX_TOOLS.slice(0, 42).map((t) => t.category)))

  return (
    <box
      id="apex-tools"
      style={{
        width: 26,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.border,
        borderStyle: "single",
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>Tools</span>
          <span style={{ fg: apexTheme.textMuted }}> ({APEX_TOOLS.length}+)</span>
        </text>
      </box>

      <scrollbox style={{ flexGrow: 1, rootOptions: { backgroundColor: apexTheme.bgSurface }, contentOptions: { backgroundColor: apexTheme.bgSurface }, scrollbarOptions: { showArrows: false, trackOptions: { foregroundColor: apexTheme.green, backgroundColor: apexTheme.scrollbarTrack } } }}>
        {toolCategories.map((category) => {
          const catTools = APEX_TOOLS.filter((t) => t.category === category).slice(0, 5)
          return (
            <box key={category} style={{ marginBottom: 1, paddingLeft: 1 }}>
              <text>
                <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>{category}</span>
                {"\n"}
                {catTools.map((tool, i) => (
                  <span key={tool.id}>
                    <span style={{ fg: apexTheme.textDim }}>  {tool.name}</span>
                    {i < catTools.length - 1 ? "\n" : ""}
                  </span>
                ))}
              </text>
            </box>
          )
        })}
      </scrollbox>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Servers</span>
        </text>
      </box>

      {[
        { name: "Filesystem MCP", status: "connected" },
        { name: "GitHub MCP", status: "connected" },
        { name: "PostgreSQL MCP", status: "connected" },
        { name: "TypeScript LSP", status: "connected" },
        { name: "Python LSP", status: "disconnected" },
      ].map((server) => (
        <box key={server.name} style={{ height: 1, paddingLeft: 1 }}>
          <text>
            <span style={{ fg: server.status === "connected" ? apexTheme.green : server.status === "error" ? apexTheme.error : apexTheme.warning }}>
              {server.status === "connected" ? "●" : "○"}
            </span>
            <span style={{ fg: apexTheme.textDim }}> {server.name}</span>
          </text>
        </box>
      ))}
    </box>
  )
}