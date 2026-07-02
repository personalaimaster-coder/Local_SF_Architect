# Local SF Architect Engine

> A fully local, offline AI assistant for Salesforce architects — runs inside Cursor or Claude Code, never sends your code to the cloud.

---

## What is this? (Simple explanation)

If you build on Salesforce, you know the pain: governor limits that are easy to hit, complex Apex class dependencies that break when you change one file, hundreds of architecture patterns to keep in your head, and AI tools that send your proprietary code to third-party servers.

**Local SF Architect Engine** solves all of that locally, on your laptop.

It is a **Model Context Protocol (MCP) server** — think of it as a plugin that plugs into your AI-powered IDE (Cursor or Claude Code) and gives the AI a set of specialized Salesforce tools to call. The AI stops guessing and instead calls our local engines to get deterministic, grounded answers.

### What it does

| Problem | What this engine does |
|---|---|
| "Will this code hit governor limits?" | Checks exact Salesforce API limits (v62.0) and tells you headroom/breach with math, not guesses |
| "What breaks if I change this Apex class?" | Parses your whole repo and computes an immediate + transitive blast radius |
| "What is the best pattern for this use case?" | Searches a curated local knowledge base of Salesforce architecture patterns using semantic (meaning-based) search |
| "Draw me an architecture diagram" | Generates Mermaid or draw.io diagrams from your actual codebase |
| "How healthy is this architecture?" | Scores the architecture across six pillars (security, performance, scalability, maintainability, reliability, cost) |
| "Lint my Apex for architectural issues" | Flags anti-patterns (deep nesting, SOQL in loops, missing bulkification) with exit codes for CI |

### What it does NOT do

- It does **not** send your code to any cloud service
- It does **not** require a GPU or any special hardware
- It does **not** phone home — the only network call is the one-time embedding model download (~130 MB) from Hugging Face on first run
- It does **not** connect to your Salesforce org

---

## Easiest setup — the VS Code / Cursor extension

If you use **VS Code (with GitHub Copilot)** or **Cursor**, the simplest path is the
companion extension. It installs the engine for you and wires it into your AI agent
in one click — no manual `mcp.json` editing.

1. Install **Local SF Architect** from the VS Code Marketplace (VS Code/Copilot) or
   Open VSX (Cursor).
2. On first activation it offers to: install the engine via `uv`, download the model,
   seed the knowledge base, and configure every detected agent (Copilot, Cursor, and
   the Claude Code CLI if present).
3. Open your AI chat in **Agent mode** and start asking questions.

The extension lives in [`extension/`](extension/); see [`extension/README.md`](extension/README.md)
for details. It still relies on `uv` being installed and needs internet once (PyPI install
plus the ~130 MB model). Prefer to set things up by hand, or using Claude Code only? The
manual MCP steps below still work exactly as before.

---

## Architecture overview

```
Your IDE (Cursor / Claude Code)
        │
        │  MCP / stdio JSON-RPC  (no TCP port, no auth surface)
        ▼
┌─────────────────────────────────┐
│        sf-architect-mcp         │  ← this package, runs on your laptop
│                                 │
│  Router → Patterns engine       │  semantic search (LanceDB + bge-small embeddings)
│         → Limits engine         │  deterministic math (SQLite)
│         → Dep-graph engine      │  Apex + XML parsing (tree-sitter + lxml)
│         → Scoring engine        │  per-pillar rubric
│         → Diagram engine        │  Mermaid / draw.io
│         → Lint engine           │  architectural infractions
└─────────────────────────────────┘
        │
        ▼
 ~/.sf-architect/           ← all state, never committed to git
   data/lance/              vector store (patterns)
   limits.db                SQLite (governor limits)
   logs/audit.db            SQLite (one row per tool call)
   config.yaml              preferences + scrape allowlist
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | 3.13 works fine too |
| [uv](https://docs.astral.sh/uv/) | any recent | replaces pip + virtualenv in one tool |
| Git | any | to clone this repo |

> **uv** is the only tool you need to install manually. Everything else is managed by uv.

### Install uv (if you don't have it)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Installation (step by step)

### Step 1 — Clone the repo

```bash
git clone https://github.com/personalaimaster-coder/Local_SF_Architect.git
cd "Local SF Architect Engine"
```

### Step 2 — Install dependencies

```bash
uv sync
```

This creates a `.venv/` in the project folder and installs all core dependencies. Takes about 60 seconds on first run.

> **Optional:** If you want the `sync_latest_patterns` scraping feature (downloads Chromium — several hundred MB):
> ```bash
> uv sync --extra scrape
> ```

### Step 3 — Check your environment

```bash
uv run sf-architect doctor
```

This verifies Python version, required packages, and local store paths. You should see a green "all checks passed" message.

### Step 4 — Download the embedding model (one-time, ~130 MB)

```bash
uv run sf-architect doctor --download
```

This pre-downloads the `bge-small-en-v1.5` model from Hugging Face. After this step, **everything runs fully offline** — no internet needed, ever. Do this before going air-gapped.

### Step 5 — Seed the knowledge base

```bash
uv run sf-architect seed
```

This loads:
- **Governor limits** (`data/limits_seed.yaml` → `~/.sf-architect/limits.db`) — 50+ Salesforce API limits for v62.0
- **Architecture patterns** (`data/patterns_seed.yaml` → `~/.sf-architect/data/lance/`) — curated best-practice patterns with semantic embeddings

### Step 6 — Verify with a quick test

```bash
uv run sf-architect test
```

All tests should pass. You are ready to go.

---

## Connecting to Cursor (MCP setup)

### Step 1 — Get the path to your virtual environment

```bash
uv run which python
# example output: /Users/yourname/path/to/project/.venv/bin/python
```

### Step 2 — Add the server to Cursor's MCP config

Open `~/.cursor/mcp.json` (create it if it doesn't exist) and add:

```json
{
  "mcpServers": {
    "sf-architect": {
      "command": "/Users/yourname/path/to/project/.venv/bin/python",
      "args": ["-m", "sf_architect.server"],
      "cwd": "/Users/yourname/path/to/project"
    }
  }
}
```

Replace the paths with your actual paths from Step 1.

### Step 3 — Restart Cursor

Open Cursor → Settings → MCP. You should see `sf-architect` listed with a green dot. The server is live.

> See [`docs/mcp-cursor-setup.md`](docs/mcp-cursor-setup.md) for a full annotated snippet and Claude Code setup.

---

## Using the CLI

All commands are run with `uv run sf-architect <command>`.

```bash
# Check your environment
uv run sf-architect doctor

# (Optional) pre-download the embedding model before going offline
uv run sf-architect doctor --download

# Load limits + seed patterns into local stores
uv run sf-architect seed

# Lint a Salesforce DX project for architectural issues
# Returns exit code 1 if violations found (useful in CI)
uv run sf-architect lint path/to/your/sfdx-project

# Run the full test suite
uv run sf-architect test

# Remove stale/superseded vectors from the pattern store
uv run sf-architect gc

# Drop and fully rebuild all local stores (use after schema changes)
uv run sf-architect rebuild

# Print version
uv run sf-architect --version
```

---

## MCP tools (what the AI can call)

Once the MCP server is running in Cursor, the AI has access to these tools. You don't call them directly — just ask the AI a question and it uses the right tool automatically.

| Tool | What it does | Example prompt |
|---|---|---|
| `query_architect_db` | Semantic search over local architecture patterns | *"What is the best pattern for async processing in Salesforce?"* |
| `check_governor_limit` | Exact headroom / breach math for any governor limit | *"I'm fetching 45,000 rows in a loop. Will I hit the SOQL limit?"* |
| `analyze_local_blast_radius` | What breaks if you change a file (immediate + transitive) | *"What will break if I refactor AccountService.cls?"* |
| `generate_architecture_diagram` | Writes a Mermaid `.md` or draw.io `.drawio` file | *"Draw me the dependency graph for the Order subsystem"* |
| `set_deliverable_preference` | Persist your preferred diagram format (Mermaid or draw.io) | *"Always generate draw.io diagrams from now on"* |
| `score_architecture` | Six-pillar scorecard + risk score with explanations | *"Score the architecture health of this project"* |
| `sync_latest_patterns` | Opt-in: scrape an allowlisted URL and store new patterns | Disabled until you add a domain to `scrape_allowlist` in `config.yaml` |

Every tool returns a common envelope:

```json
{
  "ok": true,
  "tool": "check_governor_limit",
  "data": { ... },
  "confidence": 0.94,
  "warnings": [],
  "error": null
}
```

---

## Local data & privacy

All runtime data lives under `~/.sf-architect/` and is **never committed to git**:

```
~/.sf-architect/
  config.yaml          your preferences + scrape allowlist (empty by default)
  data/lance/          vector store — patterns + embeddings
  limits.db            compiled governor limits (SQLite)
  logs/audit.db        one row per tool call (SQLite) — local only
  meta.json            schema version + embedding model record
```

### Schema migration

If you ever change the embedding model or get a schema mismatch error, the safe recovery is:

```bash
uv run sf-architect rebuild
```

This drops and rebuilds all local stores from the seed files.

---

## Security & privacy model

- **No outbound network calls** at runtime — enforced by a test that will fail if any tool makes an unexpected network request
- **Scraping is disabled by default** — `scrape_allowlist` in `config.yaml` is empty; the `sync_latest_patterns` tool is a no-op until you explicitly add a domain
- **Scraped content is sandboxed** — runs through a sanitizer (strips scripts, zero-width chars, hidden elements) and a prompt-injection guard before storage; labeled as "untrusted reference data" in all responses
- **stdio transport only** — no TCP port, no auth surface; the IDE spawns the server as a child process
- **Your code never leaves your machine**

---

## Running the tests

```bash
# Full test suite
uv run pytest

# Or via the CLI alias
uv run sf-architect test

# Specific test file
uv run pytest tests/test_limits.py -v
```

The test suite covers:
- Governor limits engine (exact math)
- Pattern retrieval (golden file regression)
- Dependency graph (blast radius)
- Mermaid + draw.io diagram generation
- Security controls (no-network, guard, sanitizer, allowlist)
- Scoring, ranking, overrides, caching, locking, versioning

---

## Project structure

```
.
├── src/sf_architect/
│   ├── cli.py                  # sf-architect CLI entry point
│   ├── server.py               # MCP server + tool registration
│   ├── bootstrap.py            # first-run directory + config setup
│   ├── engines/
│   │   ├── router.py           # intent detection → route to engine
│   │   ├── limits.py           # governor limits engine (SQLite)
│   │   ├── patterns.py         # semantic search engine (LanceDB)
│   │   ├── depgraph.py         # blast-radius / dependency graph
│   │   └── scoring.py          # architecture scorecard
│   ├── ingest/
│   │   ├── chunk.py            # text chunking
│   │   ├── embed.py            # embedding via fastembed
│   │   └── scraper.py          # opt-in web scraping (Crawl4AI)
│   ├── diagrams/
│   │   ├── mermaid.py          # Mermaid diagram generator
│   │   ├── drawio.py           # draw.io diagram generator
│   │   └── render.py           # shared render logic
│   ├── memory/
│   │   ├── persona.py          # architect persona + style preferences
│   │   ├── overrides.py        # team rules (banned/preferred patterns)
│   │   ├── env_context.py      # environment context (org type, team size)
│   │   └── ranking.py          # source trust ranking
│   ├── security/
│   │   ├── allowlist.py        # domain allowlist for scraping
│   │   ├── guard.py            # prompt-injection guard
│   │   └── sanitize.py         # content sanitizer
│   ├── obs/
│   │   └── audit.py            # audit log (one row per tool call)
│   ├── cache.py                # response caching
│   ├── confidence.py           # confidence scoring
│   ├── contracts.py            # Pydantic response envelope + contracts
│   ├── lint.py                 # architectural lint rules
│   ├── locking.py              # single-writer lock for SQLite/LanceDB
│   └── rerank.py               # result reranking
├── data/
│   ├── limits_seed.yaml        # curated Salesforce governor limits (v62.0)
│   └── patterns_seed.yaml      # seed architecture patterns + embeddings
├── tests/                      # full test suite
├── .vscode/
│   └── mcp.json                # VS Code MCP config (GitHub Copilot Agent mode)
├── docs/                       # detailed design docs
│   ├── mcp-cursor-setup.md     # Cursor + Claude Code MCP config guide
│   ├── vscode-setup.md         # VS Code + GitHub Copilot setup guide
│   ├── Tech-Stack.md           # full tech stack with versions + rationale
│   ├── Implementation-Plan.md  # phase-by-phase build playbook
│   └── Local-SF-Architect-Analysis-and-Plan.md
├── pyproject.toml              # package config + dependencies
└── uv.lock                     # pinned dependency lockfile
```

---

## Detailed documentation

| Doc | What it covers |
|---|---|
| [`docs/mcp-cursor-setup.md`](docs/mcp-cursor-setup.md) | Full Cursor + Claude Code MCP config snippets |
| [`docs/vscode-setup.md`](docs/vscode-setup.md) | VS Code + GitHub Copilot Agent mode setup (VS Code 1.99+) |
| [`docs/Tech-Stack.md`](docs/Tech-Stack.md) | Every dependency, version, license, and the reason it was chosen |
| [`docs/Implementation-Plan.md`](docs/Implementation-Plan.md) | Phase-by-phase build playbook (Phases 0–6.5 complete) |
| [`docs/Local-SF-Architect-Analysis-and-Plan.md`](docs/Local-SF-Architect-Analysis-and-Plan.md) | Full analysis, gap list, and architecture decisions |

---

## What's been built (implementation status)

| Phase | What it added | Status |
|---|---|---|
| 0 — Foundation | Repo scaffold, installable package, MCP handshake | ✅ Complete |
| 1 — MVP core loop | Patterns engine, limits engine, response envelope | ✅ Complete |
| 1.5 — Trust layer | Source trust ranking, confidence scoring, overrides | ✅ Complete |
| 2 — Repo intelligence | Dependency graph, blast-radius analysis, Apex + XML parsing | ✅ Complete |
| Gate — Security + Versioning | Sanitizer, injection guard, domain allowlist, schema versioning, locking | ✅ Complete |
| 3 — Scraping / ingestion | Opt-in Crawl4AI scraper, chunker, embedder, versioned upsert | ✅ Complete |
| 4 — Persona & memory | Architect persona, env context, team overrides, result reranking | ✅ Complete |
| 5 — Diagrams | Mermaid + draw.io generation, deliverable preference | ✅ Complete |
| 6 — Observability & lint | Audit log, architectural lint rules, CI-ready exit codes | ✅ Complete |
| 6.5 — Architecture scoring | Six-pillar scorecard, risk score, caching | ✅ Complete |
| 7 — Hardening & CI | GitHub Actions CI, full test suite, packaging | 🔄 In progress |

---

## Contributing

1. Fork the repo and create a feature branch
2. `uv sync` to install dependencies
3. Make your changes
4. `uv run pytest` — all tests must pass
5. `uv run ruff check src/ tests/` — no lint errors
6. Open a pull request

---

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
