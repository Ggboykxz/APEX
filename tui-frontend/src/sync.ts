/**
 * SyncProvider — WebSocket-based real-time sync with APEX backend.
 *
 * Follows OpenCode's architecture:
 *   - Worker (Python) runs HTTP + WS server
 *   - TUI (Ink) connects to /ws/events for real-time state
 *   - Falls back to HTTP polling if WS fails
 */

import { createRequire } from "node:module"
import { normalizeAgentEvent } from "./streaming/events.js"
import type { AgentStreamEvent, SyncEvent, SyncState } from "./types.js"

export type { SyncEvent, SyncState } from "./types.js"

/**
 * Node < 22 has no global `WebSocket`. Fall back to the `ws` package so the
 * TUI works on older Node runtimes as well.
 */
function resolveWebSocket(): typeof WebSocket | null {
  const globalWs = (globalThis as { WebSocket?: typeof WebSocket }).WebSocket
  if (globalWs) return globalWs
  try {
    const require_ = createRequire(import.meta.url)
    return require_("ws") as typeof WebSocket
  } catch {
    return null
  }
}

const DefaultWebSocketImpl = resolveWebSocket()

type WebSocketImpl = typeof WebSocket

export interface SyncClientOptions {
  /**
   * Injectable transport for tests (and for alternate runtimes). `undefined`
   * keeps the auto-detected global/`ws` implementation; `null` disables the
   * socket entirely so the HTTP/SSE fallback path is used.
   */
  webSocketImpl?: WebSocketImpl | null
}

type EventCallback = (...args: any[]) => void

export class SyncClient {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private _state: Partial<SyncState> = {}
  private _connected = false
  private _reconnectAttempts = 0
  private _maxReconnectDelay = 30000
  private _listeners: Map<string, Set<EventCallback>> = new Map()
  private readonly _wsImpl: WebSocketImpl | null

  constructor(
    private readonly url: string,
    private readonly httpBase: string,
    options: SyncClientOptions = {},
  ) {
    this._wsImpl =
      options.webSocketImpl === undefined ? DefaultWebSocketImpl : options.webSocketImpl
  }

  get state(): Partial<SyncState> {
    return this._state
  }

  get connected(): boolean {
    return this._connected
  }

  on(event: string, cb: EventCallback): void {
    if (!this._listeners.has(event)) this._listeners.set(event, new Set())
    this._listeners.get(event)!.add(cb)
  }

  off(event: string, cb: EventCallback): void {
    this._listeners.get(event)?.delete(cb)
  }

  /** Subscribe to normalized assistant/tool/session streaming events. */
  onStream(cb: (event: AgentStreamEvent) => void): void {
    this.on("stream", cb as EventCallback)
  }

  offStream(cb: (event: AgentStreamEvent) => void): void {
    this.off("stream", cb as EventCallback)
  }

  private emit(event: string, ...args: any[]): void {
    this._listeners.get(event)?.forEach((cb) => {
      try { cb(...args) } catch { /* ignore listener errors */ }
    })
  }

  connect(): void {
    this._connectWs()
  }

  disconnect(): void {
    this._cleanup()
  }

  /** Send an RPC command to the backend via WebSocket */
  rpc(method: string, params?: Record<string, unknown>): void {
    if (this.ws?.readyState === this.OPEN) {
      this.ws.send(JSON.stringify({ method, params: params ?? {} }))
    }
  }

  private get OPEN(): number {
    return this._wsImpl?.OPEN ?? 1
  }

  /** Fetch via HTTP (for non-real-time operations) */
  async fetch(path: string, opts?: RequestInit): Promise<Response> {
    return fetch(`${this.httpBase}${path}`, opts)
  }

  private _connectWs(): void {
    if (!this._wsImpl) {
      this.emit("disconnected")
      return
    }
    if (this.ws?.readyState === this.OPEN || this.ws?.readyState === this._wsImpl.CONNECTING) {
      return
    }

    try {
      this.ws = new this._wsImpl(this.url)
    } catch {
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this._connected = true
      this._reconnectAttempts = 0
      this.emit("connected")
      // Start ping to keep connection alive
      this.pingTimer = setInterval(() => {
        if (this.ws?.readyState === this.OPEN) {
          this.ws.send(JSON.stringify({ method: "ping" }))
        }
      }, 30000)
    }

    this.ws.onmessage = (event: { data: string }) => {
      try {
        const msg = JSON.parse(event.data) as SyncEvent
        this._handleEvent(msg)
      } catch {
        // Ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      const wasConnected = this._connected
      this._connected = false
      this.emit("disconnected")
      if (wasConnected) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = () => {
      // onclose will fire after this
    }
  }

  private _handleEvent(msg: SyncEvent): void {
    // Emit the typed stream event first; the switch below keeps every legacy
    // event name/emission intact for existing listeners and HTTP fallbacks.
    const streamEvent = normalizeAgentEvent(msg)
    if (streamEvent) this.emit("stream", streamEvent)

    switch (msg.event) {
      case "connected":
        this._state = {
          ...this._state,
          model: msg.data.model as string,
          agent: msg.data.agent as string,
          cwd: msg.data.cwd as string,
          version: msg.data.version as string,
          connected: true,
        }
        this.emit("state", this._state)
        break
      case "pong":
        // Heartbeat response, no action needed
        break
      case "state":
        this._state = {
          ...this._state,
          ...msg.data,
          historyLength:
            (msg.data.history_length as number | undefined) ??
            (msg.data.historyLength as number | undefined) ??
            this._state.historyLength,
          undoAvailable:
            (msg.data.undo_available as boolean | undefined) ??
            (msg.data.undoAvailable as boolean | undefined) ??
            this._state.undoAvailable,
          redoAvailable:
            (msg.data.redo_available as boolean | undefined) ??
            (msg.data.redoAvailable as boolean | undefined) ??
            this._state.redoAvailable,
          connected: true,
        }
        this.emit("state", this._state)
        break
      case "chat_complete":
        this.emit("chat_complete", msg.data)
        break
      case "undo":
        this.emit("undo", msg.data)
        break
      case "redo":
        this.emit("redo", msg.data)
        break
      case "compact":
        this.emit("compact", msg.data)
        break
      case "theme_changed":
        this.emit("theme_changed", msg.data)
        break
      default:
        this.emit("event", msg)
    }
  }

  private _scheduleReconnect(): void {
    if (this.reconnectTimer) return
    const delay = Math.min(
      1000 * Math.pow(2, this._reconnectAttempts),
      this._maxReconnectDelay,
    )
    this._reconnectAttempts++
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this._connectWs()
    }, delay)
  }

  private _cleanup(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      try {
        this.ws.close()
      } catch {
        // Ignore
      }
      this.ws = null
    }
    this._connected = false
    this._listeners.clear()
  }
}
