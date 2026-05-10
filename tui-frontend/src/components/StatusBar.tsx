import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS } from "../data/apex-data.js"

interface StatusBarProps {
  activeAgent: string
  activeModel: string
  totalTokens: number
  messageCount: number
  sessionDuration: string
}

export function StatusBar({ activeAgent, activeModel, totalTokens, messageCount, sessionDuration }: StatusBarProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const model = APEX_MODELS.find((m) => m.id === activeModel)

  return (
    <box
      id="apex-statusbar"
      style={{
        height: 1,
        flexDirection: "row",
        justifyContent: "space-between",
        backgroundColor: apexTheme.bgSurface,
        paddingLeft: 1,
        paddingRight: 1,
      }}
    >
      <text>
        <span style={{ fg: agent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>
          {agent?.name ?? "APEX"}
        </span>
        <span style={{ fg: apexTheme.textMuted }}> | </span>
        <span style={{ fg: apexTheme.textDim }}>{model?.name ?? "No Model"}</span>
      </text>

      <text>
        <span style={{ fg: apexTheme.textMuted }}>Msgs:</span>
        <span style={{ fg: apexTheme.text }}> {messageCount} </span>
        <span style={{ fg: apexTheme.textMuted }}>Tok:</span>
        <span style={{ fg: apexTheme.green }}> {totalTokens} </span>
        <span style={{ fg: apexTheme.textDim }}>{sessionDuration}</span>
      </text>

      <text>
        <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Ctrl+K</span>
        <span style={{ fg: apexTheme.textMuted }}> Model </span>
        <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Tab</span>
        <span style={{ fg: apexTheme.textMuted }}> Agent </span>
        <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>?</span>
        <span style={{ fg: apexTheme.textMuted }}> Help</span>
      </text>
    </box>
  )
}