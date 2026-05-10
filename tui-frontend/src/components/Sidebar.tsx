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
      style={{ width: "100%", height: 1, paddingLeft: 1, backgroundColor: active ? agent.color + "20" : "transparent" }}
      onMouseDown={onSelect}
    >
      <text>
        <span style={{ fg: agent.color, attributes: TextAttributes.BOLD }}>{agent.icon}</span>
        <span style={{ fg: active ? agent.color : apexTheme.textDim }}> {agent.name}</span>
      </text>
      <text style={{ textAlign: "right" }}>
        <span style={{ fg: agent.color }}>{active ? "●" : "○"}</span>
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
      <box style={{ height: 2, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ APEX v1.0</text>
        <text style={{ fg: apexTheme.textMuted }}>Agentic Coding Platform</text>
      </box>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>AGENTS</text>
      </box>

      {APEX_AGENTS.map((agent) => (
        <AgentItem key={agent.id} agent={agent} active={agent.id === activeAgent} onSelect={() => onAgentSelect(agent.id)} />
      ))}

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>SESSIONS</text>
      </box>

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.green }}>●</span>
          <span style={{ fg: apexTheme.text }}> Current</span>
        </text>
      </box>
      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.textMuted }}>○</span>
          <span style={{ fg: apexTheme.textDim }}> Saved</span>
        </text>
      </box>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text style={{ fg: apexTheme.textMuted, attributes: TextAttributes.BOLD }}>SERVERS</text>
      </box>

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.green }}>●</span>
          <span style={{ fg: apexTheme.text }}> 5 MCP · 3 LSP</span>
        </text>
      </box>
      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.warning }}>○</span>
          <span style={{ fg: apexTheme.textDim }}> 1 Offline</span>
        </text>
      </box>

      <box style={{ flexGrow: 1 }} />

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <box style={{ height: 1, paddingLeft: 1 }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Ctrl+K</span>
          <span style={{ fg: apexTheme.textMuted }}> Models  </span>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Tab</span>
          <span style={{ fg: apexTheme.textMuted }}> Agents</span>
        </text>
      </box>
    </box>
  )
}