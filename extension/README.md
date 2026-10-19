# Local SF Architect (VS Code extension)

One-click installer and configurator for the **Local SF Architect** engine — a
fully local, offline Model Context Protocol (MCP) server that gives your AI
assistant deterministic Salesforce architecture tools (governor-limit math,
Apex blast-radius analysis, architecture pattern search, diagrams, scoring, and
lint).

It also bundles **sf-compress** (`sfc`) — a dev-support output compressor that
wraps your `sf` CLI commands, stores the full raw output on disk, and feeds your
agent only a compressed view (errors, failures, summaries, counts). A 200k-token
deploy report or debug log no longer floods the context window, and nothing is
lost — every output ends with an id you can expand on demand.

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
- Internet access **once** for the engine install + the ~210 MB embedding and reranker models

## What it does on first run

1. Detects your host (VS Code vs Cursor) and installed agents.
2. Installs the engine: `uv tool install --upgrade sf-local-architect`.
3. Downloads the embedding model and seeds the local knowledge base.
4. Wires the engine into every detected agent (existing configs are backed up).
5. Installs the `local-sf-architect` **and** `sf-compress` Agent Skills into the
   workspace so your agent reliably routes Salesforce questions through the
   engine's tools and compresses verbose `sf` CLI output.

After an extension update, existing installs automatically upgrade the engine and
refresh the skill once per release — no manual steps needed.

After setup, open your AI chat in **Agent mode** and ask questions like:

- *"What breaks if I refactor AccountService.cls?"*
- *"Will fetching 45,000 rows in a loop hit governor limits?"*
- *"Score the architecture health of this project."*
- *"Deploy force-app and show me only the errors."* (routed through sf-compress)

## Commands

All under the **Local SF Architect** category in the Command Palette:

- Run Setup (Install + Configure)
- Install / Update Engine
- Download Model + Seed Knowledge Base
- Configure GitHub Copilot / VS Code · Cursor · Claude Code · All Detected Agents
- Rebuild Local Stores
- Show Logs · Show Status

## Dev-support output compression (sf-compress / `sfc`)

Verbose Salesforce CLI output is highly compressible — deploy reports, `retrieve
preview` tables, `--json` payloads, and Apex debug logs shrink dramatically while
keeping every error and summary. The bundled **sf-compress** engine is exposed
three ways, all through this one extension/engine install:

- **MCP tools** on the same `sf-local-architect` server: `sfc_status`, `sfc_on`,
  `sfc_off`, `sfc_run`, `sfc_show`, `sfc_stats`, `sfc_graph`. Your agent calls
  these automatically when it recognizes dev-support work.
- **CLI:** `sfc <args>` (standalone) or `sf-architect compress <args>` (alias),
  e.g. `sfc run -- sf project deploy start -d force-app`.
- **Agent Skill:** `sf-compress`, installed into your workspace during setup
  alongside `local-sf-architect`.

**On by default.** sf-compress is active out of the box for dev-support loops
(deploy/validate, test runs, debug logs, retrieve/preview, data queries). It
stores the full raw output under a git-ignored `.sfc/` folder and returns an id
you can expand later (`sfc show <id>`). During analysis/architecture work — where
full detail matters — turn it off per project with `sfc off` (or the `sfc_off`
tool); `sfc run` then stays fully dormant.

> sf-compress has no extra VS Code commands or settings of its own yet — it is
> driven by your AI agent (MCP tools) and the `sfc` CLI. State is project-local
> under `.sfc/`.

## Settings

- `sfArchitect.enginePackage` — PyPI package (default `sf-local-architect`)
- `sfArchitect.autoSetupOnActivate` — run setup automatically on first activation
- `sfArchitect.autoConfigureAgents` — wire detected agents without per-agent prompts
- `sfArchitect.autoDownloadModel` — download the embedding model during setup
- `sfArchitect.uvPath` — absolute path to `uv` (empty = auto-detect)

## Privacy

The engine runs locally over stdio. Your code never leaves your machine. The
only network calls are the one-time PyPI install and embedding-model download.
sf-compress is local too — it executes your `sf` commands and stores their output
on your machine only; it adds no network calls.
