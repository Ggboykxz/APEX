import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_KEYBINDINGS, APEX_AGENTS, APEX_TOOLS } from "../data/apex-data.js"

interface HelpPanelProps {
  visible: boolean
  onClose: () => void
  tab: "keybindings" | "agents" | "tools"
  onTabChange: (tab: "keybindings" | "agents" | "tools") => void
}

export function HelpPanel({ visible, onClose, tab, onTabChange }: HelpPanelProps) {
  if (!visible) return null

  const currentAgent = APEX_AGENTS[0]
  const navKbs = APEX_KEYBINDINGS.filter((kb) => kb.category === "Navigation")
  const chatKbs = APEX_KEYBINDINGS.filter((kb) => kb.category === "Chat")
  const viewKbs = APEX_KEYBINDINGS.filter((kb) => kb.category === "View")

  return (
    <box
      id="apex-help"
      style={{
        position: "absolute",
        top: 2,
        left: "50%",
        width: 70,
        height: 26,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: currentAgent?.color ?? apexTheme.cyan,
        borderStyle: "double",
        zIndex: 200,
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay, flexDirection: "row", alignItems: "center" }}>
        <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ APEX Help</span>
        <span style={{ fg: apexTheme.textMuted }}> - Press Esc to close</span>
      </box>

      <box style={{ height: 1, flexDirection: "row", paddingLeft: 1 }}>
        {(["keybindings", "agents", "tools"] as const).map((t) => (
          <box
            key={t}
            style={{
              paddingRight: 2,
              backgroundColor: tab === t ? apexTheme.bgOverlay : "transparent",
            }}
            onMouseDown={() => onTabChange(t)}
          >
            <span
              style={{
                fg: tab === t ? (currentAgent?.color ?? apexTheme.cyan) : apexTheme.textMuted,
                attributes: tab === t ? TextAttributes.BOLD : 0,
              }}
            >
              {tab === t ? "▸" : " "} {t}
            </span>
          </box>
        ))}
      </box>

      <box style={{ height: 1, backgroundColor: currentAgent?.color ?? apexTheme.cyan, opacity: 0.3 }} />

      <scrollbox
        style={{
          flexGrow: 1,
          rootOptions: { backgroundColor: apexTheme.bgSurface },
          contentOptions: { backgroundColor: apexTheme.bgSurface },
          scrollbarOptions: {
            showArrows: false,
            trackOptions: {
              foregroundColor: currentAgent?.color ?? apexTheme.cyan,
              backgroundColor: apexTheme.scrollbarTrack,
            },
          },
        }}
      >
        {tab === "keybindings" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>══ NAVIGATION ══</span>
            {navKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                <span style={{ fg: apexTheme.text }}>{kb.action}</span>
              </box>
            ))}
            <box style={{ height: 1 }} />
            <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>══ CHAT ══</span>
            {chatKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                <span style={{ fg: apexTheme.text }}>{kb.action}</span>
              </box>
            ))}
            <box style={{ height: 1 }} />
            <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>══ VIEW ══</span>
            {viewKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                <span style={{ fg: apexTheme.text }}>{kb.action}</span>
              </box>
            ))}
          </box>
        )}

        {tab === "agents" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>══ AVAILABLE AGENTS ══</span>
            {APEX_AGENTS.map((agent) => (
              <box key={agent.id} style={{ height: 2, marginBottom: 1 }}>
                <span style={{ fg: agent.color, attributes: TextAttributes.BOLD }}>{agent.icon} {agent.name}</span>
                <span style={{ fg: apexTheme.textMuted }}> - {agent.role}</span>
              </box>
            ))}
          </box>
        )}

        {tab === "tools" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>══ {APEX_TOOLS.length}+ TOOLS ══</span>
            {Array.from(new Set(APEX_TOOLS.map((t) => t.category))).map((category) => (
              <box key={category} style={{ height: 2, marginBottom: 1 }}>
                <span style={{ fg: currentAgent?.color ?? apexTheme.cyan, attributes: TextAttributes.BOLD }}>- {category}</span>
                <span style={{ fg: apexTheme.textDim }}> {APEX_TOOLS.filter((t) => t.category === category).slice(0, 5).map((t) => t.name).join(", ")}</span>
              </box>
            ))}
          </box>
        )}
      </scrollbox>

      <box style={{ height: 1, backgroundColor: apexTheme.bgOverlay }}>
        <span style={{ fg: apexTheme.textMuted }}>Press Esc to close</span>
      </box>
    </box>
  )
}