"use strict";

/**
 * Autocomplete — renders the frecency-ranked suggestion list under the
 * composer. Navigable with ↑/↓, confirmed with Enter, dismissed with Esc.
 */

import React from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import type { CompletionItem } from "../store/tuiStore.js"

interface AutocompleteProps {
  trigger: "/" | "@"
  prefix: string
  items: CompletionItem[]
  index: number
  onSelect: (value: string) => void
}

export function Autocomplete({
  trigger,
  prefix,
  items,
  index,
  onSelect,
}: AutocompleteProps) {
  if (items.length === 0) return null

  const highlighted = Math.max(0, Math.min(index, items.length - 1))

  return (
    <Box borderStyle="single" borderColor={apexTheme.border} marginLeft={1}>
      <Text color={apexTheme.cyan}>
        {trigger} {prefix} — ↑↓ navigate, Enter select, Esc close
      </Text>
      {items.map((item, i) => {
        const selected = i === highlighted
        const kindTag = {
          command: "cmd",
          file: "file",
          agent: "@agent",
          model: "@model",
          theme: "/theme",
          session: "/session",
        }[item.kind]
        return (
          <Box key={item.value} flexDirection="row">
            <Text color={apexTheme.dimGray}>
              {`  [${kindTag}] `}
            </Text>
            <Text color={selected ? apexTheme.cyan : apexTheme.fg} bold={selected}>
              {selected ? "▸ " : "  "}{item.label}
            </Text>
          </Box>
        )
      })}
    </Box>
  )
}
