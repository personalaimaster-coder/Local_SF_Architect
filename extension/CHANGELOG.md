# Change Log

## 0.3.0

- Bundles the **sf-compress** (`sfc`) dev-support compressor into the single
  `sf-local-architect` engine. The unified MCP server now also exposes
  `sfc_status` / `sfc_on` / `sfc_off` / `sfc_run` / `sfc_show` / `sfc_stats` /
  `sfc_graph`, a `sf-architect compress …` CLI passthrough, a standalone `sfc`
  console script, and the `sf-compress` Agent Skill (installed alongside
  `local-sf-architect` during setup). Pairs with engine 0.4.0 on PyPI.
- **sfc is now ON by default** — dev-support output compression works out of the
  box; run `sfc off` (or the `sfc_off` tool) to make it fully dormant per project.
- Existing installs: on activation after this extension update, the catch-up sync
  upgrades the engine (`uv tool install --upgrade`) once per release and refreshes
  the skills into an open Salesforce workspace. Reload the editor afterward so the
  MCP server restarts and surfaces the new `sfc_*` tools. No knowledge-base rebuild
  or data migration is required.

## 0.2.0

- Installs the bundled `local-sf-architect` Agent Skill into detected agents
  (`.cursor/skills/`, `.claude/skills/`, `.vibes/skills/`) and writes an always-on
  architect rule during setup, so Salesforce questions reliably route through the
  engine's MCP tools. Pairs with engine 0.3.0 on PyPI.
- Existing installs: on activation after an extension update, the engine is upgraded
  (`uv tool install --upgrade`) once per release and the skill is refreshed into an
  open Salesforce workspace — no manual steps required.

## 0.1.2

- More reliable engine-installed detection: `uv tool list` output is parsed and
  matched by normalized distribution name instead of a loose substring test.
- Activate on Salesforce projects (`workspaceContains:**/sfdx-project.json`).
- Docs/UX updated for the embedding + reranker models (~210 MB total) and the
  expanded pattern knowledge base. Pairs with engine 0.2.1 on PyPI.

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
