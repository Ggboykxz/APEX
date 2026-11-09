"use strict";

/**
 * LeaderKeys — displays the leader-key active banner (Ctrl+X then a key).
 * Styled with the APEX accent color. Shows which strokes of the sequence have
 * been entered so far (e.g. "Ctrl+X …").
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { formatKey } from "../keymap/format.js"

interface LeaderKeysProps {
  active: boolean
  strokes?: string[]
  timeout?: number
}

export function LeaderKeys({ active, strokes = [], timeout = 2000 }: LeaderKeysProps) {
  if (!active) return null
  const prefix = strokes.length > 0 ? strokes.map(formatKey).join(" ") : "Ctrl+X"
  return (
    <Box width="100%" justifyContent="center">
      <Text backgroundColor={apexTheme.accent} color="#000000" bold>
        {`⌨ ${prefix} … — press the next shortcut key (${Math.round(timeout / 1000)}s)`}
      </Text>
    </Box>
  )
}
