"use strict";

/**
 * ConnectionError — displays the connection error / reconnecting banner.
 * Styled with APEX error/warning colors.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"

interface ConnectionErrorProps {
  error: string | null
  isReconnecting: boolean
  retryCount: number
}

export function ConnectionError({
  error,
  isReconnecting,
  retryCount,
}: ConnectionErrorProps) {
  if (!error) return null
  return (
    <Box width="100%" justifyContent="space-between">
      <Text backgroundColor={apexTheme.error} color="#000000" bold>
        [!] {error}
      </Text>
      {isReconnecting && (
        <Text backgroundColor={apexTheme.warning} color="#000000" bold>
          [~] Retry {retryCount} — press R to retry
        </Text>
      )}
    </Box>
  )
}
