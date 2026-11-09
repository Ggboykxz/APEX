"use strict";

/**
 * useLeaderKeys — manages the Ctrl+X leader-key state machine.
 * On Ctrl+X, starts a timeout window during which the next keypress triggers
 * a leader command (n=new, u=undo, r=redo, c=compact, m=model, t=theme,
 * s=status, e=editor, x=export, b=sidebar, a=agent, l=session, q=quit).
 */

import { useCallback, useEffect, useRef, useState } from "react"

interface LeaderCommand {
  action: "cmd" | "overlay" | "sidebar" | "quit"
  cmd?: string
}

interface UseLeaderKeysProps {
  timeout?: number
  onCommand: (cmd: LeaderCommand) => void
}

export function useLeaderKeys({
  timeout = 2000,
  onCommand,
}: UseLeaderKeysProps) {
  const [active, setActive] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const LEADER_CMDS: Record<string, LeaderCommand> = {
    n: { action: "cmd", cmd: "/new" },
    u: { action: "cmd", cmd: "/undo" },
    r: { action: "cmd", cmd: "/redo" },
    c: { action: "cmd", cmd: "/compact" },
    m: { action: "overlay", cmd: "model" },
    t: { action: "overlay", cmd: "theme" },
    s: { action: "overlay", cmd: "status" },
    e: { action: "cmd", cmd: "/editor" },
    x: { action: "cmd", cmd: "/export" },
    b: { action: "sidebar" },
    a: { action: "overlay", cmd: "agent" },
    l: { action: "overlay", cmd: "session" },
    y: { action: "cmd", cmd: "/copy" },
    q: { action: "quit" },
  }

  const activate = useCallback(() => {
    setActive(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setActive(false), timeout)
  }, [timeout])

  const handleKey = useCallback(
    (k: string) => {
      if (!active) return false
      if (timer.current) {
        clearTimeout(timer.current)
        timer.current = null
      }
      setActive(false)
      const e = LEADER_CMDS[k.toLowerCase()]
      if (!e) return false
      onCommand(e)
      return true
    },
    [active, onCommand]
  )

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  return { active, activate, handleKey }
}
