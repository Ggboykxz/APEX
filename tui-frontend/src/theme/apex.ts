/**
 * APEX Visual Charter & Theme
 * Dark (#0d1117), Cyan (#00e5ff), Green (#00ff88)
 */

export const apexTheme = {
  // Primary colors
  bg: "#0d1117",
  bgSurface: "#161b22",
  bgSurfaceBright: "#1c2128",
  bgOverlay: "#21262d",

  // Accent colors
  cyan: "#00e5ff",
  cyanDim: "#0097a7",
  green: "#00ff88",
  greenDim: "#00c853",

  // Text colors
  text: "#e6edf3",
  textDim: "#8b949e",
  textMuted: "#484f58",
  textBright: "#ffffff",

  // Semantic colors
  error: "#f85149",
  warning: "#d29922",
  success: "#00ff88",
  info: "#00e5ff",

  // Border colors
  border: "#30363d",
  borderBright: "#484f58",
  borderFocus: "#00e5ff",

  // Agent colors
  agentCoder: "#00e5ff",
  agentArchitect: "#7c3aed",
  agentReviewer: "#f59e0b",
  agentDevOps: "#ef4444",
  agentAnalyst: "#00ff88",

  // Scrollbar
  scrollbarTrack: "#21262d",
  scrollbarThumb: "#30363d",
  scrollbarThumbHover: "#484f58",

  // Status
  statusOnline: "#00ff88",
  statusBusy: "#d29922",
  statusOffline: "#f85149",

  // Selection
  selectionBg: "#1a4a6e",
  selectionFg: "#e6edf3",
} as const

export type ApexTheme = typeof apexTheme
