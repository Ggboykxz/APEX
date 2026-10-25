# VS Code Extension

The APEX VS Code extension (`integrations/vscode/`) is a **thin client** for the
APEX backend. It implements [ADR-0007](../adr/ADR-0007-vscode-thin-client.md):
no agent loop, no provider keys, and no tool execution live in the extension —
all intelligence stays in the single `apex serve` process.

## Requirements

- VS Code `^1.90.0`
- A reachable APEX backend (`apex serve`, default `http://127.0.0.1:8765`),
  or `apex.autoStart` enabled so the extension starts one for the workspace.

## Settings

| Key | Default | Description |
|-----|---------|-------------|
| `apex.serverUrl` | `http://127.0.0.1:8765` | Base URL of the APEX backend. |
| `apex.autoStart` | `true` | Start `apex serve --cwd <workspace>` when no backend responds. |
| `apex.defaultModel` | `""` | Default model for new sessions (empty = backend default). |

## Commands

| Command | Description |
|---------|-------------|
| `APEX: Open Chat` (`apex.chat`) | Focus the APEX chat view. |
| `APEX: New Session` (`apex.newSession`) | Reset the chat and start a fresh session. |
| `APEX: Explain Selection` (`apex.explainSelection`) | Send the current selection to APEX for an explanation (context menu). |
| `APEX: Fix Selection` (`apex.fixSelection`) | Send the current selection to APEX for a fix (context menu). |
| `APEX: Review Working Tree Diff` (`apex.reviewDiff`) | Open the working-tree unified diff in a read-only editor. |
| `APEX: Set Backend API Key` (`apex.setApiKey`) | Store or clear the backend API key in VS Code SecretStorage. |
| `APEX: Restart Backend Server` (`apex.restartServer`) | Stop a backend the extension started and reconnect. |

## Security model

- The backend API key lives only in VS Code **SecretStorage**; it is sent as an
  `Authorization: Bearer …` header and never appears in settings, logs, or the
  webview.
- The chat webview runs with a strict CSP: no remote scripts or styles, and no
  inline scripts except the nonce-tagged bootstrap. It is pure presentation —
  every backend call is made by the extension host.
- Auto-start only launches `apex serve` for the first workspace folder and only
  kills processes the extension itself started.

## Build and develop

```bash
cd integrations/vscode
npm install
npm run compile     # tsc → out/
npm test            # node --test on the compiled tests
npm run package     # vsce → apex-vscode-0.1.0.vsix (artifact only, no publishing)
```

Press `F5` in VS Code to launch the "Extension Development" host, then use the
**APEX** view in the activity bar.

## Limitations (MVP)

- One backend per window (first workspace folder).
- No approval UI for `ASK`-permission tool calls yet — the backend applies its
  own permission policy.
- Cost and context metrics are not surfaced in the status bar yet.
