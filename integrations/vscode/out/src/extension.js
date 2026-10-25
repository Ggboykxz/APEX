"use strict";
/**
 * APEX VS Code extension — entry point.
 *
 * Thin client (ADR-0007): no agent loop, no provider keys, no tool
 * execution. All intelligence lives in the `apex serve` backend; this
 * extension only talks to it over HTTP/SSE and renders a webview.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const client_1 = require("./client");
const chatView_1 = require("./chatView");
const state_1 = require("./state");
const server_1 = require("./server");
let statusBar;
let secretStore;
let viewProvider;
let backend = new server_1.BackendServer();
let serverUrl = "";
let apiKey = "";
let client = null;
let chatState = (0, state_1.initialChatState)();
let selectedModel = "";
let healthTimer;
function config() {
    return vscode.workspace.getConfiguration("apex");
}
function buildClient() {
    const key = apiKey || undefined;
    return new client_1.ApexClient(serverUrl, key);
}
function ensureServer() {
    if (!client) {
        client = buildClient();
    }
    return client;
}
function setStatusBar(text) {
    statusBar.text = `$(sparkle) ${text}`;
    statusBar.show();
}
async function refreshModels() {
    const c = ensureServer();
    if (!c) {
        return;
    }
    try {
        const models = await c.models();
        viewProvider.setModels(models);
    }
    catch {
        // Models are non-critical; the webview keeps the previous list.
    }
}
async function connect() {
    const c = ensureServer();
    if (!c) {
        return false;
    }
    const health = await c.health();
    if (health.ok) {
        setStatusBar(`apex ${serverUrl}`);
        viewProvider.setServerStatus("connected");
        await refreshModels();
        return true;
    }
    return false;
}
async function ensureConnected() {
    let ok = await connect();
    if (ok) {
        return true;
    }
    // Try auto-start if enabled.
    const autoStart = config().get("autoStart", true);
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (autoStart && workspaceFolder) {
        viewProvider.setServerStatus("starting server…");
        try {
            await backend.ensureStarted(workspaceFolder.uri.fsPath, serverUrl);
        }
        catch {
            // ignore — we fall through to the not-connected state
        }
        // Give the server a moment to bind its port.
        await new Promise((resolve) => setTimeout(resolve, 1500));
        ok = await connect();
        if (!ok) {
            viewProvider.setServerStatus("not connected");
            setStatusBar(`apex ${serverUrl} (offline)`);
        }
    }
    else if (!ok) {
        viewProvider.setServerStatus("not connected");
        setStatusBar(`apex ${serverUrl} (offline)`);
    }
    return ok;
}
function workspaceFolder() {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? null;
}
async function currentSessionId() {
    if (chatState.sessionId) {
        return chatState.sessionId;
    }
    const c = ensureServer();
    const folder = workspaceFolder();
    if (!c || !folder) {
        return "current";
    }
    try {
        const id = await c.createSession();
        chatState = { ...chatState, sessionId: id };
        viewProvider.updateState(chatState);
        return id;
    }
    catch {
        return "current";
    }
}
async function sendChat(message) {
    const ok = await ensureConnected();
    if (!ok) {
        chatState = (0, state_1.chatReducer)(chatState, { type: "error", message: "backend offline" });
        viewProvider.updateState(chatState);
        return;
    }
    const sessionId = await currentSessionId();
    const c = ensureServer();
    if (!c) {
        return;
    }
    chatState = (0, state_1.chatReducer)(chatState, { type: "submit", content: message });
    viewProvider.updateState(chatState);
    await c.chatStream({
        message,
        model: selectedModel || undefined,
        onDelta: (text) => {
            chatState = (0, state_1.chatReducer)(chatState, { type: "delta", text });
            viewProvider.updateState(chatState);
        },
        onUsage: () => {
            /* usage surfaced via status bar in a future increment */
        },
        onError: (error) => {
            chatState = (0, state_1.chatReducer)(chatState, { type: "error", message: error.message });
            viewProvider.updateState(chatState);
        },
        onDone: () => {
            chatState = (0, state_1.chatReducer)(chatState, { type: "assistant-done" });
            viewProvider.updateState(chatState);
        },
    });
}
async function sendSelection(kind) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage("APEX: no active editor or selection.");
        return;
    }
    const selection = editor.selection;
    const text = editor.document.getText(selection);
    if (!text.trim()) {
        vscode.window.showWarningMessage("APEX: select code first.");
        return;
    }
    const fileName = editor.document.fileName;
    const verb = kind === "explain" ? "Explain" : "Fix";
    await sendChat(`${verb} the following ${fileName} code:\n\`\`\`\n${text}\n\`\`\``);
}
async function reviewDiff() {
    const ok = await ensureConnected();
    if (!ok) {
        vscode.window.showWarningMessage("APEX: backend offline — cannot fetch diff.");
        return;
    }
    const c = ensureServer();
    const sessionId = await currentSessionId();
    if (!c) {
        return;
    }
    try {
        const diff = await c.diff(sessionId);
        const text = diff.diff || "(working tree clean)";
        const doc = await vscode.workspace.openTextDocument({
            content: text,
            language: "diff",
        });
        await vscode.window.showTextDocument(doc, { preview: true });
    }
    catch (error) {
        vscode.window.showErrorMessage(`APEX: could not fetch diff: ${error instanceof Error ? error.message : String(error)}`);
    }
}
async function newSession() {
    chatState = (0, state_1.initialChatState)();
    selectedModel = config().get("defaultModel", "") || selectedModel;
    viewProvider.updateState(chatState);
    vscode.window.showInformationMessage("APEX: new session started.");
}
async function setApiKey() {
    const secret = secretStore;
    const current = await secret.get("apex.apiKey");
    const value = await vscode.window.showInputBox({
        prompt: "APEX backend API key",
        password: true,
        value: current ?? "",
        ignoreFocusOut: true,
    });
    if (value === undefined) {
        return;
    }
    if (value.trim() === "") {
        await secret.delete("apex.apiKey");
        apiKey = "";
        client = null;
        vscode.window.showInformationMessage("APEX: API key cleared.");
    }
    else {
        await secret.store("apex.apiKey", value);
        apiKey = value;
        client = null;
        vscode.window.showInformationMessage("APEX: API key stored.");
    }
}
async function restartServer() {
    await backend.stop();
    client = null;
    await ensureConnected();
    vscode.window.showInformationMessage("APEX: server restarted.");
}
function onWebviewMessage(message) {
    switch (message.type) {
        case "submit":
            if (message.content) {
                void sendChat(message.content);
            }
            break;
        case "select-model":
            selectedModel = message.model ?? "";
            break;
        case "ready":
            void refreshModels();
            break;
        case "stop":
            break;
    }
}
function activate(context) {
    secretStore = context.secrets;
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = "apex.chat";
    statusBar.tooltip = "Open APEX chat";
    statusBar.show();
    context.subscriptions.push(statusBar);
    viewProvider = new chatView_1.ChatWebviewProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(chatView_1.ChatWebviewProvider.viewType, viewProvider));
    const secret = secretStore;
    void (async () => {
        apiKey = (await secret.get("apex.apiKey")) ?? "";
        const raw = config().get("serverUrl", "http://127.0.0.1:8765");
        try {
            serverUrl = (0, server_1.normalizeServerUrl)(raw);
        }
        catch (error) {
            serverUrl = "http://127.0.0.1:8765";
            vscode.window.showErrorMessage(`APEX: invalid apex.serverUrl "${raw}" — falling back to 127.0.0.1:8765.`);
        }
        selectedModel = config().get("defaultModel", "");
        client = buildClient();
        await ensureConnected();
    })();
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("apex")) {
            const raw = config().get("serverUrl", "http://127.0.0.1:8765");
            try {
                serverUrl = (0, server_1.normalizeServerUrl)(raw);
            }
            catch {
                // keep previous
            }
            client = buildClient();
            void ensureConnected();
        }
    }));
    // Lightweight health polling so the status bar reflects server state.
    healthTimer = setInterval(() => {
        void (async () => {
            const c = ensureServer();
            if (!c) {
                return;
            }
            const health = await c.health();
            if (!health.ok && backend.running) {
                backend.stop().then(() => {
                    void ensureConnected();
                });
            }
        })();
    }, 30000);
    context.subscriptions.push({
        dispose: () => {
            if (healthTimer) {
                clearInterval(healthTimer);
                healthTimer = undefined;
            }
        },
    });
    const commands = [
        ["apex.chat", () => void vscode.commands.executeCommand(`${chatView_1.ChatWebviewProvider.viewType}.focus`)],
        ["apex.newSession", () => void newSession()],
        ["apex.explainSelection", () => void sendSelection("explain")],
        ["apex.fixSelection", () => void sendSelection("fix")],
        ["apex.reviewDiff", () => void reviewDiff()],
        ["apex.setApiKey", () => void setApiKey()],
        ["apex.restartServer", () => void restartServer()],
    ];
    for (const [id, fn] of commands) {
        context.subscriptions.push(vscode.commands.registerCommand(id, fn));
    }
    viewProvider.onDidReceiveMessage(onWebviewMessage);
}
function deactivate() {
    void backend.stop();
    if (healthTimer) {
        clearInterval(healthTimer);
    }
}
//# sourceMappingURL=extension.js.map