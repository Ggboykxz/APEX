/**
 * SyncProvider — WebSocket-based real-time sync with APEX backend.
 *
 * Follows OpenCode's architecture:
 *   - Worker (Python) runs HTTP + WS server
 *   - TUI (Ink) connects to /ws/events for real-time state
 *   - Falls back to HTTP polling if WS fails
 */

export interface SyncEvent {
  event: string
  data: Record<string, unknown>
  timestamp: number
}

export interface SyncState {
  model: string
  agent: string
  cwd: string
  historyLength: number
  undoAvailable: boolean
  redoAvailable: boolean
  connected: boolean
  version: string
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

  constructor(
    private readonly url: string,
    private readonly httpBase: string,
  ) {}

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
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ method, params: params ?? {} }))
    }
  }

  /** Fetch via HTTP (for non-real-time operations) */
  async fetch(path: string, opts?: RequestInit): Promise<Response> {
    return fetch(`${this.httpBase}${path}`, opts)
  }

  private _connectWs(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return
    }

    try {
      this.ws = new WebSocket(this.url)
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
        if (this.ws?.readyState === WebSocket.OPEN) {
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
        this._state = { ...this._state, ...msg.data, connected: true }
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
