"use strict";

/**
 * Toast — ephemeral notifications (OpenCode toasts pattern, APEX charter).
 *
 * Rendered below the main surface. Each toast auto-dismisses after its
 * `duration` (default 4s) by dispatching `REMOVE_TOAST` to the central store.
 */

import React, { useEffect } from "react"
import { Box, Text } from "ink"
import { apexTheme } from "../theme/apex.js"
import { useTuiStore } from "../context/TuiStoreProvider.js"
import type { Toast } from "../store/tuiStore.js"

const KIND_COLOR: Record<Toast["kind"], string> = {
  info: apexTheme.cyan,
  success: apexTheme.green,
  warn: apexTheme.yellow,
  error: apexTheme.red,
}

const KIND_ICON: Record<Toast["kind"], string> = {
  info: "ℹ",
  success: "✓",
  warn: "⚠",
  error: "✗",
}

interface ToastProps {
  toast: Toast
}

export function Toast({ toast }: ToastProps) {
  const { dispatch } = useTuiStore()

  useEffect(() => {
    const id = setTimeout(() => {
      dispatch({ type: "REMOVE_TOAST", payload: toast.id })
    }, toast.duration ?? 4000)
    return () => clearTimeout(id)
  }, [dispatch, toast.id, toast.duration])

  return (
    <Box flexDirection="row" marginBottom={1}>
      <Text color={KIND_COLOR[toast.kind]} bold>{KIND_ICON[toast.kind]} </Text>
      <Text color={apexTheme.fg}>{toast.message}</Text>
    </Box>
  )
}

interface ToastsProps {
  toasts: Toast[]
}

export function Toasts({ toasts }: ToastsProps) {
  if (toasts.length === 0) return null
  return (
    <Box flexDirection="column" marginRight={1}>
      {/* Newest on top. */}
      {toasts.slice().reverse().map((t) => (
        <Toast key={t.id} toast={t} />
      ))}
    </Box>
  )
}
