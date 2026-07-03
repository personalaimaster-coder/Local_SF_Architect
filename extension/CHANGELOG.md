# Change Log

## 0.1.1

- Fix: extension failed to activate (`Cannot find module './impl/format'`),
  which left every command unregistered. The bundler now uses each
  dependency's ESM entry so `jsonc-parser` is bundled correctly.
- Harden activation: commands are registered first and status-bar / MCP-provider
  setup is wrapped so a single failure can no longer block the commands.

## 0.1.0

- Initial release.
- Auto-detect host (VS Code / Cursor) and installed agents (Copilot, Claude Code).
- Install the engine from PyPI via `uv tool install`.
- First-run setup: download embedding model and seed the local knowledge base.
- One-click wiring into GitHub Copilot (native MCP provider API), Cursor
  (`~/.cursor/mcp.json`), and Claude Code (`claude mcp add`).
- Status bar, commands, and a getting-started walkthrough.
