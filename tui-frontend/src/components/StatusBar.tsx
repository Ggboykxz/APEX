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
  livePromptTokens?: number
  liveCompletionTokens?: number
  thinkingMode?: "show" | "hide" | "off"
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
  livePromptTokens,
  liveCompletionTokens,
  thinkingMode,
}: StatusBarProps) {
  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const model = APEX_MODELS.find((m) => m.id === activeModel)
  const isStreaming = (livePromptTokens ?? 0) > 0 || (liveCompletionTokens ?? 0) > 0
  const dispPrompt = isStreaming ? livePromptTokens! : totalPromptTokens
  const dispCompletion = isStreaming ? liveCompletionTokens! : totalCompletionTokens

  return (
    <Box paddingX={1}>
      <Box justifyContent="space-between" width="100%">
        <Box>
          <Text color={agent?.color ?? apexTheme.cyan} bold>
            {agent?.name ?? "Build"}
          </Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={apexTheme.fg}>{model?.name ?? activeModel}</Text>
        </Box>
        <Box>
          <Text color={apexTheme.dimGray}>In: </Text>
          <Text color={isStreaming ? apexTheme.yellow : apexTheme.fg}>{dispPrompt.toLocaleString()}</Text>
          <Text color={apexTheme.dimGray}> Out: </Text>
          <Text color={isStreaming ? apexTheme.yellow : apexTheme.fg}>{dispCompletion.toLocaleString()}</Text>
          <Text color={apexTheme.dimGray}> Total: </Text>
          <Text color={apexTheme.fg}>{totalTokens.toLocaleString()}</Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={contextPct > 80 ? apexTheme.warning : apexTheme.fg}>
            {isFinite(contextPct) ? `${contextPct.toFixed(1)}% ctx` : "—% ctx"}
          </Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={apexTheme.green}>${totalSpent.toFixed(4)}</Text>
          <Text color={apexTheme.dimGray}> · </Text>
          <Text color={apexTheme.dimGray}>{sessionDuration}</Text>
          {thinkingMode && thinkingMode !== "show" && (
            <>
              <Text color={apexTheme.dimGray}> · </Text>
              <Text color={apexTheme.yellow}>[think:{thinkingMode}]</Text>
            </>
          )}
        </Box>
      </Box>
    </Box>
  )
}
