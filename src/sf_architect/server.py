"""FastMCP server entrypoint."""

from __future__ import annotations

from fastmcp import FastMCP

from sf_architect.bootstrap import ensure_data_dirs

mcp = FastMCP("sf-local-architect")


@mcp.tool
def health_echo(message: str) -> str:
    """Echo a message to verify the MCP server is running."""
    return f"sf-local-architect ok: {message}"


def main() -> None:
    ensure_data_dirs()
    mcp.run()


if __name__ == "__main__":
    main()
