# Cursor MCP setup for sf-local-architect

Register the MCP server so Cursor can call `health_echo` and (once implemented) the architect tools.

## Prerequisites

1. Install dependencies from the repo root:

   ```bash
   uv sync
   ```

2. Confirm the server starts:

   ```bash
   uv run sf-architect-mcp
   ```

   Stop with Ctrl+C after verifying it launches without errors.

## Cursor configuration

Add this to `~/.cursor/mcp.json` (user-level) or `.cursor/mcp.json` (project-level).

Replace `cwd` with the absolute path to your clone of this repository.

```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "/Users/manvendrachaturvedi/Desktop/Local Salesforce Architect Engine"
    }
  }
}
```

**Note:** The `cwd` path contains spaces. Keep it as a single JSON string; do not split it across tokens.

## Alternative: installed script

After `uv sync`, you can point Cursor at the venv script directly:

```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "/Users/manvendrachaturvedi/Desktop/Local Salesforce Architect Engine/.venv/bin/sf-architect-mcp",
      "args": []
    }
  }
}
```

## Verify in Cursor

1. Restart Cursor or reload MCP servers.
2. Open the MCP tools panel and confirm `sf-local-architect` is connected.
3. Call `health_echo` with message `"hello"` — expect `sf-local-architect ok: hello`.

## Claude Code

Use the same `command` / `args` / `cwd` tuple in your Claude Code MCP configuration file for this project.
