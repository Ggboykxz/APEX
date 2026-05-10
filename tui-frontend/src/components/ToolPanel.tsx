/**
 * APEX Tool Panel Component
 * Right-side panel showing active tools, MCP/LSP status
 */

import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_TOOLS, APEX_MCP_SERVERS } from "../data/apex-data.js"

interface ToolPanelProps {
  visible: boolean
}

export function ToolPanel({ visible }: ToolPanelProps) {
  if (!visible) return null

  const activeTools = APEX_TOOLS.filter((t) => t.status === "active").slice(0, 12)
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
      {/* Header */}
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>Tools</span>
          <span style={{ fg: apexTheme.textMuted }}> ({APEX_TOOLS.length}+)</span>
        </text>
      </box>

      {/* Tool categories */}
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
        {toolCategories.map((category) => {
          const catTools = APEX_TOOLS.filter((t) => t.category === category).slice(0, 5)
          return (
            <box key={category} style={{ marginBottom: 1, paddingLeft: 1 }}>
              <text>
                <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>{category}</span>
                {"\n"}
                {catTools.map((tool, i) => (
                  <span key={tool.id}>
                    <span style={{ fg: apexTheme.textDim }}>
                      {"  "}{tool.name}
                    </span>
                    {i < catTools.length - 1 ? "\n" : ""}
                  </span>
                ))}
              </text>
            </box>
          )
        })}
      </scrollbox>

      {/* MCP/LSP Status */}
      <box style={{ height: 1, backgroundColor: apexTheme.border }} />
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Servers</span>
        </text>
      </box>

      {APEX_MCP_SERVERS.map((server) => (
        <box key={server.id} style={{ height: 1, paddingLeft: 1 }}>
          <text>
            <span
              style={{
                fg: server.status === "connected"
                  ? apexTheme.green
                  : server.status === "error"
                    ? apexTheme.error
                    : apexTheme.warning,
              }}
            >
              {server.status === "connected" ? "●" : server.status === "error" ? "✕" : "○"}
            </span>
            <span style={{ fg: apexTheme.textDim }}> {server.name}</span>
          </text>
        </box>
      ))}
    </box>
  )
}
