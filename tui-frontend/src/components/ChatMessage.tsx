"use strict";

/**
 * ChatMessage — renders a single chat message with thinking blocks, rich text
 * highlights (@file, !bash, ⚙ tool) and cost/token metadata.
 *
 * Renders `message.parts` (structured memory, §8) when present, falling back
 * to the flattened `content` otherwise. Styled with the APEX charter
 * (cyan #00e5ff primary, agent colors from apex-data.ts).
 */

import React, { memo } from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, type ChatMessage as ChatMessageData, type MessagePart } from "../data/apex-data.js"
import { MessagePart as RenderPart } from "./MessagePart.js"

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

function splitParts(content: string): { text: string; isThinking: boolean }[] {
  const parts: { text: string; isThinking: boolean }[] = []
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

/** Flattened-text path: thinking blocks, rich text, cost metadata. */
function ContentBody({ message }: { message: ChatMessageData }) {
  const parts = splitParts(message.content)
  return (
    <Box flexDirection="column">
      {parts.map((part, i) => {
        if (part.isThinking) {
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
  )
}

/** Structured-parts path: one renderer per part type. */
function PartsBody({ message }: { message: ChatMessageData }) {
  const parts: MessagePart[] = message.parts ?? []
  return (
    <Box flexDirection="column">
      {parts.map((part, i) => (
        <Box key={i} flexDirection="column" marginBottom={1}>
          <RenderPart part={part} />
        </Box>
      ))}
    </Box>
  )
}

interface ChatMessageProps {
  message: ChatMessageData
  showThinking?: boolean
}

function MessageHeader({ message, agentColor }: { message: ChatMessageData; agentColor: string }) {
  return (
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
  )
}

function AssistantBody({ message, showThinking }: { message: ChatMessageData; showThinking: boolean }) {
  if (message.content.startsWith("Error:") || message.content.startsWith("✗")) {
    return (
      <Box>
        <Text color={apexTheme.red}>✗ {message.content.replace(/^(Error:\s*|✗\s*)/, "")}</Text>
      </Box>
    )
  }
  if (message.content.startsWith("ℹ")) {
    return (
      <Box>
        <Text color={apexTheme.cyan}>ℹ {message.content.replace(/^ℹ\s*/, "")}</Text>
      </Box>
    )
  }
  return (
    <Box flexDirection="column">
      {message.parts && message.parts.length > 0 ? (
        <PartsBody message={message} />
      ) : showThinking ? (
        <ContentBody message={message} />
      ) : (
        <Box>
          <Text color={apexTheme.yellow}>[thinking block]</Text>
        </Box>
      )}
    </Box>
  )
}

/**
 * Memoized so a finished row is rendered once and never re-rendered when the
 * live window moves underneath it.
 */
export const ChatMessage = memo(function ChatMessage({
  message,
  showThinking = true,
}: ChatMessageProps) {
  const agentColor = getAgentColor(message.agent)

  return (
    <Box key={message.id} flexDirection="column" marginBottom={1}>
      {message.role === "user" ? (
        <Box flexDirection="column">
          <Box>
            <Text color={apexTheme.cyan} bold>▌ </Text>
            {message.parts && message.parts.length > 0 ? (
              <PartsBody message={message} />
            ) : (
              <RichText text={message.content} />
            )}
          </Box>
        </Box>
      ) : (
        <Box flexDirection="column">
          <MessageHeader message={message} agentColor={agentColor} />
          <AssistantBody message={message} showThinking={showThinking} />
        </Box>
      )}
    </Box>
  )
})
