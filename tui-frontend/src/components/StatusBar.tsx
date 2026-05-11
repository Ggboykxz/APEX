import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, APEX_MODELS } from "../data/apex-data.js"

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

export function StatusBar({
  activeAgent,
  activeModel,
  totalTokens,
  totalPromptTokens,
  totalCompletionTokens,
  totalSpent,
  contextPct,
  messageCount,
  sessionDuration,
}: StatusBarProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const model = APEX_MODELS.find((m) => m.id === activeModel)

  return (
    <Box justifyContent="space-between" backgroundColor={apexTheme.titleBg} paddingX={1}>
      <Box>
        <Text color={agent?.color ?? apexTheme.cyan} bold>
          {agent?.name ?? "Coder"}
        </Text>
        <Text color={apexTheme.dimGray}> │ </Text>
        <Text color={apexTheme.fg}>{model?.name ?? activeModel}</Text>
        <Text color={apexTheme.dimGray}> │ </Text>
        <Text color={apexTheme.fg}>{messageCount} msgs</Text>
      </Box>
      <Box>
        <Text color={apexTheme.dimGray}>In:</Text>
        <Text color={apexTheme.fg}> {totalPromptTokens.toLocaleString()}</Text>
        <Text color={apexTheme.dimGray}> Out:</Text>
        <Text color={apexTheme.fg}> {totalCompletionTokens.toLocaleString()}</Text>
        <Text color={apexTheme.dimGray}> Total:</Text>
        <Text color={apexTheme.fg}> {totalTokens.toLocaleString()}</Text>
        <Text color={apexTheme.dimGray}> │ </Text>
        <Text color={contextPct > 80 ? apexTheme.warning : apexTheme.fg}>
          {contextPct.toFixed(1)}% ctx
        </Text>
        <Text color={apexTheme.dimGray}> │ </Text>
        <Text color={apexTheme.green}>${totalSpent.toFixed(4)}</Text>
        <Text color={apexTheme.dimGray}> │ </Text>
        <Text color={apexTheme.dimGray}>{sessionDuration}</Text>
      </Box>
    </Box>
  )
}
