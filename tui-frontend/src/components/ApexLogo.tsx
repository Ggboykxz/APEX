"use strict";

/**
 * ApexLogo — ASCII art wordmark for the APEX TUI.
 *
 * Styled with the APEX charter: cyan #00e5ff primary, dark background
 * #0d1117. The wordmark spells out "APEX" in terminal-safe block letters.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"

/** APEX wordmark rendered in terminal-safe block letters, one line per row. */
const APEX_ART = [
  "██████╗ ██╗   ██╗██╗███╗   ██╗███████╗██████╗  ██████╗ ",
  "██╔══██╗██║   ██║██║████╗  ██║██╔════╝██╔══██╗██╔═══██╗",
  "██████╔╝██║   ██║██║██╔██╗ ██║█████╗  ██████╔╝██║   ██║",
  "██╔═══╝ ██║   ██║██║██║╚██╗██║██╔══╝  ██╔══██╗██║   ██║",
  "██║     ╚██████╔╝██║██║ ╚████║███████╗██████╔╝╚██████╔╝",
  "╚═╝     ╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝╚═════╝  ╚═════╝ ",
]

/** Summit glyph — a small peak above the wordmark. */
const SUMMIT_ART = [
  "      /\      ",
  "     /  \     ",
  "    /    \    ",
  "   /      \   ",
  "  /        \  ",
  " /          \ ",
  "/____________\\",
]

export function ApexLogo() {
  return (
    <Box flexDirection="column" paddingY={1} alignItems="center">
      <Box flexDirection="column">
        {SUMMIT_ART.map((line, i) => (
          <Text key={i} color={apexTheme.cyan} bold>
            {line}
          </Text>
        ))}
      </Box>
      <Box flexDirection="column">
        {APEX_ART.map((line, i) => (
          <Text key={i} color={apexTheme.cyan} bold>
            {line}
          </Text>
        ))}
      </Box>
      <Box marginTop={1}>
        <Text color={apexTheme.dimGray}>
          v2.0.0 — The universal AI coding agent
        </Text>
      </Box>
    </Box>
  )
}
