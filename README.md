# Local SF Architect

A local, offline Salesforce architect MCP server for Cursor and Claude Code. It grounds AI-assisted architecture work in searchable patterns, governor limits, and your repo — without sending data to the cloud.

**Status:** Phase 1 scaffold. MCP tools are stubs until implementation begins.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

Optional scraping support (Crawl4AI + Playwright):

```bash
uv sync --extra scrape
```

## CLI

```bash
uv run sf-architect --version
uv run sf-architect doctor
```

## MCP server (Cursor / Claude Code)

Register the server in your MCP config. See [docs/mcp-cursor-setup.md](docs/mcp-cursor-setup.md) for the full snippet.

```bash
uv run sf-architect-mcp
```

## Documentation

- [Analysis & implementation plan](docs/Local-SF-Architect-Analysis-and-Plan.md)
- [Cursor MCP setup](docs/mcp-cursor-setup.md)

## Local data

Runtime state is stored under `~/.sf-architect/` (LanceDB, limits DB, audit logs, config). Nothing in that directory is committed to git.
