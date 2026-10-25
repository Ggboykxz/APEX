"use strict";
/**
 * Pure chat state reducer for the APEX webview.
 *
 * No `vscode` import: the reducer is fully testable in plain Node.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.initialChatState = initialChatState;
exports.chatReducer = chatReducer;
let counter = 0;
const nextId = (prefix) => `${prefix}-${Date.now()}-${counter++}`;
function initialChatState() {
    return { sessionId: null, messages: [], streaming: false, error: null };
}
function chatReducer(state, action) {
    switch (action.type) {
        case "session":
            return { ...state, sessionId: action.sessionId };
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
            };
        case "delta": {
            const messages = state.messages.slice();
            const last = messages[messages.length - 1];
            if (last && last.role === "assistant") {
                messages[messages.length - 1] = { ...last, content: last.content + action.text };
            }
            return { ...state, messages };
        }
        case "assistant-done":
            return { ...state, streaming: false };
        case "tool":
            return {
                ...state,
                messages: [
                    ...state.messages,
                    { id: nextId("tool"), role: "tool", content: action.label },
                ],
            };
        case "error":
            return { ...state, streaming: false, error: action.message };
        case "reset":
            return initialChatState();
    }
}
//# sourceMappingURL=state.js.map