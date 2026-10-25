import * as React from "react"

const MOBILE_BREAKPOINT = 768

function subscribe(onChange: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

function getSnapshot() {
  return window.innerWidth < MOBILE_BREAKPOINT
}

export function useIsMobile() {
  // useSyncExternalStore keeps the value in sync with the media query without
  // calling setState from an effect (react-hooks/set-state-in-effect).
  return React.useSyncExternalStore(subscribe, getSnapshot, () => false)
}
