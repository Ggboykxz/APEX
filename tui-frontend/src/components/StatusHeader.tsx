"use strict";

/**
 * StatusHeader — top bar showing current agent, model, message count,
 * context percentage and total cost. Styled with the APEX charter.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface StatusHeaderProps {
  activeAgent: string
  activeModel: string | undefined
  messageCount: number
  contextPct: number
  totalSpent: number
}

function getAgentColor(agentId: string): string {
  const agent = APEX_AGENTS.find((a) => a.id === agentId)
  return agent?.color ?? apexTheme.green
}

function getAgentName(agentId: string): string {
  const agent = APEX_AGENTS.find((a) => a.id === agentId)
  return agent?.name ?? agentId
}

export function StatusHeader({
  activeAgent,
  activeModel,
  messageCount,
  contextPct,
  totalSpent,
}: StatusHeaderProps) {
  const agentColor = getAgentColor(activeAgent)
  const agentName = getAgentName(activeAgent)

  return (
    <Box width="100%" justifyContent="space-between">
      <Box>
        <Text color={agentColor} bold>{agentName}</Text>
        <Text color={apexTheme.dimGray}> · </Text>
        <Text color={apexTheme.fg}>{activeModel ?? "No Model"}</Text>
      </Box>
      <Box>
        <Text color={apexTheme.dimGray}>{messageCount} msgs</Text>
        <Text color={apexTheme.dimGray}> · </Text>
        <Text color={contextPct > 80 ? apexTheme.warning : apexTheme.fg}>
          {contextPct.toFixed(1)}% ctx
        </Text>
        <Text color={apexTheme.dimGray}> · </Text>
        <Text color={apexTheme.green}>${totalSpent.toFixed(4)}</Text>
      </Box>
    </Box>
  )
}
