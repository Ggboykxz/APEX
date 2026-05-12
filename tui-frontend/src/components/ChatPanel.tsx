import React, { useState } from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { APEX_AGENTS, type ChatMessage } from "../data/apex-data.js"

interface ChatPanelProps {
  messages: ChatMessage[]
  inputValue: string
  activeAgent: string
  activeModel: string
  isGenerating: boolean
  showThinking?: boolean
}

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

export function ChatPanel({
  messages,
  inputValue,
  activeAgent,
  activeModel,
  isGenerating,
  showThinking = true,
}: ChatPanelProps) {
  const visibleMessages = messages.slice(-20)
  const agentColor = getAgentColor(activeAgent)
  const [panelState, setPanelState] = useState<"normal" | "leader" | "command-palette" | "file-search">("normal")

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* Messages */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {visibleMessages.length === 0 && !isGenerating && (
          <Box flexDirection="column" paddingY={1}>
            <Text color={apexTheme.green} bold>▲ APEX v1.5.0</Text>
            <Text color={apexTheme.gray}>Type a message or use /commands</Text>
            <Text color={apexTheme.dimGray}>Tab — Switch agents</Text>
            <Text color={apexTheme.dimGray}>Ctrl+P — Command palette</Text>
            <Text color={apexTheme.dimGray}>@ — Reference files</Text>
            <Text color={apexTheme.dimGray}>! — Run bash commands</Text>
          </Box>
        )}

        {visibleMessages.map((msg) => (
          <Box key={msg.id} flexDirection="column" marginBottom={1}>
            {msg.role === "user" ? (
              <Box flexDirection="column">
                <Box>
                  <Text color={apexTheme.cyan} bold>▌ </Text>
                  <RichText text={msg.content} />
                </Box>
              </Box>
            ) : (
              <Box flexDirection="column">
                {/* Header with agent color, model, tokens, cost */}
                <Box>
                  <Text color={getAgentColor(msg.agent)} bold>◆ </Text>
                  <Text color={getAgentColor(msg.agent)} bold>{getAgentName(msg.agent)}</Text>
                  {msg.model && <Text color={apexTheme.gray}> · {msg.model}</Text>}
                  {(msg.promptTokens !== undefined || msg.completionTokens !== undefined) && (
                    <Text color={apexTheme.dimGray}>
                      {" "}· +{formatTokens(msg.promptTokens)}/+{formatTokens(msg.completionTokens)}
                    </Text>
                  )}
                  {(msg.cost ?? 0) > 0 && (
                    <Text color={apexTheme.dimGray}> · ${msg.cost!.toFixed(4)}</Text>
                  )}
                </Box>

                {/* Error messages */}
                {msg.content.startsWith("Error:") || msg.content.startsWith("✗") ? (
                  <Box>
                    <Text color={apexTheme.red}>✗ {msg.content.replace(/^(Error:\s*|✗\s*)/, "")}</Text>
                  </Box>
                ) : /* System messages */
                msg.content.startsWith("ℹ") ? (
                  <Box>
                    <Text color={apexTheme.cyan}>ℹ {msg.content.replace(/^ℹ\s*/, "")}</Text>
                  </Box>
                ) : (
                  /* Regular content with thinking blocks, tool calls, highlights */
                  <Box flexDirection="column">
                    {splitParts(msg.content).map((part, i) => {
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
        ))}

        {/* Streaming indicator */}
        {isGenerating && (
          <Box>
            <Text color={apexTheme.cyan}>⠋ </Text>
            <Text color={apexTheme.gray}>Thinking</Text>
            <Text color={apexTheme.gray}>▎</Text>
          </Box>
        )}
      </Box>

      {/* Input Area */}
      <Box flexDirection="column">
        {/* Input box */}
        <Box borderStyle="single" borderColor={agentColor} paddingX={1}>
          <Text color={apexTheme.cyan} bold>› </Text>
          <Text color={apexTheme.fg}>{inputValue}</Text>
          <Text color={apexTheme.gray}>▎</Text>
        </Box>
      </Box>

      {/* Help Hint Bar */}
      <Box>
        {panelState === "normal" && (
          <Text color={apexTheme.dimGray}>
            {" "}Tab:agents  @:files  !:bash  Ctrl+P:palette  ?:help
          </Text>
        )}
        {panelState === "leader" && (
          <Text color={apexTheme.yellow}>
            {" "}Leader: press key (n=new u=undo r=redo c=compact...)
          </Text>
        )}
        {panelState === "command-palette" && (
          <Text color={apexTheme.purple}>
            {" "}Type to filter ↑↓ navigate Enter select Esc close
          </Text>
        )}
        {panelState === "file-search" && (
          <Text color={apexTheme.cyan}>
            {" "}↑↓ navigate Enter select Esc close
          </Text>
        )}
      </Box>
    </Box>
  )
}
