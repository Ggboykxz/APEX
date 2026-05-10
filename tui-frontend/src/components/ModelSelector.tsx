import { TextAttributes } from "@opentui/core"
import { apexTheme } from "../theme/apex.js"
import { APEX_MODELS, type ApexModel } from "../data/apex-data.js"

interface ModelSelectorProps {
  visible: boolean
  searchQuery: string
  onSearchChange: (value: string) => void
  onSelect: (modelId: string) => void
  onClose: () => void
  activeModel: string
}

function ModelItem({ model, active, onSelect }: { model: ApexModel; active: boolean; onSelect: () => void }) {
  const providerColors: Record<string, string> = {
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

  return (
    <box
      style={{ width: "100%", height: 1, paddingLeft: 1, paddingRight: 1, backgroundColor: active ? apexTheme.selectionBg : "transparent" }}
      onMouseDown={onSelect}
    >
      <text>
        {active ? (
          <span style={{ fg: apexTheme.cyan }}>● </span>
        ) : (
          <span style={{ fg: apexTheme.textMuted }}>○ </span>
        )}
        <span style={{ fg: providerColors[model.provider] ?? apexTheme.text, attributes: TextAttributes.BOLD }}>
          {model.provider}
        </span>
        <span style={{ fg: apexTheme.textMuted }}> / </span>
        <span style={{ fg: active ? apexTheme.textBright : apexTheme.text }}>{model.name}</span>
        <span style={{ fg: apexTheme.textMuted }}> </span>
        <span style={{ fg: apexTheme.textMuted }}>
          ({(model.contextWindow / 1000).toFixed(0)}K ctx{model.supportsVision ? " +vision" : ""})
        </span>
      </text>
    </box>
  )
}

export function ModelSelector({ visible, searchQuery, onSearchChange, onSelect, onClose, activeModel }: ModelSelectorProps) {
  if (!visible) return null

  const filteredModels = APEX_MODELS.filter((m) => {
    const q = searchQuery.toLowerCase()
    return m.name.toLowerCase().includes(q) || m.provider.toLowerCase().includes(q)
  }).slice(0, 15)

  return (
    <box
      id="apex-model-selector"
      style={{
        position: "absolute",
        top: 2,
        left: "50%",
        width: 60,
        height: 22,
        flexDirection: "column",
        backgroundColor: apexTheme.bgSurface,
        border: true,
        borderColor: apexTheme.borderFocus,
        borderStyle: "single",
        zIndex: 100,
      }}
    >
      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.cyan, attributes: TextAttributes.BOLD }}>Select Model</span>
          <span style={{ fg: apexTheme.textMuted }}> (Ctrl+K)</span>
        </text>
      </box>

      <box style={{ height: 3, border: true, borderColor: apexTheme.border, borderStyle: "single" }}>
        <input
          id="apex-model-search"
          placeholder="Search models..."
          value={searchQuery}
          onInput={onSearchChange}
          focused
          style={{ focusedBackgroundColor: apexTheme.bgSurfaceBright }}
        />
      </box>

      <scrollbox style={{ flexGrow: 1, rootOptions: { backgroundColor: apexTheme.bgSurface }, contentOptions: { backgroundColor: apexTheme.bgSurface }, scrollbarOptions: { showArrows: false, trackOptions: { foregroundColor: apexTheme.cyan, backgroundColor: apexTheme.scrollbarTrack } } }}>
        {filteredModels.map((model) => (
          <ModelItem
            key={model.id}
            model={model}
            active={model.id === activeModel}
            onSelect={() => { onSelect(model.id); onClose() }}
          />
        ))}
        {filteredModels.length === 0 ? (
          <box style={{ padding: 1 }}>
            <text style={{ fg: apexTheme.textMuted }}>No models found</text>
          </box>
        ) : null}
      </scrollbox>

      <box style={{ height: 1, paddingLeft: 1, backgroundColor: apexTheme.bgOverlay }}>
        <text>
          <span style={{ fg: apexTheme.textMuted }}>{filteredModels.length} models | </span>
          <span style={{ fg: apexTheme.cyan }}>Esc</span>
          <span style={{ fg: apexTheme.textMuted }}> Close</span>
        </text>
      </box>
    </box>
  )
}