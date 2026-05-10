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
        backgroundColor: agent?.color ?? apexTheme.cyan,
        paddingLeft: 1,
        paddingRight: 1,
      }}
    >
      <text>
        <span style={{ fg: "#000000", attributes: TextAttributes.BOLD }}>
          {agent?.name ?? "APEX"}
        </span>
        <span style={{ fg: "#000000" }}> │ </span>
        <span style={{ fg: "#000000" }}>{model?.name ?? "No Model"}</span>
      </text>

      <text style={{ fg: "#000000" }}>
        <span>Messages: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{messageCount}</span>
        <span> │ Tokens: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{totalTokens.toLocaleString()}</span>
        <span> │ Time: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{sessionDuration}</span>
      </text>

      <text style={{ fg: "#000000" }}>
        <span style={{ attributes: TextAttributes.BOLD }}>⌘K</span>
        <span> Models  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>Tab</span>
        <span> Agents  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>?</span>
        <span> Help  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>⌘Q</span>
        <span> Quit</span>
      </text>
    </box>
  )
}