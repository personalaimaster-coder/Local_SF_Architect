"""Smoke tests for the MCP server scaffold."""

import asyncio

from sf_architect import __version__
from sf_architect.server import health_echo, mcp


def test_version() -> None:
    assert __version__ == "0.2.0"


def test_health_echo() -> None:
    assert health_echo("ping") == "sf-local-architect ok: ping"


def test_mcp_has_health_echo_tool() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "health_echo" in names
