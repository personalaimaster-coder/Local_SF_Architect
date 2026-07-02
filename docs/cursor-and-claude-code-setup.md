# Complete Setup Guide — Cursor & Claude Code

> **Local SF Architect Engine** — a fully local, offline AI assistant for Salesforce architects.  
> This guide covers every step to get the engine running inside **Cursor** or **Claude Code** on macOS, Windows, and Linux.

> **Fastest path for Cursor — install the extension.** The [`Local SF Architect` extension](../extension/README.md) (install from Open VSX) installs the engine and writes your `~/.cursor/mcp.json` automatically. If the Claude Code CLI is present, it also runs `claude mcp add` for you. The manual steps below remain available for full control.

---

## Table of Contents

1. [What You Are Setting Up](#1-what-you-are-setting-up)
2. [System Requirements](#2-system-requirements)
3. [Install Prerequisites](#3-install-prerequisites)
   - [3.1 Install Git](#31-install-git)
   - [3.2 Install Python 3.12+](#32-install-python-312)
   - [3.3 Install uv (package manager)](#33-install-uv-package-manager)
   - [3.4 Install Cursor or Claude Code](#34-install-cursor-or-claude-code)
4. [Get the Project](#4-get-the-project)
5. [Install Python Dependencies](#5-install-python-dependencies)
6. [First-Time Local Setup (run once per machine)](#6-first-time-local-setup-run-once-per-machine)
   - [6a. Health check](#6a-health-check)
   - [6b. Download the embedding model](#6b-download-the-embedding-model)
   - [6c. Seed the knowledge base](#6c-seed-the-knowledge-base)
   - [6d. Run the test suite](#6d-run-the-test-suite)
   - [6e. Confirm the MCP server starts](#6e-confirm-the-mcp-server-starts)
7. [Connect to Cursor](#7-connect-to-cursor)
   - [7.1 Method A — uv command (recommended)](#71-method-a--uv-command-recommended)
   - [7.2 Method B — venv script (fallback)](#72-method-b--venv-script-fallback)
   - [7.3 Verify in Cursor](#73-verify-in-cursor)
8. [Connect to Claude Code](#8-connect-to-claude-code)
   - [8.1 Add the MCP server (global)](#81-add-the-mcp-server-global)
   - [8.2 Add the MCP server (project-level)](#82-add-the-mcp-server-project-level)
   - [8.3 Verify in Claude Code](#83-verify-in-claude-code)
9. [Open Your Salesforce Project](#9-open-your-salesforce-project)
10. [Use the Tools — Example Prompts](#10-use-the-tools--example-prompts)
11. [Available MCP Tools Reference](#11-available-mcp-tools-reference)
12. [CLI Commands Reference](#12-cli-commands-reference)
13. [Local Data & Privacy](#13-local-data--privacy)
14. [Moving to a New Machine — Checklist](#14-moving-to-a-new-machine--checklist)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What You Are Setting Up

The **Local SF Architect Engine** is a **Model Context Protocol (MCP) server** — a local plugin that gives your AI IDE specialized Salesforce tools to call. The AI stops guessing and instead calls local engines for deterministic, grounded answers.

```
Your IDE (Cursor / Claude Code)
        │
        │  MCP / stdio JSON-RPC  (no TCP port, no internet)
        ▼
┌─────────────────────────────────┐
│        sf-architect-mcp         │  ← runs on your laptop
│                                 │
│  Router → Patterns engine       │  semantic search (LanceDB)
│         → Limits engine         │  governor limit math (SQLite)
│         → Dep-graph engine      │  Apex dependency analysis
│         → Scoring engine        │  six-pillar health scorecard
│         → Diagram engine        │  Mermaid / draw.io output
│         → Lint engine           │  architectural anti-pattern flags
└─────────────────────────────────┘
        │
        ▼
 ~/.sf-architect/    ← all data, never sent anywhere
```

**What it does NOT do:**
- Does not send your code to any cloud service
- Does not require a GPU
- Does not connect to your Salesforce org
- Makes zero network calls at runtime (only the one-time model download)

---

## 2. System Requirements

| Requirement | Minimum Version | Notes |
|---|---|---|
| Operating System | macOS 12, Windows 10, Linux (Ubuntu 20.04+) | All three fully supported |
| Python | **3.12** | 3.13 works too |
| Git | Any recent version | Used to clone the repo |
| uv | Any recent version | Replaces pip + virtualenv |
| Cursor | **0.40+** | Any version with MCP support |
| Claude Code | Any version with MCP support | CLI-based or desktop |
| Internet | Required **once** | Only for the ~130 MB embedding model download |
| Disk space | ~500 MB | Dependencies + model + local databases |

---

## 3. Install Prerequisites

### 3.1 Install Git

**macOS**
```bash
# Option 1 — Xcode Command Line Tools (no extra install)
xcode-select --install

# Option 2 — Homebrew
brew install git
```

Verify:
```bash
git --version
```

**Windows**  
Download and run the installer from [git-scm.com/download/win](https://git-scm.com/download/win). Accept all defaults. After install, open **PowerShell** and verify:
```powershell
git --version
```

**Linux (Ubuntu / Debian)**
```bash
sudo apt update && sudo apt install git -y
git --version
```

---

### 3.2 Install Python 3.12+

**macOS**
```bash
brew install python@3.12
python3 --version
```

**Windows**  
Download Python 3.12 from [python.org/downloads](https://www.python.org/downloads/).  
During install, check **"Add Python to PATH"**.
```powershell
python --version
```

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv -y
python3.12 --version
```

> If you have `pyenv`, you can also use `pyenv install 3.12` and `pyenv global 3.12`.

---

### 3.3 Install uv (package manager)

`uv` is the only package manager this project uses. It replaces `pip` and `virtualenv` in a single tool.

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After the install completes, restart your terminal (or run `source ~/.zshrc` / `source ~/.bashrc`), then verify:
```bash
uv --version
```

**Windows — Option 1: WinGet (recommended)**

WinGet is built into Windows 10 (1809+) and Windows 11:
```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen PowerShell, then verify:
```powershell
uv --version
```

**Windows — Option 2: PowerShell installer**

Use this if WinGet is unavailable:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> If you see "running scripts is disabled on this system", use Option 1 (WinGet) or `pip install uv`.

---

### 3.4 Install Cursor or Claude Code

**Cursor**  
Download from [cursor.com](https://www.cursor.com/) and install for your OS.  
Any version that supports MCP (Settings → MCP section is visible) is fine.

**Claude Code**  
Install the Claude Code CLI globally:
```bash
npm install -g @anthropic-ai/claude-code
```

Or download the desktop app from [claude.ai/code](https://claude.ai/code) if you prefer a GUI.

Verify the CLI:
```bash
claude --version
```

---

## 4. Get the Project

Open a terminal and run:

```bash
git clone https://github.com/personalaimaster-coder/Local_SF_Architect.git
cd "Local_SF_Architect"
```

> The folder on your machine may be named `Local Salesforce Architect Engine` if you received it as an archive. `cd` into whatever name it has.

**Verify you are in the right folder — you should see these files:**
```bash
ls
# Expected: pyproject.toml  README.md  src/  data/  docs/  .vscode/  uv.lock
```

**Find the absolute path to this folder (you will need it later):**

```bash
# macOS / Linux
pwd

# Windows
cd
```

Write this path down — you will paste it into the MCP config files in Steps 7 and 8.

---

## 5. Install Python Dependencies

From inside the project folder, run:

```bash
uv sync
```

This creates a `.venv/` folder inside the project and installs all Python packages listed in `pyproject.toml`. First run takes about 60 seconds.

**Optional — scraping feature** (downloads Chromium, several hundred MB, not needed for most users):
```bash
uv sync --extra scrape
```

> You do **not** need the scrape extra unless you plan to use the `sync_latest_patterns` tool to ingest custom URLs.

---

## 6. First-Time Local Setup (run once per machine)

Run these five commands once on every machine. They are fast and safe to re-run.

### 6a. Health check

```bash
uv run sf-architect doctor
```

Verifies Python version, installed packages, and local data directory structure. You should see all checks pass.

---

### 6b. Download the embedding model

```bash
uv run sf-architect doctor --download
```

Downloads the `bge-small-en-v1.5` model (~130 MB) from Hugging Face into the local model cache. This is the **only** network call this tool ever makes. After this step, everything runs fully offline.

> If you are about to move to an air-gapped environment, run this beforehand.

---

### 6c. Seed the knowledge base

```bash
uv run sf-architect seed
```

Reads the bundled seed files and builds two local databases:
- `~/.sf-architect/limits.db` — 50+ Salesforce governor limits for API v62.0 (SQLite)
- `~/.sf-architect/data/lance/` — semantic vector store of curated architecture patterns (LanceDB)

Takes about 30 seconds. Must be re-run on each new machine — these databases are **not** synced by Git.

---

### 6d. Run the test suite

```bash
uv run sf-architect test
```

All tests should pass. If any fail, see [Troubleshooting](#15-troubleshooting).

---

### 6e. Confirm the MCP server starts

```bash
uv run sf-architect-mcp
```

You should see startup output with no errors. Press `Ctrl+C` to stop it. Cursor and Claude Code will start it automatically once you configure them — this manual start is just to confirm there are no issues.

---

## 7. Connect to Cursor

Cursor uses a JSON config file to know which MCP servers to start. There are two methods; Method A is recommended.

### 7.1 Method A — uv command (recommended)

Open the file `~/.cursor/mcp.json` (create it if it does not exist) and add the `sf-local-architect` entry. Replace the `cwd` value with the **absolute path** to your project folder from Step 4.

**macOS / Linux example:**
```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "/Users/yourname/Local_SF_Architect"
    }
  }
}
```

**Windows example:**
```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "C:\\Users\\YourName\\Documents\\Local_SF_Architect"
    }
  }
}
```

> **Important:** If your path has spaces (e.g. `Local Salesforce Architect Engine`), keep it as a single JSON string — do not escape or split the spaces.

**Where is `~/.cursor/mcp.json`?**

| OS | Full path |
|---|---|
| macOS | `/Users/yourname/.cursor/mcp.json` |
| Windows | `C:\Users\YourName\.cursor\mcp.json` |
| Linux | `/home/yourname/.cursor/mcp.json` |

If there is already a `mcpServers` object in that file with other servers, just add the `sf-local-architect` key inside the existing `mcpServers` object — do not create a duplicate `mcpServers` block.

**Example with multiple servers already present:**
```json
{
  "mcpServers": {
    "some-other-server": {
      "command": "...",
      "args": []
    },
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "/Users/yourname/Local_SF_Architect"
    }
  }
}
```

---

### 7.2 Method B — venv script (fallback)

Use this if `uv` is not on your system PATH when Cursor launches (common on Windows or in managed environments).

First, find the path to the installed script:
```bash
# macOS / Linux
uv run which sf-architect-mcp

# Windows
uv run where sf-architect-mcp
```

Then point Cursor at the script directly (no `cwd` needed):

**macOS / Linux:**
```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "/Users/yourname/Local_SF_Architect/.venv/bin/sf-architect-mcp",
      "args": []
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "C:\\Users\\YourName\\Documents\\Local_SF_Architect\\.venv\\Scripts\\sf-architect-mcp.exe",
      "args": []
    }
  }
}
```

---

### 7.3 Verify in Cursor

1. **Restart Cursor** (fully quit and reopen, not just reload window).
2. Open **Cursor Settings** → scroll to the **MCP** section.
3. You should see `sf-local-architect` listed with a **green dot** (connected).
4. If the dot is red or yellow, click it to see the error log.
5. Open a new Cursor chat and type:

   ```
   Call health_echo with message "hello"
   ```

   Expected response: `sf-local-architect ok: hello`

---

## 8. Connect to Claude Code

Claude Code uses a different config file format. Choose between global (applies to all projects) or project-level (applies only to one project).

### 8.1 Add the MCP server (global)

Run this command once from any directory. Replace the path with the absolute path to your project.

**macOS / Linux:**
```bash
claude mcp add sf-local-architect \
  --command uv \
  --args "run,sf-architect-mcp" \
  --cwd "/Users/yourname/Local_SF_Architect"
```

**Windows (PowerShell):**
```powershell
claude mcp add sf-local-architect `
  --command uv `
  --args "run,sf-architect-mcp" `
  --cwd "C:\Users\YourName\Documents\Local_SF_Architect"
```

This writes to `~/.claude/config.json` (created automatically if it does not exist).

---

### 8.2 Add the MCP server (project-level)

If you prefer to keep the config scoped to this project, run the command from inside the project folder:

```bash
cd "/path/to/Local_SF_Architect"
claude mcp add sf-local-architect \
  --command uv \
  --args "run,sf-architect-mcp" \
  --cwd "$(pwd)" \
  --scope project
```

This creates or updates `.claude/mcp.json` inside the project folder.

**Alternatively, create `.claude/mcp.json` manually:**

```json
{
  "mcpServers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "/Users/yourname/Local_SF_Architect"
    }
  }
}
```

---

### 8.3 Verify in Claude Code

**CLI:**
```bash
claude mcp list
```

You should see `sf-local-architect` in the output with status `connected`.

**In a Claude Code session:**

Start a new conversation and type:

```
Call health_echo with message "hello"
```

Expected response: `sf-local-architect ok: hello`

If you see `MCP server not found` or a timeout, check that `uv` is on PATH (`which uv`) and that the `cwd` path is correct.

---

## 9. Open Your Salesforce Project

For the dependency graph and lint tools to work, open your SFDX project folder in the IDE. The structure should look like this:

```
my-salesforce-project/
├── sfdx-project.json
└── force-app/
    └── main/
        └── default/
            ├── classes/          ← .cls Apex class files
            ├── triggers/         ← .trigger files
            └── objects/          ← .object-meta.xml field definitions
```

The engine reads your Apex and XML metadata files **directly from disk** — it does not connect to your Salesforce org at any point.

> **Note:** The Local SF Architect Engine folder and your Salesforce project folder are two separate folders. You do not need to put your Salesforce code inside the engine folder.

---

## 10. Use the Tools — Example Prompts

Once the MCP server is running, just ask questions in plain English. The AI selects the right tool automatically.

| What to ask | What the engine does |
|---|---|
| *"What is the best pattern for async processing in Salesforce?"* | Semantic search over 18+ curated architecture patterns |
| *"I'm fetching 45,000 rows in a loop. Will I hit governor limits?"* | Exact headroom / breach math against Salesforce API v62.0 limits |
| *"What will break if I refactor AccountService.cls?"* | Parses all Apex + XML and computes immediate + transitive blast radius |
| *"Score the architecture health of this project"* | Six-pillar scorecard: security, performance, scalability, maintainability, reliability, cost |
| *"Draw me a dependency diagram for the Order subsystem"* | Generates a Mermaid `.md` or draw.io `.drawio` file |
| *"Scan my Apex for anti-patterns"* | Flags SOQL in loops, DML in loops, missing bulkification, missing sharing declarations |
| *"Always generate draw.io diagrams from now on"* | Persists your diagram format preference for the session |

Every tool response is structured like this:
```json
{
  "ok": true,
  "tool": "check_governor_limit",
  "data": { "..." },
  "confidence": 0.94,
  "warnings": [],
  "error": null
}
```

---

## 11. Available MCP Tools Reference

These are the tools the AI can call. You do not call them directly — just describe what you want.

| Tool name | What it does |
|---|---|
| `health_echo` | Ping the server — returns `ok: <your message>`. Use to verify the connection. |
| `query_architect_db` | Semantic search over local architecture patterns |
| `check_governor_limit` | Exact headroom / breach calculation for any Salesforce governor limit |
| `analyze_local_blast_radius` | What breaks if you change or delete a file (immediate + transitive) |
| `generate_architecture_diagram` | Writes a Mermaid `.md` or draw.io `.drawio` file from your actual codebase |
| `set_deliverable_preference` | Persist your preferred diagram format (Mermaid or draw.io) |
| `score_architecture` | Six-pillar scorecard + overall risk score with explanations |
| `sync_latest_patterns` | Opt-in: scrape an allowlisted URL and store new patterns locally |

> `sync_latest_patterns` is disabled by default. To enable it, add a domain to `scrape_allowlist` in `~/.sf-architect/config.yaml`.

---

## 12. CLI Commands Reference

All CLI commands use `uv run sf-architect <subcommand>`. Run them from inside the project folder.

```bash
# Check environment and local store health
uv run sf-architect doctor

# Pre-download the embedding model before going offline (~130 MB, run once)
uv run sf-architect doctor --download

# Build / rebuild the local knowledge base from seed files
uv run sf-architect seed

# Lint a Salesforce DX project for architectural anti-patterns
# Exits with code 1 if violations are found — CI/CD compatible
uv run sf-architect lint /path/to/your/sfdx-project

# Run the full automated test suite
uv run sf-architect test

# Remove stale or superseded vectors from the pattern store
uv run sf-architect gc

# Drop all local stores and rebuild from seed files (use after schema changes)
uv run sf-architect rebuild

# Print the installed version
uv run sf-architect --version
```

**Example lint output:**
```
[WARN] AccountService.cls:42  SOQL inside for-loop — risk of hitting 100 SOQL limit
[WARN] OrderProcessor.cls:17  DML inside for-loop — bulkify this operation
[FAIL] 2 infraction(s) found
```

---

## 13. Local Data & Privacy

All runtime data lives under `~/.sf-architect/` on your machine and is **never committed to Git** and **never sent anywhere**.

```
~/.sf-architect/
  config.yaml          preferences + scrape allowlist (empty by default)
  data/lance/          vector store — patterns + embeddings
  limits.db            compiled governor limits (SQLite)
  logs/audit.db        one row per tool call (SQLite) — local only
  meta.json            schema version + embedding model record
```

**Security model:**
- No outbound network calls at runtime (enforced by tests that fail if any tool makes an unexpected network request)
- Scraping is disabled by default — `scrape_allowlist` is empty until you explicitly add a domain
- stdio transport only — no TCP port, no auth surface; the IDE spawns the server as a child process
- Your code never leaves your machine

**Schema recovery:** If you update the repo and get a schema mismatch error, run:
```bash
uv run sf-architect rebuild
```

---

## 14. Moving to a New Machine — Checklist

Follow this checklist on every new machine. The `~/.sf-architect/` databases are not synced by Git and must be rebuilt locally.

- [ ] Install Git (Section 3.1)
- [ ] Install Python 3.12+ (Section 3.2)
- [ ] Install uv (Section 3.3)
- [ ] Install Cursor and/or Claude Code (Section 3.4)
- [ ] Clone the project — `git clone https://github.com/personalaimaster-coder/Local_SF_Architect.git`
- [ ] Install dependencies — `uv sync` inside the project folder
- [ ] Health check — `uv run sf-architect doctor`
- [ ] Download the embedding model — `uv run sf-architect doctor --download` (internet required once)
- [ ] Seed the databases — `uv run sf-architect seed`
- [ ] Run tests — `uv run sf-architect test`
- [ ] Update `cwd` in `~/.cursor/mcp.json` (Cursor) with the path on this machine
- [ ] Run `claude mcp add ...` (Claude Code) with the path on this machine
- [ ] Verify — ping the server with `health_echo` from the IDE chat

---

## 15. Troubleshooting

| Problem | Fix |
|---|---|
| Cursor MCP panel shows server as stopped or red dot | Check that `uv` is on PATH: run `which uv` (macOS/Linux) or `where uv` (Windows) in the terminal |
| `uv: command not found` | **macOS/Linux:** `curl -LsSf https://astral.sh/uv/install.sh \| sh` then restart terminal. **Windows:** `winget install --id=astral-sh.uv -e` then open a new PowerShell window. |
| `claude mcp list` shows server as disconnected | Verify the `--cwd` path is correct and that `uv sync` has been run in that folder |
| `doctor` fails — missing stores or databases | Run `uv run sf-architect seed` |
| Model not found / embedding error | Run `uv run sf-architect doctor --download` |
| Schema mismatch error after pulling latest code | Run `uv run sf-architect rebuild` |
| `health_echo` call times out or errors | Manually run `uv run sf-architect-mcp` in the terminal to see the startup error |
| `uv sync` fails with Python version error | Install Python 3.12+ and ensure it is on PATH: `python3 --version` |
| Path with spaces causes MCP server to not start | Ensure the entire `cwd` value is one JSON string — do not split, escape, or quote the spaces inside JSON |
| Tests fail with import errors | Make sure you ran `uv sync` (not `pip install`) and you are running commands with `uv run` |
| `git clone` fails — permission denied | Verify Git is installed (`git --version`) and you have internet access |
| Cursor shows tools but AI never calls them | Make sure you are using an AI model that supports tool calling (Claude 3.5+, GPT-4o, etc.) |
| Claude Code: `MCP server not found` | Verify with `claude mcp list` and re-run the `claude mcp add` command with the correct path |
| No diagram file created after asking for a diagram | Check `~/.sf-architect/diagrams/` — the file is written there, not in the IDE workspace |
| `sync_latest_patterns` returns "no allowlisted domains" | Add a domain to `scrape_allowlist` in `~/.sf-architect/config.yaml` |

---

## Quick Reference — Key Config File Locations

| IDE | Config file | Root key |
|---|---|---|
| Cursor (user-level) | `~/.cursor/mcp.json` | `"mcpServers"` |
| Cursor (project-level) | `.cursor/mcp.json` in project root | `"mcpServers"` |
| Claude Code (global) | `~/.claude/config.json` | `"mcpServers"` |
| Claude Code (project-level) | `.claude/mcp.json` in project root | `"mcpServers"` |

---

*For VS Code + GitHub Copilot setup, see [`docs/vscode-setup.md`](vscode-setup.md).*  
*For the full tech stack and dependency rationale, see [`docs/Tech-Stack.md`](Tech-Stack.md).*
