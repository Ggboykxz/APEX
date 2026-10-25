import React, {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  useReducer,
  useRef,
} from "react"
import { Box, Text, useInput } from "ink"
import { apexTheme } from "../theme/apex.js"
import {
  formatDiffSummary,
  parseUnifiedDiff,
  type DiffLine,
  type ParsedDiff,
} from "../diff/parser.js"
import {
  createDiffPreviewState,
  reduceDiffPreview,
  type DiffDecision,
  type DiffPreviewStatus,
} from "../diff/preview.js"

export interface DiffPreviewHandle {
  accept: () => void
  reject: () => void
  reset: () => void
}

export interface DiffPreviewProps {
  /** Unified diff text, or an already-parsed diff. */
  diff: string | ParsedDiff
  title?: string
  /** Rows of diff content shown at once (excluding the header/decision bar). */
  maxLines?: number
  /** Set false to let a parent route keys while the preview stays visible. */
  active?: boolean
  /** Called once per accept/reject (programmatic or keyboard). */
  onDecision?: (decision: DiffDecision, parsed: ParsedDiff) => void
  onAccept?: (parsed: ParsedDiff) => void
  onReject?: (parsed: ParsedDiff) => void
}

type RowKind = "file" | "hunk" | "line" | "note" | "warning"

interface DisplayRow {
  key: string
  kind: RowKind
  lineKind?: DiffLine["kind"]
  oldNumber?: number
  newNumber?: number
  content: string
  noNewlineAtEnd?: boolean
}

function flattenDiff(parsed: ParsedDiff): DisplayRow[] {
  const rows: DisplayRow[] = []
  for (const [fileIndex, file] of parsed.files.entries()) {
    const badges = [
      file.isNew ? "new" : undefined,
      file.isDeleted ? "deleted" : undefined,
      file.isBinary ? "binary" : undefined,
    ].filter(Boolean)
    rows.push({
      key: `file-${fileIndex}`,
      kind: "file",
      content: `▸ ${file.path}${badges.length ? `  [${badges.join(", ")}]` : ""}  +${file.additions} −${file.deletions}`,
    })
    for (const [hunkIndex, hunk] of file.hunks.entries()) {
      rows.push({
        key: `file-${fileIndex}-hunk-${hunkIndex}`,
        kind: "hunk",
        content: hunk.header,
      })
      for (const [lineIndex, line] of hunk.lines.entries()) {
        rows.push({
          key: `file-${fileIndex}-hunk-${hunkIndex}-line-${lineIndex}`,
          kind: "line",
          lineKind: line.kind,
          oldNumber: line.oldNumber,
          newNumber: line.newNumber,
          content: line.content,
          noNewlineAtEnd: line.noNewlineAtEnd,
        })
      }
    }
  }
  for (const [warningIndex, warning] of parsed.warnings.entries()) {
    rows.push({
      key: `warning-${warningIndex}`,
      kind: "warning",
      content: `⚠ ${warning}`,
    })
  }
  return rows
}

function rowColor(row: DisplayRow): string {
  if (row.kind === "file") return apexTheme.purple
  if (row.kind === "hunk") return apexTheme.cyan
  if (row.kind === "warning") return apexTheme.yellow
  if (row.lineKind === "addition") return apexTheme.green
  if (row.lineKind === "deletion") return apexTheme.red
  return apexTheme.fg
}

function rowMarker(row: DisplayRow): string {
  if (row.kind === "hunk") return ""
  if (row.kind === "file" || row.kind === "warning") return ""
  if (row.lineKind === "addition") return "+"
  if (row.lineKind === "deletion") return "-"
  return " "
}

function statusBanner(status: DiffPreviewStatus): { text: string; color: string } {
  if (status === "accepted") return { text: "✓ accepted (preview only — not applied)", color: apexTheme.green }
  if (status === "rejected") return { text: "✗ rejected (preview only — nothing applied)", color: apexTheme.red }
  return { text: "a accept · r reject · ↑↓ scroll · PgUp/PgDn page", color: apexTheme.dimGray }
}

/**
 * Terminal diff preview.
 *
 * Keyboard: `a`/`y` accept, `r`/`n` reject, arrows/PgUp/PgDn scroll. The
 * component never touches the filesystem; accept/reject only invoke callbacks.
 */
export const DiffPreview = forwardRef<DiffPreviewHandle, DiffPreviewProps>(function DiffPreview(
  {
    diff,
    title = "Diff Preview",
    maxLines = 24,
    active = true,
    onDecision,
    onAccept,
    onReject,
  },
  ref,
) {
  const parsed = useMemo(
    () => (typeof diff === "string" ? parseUnifiedDiff(diff) : diff),
    [diff],
  )
  const rows = useMemo(() => flattenDiff(parsed), [parsed])
  const [state, dispatch] = useReducer(reduceDiffPreview, undefined, createDiffPreviewState)
  const stateRef = useRef(state)
  stateRef.current = state
  const callbacksRef = useRef({ onDecision, onAccept, onReject })
  callbacksRef.current = { onDecision, onAccept, onReject }

  const decide = useCallback(
    (decision: DiffDecision) => {
      if (stateRef.current.status !== "pending") return
      // Update the ref synchronously so a keyboard event and a programmatic
      // call in the same tick cannot fire the callback twice.
      stateRef.current = reduceDiffPreview(stateRef.current, { type: decision })
      dispatch({ type: decision })
      callbacksRef.current.onDecision?.(decision, parsed)
      if (decision === "accept") callbacksRef.current.onAccept?.(parsed)
      else callbacksRef.current.onReject?.(parsed)
    },
    [parsed],
  )

  const reset = useCallback(() => {
    stateRef.current = reduceDiffPreview(stateRef.current, { type: "reset" })
    dispatch({ type: "reset" })
  }, [])

  useImperativeHandle(ref, () => ({
    accept: () => decide("accept"),
    reject: () => decide("reject"),
    reset,
  }), [decide, reset])

  const viewport = Math.max(1, maxLines)
  const maxScroll = Math.max(0, rows.length - viewport)

  useInput(
    (input, key) => {
      if (state.status === "pending") {
        if (input === "a" || input === "y") {
          decide("accept")
          return
        }
        if (input === "r" || input === "n" || key.escape) {
          decide("reject")
          return
        }
      }
      if (key.upArrow) {
        dispatch({ type: "scroll", delta: -1, max: maxScroll })
        return
      }
      if (key.downArrow) {
        dispatch({ type: "scroll", delta: 1, max: maxScroll })
        return
      }
      if (key.pageUp) {
        dispatch({ type: "scroll", delta: -viewport, max: maxScroll })
        return
      }
      if (key.pageDown) {
        dispatch({ type: "scroll", delta: viewport, max: maxScroll })
      }
    },
    { isActive: active },
  )

  const visible = rows.slice(state.scrollOffset, state.scrollOffset + viewport)
  const banner = statusBanner(state.status)

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={apexTheme.cyan} paddingX={1}>
      <Box justifyContent="space-between">
        <Text color={apexTheme.cyan} bold>◆ {title}</Text>
        <Text color={apexTheme.dimGray}>{formatDiffSummary(parsed)}</Text>
      </Box>

      {parsed.files.length === 0 ? (
        <Text color={apexTheme.yellow}>No parseable diff.</Text>
      ) : (
        visible.map((row) => {
          if (row.kind === "line") {
            const oldLabel = row.oldNumber === undefined ? "    " : String(row.oldNumber).padStart(4)
            const newLabel = row.newNumber === undefined ? "    " : String(row.newNumber).padStart(4)
            return (
              <Box key={row.key} flexDirection="column">
                <Box>
                  <Text color={apexTheme.dimGray}>{oldLabel} {newLabel} </Text>
                  <Text color={rowColor(row)} wrap="truncate-end">
                    {rowMarker(row)}{row.content}
                  </Text>
                </Box>
                {row.noNewlineAtEnd && (
                  <Text color={apexTheme.yellow}>{"\\ No newline at end of file"}</Text>
                )}
              </Box>
            )
          }
          return (
            <Text key={row.key} color={rowColor(row)} bold={row.kind !== "note"} wrap="truncate-end">
              {row.content}
            </Text>
          )
        })
      )}

      {rows.length > viewport && (
        <Text color={apexTheme.dimGray}>
          {state.scrollOffset + 1}–{Math.min(rows.length, state.scrollOffset + viewport)} / {rows.length}
        </Text>
      )}

      <Text color={banner.color} bold={state.status !== "pending"}>
        {banner.text}
      </Text>
    </Box>
  )
})
