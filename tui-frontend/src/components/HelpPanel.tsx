import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_KEYBINDINGS, APEX_AGENTS, APEX_TOOLS } from "../data/apex-data.js"

interface HelpPanelProps {
  visible: boolean
  onClose: () => void
  tab: "keybindings" | "agents" | "tools"
  onTabChange: (tab: "keybindings" | "agents" | "tools") => void
  activeAgent?: string
}

export function HelpPanel({ visible, onClose, tab, onTabChange, activeAgent = "coder" }: HelpPanelProps) {
  if (!visible) return null

  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const agentColor = agent?.color ?? apexTheme.cyan

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
        borderColor: agentColor,
        borderStyle: "double",
        zIndex: 200,
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay, flexDirection: "row", alignItems: "center" }}>
        <text>
          <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>▲ APEX Help</span>
          <span style={{ fg: apexTheme.textMuted }}> - Press Esc to close</span>
        </text>
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
            <text>
              <span
                style={{
                  fg: tab === t ? agentColor : apexTheme.textMuted,
                  attributes: tab === t ? TextAttributes.BOLD : undefined,
                }}
              >
                {tab === t ? "▸" : " "} {t}
              </span>
            </text>
          </box>
        ))}
      </box>

      <box style={{ height: 1, backgroundColor: agentColor, opacity: 0.3 }} />

      <scrollbox
        style={{
          flexGrow: 1,
          rootOptions: { backgroundColor: apexTheme.bgSurface },
          contentOptions: { backgroundColor: apexTheme.bgSurface },
          scrollbarOptions: {
            showArrows: false,
            trackOptions: {
              foregroundColor: agentColor,
              backgroundColor: apexTheme.scrollbarTrack,
            },
          },
        }}
      >
        {tab === "keybindings" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <text>
              <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>══ NAVIGATION ══</span>
            </text>
            {navKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <text>
                  <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                  <span style={{ fg: apexTheme.text }}>{kb.action}</span>
                </text>
              </box>
            ))}
            <box style={{ height: 1 }} />
            <text>
              <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>══ CHAT ══</span>
            </text>
            {chatKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <text>
                  <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                  <span style={{ fg: apexTheme.text }}>{kb.action}</span>
                </text>
              </box>
            ))}
            <box style={{ height: 1 }} />
            <text>
              <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>══ VIEW ══</span>
            </text>
            {viewKbs.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <text>
                  <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>{kb.key.padEnd(16)}</span>
                  <span style={{ fg: apexTheme.text }}>{kb.action}</span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "agents" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <text>
              <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>══ AVAILABLE AGENTS ══</span>
            </text>
            {APEX_AGENTS.map((a) => (
              <box key={a.id} style={{ height: 2, marginBottom: 1 }}>
                <text>
                  <span style={{ fg: a.color, attributes: TextAttributes.BOLD }}>{a.icon} {a.name}</span>
                  <span style={{ fg: apexTheme.textMuted }}> - {a.role}</span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "tools" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <text>
              <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>══ {APEX_TOOLS.length} TOOLS ══</span>
            </text>
            {Array.from(new Set(APEX_TOOLS.map((t) => t.category))).map((category) => (
              <box key={category} style={{ height: 2, marginBottom: 1 }}>
                <text>
                  <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>- {category}</span>
                  <span style={{ fg: apexTheme.textDim }}> {APEX_TOOLS.filter((t) => t.category === category).slice(0, 5).map((t) => t.name).join(", ")}</span>
                </text>
              </box>
            ))}
          </box>
        )}
      </scrollbox>

      <box style={{ height: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text style={{ fg: apexTheme.textMuted }}>Press Esc to close</text>
      </box>
    </box>
  )
}