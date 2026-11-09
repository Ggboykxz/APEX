"use strict";

/**
 * Persisted TUI configuration.
 *
 * Stored in `~/.config/apex/tui.json` (documented in AGENTS.md §21).
 * JSON is used deliberately: it is stdlib, human-editable, and sufficient —
 * no TOML parser dependency is needed. Best-effort: the TUI works without a
 * writable config directory.
 */

import { homedir } from "node:os"
import { join } from "node:path"
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"

const CONFIG_DIR = join(homedir(), ".config", "apex")
const CONFIG_FILE = join(CONFIG_DIR, "tui.json")

export interface PersistedTuiConfig {
  activeAgent?: string
  activeModel?: string
  activeTheme?: string
  sidebarVisible?: boolean
  thinkingMode?: "show" | "hide" | "off"
  completionFreq?: Record<string, number>
}

export function loadTuiConfig(): PersistedTuiConfig {
  try {
    if (!existsSync(CONFIG_FILE)) return {}
    const raw = readFileSync(CONFIG_FILE, "utf8")
    return JSON.parse(raw) as PersistedTuiConfig
  } catch {
    return {}
  }
}

export function saveTuiConfig(cfg: Partial<PersistedTuiConfig>): void {
  try {
    mkdirSync(CONFIG_DIR, { recursive: true })
    const existing = loadTuiConfig()
    writeFileSync(
      CONFIG_FILE,
      JSON.stringify({ ...existing, ...cfg }, null, 2),
      "utf8",
    )
  } catch {
    // Best-effort persistence: the TUI works without a writable config dir.
  }
}
