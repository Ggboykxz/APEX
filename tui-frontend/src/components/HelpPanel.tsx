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

  return (
    <box
      id="apex-help"
      style={{
        position: "absolute",
        top: 1,
        left: "50%",
        width: 70,
        height: 26,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.borderFocus,
        borderStyle: "double",
        zIndex: 200,
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>▲ APEX Help</span>
          <span style={{ fg: apexTheme.textMuted }}> | Press Esc or ? to close</span>
        </text>
      </box>

      <box style={{ height: 1, flexDirection: "row", paddingLeft: 1 }}>
        {(["keybindings", "agents", "tools"] as const).map((t) => (
          <box
            key={t}
            style={{ paddingRight: 2, backgroundColor: tab === t ? apexTheme.bgOverlay : "transparent" }}
            onMouseDown={() => onTabChange(t)}
          >
            <text>
              <span style={{ fg: tab === t ? apexTheme.cyan : apexTheme.textMuted, attributes: tab === t ? TextAttributes.BOLD : 0 }}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </span>
            </text>
          </box>
        ))}
      </box>

      <box style={{ height: 1, backgroundColor: apexTheme.border }} />

      <scrollbox style={{ flexGrow: 1, rootOptions: { backgroundColor: apexTheme.bgSurface }, contentOptions: { backgroundColor: apexTheme.bgSurface }, scrollbarOptions: { showArrows: false, trackOptions: { foregroundColor: apexTheme.cyan, backgroundColor: apexTheme.scrollbarTrack } } }}>
        {tab === "keybindings" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            {APEX_KEYBINDINGS.map((kb, i) => (
              <box key={i} style={{ height: 1 }}>
                <text>
                  <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>
                    {kb.key.padEnd(16)}
                  </span>
                  <span style={{ fg: apexTheme.textDim }}>{kb.action}</span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "agents" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            {APEX_AGENTS.map((agent) => (
              <box key={agent.id} style={{ marginBottom: 1 }}>
                <text>
                  <span style={{ fg: agent.color, attributes: TextAttributes.BOLD }}>
                    {agent.icon} {agent.name}
                  </span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textDim }}>  Role: {agent.role}</span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textMuted }}>
                    {"  "}
                    {agent.capabilities.join(" | ")}
                  </span>
                </text>
              </box>
            ))}
          </box>
        )}

        {tab === "tools" && (
          <box style={{ flexDirection: "column", paddingLeft: 1 }}>
            <text>
              <span style={{ fg: apexTheme.green, attributes: TextAttributes.BOLD }}>
                {APEX_TOOLS.length}+ Tools Available
              </span>
              {"\n\n"}
            </text>
            {Array.from(new Set(APEX_TOOLS.map((t) => t.category))).map((category) => (
              <box key={category} style={{ marginBottom: 1 }}>
                <text>
                  <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>{category}</span>
                  {"\n"}
                  <span style={{ fg: apexTheme.textDim }}>
                    {"  "}
                    {APEX_TOOLS.filter((t) => t.category === category)
                      .slice(0, 5)
                      .map((t) => t.name)
                      .join(", ")}
                  </span>
                </text>
              </box>
            ))}
          </box>
        )}
      </scrollbox>
    </box>
  )
}