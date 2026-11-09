"use strict";

/**
 * ChatPanel — renders the message list, live tool activity, streaming indicator,
 * input box, and hint bar. Message rendering is delegated to ChatMessage atoms;
 * tool call rendering to ToolCall atoms.
 */

import React, { useState } from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"
import { ChatMessage } from "./ChatMessage.js"
import { ToolCall } from "./ToolCall.js"
import type { ChatMessage as ChatMessageType } from "../data/apex-data.js"
import type { StreamToolCall } from "../streaming/reducer.js"

interface ChatPanelProps {
  messages: ChatMessageType[]
  inputValue: string
  activeAgent: string
  activeModel: string
  isGenerating: boolean
  showThinking?: boolean
  /** Live tool calls from the streaming reducer (WebSocket event path). */
  tools?: StreamToolCall[]
}

function formatTokens(t?: number): string {
  return t !== undefined && t !== null ? t.toString() : "-"
}

export function ChatPanel({
  messages,
  inputValue,
  activeAgent,
  activeModel,
  isGenerating,
  showThinking = true,
  tools = [],
}: ChatPanelProps) {
  const visibleMessages = messages.slice(-20)
  const agentColor = APEX_AGENTS.find((a) => a.id === activeAgent)?.color ?? apexTheme.green

  const [panelState, setPanelState] = useState<"normal" | "leader" | "command-palette" | "file-search">("normal")

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Messages */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {visibleMessages.length === 0 && !isGenerating && (
          <Box flexDirection="column" paddingY={1}>
            <Text color={apexTheme.green} bold>▲ APEX v2.0.0</Text>
            <Text color={apexTheme.gray}>Type a message or use /commands</Text>
            <Text color={apexTheme.dimGray}>Tab — Switch agents</Text>
            <Text color={apexTheme.dimGray}>Ctrl+P — Command palette</Text>
            <Text color={apexTheme.dimGray}>@ — Reference files</Text>
            <Text color={apexTheme.dimGray}>! — Run bash commands</Text>
          </Box>
        )}

        {visibleMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} showThinking={showThinking} />
        ))}

        {/* Live tool activity from the streaming reducer */}
        {tools.slice(-5).map((tool) => (
          <ToolCall key={tool.id} tool={tool} />
        ))}

        {/* Streaming indicator */}
        {isGenerating && (
          <Box>
            <Text color={apexTheme.cyan}>⠋ </Text>
            <Text color={apexTheme.gray}>Thinking</Text>
            <Text color={apexTheme.gray}>▎</Text>
          </Box>
        )}
      </Box>

      {/* Input Area */}
      <Box flexDirection="column">
        {/* Input box */}
        <Box borderStyle="single" borderColor={agentColor} paddingX={1}>
          <Text color={apexTheme.cyan} bold>› </Text>
          <Text color={apexTheme.fg}>{inputValue}</Text>
          <Text color={apexTheme.gray}>▎</Text>
        </Box>
      </Box>

      {/* Help Hint Bar */}
      <Box>
        {panelState === "normal" && (
          <Text color={apexTheme.dimGray}>
            {" "}Tab:agents  @:files  !:bash  Ctrl+P:palette  ?:help
          </Text>
        )}
        {panelState === "leader" && (
          <Text color={apexTheme.yellow}>
            {" "}Leader: press key (n=new u=undo r=redo c=compact...)
          </Text>
        )}
        {panelState === "command-palette" && (
          <Text color={apexTheme.purple}>
            {" "}Type to filter ↑↓ navigate Enter select Esc close
          </Text>
        )}
        {panelState === "file-search" && (
          <Text color={apexTheme.cyan}>
            {" "}↑↓ navigate Enter select Esc close
          </Text>
        )}
      </Box>
    </Box>
  )
}
