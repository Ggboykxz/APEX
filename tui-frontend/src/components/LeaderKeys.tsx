"use strict";

/**
 * LeaderKeys — displays the leader-key active banner (Ctrl+X then a key).
 * Styled with the APEX accent color.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"

interface LeaderKeysProps {
  active: boolean
  timeout?: number
}

export function LeaderKeys({ active, timeout = 2000 }: LeaderKeysProps) {
  if (!active) return null
  return (
    <Box width="100%" justifyContent="center">
      <Text backgroundColor={apexTheme.accent} color="#000000" bold>
        ⌨ Leader key active — press a shortcut key
      </Text>
    </Box>
  )
}
