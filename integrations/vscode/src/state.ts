/**
 * Pure chat state reducer for the APEX webview.
 *
 * No `vscode` import: the reducer is fully testable in plain Node.
 */

export type ChatRole = "user" | "assistant" | "tool" | "system"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
}

export interface ChatState {
  sessionId: string | null
  messages: ChatMessage[]
  streaming: boolean
  error: string | null
}

export type ChatAction =
  | { type: "session"; sessionId: string }
  | { type: "submit"; content: string }
  | { type: "delta"; text: string }
  | { type: "assistant-done" }
  | { type: "tool"; label: string }
  | { type: "error"; message: string }
  | { type: "reset" }

let counter = 0
const nextId = (prefix: string): string => `${prefix}-${Date.now()}-${counter++}`

export function initialChatState(): ChatState {
  return { sessionId: null, messages: [], streaming: false, error: null }
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "session":
      return { ...state, sessionId: action.sessionId }
    case "submit":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: nextId("user"), role: "user", content: action.content },
          { id: nextId("assistant"), role: "assistant", content: "" },
        ],
        streaming: true,
        error: null,
      }
    case "delta": {
      const messages = state.messages.slice()
      const last = messages[messages.length - 1]
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + action.text }
      }
      return { ...state, messages }
    }
    case "assistant-done":
      return { ...state, streaming: false }
    case "tool":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: nextId("tool"), role: "tool", content: action.label },
        ],
      }
    case "error":
      return { ...state, streaming: false, error: action.message }
    case "reset":
      return initialChatState()
  }
}
