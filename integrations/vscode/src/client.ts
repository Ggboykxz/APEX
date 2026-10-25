/**
 * Thin HTTP/SSE client for the APEX backend (`apex serve`).
 *
 * Uses the global `fetch` API only; no Node-specific modules. The class is
 * deliberately independent of the `vscode` API so it can be unit-tested
 * with a mocked global fetch.
 */

import { SSEParser, type SSEMessage } from "./sse"

export interface ModelInfo {
  name?: string
  id?: string
  [key: string]: unknown
}

export interface SessionDiffResult {
  files?: string
  diff?: string
  paths?: string[]
  fingerprint?: string
  error?: string
}

export interface ChatStreamOptions {
  message: string
  model?: string
  onDelta?: (text: string) => void
  onUsage?: (usage: Record<string, unknown>) => void
  onError?: (error: Error) => void
  onDone?: () => void
  signal?: AbortSignal
}

export class ApexClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey?: string,
  ) {}

  private headers(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json", ...extra }
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`
    }
    return headers
  }

  private url(path: string): string {
    return `${this.baseUrl.replace(/\/+$/, "")}${path}`
  }

  async health(): Promise<{ ok: boolean; status: number }> {
    try {
      const resp = await fetch(this.url("/health"), { headers: this.headers() })
      return { ok: resp.ok, status: resp.status }
    } catch {
      return { ok: false, status: 0 }
    }
  }

  async models(): Promise<ModelInfo[]> {
    const resp = await fetch(this.url("/api/v1/models"), { headers: this.headers() })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }
    const data = (await resp.json()) as { models?: ModelInfo[]; data?: ModelInfo[] }
    return data.models ?? data.data ?? []
  }

  async createSession(): Promise<string> {
    const resp = await fetch(this.url("/api/v1/sessions"), {
      method: "POST",
      headers: this.headers(),
      body: "{}",
    })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }
    const data = (await resp.json()) as { session_id?: string; id?: string }
    return data.session_id ?? data.id ?? "current"
  }

  async diff(sessionId: string): Promise<SessionDiffResult> {
    const resp = await fetch(this.url(`/api/v1/session/${encodeURIComponent(sessionId)}/diff`), {
      headers: this.headers(),
    })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }
    return (await resp.json()) as SessionDiffResult
  }

  async chatStream(options: ChatStreamOptions): Promise<void> {
    const parser = new SSEParser()
    let resp: Response
    try {
      resp = await fetch(this.url("/chat/stream"), {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ message: options.message, model: options.model }),
        signal: options.signal,
      })
    } catch (error) {
      options.onError?.(error instanceof Error ? error : new Error(String(error)))
      return
    }
    if (!resp.ok || !resp.body) {
      options.onError?.(new Error(`HTTP ${resp.status}`))
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    try {
      for (;;) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }
        const messages = parser.push(decoder.decode(value, { stream: true }))
        for (const message of messages) {
          this.handleSSE(message, options)
        }
      }
      const trailing = parser.flush()
      for (const message of trailing) {
        this.handleSSE(message, options)
      }
      options.onDone?.()
    } catch (error) {
      options.onError?.(error instanceof Error ? error : new Error(String(error)))
    }
  }

  private handleSSE(message: SSEMessage, options: ChatStreamOptions): void {
    let payload: unknown
    try {
      payload = JSON.parse(message.data)
    } catch {
      options.onDelta?.(message.data)
      return
    }
    if (typeof payload === "object" && payload !== null) {
      const record = payload as Record<string, unknown>
      if (typeof record.chunk === "string") {
        options.onDelta?.(record.chunk)
        return
      }
      if (record.usage !== undefined) {
        options.onUsage?.(record.usage as Record<string, unknown>)
        return
      }
      if (record.error !== undefined) {
        options.onError?.(new Error(String(record.error)))
        return
      }
    }
    options.onDelta?.(message.data)
  }
}
