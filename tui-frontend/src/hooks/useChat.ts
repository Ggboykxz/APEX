"use strict";

/**
 * useChat — centralizes chat logic: slash command dispatch, message sending,
 * bash execution, editor flow and input history.
 *
 * The hook no longer owns React state. It dispatches to the central TUI store
 * (OpenCode SyncProvider pattern) and performs side effects (HTTP, editor,
 * bash). All mutations go through `dispatch`.
 */

import { useCallback, useRef } from "react"
import { spawnSync } from "node:child_process"
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { api } from "../api/client.js"
import type { ChatMessage } from "../data/apex-data.js"
import { APEX_MODELS } from "../data/apex-data.js"
import type { TuiDispatch, TuiState } from "../store/tuiStore.js"

interface UseChatProps {
  dispatch: TuiDispatch
  getState: () => TuiState
}

export interface SlashResult {
  type:
    | "reset"
    | "help"
    | "models"
    | "themes"
    | "agents"
    | "sessions"
    | "editor"
    | "cost"
    | "diff"
    | "copy"
    | "exit"
    | "command"
    | "ignored"
    | "thinking"
    | "details"
    | "export"
    | boolean
  command?: string
}

const COMMANDS = [
  { id: "/help", desc: "Show help" },
  { id: "/models", desc: "List models" },
  { id: "/themes", desc: "List themes" },
  { id: "/new", desc: "New session" },
  { id: "/clear", desc: "Clear chat" },
  { id: "/compact", desc: "Compact" },
  { id: "/undo", desc: "Undo last" },
  { id: "/redo", desc: "Redo last" },
  { id: "/share", desc: "Share session" },
  { id: "/export", desc: "Export" },
  { id: "/editor", desc: "Open editor" },
  { id: "/sessions", desc: "Sessions" },
  { id: "/cost", desc: "Token usage & cost" },
  { id: "/diff", desc: "Preview working-tree diff" },
  { id: "/init", desc: "Initialize" },
  { id: "/connect", desc: "Connect remote" },
  { id: "/thinking", desc: "Toggle thinking" },
  { id: "/details", desc: "Details" },
  { id: "/agent", desc: "Switch agent" },
  { id: "/exit", desc: "Exit APEX" },
]

export function useChat({ dispatch, getState }: UseChatProps) {
  const sendMessageRef = useRef<((message: string) => Promise<{ type: string }>) | null>(null)

  const fuzzyMatch = useCallback((text: string, query: string) => {
    if (!query) return true
    const t = text.toLowerCase(), q = query.toLowerCase()
    let qi = 0
    for (let i = 0; i < t.length && qi < q.length; i++)
      if (t[i] === q[qi]) qi++
    return qi === q.length
  }, [])

  const filteredCommands = useCallback(
    (search: string) =>
      COMMANDS.filter((c) => fuzzyMatch(c.id + " " + c.desc, search)),
    [fuzzyMatch]
  )

  const handleSlashCommand = useCallback(
    (cmd: string, arg: string): SlashResult | boolean => {
      switch (cmd) {
        case "/new":
        case "/clear":
          return { type: "reset" }
        case "/help":
          return { type: "help" }
        case "/models":
          return { type: "models" }
        case "/themes":
          return { type: "themes" }
        case "/agent":
          return arg
            ? { type: "command", command: `agent ${arg}` }
            : { type: "agents" }
        case "/thinking":
          return { type: "thinking" }
        case "/details":
          return { type: "details" }
        case "/copy":
          return { type: "copy" }
        case "/exit":
        case "/quit":
        case "/q":
          return { type: "exit" }
        case "/sessions":
          return { type: "sessions" }
        case "/undo":
          api.undo().catch(() =>
            dispatch({ type: "SET_CONNECTION_ERROR", payload: "Undo failed — backend unreachable" })
          )
          return true
        case "/redo":
          api.redo().catch(() =>
            dispatch({ type: "SET_CONNECTION_ERROR", payload: "Redo failed — backend unreachable" })
          )
          return true
        case "/compact":
          api.compact().catch(() =>
            dispatch({ type: "SET_CONNECTION_ERROR", payload: "Compact failed — backend unreachable" })
          )
          return true
        case "/theme":
          if (!arg) return { type: "themes" }
          if (!["default", "light", "dark", "forest", "sunset"].includes(arg)) {
            dispatch({ type: "SET_CONNECTION_ERROR", payload: `Unknown theme: ${arg}` })
            return true
          }
          return { type: "command", command: `theme ${arg}` }
        case "/session":
          if (!arg) return { type: "sessions" }
          return { type: "command", command: `session ${arg}` }
        case "/export":
          return { type: "export" }
        case "/share":
          return { type: "command", command: `share ${arg}` }
        case "/unshare":
          if (!arg) {
            dispatch({ type: "SET_CONNECTION_ERROR", payload: "Usage: /unshare <share_id>" })
            return true
          }
          return { type: "command", command: `unshare ${arg}` }
        case "/editor":
          return { type: "editor" }
        case "/cost":
          return { type: "cost" }
        case "/diff":
          return { type: "diff" }
        case "/init":
        case "/connect":
          return false
        default:
          return false
      }
    },
    [dispatch]
  )

  const sendEditorPrompt = useCallback(() => {
    const editor = process.env.EDITOR || process.env.VISUAL || "vi"
    const dir = mkdtempSync(join(tmpdir(), "apex-editor-"))
    const file = join(dir, "prompt.md")
    try {
      writeFileSync(file, "# Enter your prompt\n\n")
      process.stdout.write("\x1b[?1049l")
      try {
        spawnSync(editor, [file], { stdio: "inherit" })
      } catch {
        dispatch({ type: "SET_CONNECTION_ERROR", payload: `Could not launch editor: ${editor}` })
      }
      process.stdout.write("\x1b[?1049h\x1b[2J\x1b[H")
      const content = readFileSync(file, "utf8")
      const prompt = content
        .split("\n")
        .filter((l) => !l.startsWith("#"))
        .join("\n")
        .trim()
      if (prompt) sendMessageRef.current?.(prompt)
    } finally {
      try {
        rmSync(dir, { recursive: true, force: true })
      } catch {}
    }
  }, [dispatch])

  const calcMessageCost = useCallback(
    (pt: number, ct: number, modelId: string) => {
      const m = APEX_MODELS.find((x) => x.id === modelId)
      if (!m?.inputCostPer1K || !m?.outputCostPer1K) return 0
      return (pt / 1000) * m.inputCostPer1K + (ct / 1000) * m.outputCostPer1K
    },
    []
  )

  const sendMessage = useCallback(
    async (userMessage: string) => {
      if (userMessage.startsWith("/")) {
        const parts = userMessage.split(/\s+/)
        const cmd = parts[0].toLowerCase()
        const arg = parts.slice(1).join(" ")
        const result = handleSlashCommand(cmd, arg)
        if (result === true) return { type: "handled" }
        if (result === false) return { type: "ignored" }
        if (typeof result === "object" && "type" in result) {
          if (result.type === "command") {
            sendMessageRef.current?.(result.command ?? "")
            return { type: "command" }
          }
          return result
        }
        return { type: "ignored" }
      }

      dispatch({ type: "SET_IS_GENERATING", payload: true })
      dispatch({ type: "SET_CONNECTION_ERROR", payload: null })
      dispatch({ type: "SET_IS_RECONNECTING", payload: false })

      const aid = `msg-${Date.now()}-a`

      try {
        const { full, usage } = await api.chatStream({
          message: userMessage,
          model: getState().activeModel,
          onChunk: () => {},
        })

        const fp = usage.prompt_tokens ?? 0
        const fc = usage.completion_tokens ?? 0
        const mc = calcMessageCost(fp, fc, getState().activeModel)

        const userMsg: ChatMessage = {
          id: `msg-${Date.now()}-u`,
          role: "user",
          content: userMessage,
          timestamp: Date.now(),
        }

        const assistantMsg: ChatMessage = {
          id: aid,
          role: "assistant",
          content: full || "(empty)",
          agent: getState().activeAgent,
          model: getState().activeModel,
          timestamp: Date.now(),
          promptTokens: fp,
          completionTokens: fc,
          cost: mc,
        }

        dispatch({ type: "ADD_MESSAGE", payload: userMsg })
        dispatch({ type: "ADD_MESSAGE", payload: assistantMsg })
        dispatch({
          type: "SET_STATS",
          payload: {
            totalPromptTokens: getState().totalPromptTokens + fp,
            totalCompletionTokens: getState().totalCompletionTokens + fc,
            totalSpent: getState().totalSpent + mc,
          },
        })
        dispatch({ type: "SET_LIVE_TOKENS", payload: { pt: fp, ct: fc } })
        dispatch({ type: "SET_RETRY_COUNT", payload: 0 })

        return {
          type: "done",
          userMsg,
          assistantMsg,
          totalPromptTokens: fp,
          totalCompletionTokens: fc,
          totalSpent: mc,
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        if (
          msg.includes("fetch") ||
          msg.includes("ECONNREFUSED") ||
          msg.includes("NetworkError")
        ) {
          dispatch({ type: "SET_CONNECTION_ERROR", payload: "Cannot connect to APEX backend" })
          dispatch({ type: "SET_IS_RECONNECTING", payload: true })
          dispatch({ type: "SET_RETRY_COUNT", payload: (c: number) => c + 1 })
        } else {
          dispatch({ type: "SET_CONNECTION_ERROR", payload: `Error: ${msg}` })
        }

        const assistantMsg: ChatMessage = {
          id: aid,
          role: "assistant",
          content: `Error: ${msg}`,
          agent: getState().activeAgent,
          model: getState().activeModel,
          timestamp: Date.now(),
          promptTokens: 0,
          completionTokens: 0,
          cost: 0,
        }
        dispatch({ type: "ADD_MESSAGE", payload: assistantMsg })

        return { type: "error", assistantMsg }
      } finally {
        dispatch({ type: "SET_IS_GENERATING", payload: false })
      }
    },
    [dispatch, getState, handleSlashCommand, calcMessageCost, sendEditorPrompt]
  )

  const sendBash = useCallback(
    async (cmd: string) => {
      dispatch({ type: "SET_IS_GENERATING", payload: true })
      dispatch({ type: "SET_CONNECTION_ERROR", payload: null })
      const rid = `msg-${Date.now()}-bash`
      try {
        const d = await api.bash(cmd)
        const assistantMsg: ChatMessage = {
          id: rid,
          role: "assistant",
          content: "```\n" + (d.stdout ?? d.output ?? d.result ?? JSON.stringify(d)) + "\n```",
          agent: "shell",
          timestamp: Date.now(),
          promptTokens: 0,
          completionTokens: 0,
          cost: 0,
        }
        dispatch({ type: "ADD_MESSAGE", payload: assistantMsg })
        return { type: "done", assistantMsg }
      } catch (e: any) {
        dispatch({ type: "SET_CONNECTION_ERROR", payload: `Bash error: ${e.message}` })
        const assistantMsg: ChatMessage = {
          id: rid,
          role: "assistant",
          content: `Bash error: ${e.message}`,
          agent: "shell",
          timestamp: Date.now(),
          promptTokens: 0,
          completionTokens: 0,
          cost: 0,
        }
        dispatch({ type: "ADD_MESSAGE", payload: assistantMsg })
        return { type: "error", assistantMsg }
      } finally {
        dispatch({ type: "SET_IS_GENERATING", payload: false })
      }
    },
    [dispatch]
  )

  const sendCost = useCallback(async () => {
    try {
      const d = await api.cost()
      const usage = d.usage ?? {}
      const content = [
        "Token usage (session):",
        `  Input: ${usage.prompt_tokens ?? 0}`,
        `  Output: ${usage.completion_tokens ?? 0}`,
        `  Total tokens: ${usage.total_tokens ?? 0}`,
        `  Cost: $${(d.total_cost ?? 0).toFixed(6)} (${
          d.currency ?? "USD"
        }, model ${d.model ?? getState().activeModel})`,
      ].join("\n")
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-c`,
        role: "assistant",
        content,
        agent: "build",
        model: getState().activeModel,
        timestamp: Date.now(),
        promptTokens: 0,
        completionTokens: 0,
        cost: 0,
      }
      dispatch({ type: "ADD_MESSAGE", payload: assistantMsg })
      return { type: "done", assistantMsg }
    } catch {
      dispatch({ type: "SET_CONNECTION_ERROR", payload: "Cost request failed — backend unreachable" })
      return { type: "error" }
    }
  }, [dispatch, getState])

  return {
    sendMessageRef,
    sendMessage,
    sendBash,
    sendCost,
    sendEditorPrompt,
    handleSlashCommand,
    filteredCommands,
    COMMANDS,
  }
}
