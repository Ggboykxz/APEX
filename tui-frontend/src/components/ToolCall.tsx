"use strict";

/**
 * ToolCall — renders a single tool call from the streaming reducer.
 * Status colors: running=yellow, success=green, error=red.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { StreamToolCall } from "../streaming/reducer.js"

interface ToolCallProps {
  tool: StreamToolCall
}

export function ToolCall({ tool }: ToolCallProps) {
  const icon =
    tool.status === "running"
      ? "⚙"
      : tool.status === "error"
        ? "✗"
        : "✓"
  const color =
    tool.status === "running"
      ? apexTheme.yellow
      : tool.status === "error"
        ? apexTheme.red
        : apexTheme.green

  return (
    <Box>
      <Text color={color}>{icon} </Text>
      <Text color={apexTheme.fg}>{tool.name}</Text>
      <Text color={apexTheme.dimGray}>
        {tool.status === "running"
          ? " running…"
          : tool.status === "error"
            ? ` ${tool.error ?? "failed"}`
            : ` ${tool.durationMs ?? 0}ms`}
      </Text>
    </Box>
  )
}
