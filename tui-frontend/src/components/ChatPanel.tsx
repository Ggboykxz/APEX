"use strict";

/**
 * ChatPanel — the conversation surface.
 *
 * Rows are split the way OpenCode does it:
 *  - `<Static>` owns the rows that scrolled out of the live window. Ink prints
 *    them once, permanently, into the terminal scrollback, so finished
 *    messages never re-render and history survives redraws.
 *  - the live area owns the tail window, the in-flight tool cards and the
 *    streaming indicator, all of which change every frame.
 *
 * `tail` decides whether new rows keep pushing the window down. When the user
 * has scrolled up (`tail === false`) the committed boundary freezes, so the
 * view is never yanked back to the bottom.
 */

import React from "react"
import { Box, Static, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"
import { ChatMessage } from "./ChatMessage.js"
import { ToolCall } from "./ToolCall.js"
import { ApexLogo } from "./ApexLogo.js"
import { Autocomplete } from "./Autocomplete.js"
import type { ChatMessage as ChatMessageType } from "../data/apex-data.js"
import type { StreamToolCall } from "../streaming/reducer.js"
import type { TuiState } from "../store/tuiStore.js"

interface ChatPanelProps {
  messages: ChatMessageType[]
  /** Monotonic count of rows already printed into `<Static>`. */
  committedCount: number
  /** Changes when the transcript is cleared, remounting `<Static>`. */
  staticEpoch: number
  tail: boolean
  inputValue: string
  activeAgent: string
  activeModel: string
  isGenerating: boolean
  showThinking?: boolean
  tools?: StreamToolCall[]
  expandedToolId?: string | null
  /** Currently visible autocomplete list, if any. */
  completion?: TuiState["completion"]
  /** Insert a selected completion value into the composer. */
  onSelectCompletion?: (value: string) => void
}

function StreamingIndicator() {
  return (
    <Box>
      <Text color={apexTheme.cyan}>⠋ </Text>
      <Text color={apexTheme.gray}>Thinking</Text>
      <Text color={apexTheme.gray}>▎</Text>
    </Box>
  )
}

export function ChatPanel({
  messages,
  committedCount,
  staticEpoch,
  tail,
  inputValue,
  activeAgent,
  activeModel,
  isGenerating,
  showThinking = true,
  tools = [],
  expandedToolId = null,
  completion,
  onSelectCompletion,
}: ChatPanelProps) {
  const committed = messages.slice(0, committedCount)
  const live = messages.slice(committedCount)
  const agentColor = APEX_AGENTS.find((a) => a.id === activeAgent)?.color ?? apexTheme.green

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Static key={staticEpoch} items={committed} style={{ flexDirection: "column" }}>
        {(message: ChatMessageType) => (
          <ChatMessage key={message.id} message={message} showThinking={showThinking} />
        )}
      </Static>

      {/* Live tail window */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {live.length === 0 && !isGenerating && (
          <Box flexDirection="column" paddingY={1} alignItems="center">
            <ApexLogo />
          </Box>
        )}

        {live.map((message) => (
          <ChatMessage key={message.id} message={message} showThinking={showThinking} />
        ))}

        {tools.slice(-5).map((tool) => (
          <ToolCall key={tool.id} tool={tool} expanded={expandedToolId === tool.id} />
        ))}

        {isGenerating ? <StreamingIndicator /> : null}
      </Box>

      {!tail ? (
        <Text color={apexTheme.yellow}>↑ Scrolled up — PgDn to follow again</Text>
      ) : null}

      {/* Input Area */}
      <Box borderStyle="single" borderColor={agentColor} paddingX={1}>
        <Text color={apexTheme.cyan} bold>› </Text>
        <Text color={apexTheme.fg}>{inputValue}</Text>
        <Text color={apexTheme.gray}>▎</Text>
      </Box>

      {completion?.visible && onSelectCompletion && (
        <Autocomplete
          trigger={completion.trigger}
          prefix={completion.prefix}
          items={completion.items}
          index={completion.index}
          onSelect={onSelectCompletion}
        />
      )}

      {/* Help Hint Bar */}
      <Box>
        <Text color={apexTheme.dimGray}>
          {" "}Tab:agents  @:files  !:bash  Ctrl+P:palette  Ctrl+E:tool  ?:help
        </Text>
      </Box>
    </Box>
  )
}
