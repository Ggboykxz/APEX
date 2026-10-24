/**
 * Overlay components for the APEX TUI.
 *
 * Rendered above the main chat surface, each overlay is a small self-contained
 * component (list + navigation) — the same mental model as OpenCode's
 * palettes/selectors. They are stateless on purpose: keyboard handling lives
 * in the parent (ApexApp), the overlays only render state.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { AgentInfo, ModelInfo, SessionInfo, ThemeInfo } from "../types.js"

interface SelectRow<T> {
  key: string
  label: string
  secondary?: string
  activeColor?: string
  item: T
}

interface SelectOverlayProps<T> {
  title: string
  hint: string
  rows: SelectRow<T>[]
  index: number
  query?: string
  onSelect: (item: T) => void
  maxVisible?: number
}

export function SelectOverlay<T>({ title, hint, rows, index, query, onSelect, maxVisible = 15 }: SelectOverlayProps<T>) {
  const visible = rows.slice(0, maxVisible)
  return (
    <Box flexDirection="column" flexGrow={1} padding={1}>
      <Text color={apexTheme.cyan} bold>{title} </Text><Text color={apexTheme.gray}>({hint})</Text>
      {query !== undefined && (
        <Box borderStyle="single" borderColor={apexTheme.border} paddingX={1}>
          <Text color={apexTheme.accent}>&gt; </Text><Text color={apexTheme.fg}>{query}</Text><Text color={apexTheme.gray}>▎</Text>
        </Box>
      )}
      <Box flexDirection="column" marginTop={1}>
        {visible.length === 0 && <Text color={apexTheme.gray}>No matches</Text>}
        {visible.map((row, i) => {
          const selected = i === index % Math.max(1, rows.length)
          return (
            <Box key={row.key}>
              <Text color={selected ? (row.activeColor ?? apexTheme.cyan) : apexTheme.fg} bold={selected}>
                {selected ? "▸ " : "  "}{row.label}
              </Text>
              {row.secondary && <Text color={apexTheme.gray}> {row.secondary}</Text>}
            </Box>
          )
        })}
      </Box>
      {rows.length > maxVisible && <Text color={apexTheme.gray}>… {rows.length - maxVisible} more</Text>}
    </Box>
  )
}

export function CommandPalette(props: {
  commands: Array<{ id: string; desc: string }>
  query: string
  index: number
  onSelect: (id: string) => void
}) {
  const rows = props.commands.map((c) => ({ key: c.id, label: c.id, secondary: `— ${c.desc}`, item: c.id }))
  return (
    <SelectOverlay
      title="Command Palette"
      hint="type, Enter select, Esc close"
      rows={rows}
      index={props.index}
      query={props.query}
      onSelect={(id) => props.onSelect(id)}
      maxVisible={15}
    />
  )
}

export function ModelSelector(props: {
  models: ModelInfo[]
  query: string
  index: number
  onSelect: (id: string) => void
}) {
  const rows = props.models.map((m) => ({
    key: m.id,
    label: m.name,
    secondary: `(${m.provider} · ${Math.round(m.contextWindow / 1000)}k ctx · $${m.inputCostPer1K}/${m.outputCostPer1K} per 1K)`,
    item: m.id,
  }))
  return <SelectOverlay title="Model Selector" hint={`${props.models.length} — type, Enter select, Esc close`} rows={rows} index={props.index} query={props.query} onSelect={(id) => props.onSelect(id)} />
}

export function ThemeSelector(props: {
  themes: ThemeInfo[]
  index: number
  onSelect: (id: string) => void
}) {
  const rows = props.themes.map((t) => ({ key: t.id, label: t.name, secondary: `(${t.id})`, item: t.id }))
  return <SelectOverlay title="Theme Selector" hint="Enter select, Esc close" rows={rows} index={props.index} onSelect={(id) => props.onSelect(id)} maxVisible={20} />
}

export function AgentSelector(props: {
  agents: AgentInfo[]
  index: number
  onSelect: (id: string) => void
}) {
  const rows = props.agents.map((a) => ({
    key: a.id,
    label: `${a.mode === "subagent" ? "@ " : "  "}${a.name}`,
    secondary: `— ${a.description}`,
    activeColor: a.color ?? apexTheme.cyan,
    item: a.id,
  }))
  return <SelectOverlay title="Agent Selector" hint="Enter select, Esc close" rows={rows} index={props.index} onSelect={(id) => props.onSelect(id)} maxVisible={20} />
}

export function SessionList(props: {
  sessions: SessionInfo[]
  index: number
  onSelect: (id: string) => void
}) {
  const rows = props.sessions.map((s) => ({ key: s.id, label: s.name, secondary: `(${s.model ?? "—"})`, item: s.id }))
  return <SelectOverlay title="Sessions" hint="Enter switch, Esc close" rows={rows} index={props.index} onSelect={(id) => props.onSelect(id)} />
}

export function FileFinder(props: {
  files: string[]
  query: string
  index: number
  onSelect: (file: string) => void
}) {
  const rows = props.files.map((f) => ({
    key: f,
    label: `${f.endsWith("/") ? "[DIR] " : "[FILE] "}${f}`,
    activeColor: f.endsWith("/") ? apexTheme.yellow : apexTheme.cyan,
    item: f,
  }))
  return (
    <Box borderStyle="single" borderColor={apexTheme.border} paddingX={1}>
      <Box flexDirection="column">
        <Text color={apexTheme.cyan} bold>@ File Reference </Text><Text color={apexTheme.gray}>(filter, Tab/Enter select, Esc close)</Text>
        <Text color={apexTheme.fg}>@{props.query}<Text color={apexTheme.gray}>▎</Text></Text>
        <Box flexDirection="column" marginTop={1}>
          {rows.length === 0 && <Text color={apexTheme.gray}>No files</Text>}
          {rows.slice(0, 8).map((row, i) => {
            const selected = i === props.index % Math.max(1, rows.length)
            return (
              <Text key={row.key} color={selected ? apexTheme.cyan : row.activeColor ?? apexTheme.fg} bold={selected}>
                {selected ? "▸ " : "  "}{row.label}
              </Text>
            )
          })}
        </Box>
      </Box>
    </Box>
  )
}

export function HelpOverlay(props: { onClose: () => void }) {
  return (
    <Box flexDirection="column" flexGrow={1} padding={1}>
      <Text color={apexTheme.cyan} bold>HELP — Keyboard Shortcuts</Text>
      <Text color={apexTheme.green} bold>Navigation</Text>
      <Text color={apexTheme.fg}>  Tab          Switch agent        PgUp/PgDown   Scroll messages</Text>
      <Text color={apexTheme.fg}>  ?            Help                 @             File finder</Text>
      <Text color={apexTheme.green} bold>Commands</Text>
      <Text color={apexTheme.fg}>  Ctrl+P       Command palette     Ctrl+K        Model selector</Text>
      <Text color={apexTheme.fg}>  Ctrl+O       Toggle sidebar      Ctrl+L        Clear chat</Text>
      <Text color={apexTheme.fg}>  Ctrl+T       Thinking mode       Ctrl+Q        Quit</Text>
      <Text color={apexTheme.green} bold>Leader Key (Ctrl+X then...)</Text>
      <Text color={apexTheme.fg}>  N  /new      U  /undo           R  /redo      C  /compact</Text>
      <Text color={apexTheme.fg}>  M  /models   T  /themes         S  Status     E  /editor</Text>
      <Text color={apexTheme.fg}>  X  /export   B  Sidebar         A  Agents     L  Sessions</Text>
      <Text color={apexTheme.fg}>  Q  Quit</Text>
      <Text color={apexTheme.green} bold>System</Text>
      <Text color={apexTheme.fg}>  Enter        Send               !command     Bash execute</Text>
      <Text color={apexTheme.gray}>  Press Escape to close</Text>
    </Box>
  )
}

export function StatusOverlay(props: {
  agentName: string
  agentColor: string
  modelName: string
  provider: string
  contextWindow: number
  messageCount: number
  totalPromptTokens: number
  totalCompletionTokens: number
  totalTokens: number
  totalSpent: number
  sessionDuration: string
  thinkingMode: string
  contextPct: number
}) {
  return (
    <Box flexDirection="column" flexGrow={1} padding={2}>
      <Text color={apexTheme.cyan} bold>Session Status</Text>
      <Text color={apexTheme.gray}>Agent:    </Text><Text color={props.agentColor} bold>{props.agentName}</Text>
      <Text color={apexTheme.gray}>Model:    </Text><Text color={apexTheme.fg}>{props.modelName}</Text>
      <Text color={apexTheme.gray}>Provider: </Text><Text color={apexTheme.fg}>{props.provider}</Text>
      <Text color={apexTheme.gray}>Context:  </Text><Text color={apexTheme.fg}>{props.contextWindow.toLocaleString()} tokens</Text>
      <Text color={apexTheme.gray}>Messages: </Text><Text color={apexTheme.fg}>{props.messageCount}</Text>
      <Text color={apexTheme.gray}>Tokens — P: {props.totalPromptTokens.toLocaleString()} / C: {props.totalCompletionTokens.toLocaleString()} / T: {props.totalTokens.toLocaleString()}</Text>
      <Text color={apexTheme.gray}>Cost:     </Text><Text color={apexTheme.green}>${props.totalSpent.toFixed(4)}</Text>
      <Text color={apexTheme.gray}>Duration: </Text><Text color={apexTheme.fg}>{props.sessionDuration}</Text>
      <Text color={apexTheme.gray}>Thinking: </Text><Text color={apexTheme.fg}>{props.thinkingMode}</Text>
      <Text color={apexTheme.gray}>Context:  </Text><Text color={props.contextPct > 80 ? apexTheme.warning : apexTheme.fg}>{props.contextPct.toFixed(1)}%</Text>
    </Box>
  )
}
