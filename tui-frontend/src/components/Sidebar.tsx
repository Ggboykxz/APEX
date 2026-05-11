import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface SidebarProps {
  activeAgent: string
  onAgentSelect: (id: string) => void
}

export function Sidebar({ activeAgent }: SidebarProps) {
  return (
    <Box flexDirection="column" width={20} borderStyle="single" borderColor={apexTheme.border} paddingX={1}>
      <Box marginBottom={1}>
        <Text color={apexTheme.cyan} bold>AGENTS</Text>
      </Box>
      {APEX_AGENTS.map((a) => (
        <Box key={a.id} marginBottom={0}>
          <Text color={a.id === activeAgent ? a.color : apexTheme.gray}>
            {a.id === activeAgent ? "● " : "  "}
            {a.name}
          </Text>
        </Box>
      ))}
      <Box marginTop={1} flexDirection="column">
        <Text color={apexTheme.dimGray}>──────────</Text>
        <Text color={apexTheme.dimGray}>Tab to switch</Text>
      </Box>
    </Box>
  )
}
