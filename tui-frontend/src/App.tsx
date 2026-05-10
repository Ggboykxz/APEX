#!/usr/bin/env bun
/**
 * APEX TUI - AI-Powered Engineering eXtended
 * Terminal User Interface built with OpenTUI + React
 *
 * Usage: bun run src/App.tsx
 */

import { createCliRenderer } from "@opentui/core"
import { createRoot } from "@opentui/react"

import { ApexApp } from "./components/ApexApp.js"

async function main() {
  const renderer = await createCliRenderer()
  createRoot(renderer).render(<ApexApp />)
}

main().catch(console.error)
