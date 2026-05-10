import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface StatusBarProps {
  activeAgent: string
  activeModel: string
  totalTokens: number
  totalPromptTokens: number
  totalCompletionTokens: number
  totalSpent: number
  contextPct: number
  messageCount: number
  sessionDuration: string
}

export function StatusBar({ activeAgent, activeModel, totalTokens, totalPromptTokens, totalCompletionTokens, totalSpent, contextPct, messageCount, sessionDuration }: StatusBarProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)

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
        <span style={{ fg: "#000000" }}> │ {activeModel}</span>
      </text>

      <text style={{ fg: "#000000" }}>
        <span>In: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{totalPromptTokens.toLocaleString()}</span>
        <span> │ Out: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{totalCompletionTokens.toLocaleString()}</span>
        <span> │ Tot: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{totalTokens.toLocaleString()}</span>
        <span> │ ctx: </span>
        <span style={{ attributes: TextAttributes.BOLD }}>{contextPct.toFixed(1)}%</span>
        <span> │ $</span>
        <span style={{ attributes: TextAttributes.BOLD }}>{totalSpent.toFixed(4)}</span>
      </text>

      <text style={{ fg: "#000000" }}>
        <span style={{ attributes: TextAttributes.BOLD }}>⌘K</span>
        <span> Models  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>Tab</span>
        <span> Agents  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>?</span>
        <span> Help  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>⌘Q</span>
        <span> Quit  </span>
        <span style={{ attributes: TextAttributes.BOLD }}>⌘L</span>
        <span> Clear</span>
      </text>
    </box>
  )
}