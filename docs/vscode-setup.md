# VS Code Setup for sf-local-architect

Complete guide to setting up and using the Local SF Architect Engine in VS Code — from installing prerequisites to asking your first question — covering every step on every operating system.

> **Fastest path — install the extension.** The [`Local SF Architect` VS Code extension](../extension/README.md) automates everything in this guide: it installs the engine via `uv`, downloads the model, seeds the knowledge base, and registers the MCP server with Copilot in one click (VS Code 1.101+). The manual steps below remain available if you prefer them or are on an older VS Code.

> **Two ways to use this tool in VS Code:**
> - **Path A — Full AI chat (recommended):** VS Code 1.99+ with a GitHub Copilot subscription. Ask questions in natural language; Copilot calls the architect tools automatically.
> - **Path B — CLI only (no subscription needed):** Run `uv run sf-architect lint` / `score` directly in the terminal. No AI subscription required.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Install Prerequisites](#2-install-prerequisites)
   - [Install Git](#21-install-git)
   - [Install Python 3.12+](#22-install-python-312)
   - [Install uv](#23-install-uv)
   - [Install VS Code](#24-install-vs-code)
3. [Get the Project from Git](#3-get-the-project-from-git)
4. [Install Project Dependencies](#4-install-project-dependencies)
5. [First-Time Setup (run once per machine)](#5-first-time-setup-run-once-per-machine)
6. [Configure VS Code MCP (Path A — GitHub Copilot)](#6-configure-vs-code-mcp-path-a--github-copilot)
7. [Enable Agent Mode in VS Code](#7-enable-agent-mode-in-vs-code)
8. [Verify the Connection](#8-verify-the-connection)
9. [Open Your Salesforce Project](#9-open-your-salesforce-project)
10. [Use the Tools](#10-use-the-tools)
11. [Path B — CLI Only (No Copilot Required)](#11-path-b--cli-only-no-copilot-required)
12. [Moving to a Different Machine](#12-moving-to-a-different-machine)
13. [Key Differences: VS Code vs Cursor](#13-key-differences-vs-code-vs-cursor)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Requirements

| Requirement | Minimum version | Notes |
|---|---|---|
| Operating System | Windows 10, macOS 12, or Linux (Ubuntu 20.04+) | All three are fully supported |
| VS Code | **1.99** (March 2025) | Earlier versions have no MCP support |
| Python | **3.12** | 3.13 also works |
| Git | Any recent version | Used to clone the repository |
| uv | Any recent version | Replaces pip + virtualenv |
| GitHub Copilot | Individual / Business / Enterprise | **Only required for Path A (AI chat)**. Path B (CLI) needs no subscription. |

---

## 2. Install Prerequisites

### 2.1 Install Git

**macOS**
```bash
# Option 1 — Xcode Command Line Tools (recommended, no extra install)
xcode-select --install

# Option 2 — Homebrew
brew install git
```

**Windows**
Download and run the installer from [git-scm.com/download/win](https://git-scm.com/download/win).
Accept all defaults. After install, open **Git Bash** or **PowerShell** and verify:
```powershell
git --version
```

**Linux (Ubuntu / Debian)**
```bash
sudo apt update && sudo apt install git -y
git --version
```

---

### 2.2 Install Python 3.12+

**macOS**
```bash
# Homebrew
brew install python@3.12

# Verify
python3 --version
```

**Windows**
Download Python 3.12 from [python.org/downloads](https://www.python.org/downloads/).
During install, check **"Add Python to PATH"**.
Verify in PowerShell:
```powershell
python --version
```

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv -y
python3.12 --version
```

---

### 2.3 Install uv

`uv` is the only package manager this project uses. It replaces `pip` and `virtualenv` in one tool.

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After install, restart your terminal (or run `source ~/.zshrc` / `source ~/.bashrc`), then verify:
```bash
uv --version
```

**Windows — Option 1: WinGet (recommended, works in all environments)**

WinGet is built into Windows 10 (1809+) and Windows 11. Open PowerShell or Command Prompt and run:
```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen PowerShell, then verify:
```powershell
uv --version
```

**Windows — Option 2: PowerShell installer script**

This works on personal machines but may be blocked by corporate Group Policy:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell, then verify:
```powershell
uv --version
```

> If Option 2 gives an error like "running scripts is disabled on this system", use Option 1 (WinGet) instead. If neither works, install via pip: `pip install uv`

---

### 2.4 Install VS Code

Download from [code.visualstudio.com](https://code.visualstudio.com/) and install for your OS.

After install, confirm the version is **1.99 or newer**:
- Open VS Code → Help → About → check the version number.

If using **Path A (GitHub Copilot)**, also install the GitHub Copilot and GitHub Copilot Chat extensions:
1. Open VS Code → Extensions sidebar (`Ctrl+Shift+X` / `Cmd+Shift+X`).
2. Search for **GitHub Copilot** → Install.
3. Search for **GitHub Copilot Chat** → Install.
4. Sign in with your GitHub account when prompted and activate your Copilot subscription.

---

## 3. Get the Project from Git

Open a terminal (macOS/Linux) or Git Bash / PowerShell (Windows) and run:

```bash
git clone https://github.com/personalaimaster-coder/Local_SF_Architect.git
```

This creates a folder called `Local_SF_Architect`. Move into it:

```bash
cd Local_SF_Architect
```

> **Already have the repo?** If you pulled the project folder from a USB drive or network share instead of Git, just `cd` into that folder. All subsequent steps are identical.

**Verify you are in the right folder** — you should see these files:

```bash
ls
# Expected output includes: pyproject.toml  README.md  src/  data/  docs/  .vscode/
```

---

## 4. Install Project Dependencies

From inside the project folder, run:

```bash
uv sync
```

This creates a `.venv/` folder and installs all Python dependencies listed in `pyproject.toml`. It takes about 60 seconds on the first run.

**Optional — scraping feature** (downloads Chromium, several hundred MB, not needed for most users):
```bash
uv sync --extra scrape
```

---

## 5. First-Time Setup (run once per machine)

These four commands must be run once on every machine you use this tool on.

### Step 5a — Check environment health
```bash
uv run sf-architect doctor
```
This verifies Python version, required packages, and local data directory paths. You should see a confirmation that all checks passed.

### Step 5b — Download the embedding model (internet required this one time)
```bash
uv run sf-architect doctor --download
```
Downloads the `bge-small-en-v1.5` model (~130 MB) from Hugging Face. After this step, **the tool runs fully offline** — no internet needed, ever. If you are about to go to an air-gapped network, run this beforehand.

### Step 5c — Seed the knowledge base
```bash
uv run sf-architect seed
```
This reads the files in `data/` and builds two local databases:
- `~/.sf-architect/limits.db` — 50+ Salesforce governor limits for API v62.0
- `~/.sf-architect/data/lance/` — semantic vector store of architecture patterns

### Step 5d — Run the test suite to verify
```bash
uv run sf-architect test
```
All tests should pass. If any fail, check the output and consult the [Troubleshooting](#14-troubleshooting) section.

### Step 5e — Confirm the MCP server starts
```bash
uv run sf-architect-mcp
```
You should see startup output with no errors. Press `Ctrl+C` to stop it. VS Code will start it automatically once configured.

---

## 6. Configure VS Code MCP (Path A — GitHub Copilot)

A ready-to-use config file is already included in this repository at `.vscode/mcp.json`.

**If you cloned the repo on this machine**, open `.vscode/mcp.json` and update the `cwd` value to the absolute path of the project folder on your machine. For example:

**macOS / Linux:**
```json
{
  "servers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "/Users/yourname/Local_SF_Architect"
    }
  }
}
```

**Windows:**
```json
{
  "servers": {
    "sf-local-architect": {
      "command": "uv",
      "args": ["run", "sf-architect-mcp"],
      "cwd": "C:\\Users\\YourName\\Documents\\Local_SF_Architect"
    }
  }
}
```

> **How to find the absolute path:**
> - macOS/Linux: run `pwd` inside the project folder in the terminal.
> - Windows: run `cd` (with no arguments) in PowerShell inside the project folder.

**Important notes:**
- VS Code uses `"servers"` as the root key. Cursor uses `"mcpServers"`. They are **not** interchangeable.
- If the path contains spaces, keep it as a single JSON string — do not split or escape the spaces.

### Alternative — use the venv script directly (if `uv` is not on PATH)

```json
{
  "servers": {
    "sf-local-architect": {
      "command": "/absolute/path/to/Local_SF_Architect/.venv/bin/sf-architect-mcp",
      "args": []
    }
  }
}
```

Windows:
```json
{
  "servers": {
    "sf-local-architect": {
      "command": "C:\\absolute\\path\\to\\Local_SF_Architect\\.venv\\Scripts\\sf-architect-mcp.exe",
      "args": []
    }
  }
}
```

---

## 7. Enable Agent Mode in VS Code

MCP tools only work inside Copilot Chat when it is in **Agent mode**.

1. Open VS Code Settings:
   - Windows/Linux: `Ctrl+,`
   - macOS: `Cmd+,`
2. Search for `chat.agent.enabled` and toggle it **on**.
3. Open Copilot Chat:
   - Windows/Linux: `Ctrl+Shift+I`
   - macOS: `Cmd+Shift+I`
4. In the chat panel, find the mode dropdown (shows "Ask" by default) and switch it to **Agent**.

---

## 8. Verify the Connection

1. Open the Command Palette:
   - Windows/Linux: `Ctrl+Shift+P`
   - macOS: `Cmd+Shift+P`
2. Type and run: `MCP: List Servers`
3. Confirm `sf-local-architect` is listed with status **Running**.
4. In Copilot Chat (Agent mode), click the **tools icon** (hammer icon) — the sf-local-architect tools should appear in the list.

If the server is not running, see [Troubleshooting](#14-troubleshooting).

---

## 9. Open Your Salesforce Project

Open your SFDX project folder (the one with your retrieved metadata) in VS Code:

```
File → Open Folder → select your SFDX project root
```

Your folder should look like this:
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

The tool reads your Apex and XML metadata files **directly from disk** — it does not connect to your Salesforce org at runtime.

---

## 10. Use the Tools

With your SFDX project open and Copilot Chat in Agent mode, ask questions in plain English. The AI picks the right tool automatically.

| What to ask | What the engine does |
|---|---|
| *"What breaks if I refactor AccountService.cls?"* | Parses all Apex + XML and computes immediate + transitive blast radius |
| *"Will fetching 45,000 rows in a loop hit governor limits?"* | Runs exact math against the Salesforce API v62.0 limits database |
| *"What is the best pattern for async Salesforce processing?"* | Semantic search over 18 curated architecture patterns |
| *"Score the architecture health of this project"* | Six-pillar scorecard: security, performance, scalability, maintainability, reliability, cost |
| *"Draw me a dependency diagram for the Order subsystem"* | Generates a Mermaid `.md` or draw.io `.drawio` file saved to `~/.sf-architect/diagrams/` |
| *"Scan my Apex for anti-patterns"* | Flags SOQL/DML in loops, missing bulkification, missing sharing declarations |

Every tool response includes a confidence score and a list of any warnings.

---

## 11. Path B — CLI Only (No Copilot Required)

If you do not have a GitHub Copilot subscription, every feature is available as a terminal command. Open VS Code's integrated terminal (`Ctrl+\`` / `Cmd+\``) and run from the project folder:

```bash
# Lint all Apex files for architectural anti-patterns
# (exits with code 1 if violations found — CI/CD compatible)
uv run sf-architect lint /path/to/your/sfdx-project

# Six-pillar architecture health scorecard
uv run sf-architect score /path/to/your/sfdx-project

# Check environment + local database health
uv run sf-architect doctor

# Drop and rebuild all local databases (use after pulling updates)
uv run sf-architect rebuild

# Remove stale vectors from the pattern store
uv run sf-architect gc

# Print installed version
uv run sf-architect --version
```

**Real example** (running lint on a project at `~/projects/my-org`):
```bash
uv run sf-architect lint ~/projects/my-org
```

Output looks like:
```
[WARN] AccountService.cls:42  SOQL inside for-loop — risk of hitting 100 SOQL limit
[WARN] OrderProcessor.cls:17  DML inside for-loop — bulkify this operation
[FAIL] 2 infraction(s) found
```

---

## 12. Moving to a Different Machine

Follow this checklist on every new machine:

- [ ] **Install Git** (Section 2.1)
- [ ] **Install Python 3.12+** (Section 2.2)
- [ ] **Install uv** — Windows: `winget install --id=astral-sh.uv -e` | macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Section 2.3)
- [ ] **Install VS Code 1.99+** (Section 2.4)
- [ ] **Clone or copy the project** — `git clone https://github.com/personalaimaster-coder/Local_SF_Architect.git`
- [ ] **Install dependencies** — `uv sync` inside the project folder
- [ ] **Download the model** — `uv run sf-architect doctor --download` (internet needed once)
- [ ] **Seed the databases** — `uv run sf-architect seed`
- [ ] **Update `cwd`** in `.vscode/mcp.json` to the path on this machine
- [ ] **Verify** — Command Palette → `MCP: List Servers` → confirm Running

> The `~/.sf-architect/` folder (local databases, vectors, audit log) is **not** synced by Git. You must run `seed` on each new machine. It takes about 30 seconds.

---

## 13. Key Differences: VS Code vs Cursor

| | Cursor | VS Code |
|---|---|---|
| MCP config file | `~/.cursor/mcp.json` (user-level) | `.vscode/mcp.json` (workspace) |
| Root JSON key | `"mcpServers"` | `"servers"` |
| AI chat access | Built-in Cursor AI | GitHub Copilot (paid subscription) |
| Agent mode | Always available | Must enable `chat.agent.enabled` |
| MCP tool use | Cursor chat panel | Copilot Chat → Agent mode |

---

## 14. Troubleshooting

| Problem | Fix |
|---|---|
| `MCP: List Servers` shows server as stopped or not found | Check that `uv` is on PATH: run `which uv` (macOS/Linux) or `where uv` (Windows) in the terminal |
| `uv: command not found` | **Windows:** run `winget install --id=astral-sh.uv -e` then open a new PowerShell window. **macOS/Linux:** run `curl -LsSf https://astral.sh/uv/install.sh \| sh` then restart terminal. |
| `doctor` fails — missing stores | Run `uv run sf-architect seed` |
| Model not found / embedding error | Run `uv run sf-architect doctor --download` |
| Schema mismatch error after updating the repo | Run `uv run sf-architect rebuild` |
| Tools not visible in Copilot Chat | Confirm the mode dropdown shows **Agent**, not Ask or Edit |
| VS Code says MCP is not supported | Update VS Code to version 1.99 or newer (Help → Check for Updates) |
| `git clone` fails — permission denied | Make sure Git is installed and you have internet access; try `git --version` first |
| `uv sync` fails with Python version error | Install Python 3.12+ and ensure it is on PATH; run `python3 --version` to verify |
| Path with spaces causes MCP server error | Ensure the entire `cwd` value is one JSON string with no line breaks |
