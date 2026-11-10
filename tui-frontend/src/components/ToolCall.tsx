"use strict";

/**
 * ToolCall — renders one tool call from the streaming reducer.
 *
 * The card is a controlled atom: `expanded` comes from the store and the
 * toggle key is owned by ApexApp, so several cards can coexist without
 * fighting over Ink's single input channel.
 *
 * Running calls show a braille spinner, finished calls a ✓/✗ and their
 * duration. Errors always render their body through `ToolErrorCard`.
 */

import React, { useEffect, useState } from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { StreamToolCall } from "../streaming/reducer.js"

const FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
const FRAME_MS = 80
const MAX_ARG_LENGTH = 120
const MAX_OUTPUT_LENGTH = 4000

function Spinner() {
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setFrame((current) => (current + 1) % FRAMES.length), FRAME_MS)
    return () => clearInterval(id)
  }, [])

  return <Text color={apexTheme.yellow}>{FRAMES[frame]}</Text>
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function formatValue(value: unknown): string {
  if (typeof value === "string") return truncate(value, MAX_ARG_LENGTH)
  try {
    return truncate(JSON.stringify(value), MAX_ARG_LENGTH)
  } catch {
    return truncate(String(value), MAX_ARG_LENGTH)
  }
}

function formatArgs(args?: Record<string, unknown>): string {
  if (!args) return ""
  return Object.entries(args)
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join("  ")
}

function formatOutput(output?: string): string {
  return truncate(output ?? "", MAX_OUTPUT_LENGTH)
}

function ToolStatus({ tool }: { tool: StreamToolCall }) {
  if (tool.status === "running") {
    return (
      <Box>
        <Spinner />
        <Text color={apexTheme.fg}> {tool.name}</Text>
        <Text color={apexTheme.dimGray}> running…</Text>
      </Box>
    )
  }

  const failed = tool.status === "error"
  return (
    <Box>
      <Text color={failed ? apexTheme.red : apexTheme.green}>{failed ? "✗" : "✓"} </Text>
      <Text color={apexTheme.fg}>{tool.name}</Text>
      <Text color={apexTheme.dimGray}>
        {failed ? ` ${tool.error ?? "failed"}` : ` ${tool.durationMs ?? 0}ms`}
      </Text>
    </Box>
  )
}

/** Error body: always visible, never collapsed. */
export function ToolErrorCard({ tool }: { tool: StreamToolCall }) {
  const lines = formatOutput(tool.error).split("\n")
  return (
    <Box flexDirection="column" marginLeft={2}>
      {lines.map((line, index) => (
        <Text key={index} color={apexTheme.red}>
          {line}
        </Text>
      ))}
    </Box>
  )
}

function ToolBody({ tool }: { tool: StreamToolCall }) {
  const args = formatArgs(tool.args)
  if (tool.status === "error") return <ToolErrorCard tool={tool} />
  const output = formatOutput(tool.output)
  if (!args && !output) return null
  return (
    <Box flexDirection="column" marginLeft={2}>
      {args ? <Text color={apexTheme.gray}>{args}</Text> : null}
      {output ? <Text color={apexTheme.gray}>{output}</Text> : null}
    </Box>
  )
}

interface ToolCallProps {
  tool: StreamToolCall
  expanded: boolean
}

export function ToolCall({ tool, expanded }: ToolCallProps) {
  const failed = tool.status === "error"
  const showBody = expanded || failed

  return (
    <Box flexDirection="column">
      <ToolStatus tool={tool} />
      {showBody ? <ToolBody tool={tool} /> : null}
    </Box>
  )
}
