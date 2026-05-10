/**
 * APEX Sidebar Component
 * Agent selection, session list, and navigation
 */

import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, type ApexAgent } from "../data/apex-data.js"

interface SidebarProps {
  activeAgent: string
  onAgentSelect: (agentId: string) => void
  visible: boolean
}

function AgentItem({ agent, active, onSelect }: { agent: ApexAgent; active: boolean; onSelect: () => void }) {
  return (
    <box
      style={{
        width: "100%",
        paddingLeft: 1,
        height: 1,
        backgroundColor: active ? apexTheme.bgOverlay : "transparent",
      }}
      onMousePress={onSelect}
    >
      <text>
        <span style={{ fg: agent.color, attributes: TextAttributes.BOLD }}>{agent.icon}</span>
        <span style={{ fg: active ? apexTheme.textBright : apexTheme.textDim }}> {agent.name}</span>
      </text>
    </box>
  )
}

export function Sidebar({ activeAgent, onAgentSelect, visible }: SidebarProps) {
  if (!visible) return null

  return (
    <box
      id="apex-sidebar"
      style={{
        width: 22,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.border,
        borderStyle: "single",
      }}
    >
      {/* APEX Logo */}
      <box style={{ height: 1, paddingLeft: 1, alignItems: "center" }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ </span>
          <span style={{ fg: apexTheme.textBright, attributes: TextAttributes.BOLD }}>APEX</span>
        </text>
      </box>

      {/* Divider */}
      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      {/* Agents section */}
      <box style={{ height: 1, paddingLeft: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>AGENTS</text>
      </box>

      {APEX_AGENTS.map((agent) => (
        <AgentItem
          key={agent.id}
          agent={agent}
          active={agent.id === activeAgent}
          onSelect={() => onAgentSelect(agent.id)}
        />
      ))}

      {/* Divider */}
      <box style={{ height: 1, marginTop: 1, backgroundColor: apexTheme.border }} />

      {/* Sessions section */}
      <box style={{ height: 1, paddingLeft: 1, marginTop: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>SESSIONS</text>
      </box>

      <box style={{ paddingLeft: 1, height: 1 }}>
        <text>
          <span style={{ fg: apexTheme.green }}>● </span>
          <span style={{ fg: apexTheme.text }}>Current</span>
        </text>
      </box>
      <box style={{ paddingLeft: 1, height: 1 }}>
        <text>
          <span style={{ fg: apexTheme.textMuted }}>○ </span>
          <span style={{ fg: apexTheme.textDim }}>Previous</span>
        </text>
      </box>

      {/* Divider */}
      <box style={{ height: 1, marginTop: 1, backgroundColor: apexTheme.border }} />

      {/* MCP/LSP status */}
      <box style={{ height: 1, paddingLeft: 1, marginTop: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>MCP/LSP</text>
      </box>

      <box style={{ paddingLeft: 1, height: 1 }}>
        <text>
          <span style={{ fg: apexTheme.green }}>+ </span>
          <span style={{ fg: apexTheme.textDim }}>5 Online</span>
        </text>
      </box>
      <box style={{ paddingLeft: 1, height: 1 }}>
        <text>
          <span style={{ fg: apexTheme.warning }}>- </span>
          <span style={{ fg: apexTheme.textDim }}>2 Offline</span>
        </text>
      </box>

      {/* Spacer */}
      <box flexGrow={1} />

      {/* Version */}
      <box style={{ height: 1, paddingLeft: 1 }}>
        <text style={{ fg: apexTheme.textMuted }}>v2.0.0</text>
      </box>
    </box>
  )
}
