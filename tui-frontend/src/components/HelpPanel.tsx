/**
 * APEX Help Panel Component
 * Help overlay showing keybindings, agents, and tools
 */

import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_KEYBINDINGS, APEX_AGENTS, APEX_TOOLS } from "../data/apex-data.js"

interface HelpPanelProps {
  visible: boolean
  onClose: () => void
  tab: "keybindings" | "agents" | "tools"
  onTabChange: (tab: "keybindings" | "agents" | "tools") => void
}

export function HelpPanel({ visible, onClose, tab, onTabChange }: HelpPanelProps) {
  if (!visible) return null

  return (
    <box
      id="apex-help"
      style={{
        position: "absolute",
        top: 1,
        left: "center",
        width: 70,
        height: 26,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.borderFocus,
        borderStyle: "double",
        zIndex: 200,
      }}
    >
      {/* Header */}
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ APEX Help</span>
          <span style={{ fg: apexTheme.textMuted }}> | Press Esc or ? to close</span>
        </text>
      </box>

      {/* Tabs */}
      <box style={{ height: 1, flexDirection: "row", paddingLeft: 1 }}>
        <box
          style={{
            paddingRight: 2,
            backgroundColor: tab === "keybindings" ? apexTheme.bgOverlay : "transparent",
          }}
          onMousePress={() => onTabChange("keybindings")}
        >
          <text>
            <span
              style={{
                fg: tab === "keybindings" ? apexTheme.cyan : apexTheme.textMuted,
                attributes: tab === "keybindings" ? TextAttributes.BOLD : 0,
              }}
            >
              Keybindings
            </span>
          </text>
        </box>
        <box
          style={{
            paddingRight: 2,
            backgroundColor: tab === "agents" ? apexTheme.bgOverlay : "transparent",
          }}
          onMousePress={() => onTabChange("agents")}
        >
          <text>
            <span
              style={{
                fg: tab === "agents" ? apexTheme.cyan : apexTheme.textMuted,
                attributes: tab === "agents" ? TextAttributes.BOLD : 0,
              }}
            >
              Agents
            </span>
          </text>
        </box>
        <box
          style={{
            paddingRight: 2,
            backgroundColor: tab === "tools" ? apexTheme.bgOverlay : "transparent",
          }}
          onMousePress={() => onTabChange("tools")}
        >
          <text>
            <span
              style={{
                fg: tab === "tools" ? apexTheme.cyan : apexTheme.textMuted,
                attributes: tab === "tools" ? TextAttributes.BOLD : 0,
              }}
            >
              Tools
            </span>
          </text>
        </box>
      </box>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      {/* Content */}
      <scrollbox
        style={{
          flexGrow: 1,
          rootOptions: { backgroundColor: apexTheme.bgSurface },
          contentOptions: { backgroundColor: apexTheme.bgSurface },
          scrollbarOptions: {
            showArrows: false,
            trackOptions: {
              foregroundColor: apexTheme.cyan,
              backgroundColor: apexTheme.scrollbarTrack,
            },
          },
        }}
      >
        {tab === "keybindings" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            {APEX_KEYBINDINGS.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <text>
                  <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>
                    {kb.key.padEnd(16)}
                  </span>
                  <span style={{ fg: apexTheme.textDim }}>{kb.action}</span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "agents" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            {APEX_AGENTS.map((agent) => (
              <box key={agent.id} style={{ marginBottom: 1 }}>
                <text>
                  <span style={{ fg: agent.color, attributes: TextAttributes.BOLD }}>
                    {agent.icon} {agent.name}
                  </span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textDim }}>  Role: {agent.role}</span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textMuted }}>
                    {"  "}
                    {agent.capabilities.join(" | ")}
                  </span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "tools" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <text>
              <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>
                {APEX_TOOLS.length}+ Tools Available
              </span>
              {"\n\n"}
            </text>
            {Array.from(new Set(APEX_TOOLS.map((t) => t.category))).map((category) => (
              <box key={category} style={{ marginBottom: 1 }}>
                <text>
                  <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>{category}</span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textDim }}>
                    {"  "}
                    {APEX_TOOLS.filter((t) => t.category === category)
                      .slice(0, 5)
                      .map((t) => t.name)
                      .join(", ")}
                  </span>
                </text>
              </box>
            ))}
          </box>
        )}
      </scrollbox>
    </box>
  )
}
