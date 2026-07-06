# Configure your agents

The extension detects which AI agents you have and wires the engine into each:

- **GitHub Copilot / VS Code** — registered natively via the MCP provider API.
- **Cursor** — written to `~/.cursor/mcp.json`.
- **Claude Code** — registered with `claude mcp add --scope user`.

Existing configurations are preserved and backed up before any change.

Then open your AI chat in Agent mode and ask, e.g. *"What breaks if I refactor
AccountService.cls?"*
