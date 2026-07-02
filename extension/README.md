# Local SF Architect (VS Code extension)

One-click installer and configurator for the **Local SF Architect** engine — a
fully local, offline Model Context Protocol (MCP) server that gives your AI
assistant deterministic Salesforce architecture tools (governor-limit math,
Apex blast-radius analysis, architecture pattern search, diagrams, scoring, and
lint).

This extension does **not** replace the engine — it installs it from PyPI and
wires it into whichever AI agent you use:

| Agent | How it is wired |
|---|---|
| GitHub Copilot / VS Code | Native MCP provider API (`registerMcpServerDefinitionProvider`, VS Code 1.101+); falls back to `.vscode/mcp.json` |
| Cursor | Merged into `~/.cursor/mcp.json` (`mcpServers`) |
| Claude Code | `claude mcp add --scope user` (falls back to `~/.claude.json`) |

## Requirements

- VS Code (or Cursor) **1.101+**
- [`uv`](https://docs.astral.sh/uv/) on your machine (the extension guides you if it is missing)
- Internet access **once** for the engine install + the ~130 MB embedding model

## What it does on first run

1. Detects your host (VS Code vs Cursor) and installed agents.
2. Installs the engine: `uv tool install --upgrade sf-local-architect`.
3. Downloads the embedding model and seeds the local knowledge base.
4. Wires the engine into every detected agent (existing configs are backed up).

After setup, open your AI chat in **Agent mode** and ask questions like:

- *"What breaks if I refactor AccountService.cls?"*
- *"Will fetching 45,000 rows in a loop hit governor limits?"*
- *"Score the architecture health of this project."*

## Commands

All under the **Local SF Architect** category in the Command Palette:

- Run Setup (Install + Configure)
- Install / Update Engine
- Download Model + Seed Knowledge Base
- Configure GitHub Copilot / VS Code · Cursor · Claude Code · All Detected Agents
- Rebuild Local Stores
- Show Logs · Show Status

## Settings

- `sfArchitect.enginePackage` — PyPI package (default `sf-local-architect`)
- `sfArchitect.autoSetupOnActivate` — run setup automatically on first activation
- `sfArchitect.autoConfigureAgents` — wire detected agents without per-agent prompts
- `sfArchitect.autoDownloadModel` — download the embedding model during setup
- `sfArchitect.uvPath` — absolute path to `uv` (empty = auto-detect)

## Privacy

The engine runs locally over stdio. Your code never leaves your machine. The
only network calls are the one-time PyPI install and embedding-model download.

> Note: a marketplace `icon.png` (128×128+) should be added under `media/` and
> referenced from `package.json` before publishing.
