import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_MODELS, type ApexModel } from "../data/apex-data.js"
import { APEX_AGENTS } from "../data/apex-data.js"

interface ModelSelectorProps {
  visible: boolean
  searchQuery: string
  onSearchChange: (value: string) => void
  onSelect: (modelId: string) => void
  onClose: () => void
  activeModel: string
  activeAgent?: string
}

const PROVIDER_COLORS: Record<string, string> = {
  OpenAI: "#10a37f",
  Anthropic: "#d4a574",
  Google: "#4285f4",
  Meta: "#0668e1",
  Mistral: "#ff7000",
  DeepSeek: "#4d6bfe",
  xAI: "#1d9bf0",
  Alibaba: "#ff6a00",
  Cohere: "#39d353",
  Microsoft: "#00a4ef",
}

function ModelItem({ model, active, onSelect }: { model: ApexModel; active: boolean; onSelect: () => void }) {
  return (
    <box
      style={{
        width: "100%",
        height: 1,
        paddingLeft: 1,
        paddingRight: 1,
        backgroundColor: active ? apexTheme.selectionBg : "transparent",
      }}
      onMouseDown={onSelect}
    >
      <text>
        {active ? (
          <span style={{ fg: apexTheme.green }}>▸ </span>
        ) : (
          <span style={{ fg: apexTheme.textMuted }}>  </span>
        )}
        <span style={{ fg: PROVIDER_COLORS[model.provider] ?? apexTheme.text, attributes: TextAttributes.BOLD }}>
          {model.provider}
        </span>
        <span style={{ fg: apexTheme.textMuted }}> / </span>
        <span style={{ fg: active ? apexTheme.textBright : apexTheme.text }}>{model.name}</span>
        <span style={{ fg: apexTheme.textMuted }}> </span>
        {model.supportsVision && (
          <span style={{ fg: apexTheme.cyan }}>👁</span>
        )}
        {model.supportsTools && (
          <span style={{ fg: apexTheme.green }}> 🔧</span>
        )}
        <span style={{ fg: apexTheme.textMuted }}> </span>
        <span style={{ fg: apexTheme.textDim }}>
          ({(model.contextWindow / 1000).toFixed(0)}K ctx)
        </span>
      </text>
    </box>
  )
}

export function ModelSelector({ visible, searchQuery, onSearchChange, onSelect, onClose, activeModel, activeAgent = "coder" }: ModelSelectorProps) {
  if (!visible) return null

  const agent = APEX_AGENTS.find((a) => a.id === activeAgent)
  const agentColor = agent?.color ?? apexTheme.cyan

  const filteredModels = APEX_MODELS.filter((m) => {
    const q = searchQuery.toLowerCase()
    return m.name.toLowerCase().includes(q) || m.provider.toLowerCase().includes(q)
  }).slice(0, 18)

  return (
    <box
      id="apex-model-selector"
      style={{
        position: "absolute",
        top: 2,
        left: "50%",
        width: 65,
        height: 24,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: agentColor,
        borderStyle: "double",
        zIndex: 100,
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: agentColor, attributes: TextAttributes.BOLD }}>◎ Select Model</span>
          <span style={{ fg: apexTheme.textMuted }}> ─ </span>
          <span style={{ fg: apexTheme.textDim }}>Search by name or provider</span>
          <box flexGrow={1} />
          <span style={{ fg: apexTheme.textMuted }}>Esc</span>
          <span style={{ fg: apexTheme.textDim }}> to close</span>
        </text>
      </box>

      <box style={{ height: 3, border: true, borderColor: agentColor, borderStyle: "single" }}>
        <input
          id="apex-model-search"
          placeholder="Search models... (e.g. claude, gpt, gemini)"
          value={searchQuery}
          onInput={onSearchChange}
          focused
          style={{
            focusedBackgroundColor: apexTheme.bgSurfaceBright,
            backgroundColor: apexTheme.bgSurface,
          }}
        />
      </box>

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
        {filteredModels.map((model) => (
          <ModelItem
            key={model.id}
            model={model}
            active={model.id === activeModel}
            onSelect={() => { onSelect(model.id); onClose() }}
          />
        ))}
        {filteredModels.length === 0 ? (
          <box style={{ padding: 2 }}>
            <text style={{ fg: apexTheme.warning }}>⚠ No models match "{searchQuery}"</text>
          </box>
        ) : null}
      </scrollbox>

      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: agentColor }}>{filteredModels.length}</span>
          <span style={{ fg: apexTheme.textMuted }}> models available │ </span>
          <span style={{ fg: apexTheme.green }}>▸ Enter</span>
          <span style={{ fg: apexTheme.textMuted }}> to select │ </span>
          <span style={{ fg: apexTheme.green }}>Esc</span>
          <span style={{ fg: apexTheme.textMuted }}> to close</span>
        </text>
      </box>
    </box>
  )
}