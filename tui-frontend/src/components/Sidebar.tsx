import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface SidebarProps {
  activeAgent: string
  onAgentSelect: (id: string) => void
}

export function Sidebar({ activeAgent }: SidebarProps) {
  const primary = APEX_AGENTS.filter((a) => a.mode === "primary")
  const subagents = APEX_AGENTS.filter((a) => a.mode === "subagent")

  return (
    <Box flexDirection="column" width={22} borderStyle="single" borderColor={apexTheme.border} paddingX={1}>
      <Box marginBottom={1}>
        <Text color={apexTheme.cyan} bold>APEX</Text>
      </Box>

      <Text color={apexTheme.dimGray} bold>Agents</Text>
      {primary.map((a) => (
        <Box key={a.id}>
          <Text color={a.id === activeAgent ? a.color : apexTheme.gray}>
            {a.id === activeAgent ? "● " : "  "}{a.name}
          </Text>
        </Box>
      ))}

      <Box marginTop={1}>
        <Text color={apexTheme.dimGray} bold>Subagents</Text>
      </Box>
      {subagents.map((a) => (
        <Box key={a.id}>
          <Text color={a.id === activeAgent ? a.color : apexTheme.gray}>
            {a.id === activeAgent ? "● " : "  "}@{a.name}
          </Text>
        </Box>
      ))}

      <Box marginTop={1}>
        <Text color={apexTheme.dimGray}>──────────</Text>
      </Box>
      <Box flexDirection="column">
        <Text color={apexTheme.dimGray}>Tab: cycle agents</Text>
        <Text color={apexTheme.dimGray}>Ctrl+O: toggle</Text>
      </Box>
    </Box>
  )
}
