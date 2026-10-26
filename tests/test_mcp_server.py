"""Tests for the MCP stdio server (ADR-0006).

Most protocol behavior is exercised in-process through ``serve`` with
``StringIO`` streams (fast, hermetic). One end-to-end subprocess test
spawns ``python -m apex mcp serve`` to validate the CLI wiring, stdout
purity, and exit behavior.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apex.mcp_server import (
    MAX_REQUEST_BYTES,
    READ_ONLY_TOOLS,
    resolve_allow_tools,
    serve,
)

PY = sys.executable


# ── in-process helpers ─────────────────────────────────────


def run_lines(
    input_lines: list[str],
    cwd: Path | str = ".",
    allow_tools: list[str] | None = None,
):
    """Feed lines through ``serve`` and return (exit_code, parsed responses)."""
    inp = io.StringIO("\n".join(input_lines) + "\n")
    out = io.StringIO()
    rc = serve(cwd=cwd, allow_tools=allow_tools, stdin=inp, stdout=out)
    responses = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
    return rc, responses


def req(req_id: int, method: str, params: dict | None = None) -> str:
    message: dict = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        message["params"] = params
    return json.dumps(message)


INIT = req(
    1,
    "initialize",
    {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0.0"},
    },
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello mcp\n", encoding="utf-8")
    return tmp_path


# ── handshake & protocol (in-process) ──────────────────────


def test_initialize_handshake(workspace: Path) -> None:
    rc, responses = run_lines([INIT], cwd=workspace)
    assert rc == 0
    assert len(responses) == 1
    result = responses[0]["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["capabilities"]["tools"]["listChanged"] is False
    assert result["serverInfo"]["name"] == "apex"
    assert isinstance(result["serverInfo"]["version"], str) and result["serverInfo"]["version"]


def test_notification_produces_no_response(workspace: Path) -> None:
    lines = [
        INIT,
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        req(7, "ping"),
    ]
    rc, responses = run_lines(lines, cwd=workspace)
    assert rc == 0
    assert len(responses) == 2
    assert responses[1]["result"] == {}
    assert responses[1]["id"] == 7


def test_ping(workspace: Path) -> None:
    rc, responses = run_lines([INIT, req(5, "ping")], cwd=workspace)
    assert responses[-1]["result"] == {}
    assert responses[-1]["id"] == 5


def test_unknown_method_returns_32601(workspace: Path) -> None:
    rc, responses = run_lines([INIT, req(9, "resources/list")], cwd=workspace)
    assert responses[-1]["error"]["code"] == -32601


def test_malformed_json_returns_32700_and_survives(workspace: Path) -> None:
    lines = [INIT, "{not json", req(10, "ping")]
    rc, responses = run_lines(lines, cwd=workspace)
    assert responses[1]["error"]["code"] == -32700
    assert responses[2]["result"] == {}


def test_non_object_request_returns_32600(workspace: Path) -> None:
    rc, responses = run_lines([INIT, '"just a string"'], cwd=workspace)
    assert responses[-1]["error"]["code"] == -32600


def test_batch_requests(workspace: Path) -> None:
    batch = json.dumps(
        [
            {"jsonrpc": "2.0", "id": 11, "method": "ping"},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 13, "method": "no_such_method"},
        ]
    )
    rc, responses = run_lines([INIT, batch], cwd=workspace)
    assert len(responses) == 2
    last = responses[-1]
    assert isinstance(last, list)
    by_id = {r["id"]: r for r in last}
    assert by_id[11]["result"] == {}
    assert by_id[13]["error"]["code"] == -32601


def test_oversize_request_rejected(workspace: Path) -> None:
    big = "x" * (MAX_REQUEST_BYTES + 10)
    rc, responses = run_lines([INIT, big, req(20, "ping")], cwd=workspace)
    assert responses[1]["error"]["code"] == -32600
    assert "1 MiB" in responses[1]["error"]["message"]
    assert responses[2]["result"] == {}


# ── tool profile (in-process) ──────────────────────────────


def test_default_profile_is_read_only(workspace: Path) -> None:
    rc, responses = run_lines([INIT, req(2, "tools/list")], cwd=workspace)
    tools = responses[-1]["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "read_file" in names
    assert "repo_map" in names
    assert names <= READ_ONLY_TOOLS
    assert "write_file" not in names
    assert "apply_patch" not in names
    assert "run_command" not in names


def test_tool_schema_shape(workspace: Path) -> None:
    rc, responses = run_lines([INIT, req(2, "tools/list")], cwd=workspace)
    tools = responses[-1]["result"]["tools"]
    read = next(t for t in tools if t["name"] == "read_file")
    assert isinstance(read["description"], str) and read["description"]
    assert read["inputSchema"]["type"] == "object"
    assert "path" in read["inputSchema"]["properties"]


def test_call_read_file(workspace: Path) -> None:
    call = req(3, "tools/call", {"name": "read_file", "arguments": {"path": "hello.txt"}})
    rc, responses = run_lines([INIT, call], cwd=workspace)
    result = responses[-1]["result"]
    assert result["isError"] is False
    assert "hello mcp" in result["content"][0]["text"]


def test_call_read_file_absolute_path_error(workspace: Path) -> None:
    outside = str(Path.home() / "unrelated.txt")
    call = req(3, "tools/call", {"name": "read_file", "arguments": {"path": outside}})
    rc, responses = run_lines([INIT, call], cwd=workspace)
    assert responses[-1]["result"]["isError"] is True


def test_unknown_tool_returns_32602(workspace: Path) -> None:
    call = req(3, "tools/call", {"name": "does_not_exist", "arguments": {}})
    rc, responses = run_lines([INIT, call], cwd=workspace)
    assert responses[-1]["error"]["code"] == -32602


def test_disallowed_tool_returns_32602(workspace: Path) -> None:
    call = req(
        3,
        "tools/call",
        {"name": "write_file", "arguments": {"path": "x.txt", "content": "x"}},
    )
    rc, responses = run_lines([INIT, call], cwd=workspace)
    assert responses[-1]["error"]["code"] == -32602
    assert "not allowed" in responses[-1]["error"]["message"]
    assert not (workspace / "x.txt").exists()


def test_invalid_arguments_returns_32602(workspace: Path) -> None:
    call = req(3, "tools/call", {"name": "read_file", "arguments": "not-an-object"})
    rc, responses = run_lines([INIT, call], cwd=workspace)
    assert responses[-1]["error"]["code"] == -32602


def test_allow_tool_cli_exposes_destructive_tool(workspace: Path) -> None:
    call = req(
        3,
        "tools/call",
        {"name": "write_file", "arguments": {"path": "created.txt", "content": "made by test\n"}},
    )
    rc, responses = run_lines(
        [INIT, req(2, "tools/list"), call], cwd=workspace, allow_tools=["write_file"]
    )
    names = {t["name"] for t in responses[1]["result"]["tools"]}
    assert "write_file" in names
    assert "read_file" not in names
    result = responses[2]["result"]
    assert result["isError"] is False
    assert (workspace / "created.txt").read_text(encoding="utf-8") == "made by test\n"


def test_allow_tool_unknown_name_filtered(workspace: Path) -> None:
    rc, responses = run_lines(
        [INIT, req(2, "tools/list")], cwd=workspace, allow_tools=["not_a_real_tool"]
    )
    assert responses[-1]["result"]["tools"] == []


def test_tool_error_result_is_error_flag(workspace: Path) -> None:
    call = req(3, "tools/call", {"name": "read_file", "arguments": {"path": "missing.txt"}})
    rc, responses = run_lines([INIT, call], cwd=workspace)
    result = responses[-1]["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("ERROR:")


# ── subprocess end-to-end (CLI wiring) ─────────────────────


def test_subprocess_end_to_end(workspace: Path) -> None:
    env = dict(os.environ)
    env.pop("APEX_MCP_ALLOW_TOOLS", None)
    env["APEX_CONFIG_CONTENT"] = json.dumps({"autoupdate": False})
    proc = subprocess.Popen(
        [PY, "-m", "apex", "mcp", "serve", "--cwd", str(workspace)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        proc.stdin.write(INIT + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line != "", "server produced no initialize response"
        response = json.loads(line)  # raises if stdout is contaminated
        assert response["id"] == 1
        assert response["result"]["serverInfo"]["name"] == "apex"
    finally:
        proc.stdin.close()
        assert proc.wait(timeout=120) == 0


# ── pure helpers ───────────────────────────────────────────


def test_resolve_allow_tools_union() -> None:
    allowed = resolve_allow_tools(
        cli=["write_file", "write_file"],
        env="read_file, glob_search, ,apply_patch",
        config={"server": {"allow_tools": ["repo_map", 42]}},
    )
    assert allowed == {"write_file", "read_file", "glob_search", "apply_patch", "repo_map"}


def test_resolve_allow_tools_empty() -> None:
    assert resolve_allow_tools(None, None, None) == set()
    assert resolve_allow_tools([], "", {}) == set()
