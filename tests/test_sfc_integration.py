"""Merge guardrails for the sf-compress <-> sf-local-architect integration.

Covers:
- both toolsets registered on the single unified server,
- sfc setup/install-skill deliberately NOT exposed there,
- sfc importable in the same environment,
- the real MCP call pathway via the fastmcp in-memory Client (dispatch + serialize),
- the sfc dev-support lifecycle through the server wrappers (on -> run -> stats -> off),
- OFF-gating of sfc_run after an explicit `sfc off` (dormant on opt-out),
- sfc being ON by default (sfc_run executes without an explicit `sfc on`),
- the `sf-architect compress` CLI passthrough.

All tests redirect the audit DB into a temp dir and chdir into a temp cwd, so they
write nothing into the repo (no stray .sfc/ or ~/.sf-architect writes).
"""

from __future__ import annotations

import asyncio
import importlib
import sys

ARCHITECT_TOOLS = {
    "health_echo",
    "query_architect_db",
    "analyze_local_blast_radius",
    "check_governor_limit",
    "generate_architecture_diagram",
    "set_deliverable_preference",
    "score_architecture",
    "sync_latest_patterns",
}

SFC_TOOLS = {
    "sfc_status",
    "sfc_on",
    "sfc_off",
    "sfc_run",
    "sfc_show",
    "sfc_stats",
    "sfc_graph",
}


def _server():
    return importlib.import_module("sf_architect.server")


def _isolate(tmp_path, monkeypatch):
    """Redirect the audit DB into tmp and chdir there so nothing touches the repo."""
    audit = importlib.import_module("sf_architect.obs.audit")
    monkeypatch.setattr(audit, "DB_PATH", tmp_path / "audit.db")
    monkeypatch.chdir(tmp_path)


def _tool_names():
    tools = asyncio.run(_server().mcp.list_tools())
    return {t.name for t in tools}


def test_unified_server_exposes_both_toolsets():
    names = _tool_names()
    assert ARCHITECT_TOOLS.issubset(names), ARCHITECT_TOOLS - names
    assert SFC_TOOLS.issubset(names), SFC_TOOLS - names


def test_setup_tools_not_exposed_on_unified_server():
    names = _tool_names()
    assert "sfc_setup" not in names
    assert "sfc_install_skill" not in names


def test_sfc_is_importable_in_same_env():
    assert importlib.import_module("sfc") is not None


def _client_text(result):
    data = getattr(result, "data", None)
    if isinstance(data, str) and data:
        return data
    content = getattr(result, "content", None) or []
    return "\n".join(getattr(b, "text", "") for b in content) or str(result)


def test_mcp_client_call_pathway(tmp_path, monkeypatch):
    # Exercise the actual MCP protocol path the extension uses: list_tools +
    # call_tool through the fastmcp in-memory client (dispatch + serialization).
    _isolate(tmp_path, monkeypatch)
    from fastmcp import Client

    server = _server()

    async def go():
        async with Client(server.mcp) as client:
            names = {t.name for t in await client.list_tools()}
            assert ARCHITECT_TOOLS.issubset(names)
            assert SFC_TOOLS.issubset(names)
            return _client_text(await client.call_tool("sfc_status", {}))

    assert "ACTIVE" in asyncio.run(go())  # sfc is ON by default


def test_sfc_lifecycle_through_unified_server(tmp_path, monkeypatch):
    # on -> run (pass-through) -> stats -> off, through the server wrappers, proving
    # the delegation + _sfc_text flattening glue works end to end.
    _isolate(tmp_path, monkeypatch)
    server = _server()

    assert "ACTIVE" in server.sfc_status()  # ON by default
    assert "ACTIVE" in server.sfc_on()
    assert "ACTIVE" in server.sfc_status()

    run_out = server.sfc_run([sys.executable, "-c", "print('hello sfc')"])
    assert "hello sfc" in run_out  # pass-through family echoes the child output

    assert isinstance(server.sfc_stats(), str)

    assert "OFF" in server.sfc_off()
    assert "OFF" in server.sfc_status()


def test_sfc_run_refuses_when_off(tmp_path, monkeypatch):
    # After an explicit opt-out (sfc off), sfc_run must not execute the child command.
    _isolate(tmp_path, monkeypatch)
    server = _server()

    assert "OFF" in server.sfc_off()
    out = server.sfc_run([sys.executable, "-c", "print('should-not-run')"])
    assert "should-not-run" not in out
    assert "inactive" in out.lower()


def test_sfc_run_executes_by_default(tmp_path, monkeypatch):
    # ON by default: sfc_run executes without an explicit sfc_on first.
    _isolate(tmp_path, monkeypatch)
    server = _server()

    out = server.sfc_run([sys.executable, "-c", "print('runs-by-default')"])
    assert "runs-by-default" in out


def test_compress_cli_passthrough(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from sf_architect.cli import main

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["compress", "status"])
    assert result.exit_code == 0  # sfc ON by default -> exit 0
    assert "ACTIVE" in result.output
