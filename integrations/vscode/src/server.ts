/**
 * Backend server resolution and lifecycle.
 *
 * Pure URL helpers are separated from the child-process management so they
 * can be unit-tested without spawning anything.
 */

import { spawn, type ChildProcess } from "node:child_process"

export function normalizeServerUrl(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) {
    throw new Error("server URL is empty")
  }
  if (!/^https?:\/\//i.test(trimmed)) {
    throw new Error(`invalid server URL: ${raw} (expected http(s)://host:port)`)
  }
  return trimmed.replace(/\/+$/, "")
}

export function portOf(url: string): number {
  try {
    const port = Number(new URL(url).port)
    return Number.isFinite(port) && port > 0 ? port : 8765
  } catch {
    return 8765
  }
}

export interface BackendServerOptions {
  /** Path to the `apex` executable (defaults to `apex` on PATH). */
  binary?: string
}

export class BackendServer {
  private child: ChildProcess | null = null

  get running(): boolean {
    return this.child !== null
  }

  /** True when this extension started the process (so it owns the lifecycle). */
  startedByUs(): boolean {
    return this.child !== null
  }

  async ensureStarted(cwd: string, url: string, options?: BackendServerOptions): Promise<void> {
    if (this.child) {
      return
    }
    const port = portOf(url)
    const binary = options?.binary ?? process.env.APEX_BIN ?? "apex"
    this.child = spawn(binary, ["serve", "--cwd", cwd, "--port", String(port)], {
      cwd,
      stdio: "ignore",
    })
    this.child.on("exit", () => {
      this.child = null
    })
    this.child.on("error", () => {
      this.child = null
    })
  }

  async stop(): Promise<void> {
    const child = this.child
    this.child = null
    if (!child) {
      return
    }
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        child.kill("SIGKILL")
        resolve()
      }, 5000)
      child.once("exit", () => {
        clearTimeout(timer)
        resolve()
      })
      child.kill("SIGTERM")
    })
  }
}
