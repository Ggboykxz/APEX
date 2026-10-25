/**
 * Unified-diff parser tests: multi-file, CRLF, no-newline markers, malformed
 * input and content that looks like a file header.
 */

import { describe, it } from "node:test"
import assert from "node:assert/strict"
import { formatDiffSummary, parseUnifiedDiff } from "../src/diff/parser.js"

const MULTI_FILE = [
  "diff --git a/src/a.ts b/src/a.ts",
  "index 1111111..2222222 100644",
  "--- a/src/a.ts",
  "+++ b/src/a.ts",
  "@@ -1,3 +1,4 @@",
  " const a = 1",
  "-const b = 2",
  "+const b = 3",
  "+const c = 4",
  " export { a }",
  "",
  "diff --git a/src/new.ts b/src/new.ts",
  "new file mode 100644",
  "--- /dev/null",
  "+++ b/src/new.ts",
  "@@ -0,0 +1,2 @@",
  "+one",
  "+two",
  "",
].join("\n")

describe("parseUnifiedDiff", () => {
  it("parses multiple files and totals additions/deletions", () => {
    const parsed = parseUnifiedDiff(MULTI_FILE)
    assert.equal(parsed.files.length, 2)
    assert.equal(parsed.files[0]!.path, "src/a.ts")
    assert.equal(parsed.files[0]!.hunks.length, 1)
    assert.equal(parsed.files[0]!.hunks[0]!.oldStart, 1)
    assert.equal(parsed.files[0]!.hunks[0]!.oldCount, 3)
    assert.equal(parsed.files[0]!.hunks[0]!.newCount, 4)
    assert.equal(parsed.files[0]!.additions, 2)
    assert.equal(parsed.files[0]!.deletions, 1)
    assert.equal(parsed.files[1]!.path, "src/new.ts")
    assert.equal(parsed.files[1]!.isNew, true)
    assert.equal(parsed.files[1]!.oldPath, undefined)
    assert.equal(parsed.files[1]!.additions, 2)
    assert.equal(parsed.additions, 4)
    assert.equal(parsed.deletions, 1)
    assert.deepEqual(parsed.warnings, [])
    assert.equal(formatDiffSummary(parsed), "2 files · +4 −1")
  })

  it("normalizes CRLF and assigns old/new line numbers", () => {
    const crlf = [
      "--- a/x.ts\t2026-10-25 12:00:00",
      "+++ b/x.ts\t2026-10-25 12:00:01",
      "@@ -1,2 +1,2 @@",
      " keep",
      "-old",
      "+new",
      "",
    ].join("\r\n")
    const parsed = parseUnifiedDiff(crlf)
    const hunk = parsed.files[0]!.hunks[0]!

    assert.equal(parsed.files[0]!.path, "x.ts")
    assert.equal(hunk.lines.length, 3)
    assert.equal(hunk.lines[0]!.content, "keep")
    assert.equal(hunk.lines[1]!.content, "old")
    assert.equal(hunk.lines[2]!.content, "new")
    assert.equal(hunk.lines[1]!.oldNumber, 2)
    assert.equal(hunk.lines[1]!.newNumber, undefined)
    assert.equal(hunk.lines[2]!.newNumber, 2)
    assert.ok(hunk.lines.every((line) => !line.content.includes("\r")))
  })

  it("attaches the no-newline marker to the preceding line", () => {
    const diff = [
      "--- a/eof.txt",
      "+++ b/eof.txt",
      "@@ -1 +1 @@",
      "-old",
      "\\ No newline at end of file",
      "+new",
      "\\ No newline at end of file",
      "",
    ].join("\n")
    const parsed = parseUnifiedDiff(diff)
    const lines = parsed.files[0]!.hunks[0]!.lines

    assert.equal(lines.length, 2)
    assert.equal(lines[0]!.noNewlineAtEnd, true)
    assert.equal(lines[1]!.noNewlineAtEnd, true)
    assert.equal(parsed.additions, 1)
    assert.equal(parsed.deletions, 1)
  })

  it("handles malformed hunks and truncated input without throwing", () => {
    const malformed = [
      "--- a/ok.txt",
      "+++ b/ok.txt",
      "@@ not a hunk @@",
      "+orphan",
      "@@ -10,8 +10,8 @@",
      " only-one-line",
      "",
    ].join("\n")
    const parsed = parseUnifiedDiff(malformed)

    assert.equal(parsed.files.length, 1)
    assert.equal(parsed.files[0]!.hunks.length, 1)
    assert.ok(parsed.warnings.length >= 2)
    assert.ok(parsed.warnings.some((warning) => warning.includes("Malformed hunk header")))
    assert.ok(parsed.warnings.some((warning) => warning.includes("ended early")))

    const garbage = parseUnifiedDiff("this is not a diff\n@@ still not a hunk @@\n")
    assert.equal(garbage.files.length, 0)
    assert.ok(garbage.warnings.length >= 1)
    assert.equal(garbage.additions, 0)
    assert.equal(garbage.deletions, 0)
    assert.deepEqual(parseUnifiedDiff(""), { files: [], additions: 0, deletions: 0, warnings: [] })
  })

  it("does not confuse deletion content that starts with -- with a file header", () => {
    const diff = [
      "--- a/flags.txt",
      "+++ b/flags.txt",
      "@@ -1,2 +1,2 @@",
      "--- keep",
      "+++ keep",
      "",
    ].join("\n")
    const parsed = parseUnifiedDiff(diff)
    assert.equal(parsed.files.length, 1)
    const lines = parsed.files[0]!.hunks[0]!.lines
    assert.equal(lines.length, 2)
    assert.equal(lines[0]!.kind, "deletion")
    assert.equal(lines[0]!.content, "-- keep")
    assert.equal(lines[1]!.kind, "addition")
    assert.equal(lines[1]!.content, "++ keep")
  })

  it("distinguishes new, deleted and binary files", () => {
    const diff = [
      "diff --git a/gone.txt b/gone.txt",
      "deleted file mode 100644",
      "--- a/gone.txt",
      "+++ /dev/null",
      "@@ -1 +0,0 @@",
      "-gone",
      "diff --git a/blob.bin b/blob.bin",
      "Binary files a/blob.bin and b/blob.bin differ",
      "",
    ].join("\n")
    const parsed = parseUnifiedDiff(diff)

    assert.equal(parsed.files.length, 2)
    assert.equal(parsed.files[0]!.isDeleted, true)
    assert.equal(parsed.files[0]!.newPath, undefined)
    assert.equal(parsed.files[0]!.path, "gone.txt")
    assert.equal(parsed.files[1]!.isBinary, true)
    assert.equal(parsed.files[1]!.path, "blob.bin")
    assert.equal(parsed.deletions, 1)
  })
})
