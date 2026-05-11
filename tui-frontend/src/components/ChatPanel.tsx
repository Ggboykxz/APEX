import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { ChatMessage } from "../data/apex-data.js"

interface ChatPanelProps {
  messages: ChatMessage[]
  inputValue: string
  activeAgent: string
  activeModel: string
  isGenerating: boolean
}

export function ChatPanel({ messages, inputValue, activeAgent, activeModel, isGenerating }: ChatPanelProps) {
  // Show only the last N messages that fit in the terminal
  const visibleMessages = messages.slice(-20)

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Messages */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {visibleMessages.length === 0 && (
          <Box paddingY={2}>
            <Text color={apexTheme.gray}>
              Welcome to APEX. Type a message to start chatting.
            </Text>
          </Box>
        )}
        {visibleMessages.map((msg) => (
          <Box key={msg.id} flexDirection="column" marginBottom={1}>
            {msg.role === "user" ? (
              <Box>
                <Text color={apexTheme.cyan} bold>› </Text>
                <Text color={apexTheme.fg}>{msg.content}</Text>
              </Box>
            ) : (
              <Box flexDirection="column">
                <Box>
                  <Text color={apexTheme.green} bold>◆ </Text>
                  <Text color={apexTheme.gray}>{msg.agent ?? "assistant"}</Text>
                  {msg.model && <Text color={apexTheme.dimGray}> · {msg.model}</Text>}
                  {msg.cost !== undefined && msg.cost > 0 && (
                    <Text color={apexTheme.dimGray}> · ${msg.cost.toFixed(4)}</Text>
                  )}
                </Box>
                <Text color={apexTheme.fg}>{msg.content}</Text>
              </Box>
            )}
          </Box>
        ))}
        {isGenerating && (
          <Box>
            <Text color={apexTheme.cyan}>⠋ </Text>
            <Text color={apexTheme.gray}>Thinking...</Text>
          </Box>
        )}
      </Box>

      {/* Input Line */}
      <Box borderStyle="single" borderColor={apexTheme.border} paddingX={1}>
        <Text color={apexTheme.cyan} bold>› </Text>
        <Text color={apexTheme.fg}>{inputValue}</Text>
        <Text color={apexTheme.gray}>▎</Text>
      </Box>

      {/* Help hint */}
      <Box>
        <Text color={apexTheme.dimGray}>
          {" "}Tab:agents  Ctrl+O:sidebar  Ctrl+L:clear  Ctrl+Q:quit
        </Text>
      </Box>
    </Box>
  )
}
