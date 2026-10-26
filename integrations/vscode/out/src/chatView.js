"use strict";
/**
 * Webview chat view.
 *
 * The webview is a pure presentation surface: it owns no backend calls and
 * exchanges typed messages with the extension host. The CSP denies every
 * remote and inline source except the nonce-tagged bootstrap script.
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
exports.ChatWebviewProvider = void 0;
const vscode = __importStar(require("vscode"));
class ChatWebviewProvider {
    extensionUri;
    static viewType = "apex.chatView";
    view;
    chatState;
    models = [];
    serverStatus = "connecting…";
    onMessage = new vscode.EventEmitter();
    /** Fired when the webview sends a message to the host. */
    onDidReceiveMessage = this.onMessage.event;
    constructor(extensionUri) {
        this.extensionUri = extensionUri;
        this.chatState = { sessionId: null, messages: [], streaming: false, error: null };
    }
    resolveWebviewView(webviewView, _context, _token) {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "out", "webview")],
        };
        webviewView.webview.html = this.renderHtml(webviewView.webview);
        webviewView.webview.onDidReceiveMessage((message) => {
            this.onMessage.fire(message);
        });
        // Push the latest snapshot once the webview is ready.
        this.post({ type: "state", state: this.chatState });
        this.post({ type: "models", models: this.models });
        this.post({ type: "server-status", status: this.serverStatus });
    }
    updateState(state) {
        this.chatState = state;
        if (!this.view) {
            return;
        }
        this.post({ type: "state", state });
    }
    setModels(models) {
        this.models = models;
        this.post({ type: "models", models });
    }
    setServerStatus(status) {
        this.serverStatus = status;
        this.post({ type: "server-status", status });
    }
    showError(message) {
        this.post({ type: "error", error: message });
    }
    post(message) {
        if (this.view) {
            void this.view.webview.postMessage(message);
        }
    }
    renderHtml(webview) {
        const nonce = getNonce();
        const csp = [
            "default-src 'none'",
            `img-src ${webview.cspSource} data:`,
            `style-src ${webview.cspSource}`,
            `script-src 'nonce-${nonce}'`,
            "font-src 'none'",
        ].join("; ");
        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>
  :root { --fg: #d8dee9; --bg: #151a21; --accent: #00e5ff; --muted: #7b8794; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg);
         font-family: var(--vscode-font-family); font-size: 13px;
         display: flex; flex-direction: column; height: 100vh; }
  #status { padding: 4px 10px; color: var(--muted); border-bottom: 1px solid #262d36;
            display: flex; gap: 8px; align-items: center; }
  #status .dot { width: 8px; height: 8px; border-radius: 50%; background: #e2b93b; }
  #status.ok .dot { background: #4caf50; }
  #status.bad .dot { background: #e5534b; }
  #messages { flex: 1; overflow-y: auto; padding: 10px; }
  .msg { margin: 4px 0; padding: 6px 10px; border-radius: 6px; white-space: pre-wrap;
         word-break: break-word; }
  .msg.user { background: #1e2733; border: 1px solid #2a3648; }
  .msg.assistant { background: #1a2029; }
  .msg.tool { color: var(--muted); font-style: italic; font-size: 12px; }
  .msg.error { color: #e5534b; }
  .msg .role { display: block; font-size: 11px; color: var(--muted); margin-bottom: 2px; }
  #composer { display: flex; gap: 6px; padding: 8px; border-top: 1px solid #262d36; }
  #composer textarea { flex: 1; resize: none; background: #0f1318; color: var(--fg);
                       border: 1px solid #2a3648; border-radius: 4px; padding: 6px;
                       font-family: inherit; }
  #composer button { background: #00e5ff22; color: var(--accent); border: 1px solid var(--accent);
                     border-radius: 4px; padding: 6px 12px; cursor: pointer; }
  #composer button:disabled { opacity: .4; cursor: default; }
  #meta { padding: 2px 10px 8px; display: flex; gap: 8px; align-items: center; }
  select { background: #0f1318; color: var(--fg); border: 1px solid #2a3648; }
</style>
</head>
<body>
  <div id="status" class=""><span class="dot"></span><span id="status-text">connecting…</span></div>
  <div id="messages"></div>
  <div id="meta">
    <select id="model"><option value="">model (default)</option></select>
    <span id="session" style="color:var(--muted);font-size:11px"></span>
  </div>
  <div id="composer">
    <textarea id="input" rows="2" placeholder="Ask APEX… (Enter to send, Shift+Enter for newline)"></textarea>
    <button id="send">Send</button>
  </div>
<script nonce="${nonce}">
(function () {
  var vscode = acquireVsCodeApi();
  var messages = document.getElementById('messages');
  var input = document.getElementById('input');
  var send = document.getElementById('send');
  var status = document.getElementById('status');
  var statusText = document.getElementById('status-text');
  var modelSelect = document.getElementById('model');
  var sessionEl = document.getElementById('session');

  function sendMessage(msg) { vscode.postMessage(msg); }

  function render(state) {
    messages.innerHTML = '';
    if (!state || !state.messages) { return; }
    state.messages.forEach(function (m) {
      var el = document.createElement('div');
      el.className = 'msg ' + m.role;
      var role = document.createElement('span');
      role.className = 'role';
      role.textContent = m.role;
      el.appendChild(role);
      var text = document.createElement('span');
      text.textContent = m.content || (m.role === 'assistant' ? '…' : '');
      el.appendChild(text);
      messages.appendChild(el);
    });
    messages.scrollTop = messages.scrollHeight;
    if (state.streaming) {
      send.textContent = 'Stop';
      send.disabled = false;
    } else {
      send.textContent = 'Send';
      send.disabled = false;
    }
    sessionEl.textContent = state.sessionId ? 'session ' + state.sessionId : '';
  }

  function renderModels(models) {
    modelSelect.innerHTML = '<option value="">model (default)</option>';
    (models || []).forEach(function (m) {
      var opt = document.createElement('option');
      var label = m.name || m.id || m.model || '';
      opt.value = m.id || label;
      opt.textContent = label;
      modelSelect.appendChild(opt);
    });
  }

  function renderStatus(text, ok) {
    statusText.textContent = text;
    status.className = ok ? 'ok' : (text.indexOf('bad') === 0 ? 'bad' : '');
  }

  window.addEventListener('message', function (event) {
    var msg = event.data;
    if (msg.type === 'state') { render(msg.state); }
    else if (msg.type === 'models') { renderModels(msg.models); }
    else if (msg.type === 'server-status') { renderStatus(msg.status, msg.status === 'connected'); }
    else if (msg.type === 'error') {
      var el = document.createElement('div');
      el.className = 'msg error';
      el.textContent = 'error: ' + msg.error;
      messages.appendChild(el);
    }
  });

  function submit() {
    var content = input.value.trim();
    if (!content) { return; }
    sendMessage({ type: 'submit', content: content });
    input.value = '';
  }

  send.addEventListener('click', function () { submit(); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  });
  modelSelect.addEventListener('change', function () {
    sendMessage({ type: 'select-model', model: modelSelect.value });
  });

  sendMessage({ type: 'ready' });
})();
</script>
</body>
</html>`;
    }
}
exports.ChatWebviewProvider = ChatWebviewProvider;
function getNonce() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let text = "";
    for (let i = 0; i < 32; i++) {
        text += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return text;
}
//# sourceMappingURL=chatView.js.map