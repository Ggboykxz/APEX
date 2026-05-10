/**
 * APEX Chat Panel Component
 * Main conversation interface with messages, input, and status
 */

import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS, type ChatMessage } from "../data/apex-data.js"

interface ChatPanelProps {
  messages: ChatMessage[]
  inputValue: string
  onInputChange: (value: string) => void
  onSubmit: () => void
  activeAgent: string
  activeModel: string
  isGenerating: boolean
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  const agent = APEX_AGENTS.find((a) => a.id === message.agent)

  return (
    <box style={{ width: "100%", paddingLeft: 1, paddingRight: 1, marginBottom: 1 }}>
      <text>
        {isUser ? (
          <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>You</span>
        ) : (
          <span style={{ fg: agent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>
            {agent?.name ?? "APEX"}
          </span>
        )}
        {"\n"}
        <span style={{ fg: isUser ? apexTheme.text : apexTheme.textDim }}>
          {message.content.length > 150 ? message.content.slice(0, 150) + "..." : message.content}
        </span>
      </text>
    </box>
  )
}

export function ChatPanel({
  messages,
  inputValue,
  onInputChange,
  onSubmit,
  activeAgent,
  activeModel,
  isGenerating,
}: ChatPanelProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const model = APEX_MODELS.find((m) => m.id === activeModel)

  return (
    <box
      id="apex-chat"
      style={{
        flexDirection: "column",
        flexGrow: 1,
        backgroundColor: apexTheme.bg,
      }}
    >
      {/* Chat header bar */}
      <box
        style={{
          height: 1,
          paddingLeft: 1,
          paddingRight: 1,
          flexDirection: "row",
          justifyContent: "space-between",
          backgroundColor: apexTheme.bgSurface,
        }}
      >
        <text>
          <span style={{ fg: agent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>
            {agent?.name ?? "APEX Coder"}
          </span>
          <span style={{ fg: apexTheme.textMuted }}> | </span>
          <span style={{ fg: apexTheme.textDim }}>{model?.name ?? "No Model"}</span>
        </text>
        {isGenerating ? (
          <text>
            <span style={{ fg: apexTheme.warning }}>Generating...</span>
          </text>
        ) : (
          <text>
            <span style={{ fg: apexTheme.green }}>Ready</span>
          </text>
        )}
      </box>

      {/* Messages area */}
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
            trackOptions: {
              foregroundColor: apexTheme.cyan,
              backgroundColor: apexTheme.scrollbarTrack,
            },
          },
        }}
      >
        {/* Welcome message when no messages */}
        {messages.length === 0 ? (
          <box style={{ padding: 2, flexDirection: "column" }}>
            <text>
              <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>{"    "}APEX</span>
              {"\n"}
              <span style={{ fg: apexTheme.textDim }}> AI-Powered Engineering eXtended</span>
              {"\n\n"}
              <span style={{ fg: apexTheme.textMuted }}> Type a message below to start</span>
              {"\n"}
              <span style={{ fg: apexTheme.textMuted }}> Ctrl+K: Model | Tab: Agent | ?: Help</span>
            </text>
          </box>
        ) : null}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isGenerating ? (
          <box style={{ paddingLeft: 1 }}>
            <text>
              <span style={{ fg: apexTheme.cyan }}>| </span>
              <span style={{ fg: apexTheme.textDim }}>Thinking...</span>
            </text>
          </box>
        ) : null}
      </scrollbox>

      {/* Input area */}
      <box
        style={{
          height: 3,
          flexDirection: "column",
          border: true,
          borderColor: apexTheme.borderFocus,
          borderStyle: "single",
          backgroundColor: apexTheme.bgSurface,
        }}
      >
        <input
          id="apex-chat-input"
          placeholder="Message APEX... (Enter to send)"
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
