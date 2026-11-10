import { describe, expect, test } from "bun:test"
import { Keymap } from "../src/keymap/engine.js"
import { parseKey, strokeToMatch, fromInkKey } from "../src/keymap/parser.js"
import { formatKey } from "../src/keymap/format.js"
import type { CommandCtx, KeymapLayer } from "../src/keymap/types.js"

function ctx(partial: Partial<CommandCtx> = {}): () => CommandCtx {
  return () => ({ state: {}, input: "", ...partial })
}

describe("parser", () => {
  test("strokeToMatch prefixes modifiers in order", () => {
    expect(strokeToMatch({ name: "p", ctrl: true, shift: false, meta: false })).toBe("ctrl+p")
    expect(strokeToMatch({ name: "return", ctrl: false, shift: false, meta: false })).toBe("return")
    expect(strokeToMatch({ name: "x", ctrl: true, shift: true, meta: true })).toBe("ctrl+shift+meta+x")
  })

  test("parseKey splits multi-stroke bindings", () => {
    expect(parseKey("ctrl+x n")).toEqual(["ctrl+x", "n"])
    expect(parseKey("ctrl+p")).toEqual(["ctrl+p"])
    expect(parseKey("shift+tab")).toEqual(["shift+tab"])
  })

  test("fromInkKey maps named booleans and printable input", () => {
    expect(fromInkKey("", { return: true })).toEqual({ name: "return", ctrl: false, shift: false, meta: false })
    expect(fromInkKey("p", { ctrl: true })).toEqual({ name: "p", ctrl: true, shift: false, meta: false })
    expect(fromInkKey("", { upArrow: true })).toEqual({ name: "up", ctrl: false, shift: false, meta: false })
  })

  test("formatKey renders compact glyphs", () => {
    expect(formatKey("ctrl+p")).toBe("^P")
    expect(formatKey("shift+tab")).toBe("⇧Tab")
    expect(formatKey("return")).toBe("Enter")
    expect(formatKey("ctrl+x n")).toBe("^X N")
    expect(formatKey("up")).toBe("↑")
  })
})

describe("Keymap", () => {
  test("global layer resolves a binding", () => {
    const km = new Keymap(ctx())
    const calls: string[] = []
    km.register({
      id: "g",
      commands: [{ name: "quit", run: () => calls.push("quit") }],
      bindings: [{ key: "ctrl+q", cmd: "quit" }],
    })
    expect(km.resolve({ name: "q", ctrl: true, shift: false, meta: false })).toMatchObject({ handled: true, reason: "executed", cmd: "quit" })
    expect(calls).toEqual(["quit"])
    expect(km.resolve({ name: "q", ctrl: false, shift: false, meta: false })).toMatchObject({ handled: false })
  })

  test("priority: higher runs first; reject falls through", () => {
    const km = new Keymap(ctx())
    const calls: string[] = []
    km.register({
      id: "low",
      priority: 0,
      commands: [{ name: "a", run: () => calls.push("low") }],
      bindings: [{ key: "x", cmd: "a" }],
    })
    km.register({
      id: "high",
      priority: 10,
      commands: [{ name: "a", run: () => false }],
      bindings: [{ key: "x", cmd: "a" }],
    })
    km.resolve({ name: "x", ctrl: false, shift: false, meta: false })
    expect(calls).toEqual(["low"])
  })

  test("fallthrough continues after a handled binding", () => {
    const km = new Keymap(ctx())
    const calls: string[] = []
    km.register({
      id: "g",
      commands: [
        { name: "first", run: () => calls.push("first") },
        { name: "second", run: () => calls.push("second") },
      ],
      bindings: [
        { key: "x", cmd: "first", fallthrough: true },
        { key: "x", cmd: "second" },
      ],
    })
    km.resolve({ name: "x", ctrl: false, shift: false, meta: false })
    expect(calls).toEqual(["first", "second"])
  })

  test("context-targeted layer only active for matching target", () => {
    const km = new Keymap(ctx())
    let ran = false
    km.register({
      id: "overlay",
      target: "overlay",
      commands: [{ name: "close", run: () => (ran = true) }],
      bindings: [{ key: "escape", cmd: "close" }],
    })
    expect(km.resolve({ name: "escape", ctrl: false, shift: false, meta: false }).handled).toBe(false)
    expect(km.resolve({ name: "escape", ctrl: false, shift: false, meta: false }, ["overlay"]).handled).toBe(true)
    expect(ran).toBe(true)
  })

  test("swallowAll consumes unhandled keys when active", () => {
    const km = new Keymap(ctx())
    km.register({
      id: "overlay",
      target: "overlay",
      swallowAll: true,
      commands: [{ name: "close", run: () => {} }],
      bindings: [{ key: "escape", cmd: "close" }],
    })
    // Unhandled key in overlay context is consumed.
    expect(km.resolve({ name: "a", ctrl: false, shift: false, meta: false }, ["overlay"]).handled).toBe(true)
    // Outside the overlay context, nothing consumes it.
    expect(km.resolve({ name: "a", ctrl: false, shift: false, meta: false }).handled).toBe(false)
  })

  test("enabled gate skips a command", () => {
    const km = new Keymap(ctx())
    let ran = false
    km.register({
      id: "g",
      commands: [{ name: "c", enabled: () => false, run: () => (ran = true) }],
      bindings: [{ key: "x", cmd: "c" }],
    })
    expect(km.resolve({ name: "x", ctrl: false, shift: false, meta: false }).handled).toBe(false)
    expect(ran).toBe(false)
  })

  test("leader sequence starts, advances, and executes", () => {
    const km = new Keymap(ctx())
    let ran = false
    km.register({
      id: "leader",
      commands: [{ name: "new", run: () => (ran = true) }],
      bindings: [{ key: "ctrl+x n", cmd: "new" }],
    })
    const start = km.resolve({ name: "x", ctrl: true, shift: false, meta: false })
    expect(start).toMatchObject({ handled: true, reason: "sequence-start", pending: true })
    const advance = km.resolve({ name: "n", ctrl: false, shift: false, meta: false })
    expect(advance).toMatchObject({ reason: "sequence-executed", pending: false })
    expect(ran).toBe(true)
  })

  test("leader miss swallows the key and clears", () => {
    const km = new Keymap(ctx())
    km.register({
      id: "leader",
      commands: [{ name: "new", run: () => {} }],
      bindings: [{ key: "ctrl+x n", cmd: "new" }],
    })
    km.resolve({ name: "x", ctrl: true, shift: false, meta: false })
    const miss = km.resolve({ name: "z", ctrl: false, shift: false, meta: false })
    expect(miss).toMatchObject({ handled: true, reason: "sequence-miss", pending: false })
    expect(km.hasPending()).toBe(false)
  })

  test("getActiveKeys lists reachable single-stroke bindings", () => {
    const km = new Keymap(ctx())
    km.register({
      id: "g",
      commands: [
        { name: "q", run: () => {} },
        { name: "restricted", enabled: () => false, run: () => {} },
      ],
      bindings: [
        { key: "ctrl+q", cmd: "q" },
        { key: "r", cmd: "restricted" },
        { key: "ctrl+x n", cmd: "new" },
      ],
    })
    const keys = km.getActiveKeys()
    expect(keys).toHaveLength(2)
    expect(keys.find((k) => k.cmd === "q")?.enabled).toBe(true)
    expect(keys.find((k) => k.cmd === "restricted")?.enabled).toBe(false)
  })

  test("listKeys enumerates every binding including multi-stroke", () => {
    const km = new Keymap(ctx())
    km.register({
      id: "leader",
      commands: [{ name: "new", run: () => {} }],
      bindings: [{ key: "ctrl+x n", cmd: "new" }],
    })
    km.register({
      id: "g",
      commands: [{ name: "q", run: () => {} }],
      bindings: [{ key: "ctrl+q", cmd: "q" }],
    })
    const keys = km.listKeys()
    expect(keys).toHaveLength(2)
    expect(keys.find((k) => k.layer === "leader")?.key).toBe("ctrl+x n")
    expect(keys.find((k) => k.layer === "g")?.key).toBe("ctrl+q")
  })

  test("setData/getData", () => {
    const km = new Keymap(ctx())
    km.setData("theme", "nord")
    expect(km.getData("theme")).toBe("nord")
    km.setData("theme", undefined)
    expect(km.getData("theme")).toBeUndefined()
  })

  test("composes into a typical layer set", () => {
    // Simulate an overlay + composer pair sharing a key with different targets.
    const km = new Keymap(ctx())
    let overlayClosed = false
    let submitted = false
    km.register({
      id: "overlay",
      target: "overlay",
      commands: [{ name: "overlay.close", run: () => (overlayClosed = true) }],
      bindings: [{ key: "escape", cmd: "overlay.close" }],
    })
    km.register({
      id: "composer",
      target: "composer",
      commands: [{ name: "composer.submit", run: () => (submitted = true) }],
      bindings: [{ key: "return", cmd: "composer.submit" }],
    })
    km.resolve({ name: "return", ctrl: false, shift: false, meta: false }, ["composer"])
    expect(submitted).toBe(true)
    expect(overlayClosed).toBe(false)
    km.resolve({ name: "escape", ctrl: false, shift: false, meta: false }, ["overlay"])
    expect(overlayClosed).toBe(true)
  })
})
