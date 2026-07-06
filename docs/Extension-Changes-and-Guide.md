# Local SF Architect — Extension Changes, Usage Guide, and Publishing Handbook

> **Audience:** Anyone who wants to understand what was built, how to use it, or how to publish it to the VS Code Marketplace.

---

## Table of Contents

1. [Simple Explanation — What Was Built and Why](#1-simple-explanation--what-was-built-and-why)
2. [What Changed in the Existing Python Project](#2-what-changed-in-the-existing-python-project)
3. [The New VS Code Extension — File-by-File Guide](#3-the-new-vs-code-extension--file-by-file-guide)
4. [How Everything Connects — Architecture Diagram](#4-how-everything-connects--architecture-diagram)
5. [How to Use the Extension (End-User Guide)](#5-how-to-use-the-extension-end-user-guide)
6. [Why the Extension Is Not Visible in the Marketplace Yet](#6-why-the-extension-is-not-visible-in-the-marketplace-yet)
   - [6a. Publish the Python Engine to PyPI (do this first)](#6a-publish-the-python-engine-to-pypi-do-this-first)
   - [6b. How to Publish to the VS Code Marketplace](#6b-how-to-publish-to-the-vs-code-marketplace)
   - [6c. How to Publish to Open VSX (required for Cursor)](#6c-how-to-publish-to-open-vsx-required-for-cursor)
7. [CI / GitHub Actions — What Triggers What](#7-ci--github-actions--what-triggers-what)
8. [What You Still Need to Do — Master Checklist](#8-what-you-still-need-to-do--master-checklist)
9. [Frequently Asked Questions](#9-frequently-asked-questions)

---

## 1. Simple Explanation — What Was Built and Why

### The original situation

Before this change, the Local SF Architect Engine was a **Python MCP server** that ran on your laptop and gave AI tools (Cursor, Claude Code, GitHub Copilot) specialized Salesforce knowledge. But to use it, every developer had to:

1. Clone the GitHub repository manually.
2. Install `uv`, run `uv sync`, run several setup commands.
3. Hand-edit a JSON config file (`~/.cursor/mcp.json` or `.vscode/mcp.json`) with the exact path to the Python binary on their machine.

That is a lot of friction. If a developer opens Cursor or VS Code and searches "Salesforce MCP" in the extension marketplace, nothing comes up.

### What was built to fix this

A **VS Code extension** (`extension/` folder) that acts as a one-click installer and configurator. Think of it the same way you think of any VS Code extension:

- User opens VS Code → goes to Extensions panel → searches "Local SF Architect" → clicks Install.
- The extension handles **everything else automatically**: installing the Python engine from PyPI, downloading the AI model, building the local databases, and writing the right config files for Copilot, Cursor, and Claude Code.

The extension is **not** the Python engine. It is a thin (17 KB) Node.js wrapper that installs and wires up the real engine. The Python engine stays exactly as it was — the extension just makes it zero-effort to set up.

### The three targets

| AI Tool | How It Gets Wired |
|---|---|
| **GitHub Copilot in VS Code** | Extension uses VS Code's native MCP API (`registerMcpServerDefinitionProvider`) — no JSON files needed |
| **Cursor** | Extension writes / merges `~/.cursor/mcp.json` (the file Cursor reads for MCP servers) |
| **Claude Code CLI** | Extension runs `claude mcp add --scope user` — the command Claude Code uses to register servers |

All three can be wired simultaneously. For example, if a developer has VS Code with Copilot and also has the Claude Code CLI installed, both get configured in the same setup run.

---

## 2. What Changed in the Existing Python Project

Only **three existing files** were changed. Everything else was added new.

### 2a. `pyproject.toml` — Critical packaging fix

**The problem it solved:** When a user installs the engine from PyPI (`uv tool install sf-local-architect`), the Python wheel needs to include the seed data files (`limits_seed.yaml`, `patterns_seed.yaml`). These files were in a `data/` folder at the repo root — a location that is not included in a Python wheel by default. Without this fix, `sf-architect seed` would crash on a PyPI install because it couldn't find the data files.

**What was added:**

```toml
[tool.hatch.build.targets.wheel.force-include]
"data/limits_seed.yaml" = "sf_architect/data/limits_seed.yaml"
"data/patterns_seed.yaml" = "sf_architect/data/patterns_seed.yaml"
```

This tells the build tool (Hatchling) to copy those two files inside the Python wheel, next to the source code, even though they live outside the `src/` folder.

**Verified:** The wheel was built, unpacked, and inspected — both files are present at `sf_architect/data/` inside the wheel. A test install outside the repo confirmed that `sf-architect seed` works correctly from a PyPI install.

---

### 2b. `src/sf_architect/bootstrap.py` — Smart data path resolution

**The problem it solved:** The function `repo_data_dir()` previously looked for seed data in two places: the repo-root `data/` folder (dev checkout) and `./data` (working directory). It had no knowledge of the packaged location inside the wheel.

**What was changed:** The function now checks three locations in order, returning the first one where `limits_seed.yaml` actually exists:

```
1. sf_architect/data/  ← inside the installed wheel (PyPI install)
2. <repo-root>/data/   ← dev checkout of the repository  
3. ./data/             ← last-resort fallback
```

This means the same code works correctly whether you:
- Cloned the repo and are running `uv run sf-architect seed` (uses location 2)
- Installed from PyPI with `uv tool install sf-local-architect` (uses location 1)

---

### 2c. `README.md` — Added the extension fast-path

A new section was inserted near the top explaining that a VS Code / Cursor extension now exists and is the easiest way to get started. The manual setup steps remain intact for users who prefer them.

---

## 3. The New VS Code Extension — File-by-File Guide

The entire extension lives in the `extension/` folder. Here is every file and what it does.

```
extension/
├── package.json            ← Extension manifest (tells VS Code what the extension contributes)
├── tsconfig.json           ← TypeScript compiler configuration
├── esbuild.js              ← Build script (bundles TS into a single JS file)
├── eslint.config.js        ← Linter configuration (ESLint 9 flat config)
├── .vscodeignore           ← Files excluded from the published .vsix package
├── .gitignore              ← node_modules, dist, *.vsix
├── LICENSE                 ← Apache-2.0 (copied from repo root)
├── README.md               ← Marketplace-facing description
├── CHANGELOG.md            ← Version history
├── media/
│   ├── walkthrough-install.md     ← Content for step 1 of the Getting Started walkthrough
│   ├── walkthrough-seed.md        ← Content for step 2
│   └── walkthrough-configure.md   ← Content for step 3
└── src/
    ├── constants.ts        ← Shared string constants (IDs, keys, URLs)
    ├── log.ts              ← OutputChannel logger
    ├── proc.ts             ← Child-process helpers (exec, which)
    ├── detect.ts           ← Detect host (VS Code vs Cursor) and installed agents
    ├── engine.ts           ← Find uv, install engine, resolve command paths
    ├── setup.ts            ← First-run flow (ensureUv, install, doctor, seed, rebuild)
    ├── statusBar.ts        ← Status bar item in the bottom-right of VS Code
    ├── jsonConfig.ts       ← Safe JSON read/merge/write for config files
    ├── extension.ts        ← Main entry point — activate(), all commands
    └── wiring/
        ├── vscode.ts       ← Wire into GitHub Copilot (native MCP provider API)
        ├── cursor.ts       ← Wire into Cursor (~/.cursor/mcp.json)
        └── claudeCode.ts   ← Wire into Claude Code CLI (~/.claude.json)
```

### `package.json` — The manifest

This is the most important file. It declares everything the extension contributes to VS Code:

- **`engines.vscode: "^1.101.0"`** — Minimum VS Code version. 1.101 is when the native MCP provider API became available.
- **`activationEvents: ["onStartupFinished"]`** — The extension activates once VS Code has fully started, so it doesn't slow down the editor launch.
- **`contributes.mcpServerDefinitionProviders`** — Declares the MCP provider. This is what allows VS Code/Copilot to ask our extension for MCP server definitions instead of reading a JSON file.
- **`contributes.commands`** — 10 commands that appear in the Command Palette (Ctrl+Shift+P).
- **`contributes.configuration`** — 5 user-facing settings (engine package name, uv path, auto-setup flags).
- **`contributes.walkthroughs`** — A 3-step "Getting Started" guide that appears in the Welcome tab.
- **`dependencies: { "jsonc-parser" }`** — The only runtime dependency. Used to safely read JSON/JSONC config files (handles comments and trailing commas in existing `mcp.json` files without corrupting them).

### `src/constants.ts` — Shared identifiers

All magic strings are centralized here. If the PyPI package name ever changes or the server key changes, this is the one file to update.

| Constant | Value | Used for |
|---|---|---|
| `EXTENSION_ID` | `sfArchitect` | Config namespace (`sfArchitect.uvPath`, etc.) |
| `MCP_PROVIDER_ID` | `sfLocalArchitect.mcpProvider` | Must match the id in `package.json` |
| `SERVER_KEY` | `sf-local-architect` | Key written inside `mcpServers` / `servers` JSON |
| `MCP_SCRIPT` | `sf-architect-mcp` | Console script name for the server entry point |
| `CLI_SCRIPT` | `sf-architect` | Console script name for CLI commands (seed, doctor) |
| `STATE_SETUP_COMPLETE` | `sfArchitect.setupComplete` | globalState key — prevents re-running setup |
| `STATE_INSTALL_PROMPTED` | `sfArchitect.installPrompted` | globalState key — shows the prompt only once |

### `src/proc.ts` — Safe process execution

Provides two functions used throughout the extension:

- **`exec(command, args, options)`** — Spawns a process, streams stdout/stderr to an `onData` callback (so the user sees live progress), and returns `{ code, stdout, stderr }`. Never rejects on non-zero exit codes — the caller decides what to do. Supports `AbortSignal` for cancellation.
- **`which(name)`** — Finds an executable on PATH using `which` (macOS/Linux) or `where` (Windows). Returns the absolute path or null.

### `src/detect.ts` — Environment detection

Runs at startup and before any wiring. Detects:

- **Is this Cursor or VS Code?** Checks `vscode.env.appName` for the word "Cursor". This matters because Cursor and VS Code have different MCP config systems.
- **Is the native MCP provider API available?** Feature-detects `vscode.lm.registerMcpServerDefinitionProvider` and `vscode.McpStdioServerDefinition` at runtime. This is safer than trusting the version number (Cursor reports its own version).
- **Is GitHub Copilot installed?** Checks for the `GitHub.copilot-chat` or `GitHub.copilot` extension.
- **Is the Claude Code CLI on PATH?** Runs `claude --version` to confirm it responds. Returns the absolute path if found.

### `src/engine.ts` — Engine install and command resolution

**Finding `uv`:** Checks in order:
1. The `sfArchitect.uvPath` setting (user override)
2. System PATH (`which uv`)
3. Well-known install locations: `~/.local/bin/uv`, `~/.cargo/bin/uv`, `/opt/homebrew/bin/uv`, `/usr/local/bin/uv` (macOS/Linux) or `%USERPROFILE%\.local\bin\uv.exe` (Windows)

**Installing the engine:** Runs `uv tool install --upgrade sf-local-architect`. The `--upgrade` flag means re-running this command always gets the latest version — useful for updates.

**Resolving the MCP server command:** The command written into config files must be an absolute path to a binary, not just a bare name, because editors spawn the MCP server with a minimal PATH. The resolution order:
1. Find the `sf-architect-mcp` shim using `which`
2. Ask `uv tool dir --bin` for the tool bin directory and look there
3. Check `~/.local/bin/` as a fallback
4. If none found, use `uv tool run --from sf-local-architect sf-architect-mcp` (works even without PATH)

### `src/setup.ts` — First-run setup flow

Orchestrates the three setup steps in a VS Code progress notification (with a spinner and cancel button):

1. **Install engine** — runs `uv tool install --upgrade sf-local-architect`. Streams every line to the OutputChannel so the user can see what's happening.
2. **Download model** — runs `sf-architect doctor --download`. Downloads the ~130 MB `bge-small-en-v1.5` embedding model from Hugging Face. Only runs if `sfArchitect.autoDownloadModel` is `true` (default: yes). Skippable for offline/CI environments.
3. **Seed knowledge base** — runs `sf-architect seed`. Builds the SQLite limits database and the LanceDB vector store from the bundled YAML files.

After all three steps succeed, `STATE_SETUP_COMPLETE` is saved in `context.globalState` so the setup doesn't repeat on the next launch.

**Error handling at each step:**
- Install fails → shows "Failed to install" error with a "Show Logs" button.
- Model download fails → shows "Setup failed" with "Show Logs" and "Retry" buttons.
- Seed fails → same.
- User cancels → the AbortController stops the running process.

**Rebuild path:** A separate `rebuildStores()` function runs `sf-architect rebuild` — the recovery command when the vector store schema changes after an engine update.

### `src/jsonConfig.ts` — Safe config file merging

All config files (`.vscode/mcp.json`, `~/.cursor/mcp.json`, `~/.claude.json`) may already have other servers in them. This module handles merging safely:

- **`readJsonc(filePath)`** — Reads a JSON or JSONC (JSON with comments) file using `jsonc-parser`. Returns `{}` if the file doesn't exist. Never crashes on malformed JSON — it logs warnings and does best-effort parsing.
- **`backupFile(filePath)`** — Before overwriting any file, copies it to `<filename>.<timestamp>.bak` next to the original. For example: `mcp.json.2026-06-30T12-00-00-000Z.bak`. This means a user can always recover their old config.
- **`mergeServerEntry(...)`** — The core operation. Reads the file, inserts or updates the `sf-local-architect` entry under the right key (`mcpServers` or `servers`), leaves all other servers untouched, backs up, and writes. If the entry is already identical, it writes nothing (idempotent).

### `src/wiring/vscode.ts` — GitHub Copilot wiring

**Primary path (VS Code 1.101+):** Registers a `McpServerDefinitionProvider` using `vscode.lm.registerMcpServerDefinitionProvider`. This is a native VS Code API — no JSON files are touched. When Copilot asks "which MCP servers are available?", the provider responds with the absolute path to `sf-architect-mcp`. When `refreshVsCodeMcp()` is called (after install or config change), the provider fires a change event and Copilot re-queries.

**Fallback (older hosts):** If the native API is not present, writes the server into `.vscode/mcp.json` in the open workspace folder under the `"servers"` key (VS Code's JSON key, not Cursor's `"mcpServers"` key).

### `src/wiring/cursor.ts` — Cursor wiring

Writes into `~/.cursor/mcp.json` under the `"mcpServers"` key. Uses the `mergeServerEntry` helper to:
1. Read the existing file (backup it first)
2. Insert or update the `"sf-local-architect"` entry
3. Write the result, preserving all other servers

### `src/wiring/claudeCode.ts` — Claude Code wiring

**Primary path:** Runs `claude mcp remove sf-local-architect --scope user` (to clean up any stale entry), then `claude mcp add --scope user sf-local-architect -- <command> <args>`. This is the official Claude Code API for registering servers — it writes into `~/.claude.json` at the top-level `"mcpServers"` key.

**Fallback:** If the `claude` CLI fails for any reason (wrong version, permissions, unexpected output), the module falls back to editing `~/.claude.json` directly using `mergeServerEntry`.

**Skip if absent:** If `claude` is not found on PATH and no CLI path was detected, this module simply logs and returns `false`. It does not error out.

### `src/statusBar.ts` — Status bar

Shows a persistent indicator in the bottom-right of VS Code. Clicking it runs `sfArchitect.showStatus`. The icon and text change based on state:

| State | Icon | Text |
|---|---|---|
| `unknown` | `$(tools)` | SF Architect |
| `missing` | `$(cloud-download)` | SF Architect |
| `installing` | `$(sync~spin)` | SF Architect (animated) |
| `ready` | `$(check)` | SF Architect |
| `error` | `$(error)` | SF Architect |

### `src/extension.ts` — The main orchestrator

This is the entry point. VS Code calls `activate()` once the editor is ready. The function:

1. Creates the status bar.
2. Registers the native MCP provider immediately (even before setup — the provider returns an empty list until the engine is installed, then fires a refresh).
3. Registers all 10 commands.
4. Checks the current installed state and updates the status bar.
5. If `autoSetupOnActivate` is true and this is the first activation ever, shows a one-time prompt: "Set up now / Later".

**The 10 commands:**

| Command ID | What it does |
|---|---|
| `sfArchitect.setup` | Full setup: install engine + model + seed + configure all agents |
| `sfArchitect.installEngine` | Only install / upgrade the engine package |
| `sfArchitect.firstRunSetup` | Only run `doctor --download` + `seed` (skip if engine not yet installed) |
| `sfArchitect.configureCopilot` | Wire into VS Code/Copilot only |
| `sfArchitect.configureCursor` | Wire into Cursor only |
| `sfArchitect.configureClaudeCode` | Wire into Claude Code only |
| `sfArchitect.configureAll` | Wire into all detected agents |
| `sfArchitect.rebuildStores` | Run `sf-architect rebuild` (recovery after schema mismatch) |
| `sfArchitect.showLogs` | Open the "Local SF Architect" OutputChannel |
| `sfArchitect.showStatus` | Show a modal with full status + "Run Setup" / "Show Logs" buttons |

---

## 4. How Everything Connects — Architecture Diagram

```
User opens VS Code / Cursor
         │
         ▼
Extension activates (onStartupFinished)
         │
         ├─ 1. Register native MCP provider (VS Code API) immediately
         │      └─ Returns [] until engine installed; fires refresh after
         │
         ├─ 2. Check status → update status bar icon
         │
         └─ 3. First time? Show prompt: "Set up now / Later"
                    │ "Set up now"
                    ▼
            ensureUv() ──── not found ───► Open install guide URL
                    │ found
                    ▼
            installEngine()     [ uv tool install --upgrade sf-local-architect ]
                    │
                    ▼
            runFirstRunSetup()
              ├─ doctor --download  (~130 MB model, one time)
              └─ seed               (build limits.db + LanceDB)
                    │
                    ▼
            detectAgents()
              ├─ VS Code + Copilot?  → registerMcpServerDefinitionProvider ✓
              ├─ Cursor?             → merge ~/.cursor/mcp.json            ✓
              └─ Claude Code CLI?    → claude mcp add --scope user         ✓
                    │
                    ▼
            Status bar: ✓ SF Architect
            Notification: "Ready, wired to: Copilot, Cursor, Claude Code"

─────────────────────────────────────────────────────────────────────────────

FROM THIS POINT, THE AI ASSISTANT CAN USE THE ENGINE:

User (in Copilot / Cursor AI / Claude Code chat):
  "What breaks if I refactor AccountService.cls?"
         │
         ▼
AI calls MCP tool: analyze_local_blast_radius
         │
         ▼  (stdio JSON-RPC over the process pipe)
sf-architect-mcp (Python, running locally)
         │
         ▼
Apex parser + dependency graph
         │
         ▼
Result returned to AI → AI explains impact to user
```

---

## 5. How to Use the Extension (End-User Guide)

### Prerequisites

You need exactly **two things** on your machine before installing the extension:

1. **VS Code 1.101 or newer** — or **Cursor** (any recent version).
2. **`uv`** — a fast Python package manager. If you don't have it, the extension will tell you and link you to the install page.

That's it. Python itself does not need to be on your PATH — `uv` manages its own Python.

---

### Step 1 — Install the extension

**In VS Code (for GitHub Copilot users):**
1. Open Extensions (`Ctrl+Shift+X` / `Cmd+Shift+X`).
2. Search for **"Local SF Architect"**.
3. Click **Install**.

**In Cursor:**
1. Cursor uses Open VSX (not the VS Code Marketplace).
2. Open Extensions in Cursor → search "Local SF Architect" → Install.
   - Alternatively: download the `.vsix` file from GitHub Releases and run `Extensions: Install from VSIX` from the Command Palette.

---

### Step 2 — First activation

When VS Code/Cursor finishes loading after you install the extension, a notification appears in the bottom-right:

> "Local SF Architect can install its offline engine and wire it into your AI agents (Copilot, Cursor, Claude Code). Set up now?"

Click **"Set up now"**.

If you dismiss it and want to run setup later, open the Command Palette (`Ctrl+Shift+P`) and run:
```
Local SF Architect: Run Setup (Install + Configure)
```

---

### Step 3 — Setup runs automatically

You will see a progress spinner in the bottom-right. The four steps happen sequentially:

1. **Installing sf-local-architect…** — downloads the Python engine from PyPI (~60 seconds first time, faster after caching).
2. **Downloading embedding model (~130 MB, one time)…** — downloads the `bge-small-en-v1.5` model from Hugging Face. This is the only internet call at runtime and only happens once per machine.
3. **Seeding governor limits + architecture patterns…** — builds the two local databases (~30 seconds).
4. **Detecting and configuring agents** — writes the right config for each agent found.

Total first-run time: approximately 3–5 minutes depending on internet speed and machine performance. Every subsequent launch is instant.

---

### Step 4 — Verify it worked

After setup, the status bar (bottom-right) shows:

```
✓ SF Architect
```

Hovering over it shows which agents are wired, e.g.: `Local SF Architect ready (wired to Copilot, Cursor, Claude Code)`.

To double-check: open Command Palette → `Local SF Architect: Show Status`. A popup shows:
- Which host you are running in
- Whether `uv` was found and where
- Whether the engine is installed
- Whether the model and knowledge base are ready
- Which agents were detected

---

### Step 5 — Use it in your AI chat

**In VS Code with GitHub Copilot:**
1. Open Copilot Chat (`Ctrl+Shift+I` / `Cmd+Shift+I`).
2. Switch the dropdown from **Ask** to **Agent**.
3. Ask a question — Copilot automatically calls the right tool.

**In Cursor:**
1. Open the AI chat panel.
2. Ask a question in the chat.

**In Claude Code:**
1. Open a new Claude Code session in your terminal.
2. Ask a question.

**Example questions that work immediately:**

| Question | Tool called behind the scenes |
|---|---|
| "What breaks if I refactor AccountService.cls?" | `analyze_local_blast_radius` |
| "Will fetching 45,000 rows hit governor limits?" | `check_governor_limit` |
| "What is the best pattern for async Salesforce processing?" | `query_architect_db` |
| "Score the architecture health of this project" | `score_architecture` |
| "Draw a dependency diagram for the Order subsystem" | `generate_architecture_diagram` |
| "Scan my Apex for anti-patterns" | `score_architecture` + `lint` |

---

### Step 6 — Individual commands you can run any time

Open Command Palette (`Ctrl+Shift+P`) and type "Local SF Architect":

| Command | When to use it |
|---|---|
| Run Setup (Install + Configure) | Full setup from scratch or after a fresh install |
| Install / Update Engine | Pull the latest engine version from PyPI |
| Download Model + Seed Knowledge Base | Re-run the model download and seed (e.g. on a new machine) |
| Configure GitHub Copilot / VS Code | Wire/re-wire only Copilot |
| Configure Cursor | Wire/re-wire only Cursor |
| Configure Claude Code | Wire/re-wire only Claude Code |
| Configure All Detected Agents | Wire all at once |
| Rebuild Local Stores | Run if you see "schema mismatch" errors after an engine update |
| Show Logs | Open the OutputChannel to see detailed diagnostic output |
| Show Status | See a full status summary |

---

### Settings you can configure

Open VS Code Settings (`Ctrl+,`) and search "SF Architect":

| Setting | Default | What it does |
|---|---|---|
| `sfArchitect.enginePackage` | `sf-local-architect` | PyPI package name. Change to a specific version like `sf-local-architect==0.3.0` to pin |
| `sfArchitect.autoSetupOnActivate` | `true` | Whether to show the "Set up now?" prompt on first launch |
| `sfArchitect.autoConfigureAgents` | `true` | Whether to wire agents automatically (if false, prompts you after install) |
| `sfArchitect.autoDownloadModel` | `true` | Whether to download the embedding model during setup (disable for air-gapped environments) |
| `sfArchitect.uvPath` | _(empty)_ | Full absolute path to `uv` if it is not on PATH when VS Code launches |

---

### Troubleshooting

| Symptom | Fix |
|---|---|
| "uv not found" error | Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh \| sh` then restart VS Code, or set `sfArchitect.uvPath` to the full path |
| Status bar shows `$(cloud-download)` after setup | Run `Local SF Architect: Show Status` to see what is missing; usually means install failed — run `Local SF Architect: Install / Update Engine` |
| Schema mismatch error in AI chat | Run `Local SF Architect: Rebuild Local Stores` |
| Model download failed | Run `Local SF Architect: Download Model + Seed Knowledge Base` while connected to the internet |
| Copilot shows no tools | Make sure the mode dropdown in the Copilot Chat panel shows **Agent**, not Ask or Edit |
| Cursor shows no tools after extension install | Run `Local SF Architect: Configure Cursor` to write/update `~/.cursor/mcp.json`, then restart Cursor |
| Claude Code does not see the server | Run `Local SF Architect: Configure Claude Code`, then start a new Claude Code session |

---

## 6. Why the Extension Is Not Visible in the Marketplace Yet

> **Important:** If you search for "Local SF Architect" in VS Code or Cursor and nothing appears, this is the reason — the extension has been **built** but has **never been uploaded** to any registry. The `.vsix` package exists only on your laptop. Publishing is a manual, one-time process that requires creating external accounts. The steps below walk through it exactly.

There are **four things** blocking it from appearing in search right now:

| # | Blocker | Time to fix |
|---|---|---|
| 1 | Publisher account not created; placeholder ID in `package.json` | 5 minutes |
| 2 | No icon — Marketplace rejects extensions without one | 5 minutes |
| 3 | `vsce publish` command never run | 10 minutes |
| 4 | Not published to Open VSX (Cursor uses this, not the VS Code Marketplace) | 5 minutes |
| 5 | Engine not on PyPI — the extension can't install what doesn't exist | 10 minutes |

---

## 6a. Publish the Python Engine to PyPI (do this first)

The extension works by running `uv tool install sf-local-architect` on the user's machine. If the package does not exist on PyPI, that step fails for every end user. **Publish the engine before the extension.**

### Step 1 — Create a PyPI account

Go to [https://pypi.org/account/register/](https://pypi.org/account/register/) and create a free account.

After registering, verify your email address.

### Step 2 — Check the package name is available

Go to [https://pypi.org/project/sf-local-architect/](https://pypi.org/project/sf-local-architect/) — if the page shows "404 Not Found" the name is available and you can claim it.

### Step 3 — Create a PyPI API token

In PyPI → Account settings → **API tokens** → **Add API token**:
- Token name: anything (e.g. `publish-token`)
- Scope: **Entire account** (you can narrow it to just this project later)

Copy the token — it starts with `pypi-` and you only see it once.

### Step 4 — Build and upload

```bash
# From the repo root
cd "/Users/manvendrachaturvedi/Desktop/Local Salesforce Architect Engine"

# Build both the wheel and the source distribution
uv build

# Install twine (the PyPI upload tool)
uv tool install twine

# Recommended: test on TestPyPI first to make sure everything looks right
uv run twine upload --repository testpypi dist/*
# (username: __token__ | password: paste your TestPyPI token)

# Then upload to the real PyPI
uv run twine upload dist/*
# (username: __token__ | password: paste your PyPI API token)
```

After upload, the package is live at `https://pypi.org/project/sf-local-architect/` within 1–2 minutes.

> **Faster option for future releases:** Push a `v*` tag (e.g. `git tag v0.2.0 && git push origin v0.2.0`). The GitHub Actions workflow `.github/workflows/engine.yml` publishes to PyPI automatically using Trusted Publishing (no token required — configure the `pypi` environment in your repo settings).

---

## 6b. How to Publish to the VS Code Marketplace

### Phase 1 — Create your publisher account (one time, ~5 minutes)

**Step 1.1 — Sign in to the Marketplace**

Open [https://marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage) in a browser. Sign in with a Microsoft account (or create one for free).

Click **"Create publisher"** and fill in:
- **ID** — e.g. `manvendrachaturvedi` or `sf-architect-team`. This appears in the extension URL and cannot be changed later. Write it down.
- **Display name** — your name or team name
- **Description** — optional

**Step 1.2 — Update `package.json` with your real publisher ID**

Open `extension/package.json` and change line 6 from:
```json
"publisher": "local-sf-architect",
```
to:
```json
"publisher": "your-actual-publisher-id",
```

Replace `your-actual-publisher-id` with the ID you just registered above.

---

### Phase 2 — Add an icon (required — Marketplace rejects without it)

The Marketplace requires every extension to have an icon of at least 128×128 pixels in PNG format.

1. Create or obtain a 128×128 PNG image representing the extension.
2. Save it as `extension/media/icon.png`.
3. Open `extension/package.json` and add this line after the `"repository"` block:

```json
"icon": "media/icon.png",
```

The full top of `package.json` after this change should look like:

```json
{
  "name": "sf-local-architect",
  "displayName": "Local SF Architect",
  "publisher": "your-actual-publisher-id",
  ...
  "repository": {
    "type": "git",
    "url": "https://github.com/..."
  },
  "icon": "media/icon.png",
  "main": "./dist/extension.js",
  ...
}
```

---

### Phase 3 — Create a Personal Access Token (PAT)

The `vsce` publish tool authenticates with a PAT from Azure DevOps.

1. Go to [https://dev.azure.com](https://dev.azure.com) and sign in with the **same Microsoft account** you used to create the publisher.
2. Click your profile picture (top right) → **Personal access tokens** → **New Token**.
3. Fill in:
   - **Name**: anything (e.g. `vsce-publish`)
   - **Organization**: select **All accessible organizations**
   - **Expiration**: 1 year (maximum)
   - **Scopes**: click "Custom defined" → find **Marketplace** → check **Manage**
4. Click **Create**. Copy the token immediately — you will not see it again.

---

### Phase 4 — Run the publish commands

Open a terminal on your Mac:

```bash
cd "/Users/manvendrachaturvedi/Desktop/Local Salesforce Architect Engine/extension"

# Install dependencies (uses the lockfile — exact versions)
npm ci

# Log in with your publisher ID and the PAT you just created
npx vsce login your-actual-publisher-id
# Paste the PAT when prompted

# Build the production bundle (minified, no source maps)
npm run package

# Package into a .vsix file so you can inspect it before uploading
npx vsce package --no-dependencies
# This creates: sf-local-architect-0.1.0.vsix

# Publish to the VS Code Marketplace
npx vsce publish --no-dependencies
```

After a few minutes of processing on Microsoft's servers, the extension is live at:
```
https://marketplace.visualstudio.com/items?itemName=your-actual-publisher-id.sf-local-architect
```

Users can now find it by searching "Local SF Architect" in VS Code.

---

### Publish updates (subsequent versions)

1. Bump the version in `extension/package.json` (e.g. `"version": "0.1.0"` → `"0.2.0"`).
2. Add an entry to `extension/CHANGELOG.md` describing what changed.
3. Commit, create a tag, and push:

```bash
git add extension/package.json extension/CHANGELOG.md
git commit -m "chore: release extension v0.2.0"
git tag ext-v0.2.0
git push origin main ext-v0.2.0
```

The GitHub Actions workflow (`.github/workflows/extension.yml`) runs automatically:
1. Installs Node 20, runs `npm ci`, typechecks, lints, builds, and packages.
2. Publishes to the VS Code Marketplace using the `VSCE_PAT` secret.
3. Publishes to Open VSX using the `OVSX_PAT` secret.

---

### Adding the GitHub Secrets (required for automated CI publish)

In your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
|---|---|
| `VSCE_PAT` | The Azure DevOps Personal Access Token you created in Phase 3 above |
| `OVSX_PAT` | Your Open VSX access token (see Section 6c below) |

---

## 6c. How to Publish to Open VSX (required for Cursor)

**Why this matters:** Cursor does not use the VS Code Marketplace. It uses a separate registry called [Open VSX](https://open-vsx.org). If you only publish to the VS Code Marketplace, users searching inside Cursor will still not find the extension. You must publish to both.

### Step 1 — Create an Open VSX account

Go to [https://open-vsx.org](https://open-vsx.org) and click **Sign in with GitHub**. Authorize the app.

### Step 2 — Generate a publish token

- Click your profile name (top right) → **Settings** → **Access Tokens**.
- Click **Generate new token**.
- Give it a name (e.g. `publish`) and check the **publish** permission.
- Copy the token immediately.

### Step 3 — Publish the extension

```bash
cd "/Users/manvendrachaturvedi/Desktop/Local Salesforce Architect Engine/extension"

# Make sure you have the .vsix file built (from Phase 4 above)
# If not, build it first:
npm run package
npx vsce package --no-dependencies

# Publish to Open VSX
npx ovsx publish sf-local-architect-0.1.0.vsix --pat YOUR_OVSX_TOKEN
```

After upload, the extension appears in Cursor's extension search within a few minutes.

> For subsequent releases, just push the `ext-v*` tag. The GitHub Actions workflow publishes to Open VSX automatically using the `OVSX_PAT` secret.

---

## 7. CI / GitHub Actions — What Triggers What

Two workflow files were created under `.github/workflows/`.

### `engine.yml` — Python engine CI + PyPI publish

| Trigger | What runs |
|---|---|
| Push to `main` | Install deps → ruff lint → pytest → build wheel → verify seed data in wheel |
| Pull request to `main` | Same as above |
| Push a `v*` tag (e.g. `v0.3.0`) | Tests + wheel check + **publish to PyPI** |

The PyPI publish uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token needed, just a `pypi` GitHub Environment configured with the package name.

### `extension.yml` — TypeScript extension CI + Marketplace publish

| Trigger | What runs |
|---|---|
| Push to `main` | `npm ci` → typecheck → lint → build → `vsce package` → upload `.vsix` as artifact |
| Pull request to `main` | Same |
| Push an `ext-v*` tag (e.g. `ext-v0.2.0`) | Build + **publish to VS Code Marketplace** + **publish to Open VSX** |

The two workflows use different tag prefixes (`v*` vs `ext-v*`) so you can release the engine and the extension independently.

---

## 8. What You Still Need to Do — Master Checklist

This is the complete ordered checklist of every manual step still required before the extension appears in VS Code and Cursor search. Check them off as you go.

### A. Python engine (do first)

- [ ] **1.** Create a PyPI account at [pypi.org/account/register](https://pypi.org/account/register/)
- [ ] **2.** Verify your email on PyPI
- [ ] **3.** Create a PyPI API token (Account settings → API tokens → Add API token → scope: Entire account)
- [ ] **4.** Run `uv build` from the repo root to build the wheel and sdist
- [ ] **5.** Run `uv run twine upload dist/*` to publish to PyPI (username: `__token__`, password: your API token)
- [ ] **6.** Verify the package is live: [pypi.org/project/sf-local-architect](https://pypi.org/project/sf-local-architect/)

### B. VS Code Marketplace (for VS Code + Copilot users)

- [ ] **7.** Create a publisher account at [marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage) — sign in with a Microsoft account
- [ ] **8.** Write down your publisher ID (e.g. `manvendrachaturvedi`) — it cannot be changed after creation
- [ ] **9.** Update `extension/package.json` line 6: `"publisher": "your-actual-publisher-id"`
- [ ] **10.** Add a 128×128 PNG icon at `extension/media/icon.png`
- [ ] **11.** Add `"icon": "media/icon.png"` to `extension/package.json` (after the `"repository"` block)
- [ ] **12.** Create an Azure DevOps PAT at [dev.azure.com](https://dev.azure.com): Organization = All, Scope = Marketplace → Manage
- [ ] **13.** Run `npx vsce login your-publisher-id` and paste the PAT
- [ ] **14.** Run `npm run package && npx vsce publish --no-dependencies` from the `extension/` folder
- [ ] **15.** Verify it is live: `https://marketplace.visualstudio.com/items?itemName=your-publisher-id.sf-local-architect`

### C. Open VSX (for Cursor users — required for Cursor search)

- [ ] **16.** Create an account at [open-vsx.org](https://open-vsx.org) using GitHub sign-in
- [ ] **17.** Generate a publish token (Profile → Settings → Access Tokens → Generate new token → check **publish**)
- [ ] **18.** Run `npx ovsx publish sf-local-architect-0.1.0.vsix --pat YOUR_OVSX_TOKEN` from the `extension/` folder
- [ ] **19.** Verify it is live by searching "Local SF Architect" in Cursor's extension panel

### D. GitHub Actions (enables automated future releases)

- [ ] **20.** Add `VSCE_PAT` secret in GitHub repo → Settings → Secrets and variables → Actions
- [ ] **21.** Add `OVSX_PAT` secret in the same place
- [ ] **22.** (Optional) Set up PyPI Trusted Publishing at pypi.org → Account settings → Publishing → Add pending publisher (GitHub Actions OIDC — no token needed)
- [ ] **23.** Test the CI release: push a `v0.2.0` tag for engine, `ext-v0.1.1` for extension — verify both publish automatically

---

## 9. Frequently Asked Questions

**Q: Does the extension work if I don't have GitHub Copilot?**  
A: Yes. In VS Code without Copilot, the extension still installs the engine and can configure Cursor and Claude Code. For VS Code specifically, you need Copilot (paid subscription) to use MCP tools in chat. The CLI commands (`sf-architect lint`, `sf-architect score`) work without any AI subscription.

**Q: Can I use the extension in Cursor without a Cursor subscription?**  
A: The extension installs and wires the MCP server into Cursor regardless of subscription. Whether Cursor's AI can call MCP tools depends on your Cursor plan.

**Q: What happens if I run setup twice?**  
A: All operations are idempotent. `uv tool install --upgrade` updates the engine if a newer version exists. The config merges never duplicate entries. Before overwriting any JSON file, a timestamped backup is created next to the original.

**Q: The extension installed but the engine did not. What happened?**  
A: Open `Local SF Architect: Show Logs`. Look for the `exec: uv tool install` line and what followed it. The most common cause is `uv` not being found — check `sfArchitect.uvPath` in settings or verify `which uv` in a terminal.

**Q: Can I use a specific version of the engine?**  
A: Yes. Set `sfArchitect.enginePackage` to `sf-local-architect==0.2.0` (or any version on PyPI) and run `Local SF Architect: Install / Update Engine`.

**Q: My Salesforce code is in a different folder from where VS Code is open. Will the extension still work?**  
A: Yes. The engine itself and the MCP tools work anywhere. For tools like `analyze_local_blast_radius` you pass the full path to the file, and for `score_architecture` you pass the full path to the SFDX project root. These paths are not tied to which folder VS Code has open.

**Q: Does the extension send any data anywhere?**  
A: No. The extension only makes network calls to PyPI (to install the engine) and to Hugging Face (to download the embedding model). Both only happen during setup. After that, the engine runs fully offline. Your Salesforce code never leaves your machine.

**Q: How do I uninstall cleanly?**  
A: Uninstall the extension from the Extensions panel. To remove the engine: `uv tool uninstall sf-local-architect`. To remove all local data: `rm -rf ~/.sf-architect`.
