import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_MODELS, type ChatMessage } from "../data/apex-data.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface ChatPanelProps {
  messages: ChatMessage[]
  inputValue: string
  onInputChange: (value: string) => void
  onSubmit: () => void
  activeAgent: string
  activeModel: string
  isGenerating: boolean
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`
}

export function ChatPanel({ messages, inputValue, onInputChange, onSubmit, activeAgent, activeModel, isGenerating }: ChatPanelProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const model = APEX_MODELS.find((m) => m.id === activeModel)
  const agentColor = agent?.color ?? apexTheme.cyan

  return (
    <box id="apex-chat" style={{ flexDirection: "column", flexGrow: 1, backgroundColor: apexTheme.bg }}>
      <box style={{ height: 1, paddingLeft: 1, paddingRight: 1, flexDirection: "row", justifyContent: "space-between", backgroundColor: apexTheme.bgSurface }}>
        <text style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>
          {agent?.name ?? "APEX Coder"} | {model?.name ?? "No Model"}
        </text>
        <text style={{ fg: isGenerating ? apexTheme.warning : apexTheme.green }}>
          {isGenerating ? "● Thinking" : "● Ready"}
        </text>
      </box>

      <scrollbox
        id="apex-chat-messages"
        style={{
          flexGrow: 1,
          rootOptions: { backgroundColor: apexTheme.bg },
          wrapperOptions: { backgroundColor: apexTheme.bg },
          viewportOptions: { backgroundColor: apexTheme.bg },
          contentOptions: { backgroundColor: apexTheme.bg },
          scrollbarOptions: {
            showArrows: false,
            trackOptions: { foregroundColor: agentColor, backgroundColor: apexTheme.scrollbarTrack },
          },
        }}
      >
        {messages.length === 0 ? (
          <box style={{ padding: 3, flexDirection: "column" }}>
            <text style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ APEX</text>
            <text style={{ fg: apexTheme.textDim }}>AI-Powered Engineering eXtended</text>
            <text style={{ fg: apexTheme.textMuted }}>Type a message below to begin</text>
            <text style={{ fg: apexTheme.textMuted }}>Ctrl+K: Models  Tab: Agents  ?: Help</text>
          </box>
        ) : null}

        {messages.map((msg) => {
          const isUser = msg.role === "user"
          const msgAgent = APEX_AGENTS.find((a) => a.id === msg.agent)
          const nameColor = isUser ? apexTheme.green : (msgAgent?.color ?? agentColor)
          const bodyColor = isUser ? apexTheme.textBright : apexTheme.text
          const content = msg.content.length > 130 ? msg.content.slice(0, 130) + "..." : msg.content
          return (
            <box key={msg.id} style={{ width: "100%", marginBottom: 1 }}>
              <text>
                <span style={{ fg: nameColor, attributes: TextAttributes.BOLD }}>
                  {isUser ? "You" : (msgAgent?.name ?? "APEX")}
                </span>
                <span style={{ fg: apexTheme.textMuted }}> · </span>
                <span style={{ fg: apexTheme.textDim }}>{formatTime(msg.timestamp)}</span>
                {msg.tokens && (
                  <span>
                    <span style={{ fg: apexTheme.textMuted }}> · </span>
                    <span style={{ fg: apexTheme.cyan }}>+{msg.tokens}tok</span>
                  </span>
                )}
              </text>
              <text style={{ fg: bodyColor }}>{content}</text>
            </box>
          )
        })}

        {isGenerating ? (
          <box style={{ paddingLeft: 1 }}>
            <text>
              <span style={{ fg: agentColor }}>▸ </span>
              <span style={{ fg: apexTheme.textDim }}>Processing request...</span>
            </text>
          </box>
        ) : null}
      </scrollbox>

      <box style={{ height: 4, flexDirection: "column", border: true, borderColor: agentColor, borderStyle: "single", backgroundColor: apexTheme.bgSurface }}>
        <box style={{ height: 1, paddingLeft: 1, flexDirection: "row", alignItems: "center", backgroundColor: apexTheme.bgOverlay }}>
          <text style={{ fg: agentColor }}>{isGenerating ? "◌" : "▸"}</text>
          <text style={{ fg: apexTheme.textMuted }}> {agent?.name ?? "APEX"}</text>
          <text style={{ fg: apexTheme.textMuted }}>      {messages.length} msg{messages.length !== 1 ? "s" : ""}</text>
        </box>
        <input
          id="apex-chat-input"
          placeholder={`Ask ${agent?.name ?? "APEX"}... (Enter to send)`}
          value={inputValue}
          onInput={onInputChange}
          onSubmit={onSubmit}
          focused
          style={{
            focusedBackgroundColor: apexTheme.bgSurfaceBright,
            backgroundColor: apexTheme.bgSurface,
          }}
        />
      </box>
    </box>
  )
}