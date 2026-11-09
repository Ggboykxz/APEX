"use strict";

/**
 * ChatMessage — renders a single chat message with thinking blocks,
 * tool calls, rich text highlights (@file, !bash, ⚙ tool) and cost/token
 * metadata. Styled with the APEX charter (cyan #00e5ff primary, agent colors
 * from apex-data.ts).
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, type ChatMessage } from "../data/apex-data.js"

function getAgentColor(agentId?: string): string {
  const agent = APEX_AGENTS.find((a) => a.id === agentId)
  return agent?.color ?? apexTheme.green
}

function getAgentName(agentId?: string): string {
  const agent = APEX_AGENTS.find((a) => a.id === agentId)
  return agent?.name ?? agentId ?? "assistant"
}

function formatTokens(t?: number): string {
  return t !== undefined && t !== null ? t.toString() : "-"
}

interface ContentPart {
  text: string
  isThinking: boolean
}

function splitParts(content: string): ContentPart[] {
  const parts: ContentPart[] = []
  const re = /<thinking>([\s\S]*?)<\/thinking>/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(content)) !== null) {
    if (m.index > last) parts.push({ text: content.slice(last, m.index), isThinking: false })
    parts.push({ text: m[1], isThinking: true })
    last = re.lastIndex
  }
  if (last < content.length) parts.push({ text: content.slice(last), isThinking: false })
  return parts.length ? parts : [{ text: content, isThinking: false }]
}

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

interface ChatMessageProps {
  message: ChatMessage
  showThinking?: boolean
  isLast?: boolean
}

export function ChatMessage({
  message,
  showThinking = true,
  isLast = false,
}: ChatMessageProps) {
  const agentColor = getAgentColor(message.agent)

  return (
    <Box key={message.id} flexDirection="column" marginBottom={1}>
      {message.role === "user" ? (
        <Box flexDirection="column">
          <Box>
            <Text color={apexTheme.cyan} bold>▌ </Text>
            <RichText text={message.content} />
          </Box>
        </Box>
      ) : (
        <Box flexDirection="column">
          <Box>
            <Text color={agentColor} bold>◆ </Text>
            <Text color={agentColor} bold>{getAgentName(message.agent)}</Text>
            {message.model && <Text color={apexTheme.gray}> · {message.model}</Text>}
            {(
              message.promptTokens !== undefined ||
              message.completionTokens !== undefined
            ) && (
              <Text color={apexTheme.dimGray}>
                {" "}· +{formatTokens(message.promptTokens)}/+{formatTokens(message.completionTokens)}
              </Text>
            )}
            {(message.cost ?? 0) > 0 && (
              <Text color={apexTheme.dimGray}> · ${message.cost!.toFixed(4)}</Text>
            )}
          </Box>

          {message.content.startsWith("Error:") || message.content.startsWith("✗") ? (
            <Box>
              <Text color={apexTheme.red}>✗ {message.content.replace(/^(Error:\s*|✗\s*)/, "")}</Text>
            </Box>
          ) : message.content.startsWith("ℹ") ? (
            <Box>
              <Text color={apexTheme.cyan}>ℹ {message.content.replace(/^ℹ\s*/, "")}</Text>
            </Box>
          ) : (
            <Box flexDirection="column">
              {splitParts(message.content).map((part, i) => {
                if (part.isThinking) {
                  if (!showThinking) {
                    return (
                      <Box key={i}>
                        <Text color={apexTheme.yellow}>[thinking block]</Text>
                      </Box>
                    )
                  }
                  return (
                    <Box key={i} marginLeft={1}>
                      <Text color={apexTheme.yellow}>{part.text}</Text>
                    </Box>
                  )
                }
                return (
                  <Box key={i}>
                    <RichText text={part.text} />
                  </Box>
                )
              })}
            </Box>
          )}
        </Box>
      )}
    </Box>
  )
}
