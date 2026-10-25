/**
 * APIClient — typed HTTP/SSE client for the APEX backend.
 *
 * Follows OpenCode's client/server split: the TUI is a thin client talking to
 * the backend (Python HTTP+WS server) over HTTP and WebSocket. This module
 * centralizes every wire interaction so components never touch `fetch`
 * directly.
 */

import type { SessionInfo, StreamChunk, ThemeInfo, TuiConfig, Usage } from "../types.js"

export interface ChatStreamOptions {
  message: string
  model: string
  signal?: AbortSignal
  /** Invoked with the accumulated text after every SSE chunk (live streaming). */
  onChunk?: (full: string) => void
}

export interface ChatStreamResult {
  full: string
  usage: Usage
}

export interface BashResult {
  stdout?: string
  stderr?: string
  output?: string
  result?: string
}

export interface SessionDiffResult {
  files?: string
  diff?: string
  session_id?: string
  error?: string
}

const DEFAULT_PORT = 8765

function resolvePort(): number {
  const raw = parseInt(process.env.APEX_HTTP_PORT ?? "0", 10)
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_PORT
}

export class APIClient {
  readonly baseUrl: string
  readonly wsUrl: string

  constructor(port: number = resolvePort()) {
    this.baseUrl = `http://127.0.0.1:${port}`
    this.wsUrl = `ws://127.0.0.1:${port}/ws/events`
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, init)
    if (!resp.ok) {
      const text = await resp.text().catch(() => "")
      throw new Error(`HTTP ${resp.status}${text ? `: ${text}` : ""}`)
    }
    return (await resp.json()) as T
  }

  private post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  }

  getTuiConfig(): Promise<TuiConfig> {
    return this.request<TuiConfig>("/api/v1/tui-config")
  }

  undo(): Promise<{ error?: string }> {
    return this.post("/api/v1/undo")
  }

  redo(): Promise<Record<string, unknown>> {
    return this.post("/api/v1/redo")
  }

  compact(): Promise<Record<string, unknown>> {
    return this.post("/api/v1/compact", {})
  }

  loadSession(id: string): Promise<{ error?: string }> {
    return this.post(`/api/v1/sessions/${encodeURIComponent(id)}/load`)
  }

  sessionHistory(id: string): Promise<{ messages?: Array<Record<string, unknown>>; model?: string }> {
    return this.request(`/api/v1/sessions/${encodeURIComponent(id)}/history`)
  }

  exportSession(sessionId: string): Promise<{ path?: string; error?: string }> {
    return this.post("/api/v1/export", { session_id: sessionId })
  }

  /** Unified diff of the current working tree (preview only). */
  sessionDiff(sessionId: string): Promise<SessionDiffResult> {
    return this.request(`/api/v1/session/${encodeURIComponent(sessionId)}/diff`)
  }

  share(sessionId: string, title: string): Promise<{ url?: string; error?: string }> {
    return this.post("/api/v1/share", { session_id: sessionId, title })
  }

  unshare(shareId: string): Promise<{ ok?: boolean; error?: string }> {
    return this.post(`/api/v1/share/${encodeURIComponent(shareId)}`, undefined) as Promise<{ ok?: boolean; error?: string }>
  }

  cost(): Promise<{ usage?: Usage; total_cost?: number; currency?: string; model?: string }> {
    return this.request("/api/v1/cost")
  }

  listThemes(): Promise<ThemeInfo[]> {
    return this.request<{ themes?: ThemeInfo[] }>("/api/v1/themes").then((d) => d.themes ?? [])
  }

  listSessions(): Promise<SessionInfo[]> {
    return this.request<{ sessions?: SessionInfo[] }>("/api/v1/sessions").then((d) => d.sessions ?? [])
  }

  listFiles(): Promise<string[]> {
    return this.request<{ files?: string[] }>("/api/v1/files").then((d) => d.files ?? [])
  }

  bash(command: string): Promise<BashResult> {
    return this.post<BashResult>("/api/v1/bash", { command })
  }

  /**
   * Stream a chat completion over SSE (`POST /chat/stream`).
   * Returns the accumulated text and final usage once the stream ends.
   */
  async chatStream(opts: ChatStreamOptions): Promise<ChatStreamResult> {
    const resp = await fetch(`${this.baseUrl}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: opts.message, model: opts.model }),
      signal: opts.signal,
    })
    if (!resp.ok) {
      const text = await resp.text().catch(() => "")
      throw new Error(`Server error ${resp.status}: ${text}`)
    }
    if (!resp.body) {
      throw new Error("Empty response")
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ""
    let full = ""
    let usage: Usage = {}

    const consumeLine = (line: string) => {
      if (!line.trim() || line.startsWith(":")) return
      const p = parseSSE(line)
      if (typeof p.chunk === "string") {
        full += p.chunk
        opts.onChunk?.(full)
      }
      if (p.usage) usage = p.usage
      if (p.error) throw new Error(String(p.error))
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split("\n")
      buf = lines.pop() ?? ""
      for (const line of lines) consumeLine(line)
    }
    if (buf.trim()) consumeLine(buf)

    return { full, usage }
  }
}

function parseSSE(data: string): StreamChunk {
  if (!data.startsWith("data: ")) return {}
  try {
    return JSON.parse(data.slice(6)) as StreamChunk
  } catch {
    return {}
  }
}

/** Singleton client (module-level), mirroring the backend's global server. */
export const api = new APIClient()
