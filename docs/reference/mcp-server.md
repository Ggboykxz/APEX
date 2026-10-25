# MCP Server (`apex mcp serve`)

APEX exposes its native tools to any [Model Context Protocol](https://modelcontextprotocol.io)
client as a **stdio** server. The server speaks JSON-RPC 2.0 over
newline-delimited messages on `stdin`/`stdout` and implements the contract
defined in [ADR-0006](../adr/ADR-0006-mcp-server-stdio.md).

```bash
apex mcp serve [--cwd PATH] [--allow-tool NAME]...
```

## Client configuration

```json
{
  "mcpServers": {
    "apex": {
      "command": "python",
      "args": ["-m", "apex", "mcp", "serve", "--cwd", "/path/to/project"]
    }
  }
}
```

## Protocol surface

| Method | Behavior |
|--------|----------|
| `initialize` | Returns `protocolVersion` (echoes the client's when recognized), `capabilities.tools`, `serverInfo { name: "apex", version }`. |
| `notifications/initialized` | Accepted, no response. |
| `tools/list` | `{ tools: [{ name, description, inputSchema }] }`, filtered by the active profile. |
| `tools/call` | `{ name, arguments }` → executed through the APEX `ToolExecutor`; returns `{ content: [{ type: "text", text }], isError }`. |
| `ping` | `{}`. |
| batches | JSON-RPC arrays are supported; one array response is emitted per batch. |

Errors follow JSON-RPC: `-32700` parse error, `-32600` invalid request,
`-32601` method not found, `-32602` invalid params (unknown/forbidden tool),
`-32603` internal error. The server never crashes the loop on malformed
input and exits cleanly (code 0) on EOF.

## Tool profile and security

- **Default: read-only.** Read-only tools (`read_file`, `search_in_files`,
  `glob_search`, `get_repo_map`/`repo_map`, `get_git_status`, `git_diff`,
  `get_git_log`, `get_file_tree`, LSP tools, …) are exposed out of the box.
- **Destructive tools are opt-in.** `write_file`, `edit_file`,
  `apply_patch`, `run_command`, git mutations, … are only exposed when
  explicitly allowed. An explicit allow-list **replaces** the read-only
  default (unknown names are filtered against the real registry).

Allow-list sources, merged as a union:

| Source | Shape |
|--------|-------|
| CLI | `apex mcp serve --allow-tool write_file --allow-tool edit_file` |
| Environment | `APEX_MCP_ALLOW_TOOLS=write_file,edit_file` |
| Config | `"mcp": { "server": { "allow_tools": ["write_file"] } }` in `apex.json` |

Every call still runs through the existing `ToolExecutor`, so path
resolution, doom-loop detection, and tool-level guards behave exactly as in
the agent. Trust is the parent process's (stdio); there is no network
listener and no authentication surface.

## Limits

| Limit | Value |
|-------|-------|
| Request size | 1 MiB (rejected with `-32600`) |
| Response size | 1 MiB (truncated with a `…[truncated]` marker) |
| Per-call timeout | 120 s (returns an `isError` result) |
| Stdout | protocol messages only — all logs go to `stderr` |

## Testing

`tests/test_mcp_server.py` drives the server in-process (hermetic
`StringIO` streams) and once end-to-end as a real subprocess
(`python -m apex mcp serve`), asserting: handshake, notification
suppression, batch handling, error codes, the read-only default profile,
`--allow-tool` exposure (including that it replaces the default), tool
call round-trips, oversize rejection, and stdout purity.
