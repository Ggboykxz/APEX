# APEX — VS Code extension

Thin-client VS Code extension for the APEX backend (`apex serve`). It
implements [ADR-0007](../../docs/adr/ADR-0007-vscode-thin-client.md): **no
agent loop, no provider keys, no tool execution** in the extension — all
intelligence stays in the single Python backend.

## Build

```bash
cd integrations/vscode
npm install
npm run compile     # tsc → out/
npm test            # node --test on the compiled tests
npm run package     # vsce → apex-vscode-0.1.0.vsix (artifact only, no publishing)
```

### Development (F5)

1. Open this folder in VS Code.
2. Press F5 (launch config "Extension Development").
3. In the dev host, run `apex serve --cwd <a repo>` (or let the extension
   auto-start it) and use the **APEX** view in the activity bar.

## Settings

| Key | Default | Description |
|-----|---------|-------------|
| `apex.serverUrl` | `http://127.0.0.1:8765` | Base URL of the APEX backend. |
| `apex.autoStart` | `true` | Start `apex serve --cwd <workspace>` when no backend responds. |
| `apex.defaultModel` | `""` | Default model for new sessions. |

## Commands

| Command | Description |
|---------|-------------|
| `apex.chat` | Focus the APEX chat view. |
| `apex.newSession` | Reset the chat and start a fresh session. |
| `apex.explainSelection` | Send the current selection to APEX for an explanation (context menu). |
| `apex.fixSelection` | Send the current selection to APEX for a fix (context menu). |
| `apex.reviewDiff` | Open the working-tree unified diff in a read-only editor. |
| `apex.setApiKey` | Store/clear the backend API key in VS Code SecretStorage. |
| `apex.restartServer` | Stop a backend the extension started and reconnect. |

## Security model

- The backend API key lives only in VS Code **SecretStorage**; it is sent as
  an `Authorization: Bearer …` header and never appears in settings, logs,
  or the webview.
- The chat webview runs with a strict CSP: no remote scripts/styles, no
  inline scripts except the nonce-tagged bootstrap. It is pure
  presentation — every backend call is made by the extension host.
- Auto-start only ever launches `apex serve` for the first workspace folder
  and only kills processes the extension itself started.

## Tests

`npm test` compiles `test/*.test.ts` and runs them with `node --test`
(18+ cases): SSE parser (chunk splits, multi-line data, CRLF, comments),
chat reducer (deltas, errors, reset/session isolation), HTTP client
(auth header, URL construction, health failure, stream deltas/error frames,
diff, session creation) with a mocked global `fetch`, and the pure server
URL helpers. No VS Code instance or network is required.

## Limitations (MVP)

- One backend per window (first workspace folder).
- No approval UI for `ASK`-permission tool calls yet — the backend applies
  its own permission policy.
- Cost/context metrics are not surfaced in the status bar yet.
