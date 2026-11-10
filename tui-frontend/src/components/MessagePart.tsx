"use strict";

/**
 * MessagePart — renders one structured memory part (OpenCode parts pattern,
 * APEX charter colors).
 *
 * Each part is a self-contained atom: text is rich-highlighted, files show
 * their path, tool calls/results render their I/O, images render a placeholder.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { MessagePart } from "../data/apex-data.js"

/** Inline rich text: @file, !bash, ⚙tool are colorized. */
function RichText({ text }: { text: string }) {
  if (!text) return <Text />
  const segments = text.split(
    /(@[\w./-]+|!\w[\w-]*(?:\s+[\w\/.\-~]+)*|⚙\s*\w+\([^)]*\))/g
  )
  return (
    <Text>
      {segments.map((seg, i) => {
        if (seg.startsWith("@")) return <Text key={i} color={apexTheme.cyan}>{seg}</Text>
        if (seg.startsWith("!")) return <Text key={i} color={apexTheme.green}>{seg}</Text>
        if (/^⚙/.test(seg)) return <Text key={i} color={apexTheme.dimGray}>{seg}</Text>
        return <Text key={i}>{seg}</Text>
      })}
    </Text>
  )
}

function PartText({ text }: { text: string }) {
  return (
    <Box flexDirection="column">
      <RichText text={text} />
    </Box>
  )
}

function PartFile({ path, content }: { path: string; content?: string }) {
  return (
    <Box flexDirection="column" marginLeft={2}>
      <Text color={apexTheme.cyan}>📄 {path}</Text>
      {content ? <Text color={apexTheme.dimGray}>{content}</Text> : null}
    </Box>
  )
}

function PartToolCall({
  toolCallId,
  name,
  args,
}: {
  toolCallId: string
  name: string
  args?: Record<string, unknown>
}) {
  const argsText = args ? ` ${JSON.stringify(args).slice(0, 120)}` : ""
  return (
    <Box flexDirection="column" marginLeft={2}>
      <Text color={apexTheme.yellow}>⚙ {name}{argsText}</Text>
      <Text color={apexTheme.dimGray}>id={toolCallId}</Text>
    </Box>
  )
}

function PartToolResult({
  toolCallId,
  output,
  error,
}: {
  toolCallId: string
  output?: string
  error?: string
}) {
  const failed = !!error
  return (
    <Box flexDirection="column" marginLeft={2}>
      <Text color={failed ? apexTheme.red : apexTheme.green}>
        {failed ? "✗" : "✓"} tool result {toolCallId}
      </Text>
      {error ? <Text color={apexTheme.red}>{error}</Text> : null}
      {output ? <Text color={apexTheme.dimGray}>{output}</Text> : null}
    </Box>
  )
}

function PartImage({ path, dataUrl }: { path: string; dataUrl?: string }) {
  return (
    <Box flexDirection="column" marginLeft={2}>
      <Text color={apexTheme.purple}>🖼 {path}</Text>
      {dataUrl ? <Text color={apexTheme.dimGray}>{dataUrl.slice(0, 60)}…</Text> : null}
    </Box>
  )
}

interface MessagePartProps {
  part: MessagePart
}

export function MessagePart({ part }: MessagePartProps) {
  switch (part.type) {
    case "text":
      return <PartText text={part.text} />
    case "file":
      return <PartFile path={part.path} content={part.content} />
    case "tool_call":
      return <PartToolCall toolCallId={part.toolCallId} name={part.name} args={part.args} />
    case "tool_result":
      return <PartToolResult toolCallId={part.toolCallId} output={part.output} error={part.error} />
    case "image":
      return <PartImage path={part.path} dataUrl={part.dataUrl} />
  }
}
