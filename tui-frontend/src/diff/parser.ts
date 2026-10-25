/**
 * Unified-diff parser.
 *
 * Handles multi-file diffs, CRLF (and lone-CR) input, `\ No newline at end of
 * file` markers, new/deleted files, binary notices and malformed hunks. It
 * never throws: malformed fragments are skipped and reported in `warnings`, so
 * a streamed patch can be previewed while it is still incomplete.
 *
 * The parser is deliberately decoupled from React/Ink and from the filesystem;
 * callers only get a typed preview structure.
 */

export type DiffLineKind = "context" | "addition" | "deletion"

export interface DiffLine {
  kind: DiffLineKind
  /** Line content without the leading ` `, `+` or `-` marker. */
  content: string
  oldNumber?: number
  newNumber?: number
  noNewlineAtEnd?: boolean
}

export interface DiffHunk {
  header: string
  oldStart: number
  oldCount: number
  newStart: number
  newCount: number
  /** Text following the closing `@@` (function/context name). */
  section?: string
  lines: DiffLine[]
}

export interface DiffFile {
  /** `undefined` for a newly-created file (`--- /dev/null`). */
  oldPath?: string
  /** `undefined` for a deleted file (`+++ /dev/null`). */
  newPath?: string
  /** Best display path: new path, then old path, then "(unknown)". */
  path: string
  hunks: DiffHunk[]
  additions: number
  deletions: number
  isNew: boolean
  isDeleted: boolean
  isBinary: boolean
}

export interface ParsedDiff {
  files: DiffFile[]
  additions: number
  deletions: number
  warnings: string[]
}

const HUNK_HEADER = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$/

function cleanPath(raw: string): string | undefined {
  let path = raw.trim()
  if (path.startsWith('"') && path.endsWith('"')) path = path.slice(1, -1)
  const tab = path.indexOf("\t")
  if (tab >= 0) path = path.slice(0, tab).trim()
  if (path === "/dev/null") return undefined
  if (path.startsWith("a/") || path.startsWith("b/")) path = path.slice(2)
  return path.length > 0 ? path : undefined
}

function pathFromGitHeader(line: string): { oldPath?: string; newPath?: string } {
  const rest = line.slice("diff --git ".length)
  const quoted = /^"a\/(.+)" "b\/(.+)"$/.exec(rest)
  if (quoted) return { oldPath: quoted[1], newPath: quoted[2] }
  const sep = rest.indexOf(" b/")
  if (rest.startsWith("a/") && sep > 2) {
    return {
      oldPath: cleanPath(rest.slice(0, sep)),
      newPath: cleanPath(rest.slice(sep + 1)),
    }
  }
  const parts = rest.split(/\s+/)
  if (parts.length >= 2) {
    return { oldPath: cleanPath(parts[0]!), newPath: cleanPath(parts[1]!) }
  }
  return {}
}

function createFile(path?: string): DiffFile {
  return {
    path: path ?? "(unknown)",
    hunks: [],
    additions: 0,
    deletions: 0,
    isNew: false,
    isDeleted: false,
    isBinary: false,
  }
}

/**
 * Parse a unified diff into typed files/hunks/lines.
 *
 * Tolerant by design: a hunk that is still streaming in, or one with a broken
 * header, yields warnings instead of an exception.
 */
export function parseUnifiedDiff(input: string): ParsedDiff {
  const normalized = (input ?? "")
    .replace(/^\uFEFF/, "")
    .replace(/\r\n?/g, "\n")
  const lines = normalized.split("\n")
  const files: DiffFile[] = []
  const warnings: string[] = []
  let suppressed = 0

  const warn = (message: string) => {
    if (warnings.length >= 20) {
      suppressed += 1
      return
    }
    warnings.push(message)
  }

  let current: DiffFile | null = null
  let hunk: DiffHunk | null = null
  let oldRemaining = 0
  let newRemaining = 0
  let oldLine = 0
  let newLine = 0
  let pendingNewHeader = false

  const hunkComplete = () => oldRemaining <= 0 && newRemaining <= 0
  const getHunk = (): DiffHunk | null => hunk

  const finishHunk = () => {
    if (hunk && !hunkComplete()) {
      warn(
        `Hunk at line ${hunk.header} ended early (expected ${oldRemaining} old / ${newRemaining} new more lines)`,
      )
    }
    hunk = null
    oldRemaining = 0
    newRemaining = 0
  }

  const ensureFile = (path?: string): DiffFile => {
    if (current) return current
    current = createFile(path)
    files.push(current)
    return current
  }

  const startHunk = (line: string): boolean => {
    const match = HUNK_HEADER.exec(line)
    if (!match) {
      warn(`Malformed hunk header: ${line.slice(0, 80)}`)
      finishHunk()
      return false
    }
    finishHunk()
    const file = ensureFile()
    hunk = {
      header: line,
      oldStart: Number(match[1]),
      oldCount: match[2] === undefined ? 1 : Number(match[2]),
      newStart: Number(match[3]),
      newCount: match[4] === undefined ? 1 : Number(match[4]),
      section: match[5]?.trim() || undefined,
      lines: [],
    }
    oldRemaining = hunk.oldCount
    newRemaining = hunk.newCount
    oldLine = hunk.oldStart
    newLine = hunk.newStart
    file.hunks.push(hunk)
    return true
  }

  const appendLine = (kind: DiffLineKind, content: string) => {
    if (!hunk) return
    const file = ensureFile()
    const entry: DiffLine = { kind, content }
    if (kind !== "addition") {
      entry.oldNumber = oldLine
      oldLine += 1
      oldRemaining -= 1
    }
    if (kind !== "deletion") {
      entry.newNumber = newLine
      newLine += 1
      newRemaining -= 1
    }
    hunk.lines.push(entry)
    if (kind === "addition") {
      file.additions += 1
    } else if (kind === "deletion") {
      file.deletions += 1
    }
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]!

    if (line.startsWith("diff --git ")) {
      finishHunk()
      pendingNewHeader = false
      const paths = pathFromGitHeader(line)
      current = createFile(paths.newPath ?? paths.oldPath)
      current.oldPath = paths.oldPath
      current.newPath = paths.newPath
      files.push(current)
      continue
    }

    if (line.startsWith("Binary files ") || line === "GIT binary patch") {
      const file = ensureFile()
      file.isBinary = true
      finishHunk()
      continue
    }

    if (line.startsWith("new file mode")) {
      ensureFile().isNew = true
      continue
    }
    if (line.startsWith("deleted file mode")) {
      ensureFile().isDeleted = true
      continue
    }

    // A `--- ` line also appears as deletion content whose text starts with
    // `--`. Only treat it as a file header when the current hunk is complete.
    const looksLikeOldHeader = line.startsWith("--- ") && (!hunk || hunkComplete())
    if (looksLikeOldHeader) {
      finishHunk()
      pendingNewHeader = true
      if (!current || current.hunks.length > 0) {
        current = createFile()
        files.push(current)
      }
      const file = current
      file.oldPath = cleanPath(line.slice(4))
      file.isNew = file.oldPath === undefined
      if (file.oldPath === undefined && file.newPath === undefined) file.path = "(unknown)"
      continue
    }

    const looksLikeNewHeader =
      line.startsWith("+++ ") && (pendingNewHeader || !hunk || hunkComplete())
    if (looksLikeNewHeader) {
      finishHunk()
      pendingNewHeader = false
      const file = ensureFile()
      file.newPath = cleanPath(line.slice(4))
      file.isDeleted = file.newPath === undefined
      file.path = file.newPath ?? file.oldPath ?? file.path ?? "(unknown)"
      continue
    }

    if (line.startsWith("@@")) {
      pendingNewHeader = false
      if (!current) warn(`Hunk before any file header: ${line.slice(0, 80)}`)
      startHunk(line)
      continue
    }

    if (line.startsWith("\\ No newline at end of file")) {
      const activeHunk = getHunk()
      if (activeHunk && activeHunk.lines.length > 0) {
        activeHunk.lines[activeHunk.lines.length - 1]!.noNewlineAtEnd = true
      } else {
        warn("`No newline` marker without a preceding content line")
      }
      continue
    }

    const activeHunk = getHunk()
    if (activeHunk) {
      if (line.startsWith("+")) {
        appendLine("addition", line.slice(1))
        continue
      }
      if (line.startsWith("-")) {
        appendLine("deletion", line.slice(1))
        continue
      }
      if (line.startsWith(" ")) {
        appendLine("context", line.slice(1))
        continue
      }
      if (line.length === 0 && !hunkComplete() && index < lines.length - 1) {
        // Some editors strip the trailing space of an empty context line.
        // The final empty element produced by a trailing newline is ignored.
        appendLine("context", "")
        continue
      }
      if (line.length === 0) {
        continue
      }
      warn(`Unrecognized line inside hunk: ${line.slice(0, 80)}`)
      continue
    }

    // Preamble/metadata outside a hunk (index, mode, similarity, ---/+++
    // handled above) is intentionally ignored.
  }

  finishHunk()
  if (suppressed > 0) {
    warnings.push(`${suppressed} additional warning(s) suppressed`)
  }
  if (files.length === 0 && normalized.trim().length > 0) {
    warn("No unified-diff file headers found")
  }

  const additions = files.reduce((total, file) => total + file.additions, 0)
  const deletions = files.reduce((total, file) => total + file.deletions, 0)
  return { files, additions, deletions, warnings }
}

/** Human-readable summary used by the preview header. */
export function formatDiffSummary(parsed: ParsedDiff): string {
  const fileLabel = parsed.files.length === 1 ? "file" : "files"
  return `${parsed.files.length} ${fileLabel} · +${parsed.additions} −${parsed.deletions}`
}
