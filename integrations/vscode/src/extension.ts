/**
 * APEX VS Code extension — entry point.
 *
 * Thin client (ADR-0007): no agent loop, no provider keys, no tool
 * execution. All intelligence lives in the `apex serve` backend; this
 * extension only talks to it over HTTP/SSE and renders a webview.
 */

import * as vscode from "vscode"
import { ApexClient, type ModelInfo } from "./client"
import { ChatWebviewProvider, type WebviewMessage } from "./chatView"
import { chatReducer, initialChatState, type ChatState } from "./state"
import { BackendServer, normalizeServerUrl, portOf } from "./server"

let statusBar: vscode.StatusBarItem
let secretStore: vscode.SecretStorage
let viewProvider: ChatWebviewProvider
let backend = new BackendServer()
let serverUrl = ""
let apiKey = ""
let client: ApexClient | null = null
let chatState: ChatState = initialChatState()
let selectedModel = ""
let healthTimer: NodeJS.Timeout | undefined

function config(): vscode.WorkspaceConfiguration {
  return vscode.workspace.getConfiguration("apex")
}

function buildClient(): ApexClient {
  const key = apiKey || undefined
  return new ApexClient(serverUrl, key)
}

function ensureServer(): ApexClient | null {
  if (!client) {
    client = buildClient()
  }
  return client
}

function setStatusBar(text: string): void {
  statusBar.text = `$(sparkle) ${text}`
  statusBar.show()
}

async function refreshModels(): Promise<void> {
  const c = ensureServer()
  if (!c) {
    return
  }
  try {
    const models = await c.models()
    viewProvider.setModels(models)
  } catch {
    // Models are non-critical; the webview keeps the previous list.
  }
}

async function connect(): Promise<boolean> {
  const c = ensureServer()
  if (!c) {
    return false
  }
  const health = await c.health()
  if (health.ok) {
    setStatusBar(`apex ${serverUrl}`)
    viewProvider.setServerStatus("connected")
    await refreshModels()
    return true
  }
  return false
}

async function ensureConnected(): Promise<boolean> {
  let ok = await connect()
  if (ok) {
    return true
  }
  // Try auto-start if enabled.
  const autoStart = config().get<boolean>("autoStart", true)
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]
  if (autoStart && workspaceFolder) {
    viewProvider.setServerStatus("starting server…")
    try {
      await backend.ensureStarted(workspaceFolder.uri.fsPath, serverUrl)
    } catch {
      // ignore — we fall through to the not-connected state
    }
    // Give the server a moment to bind its port.
    await new Promise((resolve) => setTimeout(resolve, 1500))
    ok = await connect()
    if (!ok) {
      viewProvider.setServerStatus("not connected")
      setStatusBar(`apex ${serverUrl} (offline)`)
    }
  } else if (!ok) {
    viewProvider.setServerStatus("not connected")
    setStatusBar(`apex ${serverUrl} (offline)`)
  }
  return ok
}

function workspaceFolder(): string | null {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? null
}

async function currentSessionId(): Promise<string> {
  if (chatState.sessionId) {
    return chatState.sessionId
  }
  const c = ensureServer()
  const folder = workspaceFolder()
  if (!c || !folder) {
    return "current"
  }
  try {
    const id = await c.createSession()
    chatState = { ...chatState, sessionId: id }
    viewProvider.updateState(chatState)
    return id
  } catch {
    return "current"
  }
}

async function sendChat(message: string): Promise<void> {
  const ok = await ensureConnected()
  if (!ok) {
    chatState = chatReducer(chatState, { type: "error", message: "backend offline" })
    viewProvider.updateState(chatState)
    return
  }
  const sessionId = await currentSessionId()
  const c = ensureServer()
  if (!c) {
    return
  }
  chatState = chatReducer(chatState, { type: "submit", content: message })
  viewProvider.updateState(chatState)
  await c.chatStream({
    message,
    model: selectedModel || undefined,
    onDelta: (text) => {
      chatState = chatReducer(chatState, { type: "delta", text })
      viewProvider.updateState(chatState)
    },
    onUsage: () => {
      /* usage surfaced via status bar in a future increment */
    },
    onError: (error) => {
      chatState = chatReducer(chatState, { type: "error", message: error.message })
      viewProvider.updateState(chatState)
    },
    onDone: () => {
      chatState = chatReducer(chatState, { type: "assistant-done" })
      viewProvider.updateState(chatState)
    },
  })
}

async function sendSelection(kind: "explain" | "fix"): Promise<void> {
  const editor = vscode.window.activeTextEditor
  if (!editor) {
    vscode.window.showWarningMessage("APEX: no active editor or selection.")
    return
  }
  const selection = editor.selection
  const text = editor.document.getText(selection)
  if (!text.trim()) {
    vscode.window.showWarningMessage("APEX: select code first.")
    return
  }
  const fileName = editor.document.fileName
  const verb = kind === "explain" ? "Explain" : "Fix"
  await sendChat(`${verb} the following ${fileName} code:\n\`\`\`\n${text}\n\`\`\``)
}

async function reviewDiff(): Promise<void> {
  const ok = await ensureConnected()
  if (!ok) {
    vscode.window.showWarningMessage("APEX: backend offline — cannot fetch diff.")
    return
  }
  const c = ensureServer()
  const sessionId = await currentSessionId()
  if (!c) {
    return
  }
  try {
    const diff = await c.diff(sessionId)
    const text = diff.diff || "(working tree clean)"
    const doc = await vscode.workspace.openTextDocument({
      content: text,
      language: "diff",
    })
    await vscode.window.showTextDocument(doc, { preview: true })
  } catch (error) {
    vscode.window.showErrorMessage(
      `APEX: could not fetch diff: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

async function newSession(): Promise<void> {
  chatState = initialChatState()
  selectedModel = config().get<string>("defaultModel", "") || selectedModel
  viewProvider.updateState(chatState)
  vscode.window.showInformationMessage("APEX: new session started.")
}

async function setApiKey(): Promise<void> {
  const secret = secretStore
  const current = await secret.get("apex.apiKey")
  const value = await vscode.window.showInputBox({
    prompt: "APEX backend API key",
    password: true,
    value: current ?? "",
    ignoreFocusOut: true,
  })
  if (value === undefined) {
    return
  }
  if (value.trim() === "") {
    await secret.delete("apex.apiKey")
    apiKey = ""
    client = null
    vscode.window.showInformationMessage("APEX: API key cleared.")
  } else {
    await secret.store("apex.apiKey", value)
    apiKey = value
    client = null
    vscode.window.showInformationMessage("APEX: API key stored.")
  }
}

async function restartServer(): Promise<void> {
  await backend.stop()
  client = null
  await ensureConnected()
  vscode.window.showInformationMessage("APEX: server restarted.")
}

function onWebviewMessage(message: WebviewMessage): void {
  switch (message.type) {
    case "submit":
      if (message.content) {
        void sendChat(message.content)
      }
      break
    case "select-model":
      selectedModel = message.model ?? ""
      break
    case "ready":
      void refreshModels()
      break
    case "stop":
      break
  }
}

export function activate(context: vscode.ExtensionContext): void {
  secretStore = context.secrets
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100)
  statusBar.command = "apex.chat"
  statusBar.tooltip = "Open APEX chat"
  statusBar.show()
  context.subscriptions.push(statusBar)

  viewProvider = new ChatWebviewProvider(context.extensionUri)
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(ChatWebviewProvider.viewType, viewProvider),
  )

  const secret = secretStore
  void (async () => {
    apiKey = (await secret.get("apex.apiKey")) ?? ""
    const raw = config().get<string>("serverUrl", "http://127.0.0.1:8765")
    try {
      serverUrl = normalizeServerUrl(raw)
    } catch (error) {
      serverUrl = "http://127.0.0.1:8765"
      vscode.window.showErrorMessage(
        `APEX: invalid apex.serverUrl "${raw}" — falling back to 127.0.0.1:8765.`,
      )
    }
    selectedModel = config().get<string>("defaultModel", "")
    client = buildClient()
    await ensureConnected()
  })()

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("apex")) {
        const raw = config().get<string>("serverUrl", "http://127.0.0.1:8765")
        try {
          serverUrl = normalizeServerUrl(raw)
        } catch {
          // keep previous
        }
        client = buildClient()
        void ensureConnected()
      }
    }),
  )

  // Lightweight health polling so the status bar reflects server state.
  healthTimer = setInterval(() => {
    void (async () => {
      const c = ensureServer()
      if (!c) {
        return
      }
      const health = await c.health()
      if (!health.ok && backend.running) {
        backend.stop().then(() => {
          void ensureConnected()
        })
      }
    })()
  }, 30000)
  context.subscriptions.push({
    dispose: () => {
      if (healthTimer) {
        clearInterval(healthTimer)
        healthTimer = undefined
      }
    },
  })

  const commands: Array<[string, (...a: unknown[]) => unknown]> = [
    ["apex.chat", () => void vscode.commands.executeCommand(`${ChatWebviewProvider.viewType}.focus`)],
    ["apex.newSession", () => void newSession()],
    ["apex.explainSelection", () => void sendSelection("explain")],
    ["apex.fixSelection", () => void sendSelection("fix")],
    ["apex.reviewDiff", () => void reviewDiff()],
    ["apex.setApiKey", () => void setApiKey()],
    ["apex.restartServer", () => void restartServer()],
  ]
  for (const [id, fn] of commands) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn))
  }

  viewProvider.onDidReceiveMessage(onWebviewMessage)
}

export function deactivate(): void {
  void backend.stop()
  if (healthTimer) {
    clearInterval(healthTimer)
  }
}
