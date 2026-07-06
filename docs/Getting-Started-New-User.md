# Getting Started with Local SF Architect — A First-Time User Guide

> **Who this is for:** Someone who has never seen this extension before and just wants
> to install it and try it out. No prior knowledge assumed. Follow the steps in order.

---

## Table of Contents

1. [What is this? (30-second version)](#1-what-is-this-30-second-version)
2. [Before you start — prerequisites](#2-before-you-start--prerequisites)
3. [Step 1 — Install `uv` (the only manual dependency)](#3-step-1--install-uv-the-only-manual-dependency)
4. [Step 2 — Install the extension](#4-step-2--install-the-extension)
5. [Step 3 — Let first-run setup do its thing](#5-step-3--let-first-run-setup-do-its-thing)
6. [Step 4 — Verify it worked](#6-step-4--verify-it-worked)
7. [Step 5 — Turn on Agent mode and ask your first question](#7-step-5--turn-on-agent-mode-and-ask-your-first-question)
8. [Prompts to try right away](#8-prompts-to-try-right-away)
9. [Optional — try it from the terminal (no AI needed)](#9-optional--try-it-from-the-terminal-no-ai-needed)
10. [Command Palette reference](#10-command-palette-reference)
11. [Settings you can change](#11-settings-you-can-change)
12. [Troubleshooting](#12-troubleshooting)
13. [Privacy — what leaves your machine](#13-privacy--what-leaves-your-machine)
14. [Uninstalling cleanly](#14-uninstalling-cleanly)
15. [Quick checklist (copy/paste)](#15-quick-checklist-copypaste)

---

## 1. What is this? (30-second version)

**Local SF Architect** is a fully **local, offline** assistant for Salesforce
architects. It plugs into your AI-powered editor (GitHub Copilot in VS Code,
Cursor, or the Claude Code CLI) and gives the AI a set of specialised, deterministic
Salesforce tools:

| You ask… | The engine does… |
|---|---|
| "Will this code hit governor limits?" | Exact governor-limit math (Salesforce API limits), not a guess |
| "What breaks if I change this Apex class?" | Parses your repo and computes the blast radius (immediate + transitive) |
| "What's the best pattern for this?" | Semantic search over a curated local architecture-pattern knowledge base |
| "Draw me a diagram" | Generates a Mermaid or draw.io diagram from your actual code |
| "How healthy is this architecture?" | Six-pillar scorecard (security, performance, scalability, maintainability, reliability, cost) |
| "Lint my Apex" | Flags anti-patterns (SOQL-in-loops, deep nesting, missing bulkification) |

**Important:** The extension is only a thin installer/configurator. The real work is
done by a Python "engine" that the extension installs for you. Your Salesforce code
**never leaves your machine** — the only network calls are the one-time downloads
during setup (see [Privacy](#13-privacy--what-leaves-your-machine)).

---

## 2. Before you start — prerequisites

You need just **two things** on your machine:

| Requirement | Details |
|---|---|
| **VS Code 1.101+** *or* **Cursor** | Any recent Cursor build works. VS Code must be **1.101 or newer** (that's when the native MCP support the extension uses became available). Check via **Code → About**. |
| **`uv`** | A fast Python package manager. It's the only thing you install by hand. The extension installs and manages everything else (including Python itself). |

Notes:

- You do **not** need Python on your PATH — `uv` brings its own.
- You do **not** need a GPU or any special hardware.
- To actually use the AI tools in chat you need an AI assistant that supports MCP:
  **GitHub Copilot (Agent mode)** in VS Code, **Cursor's** AI, or the **Claude Code** CLI.
  (The command-line tools like `lint` and `score` work with no AI subscription at all.)

---

## 3. Step 1 — Install `uv` (the only manual dependency)

Skip this if you already have `uv`. To check, open a terminal and run `uv --version`.

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, **fully quit and reopen** VS Code / Cursor so it picks up the
updated PATH. (If the extension later says it can't find `uv`, see
[Troubleshooting](#12-troubleshooting).)

Official install guide: https://docs.astral.sh/uv/getting-started/installation/

---

## 4. Step 2 — Install the extension

### If you use VS Code (with GitHub Copilot)

1. Open the **Extensions** panel (`Cmd+Shift+X` on macOS / `Ctrl+Shift+X` on Windows/Linux).
2. Search for **`Local SF Architect`**.
3. Click **Install**.

That's it — it's published on the VS Code Marketplace.

### If you use Cursor

Cursor uses a different registry (Open VSX), and the extension is **not on Open VSX
yet**, so searching inside Cursor will not find it. Install it from the packaged
`.vsix` file instead:

1. Get the file `sf-local-architect-0.1.2.vsix`. It lives in this project under
   [`extension/`](../extension/). (If you were given the project folder, it's already there.)
2. In Cursor, open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`).
3. Run **`Extensions: Install from VSIX…`**.
4. Select the `.vsix` file.
5. Reload Cursor when prompted.

> The same VSIX method also works in VS Code if you'd rather install from a file than
> from the Marketplace.

---

## 5. Step 3 — Let first-run setup do its thing

The extension activates automatically once the editor finishes loading (or as soon as
it detects a Salesforce project — a file named `sfdx-project.json`). On the **very
first** activation you'll see a notification in the bottom-right:

> "Local SF Architect can install its offline engine and wire it into your AI agents
> (Copilot, Cursor, Claude Code). Set up now?"

Click **"Set up now"**.

> Missed the prompt or clicked "Later"? Open the Command Palette and run
> **`Local SF Architect: Run Setup (Install + Configure)`**.

A progress spinner appears and these steps run in order:

1. **Install the engine** — runs `uv tool install --upgrade sf-local-architect`
   (downloads the Python engine from PyPI). ~1 minute the first time.
2. **Download the models (~210 MB, one time)** — pulls the embedding model and the
   reranker model from Hugging Face. This is the largest download and only happens
   once per machine. (Can be disabled for offline/air-gapped machines — see settings.)
3. **Seed the knowledge base** — builds the local governor-limits database and the
   architecture-patterns vector store from bundled data. ~30 seconds.
4. **Detect & configure your agents** — writes the correct MCP config for each agent
   it finds (Copilot / Cursor / Claude Code). Any existing config file is **backed up
   first** (a timestamped `.bak` copy is created next to it), so nothing is lost.

**Total first-run time: roughly 3–5 minutes** depending on your internet speed. Every
launch after that is instant — nothing re-downloads.

When it finishes you'll get a notification like:
`Local SF Architect is ready and wired to: Copilot, Cursor, Claude Code.`

---

## 6. Step 4 — Verify it worked

Two quick checks:

1. **Status bar** (bottom-right of the window) shows **`✓ SF Architect`**. Hover over
   it to see which agents were wired.
2. **Command Palette → `Local SF Architect: Show Status`.** A popup summarises:
   - Which host you're in (VS Code vs Cursor)
   - Whether `uv` was found (and where)
   - Whether the engine is installed
   - Whether the model + knowledge base are ready
   - Which agents were detected and configured

If anything shows as missing, the popup gives you **Run Setup** and **Show Logs**
buttons.

---

## 7. Step 5 — Turn on Agent mode and ask your first question

The tools only work when your AI assistant is in a mode that can **call tools** (MCP).
This is the single most common thing new users miss.

**VS Code + GitHub Copilot:**
1. Open Copilot Chat (`Cmd+Shift+I` / `Ctrl+Shift+I`).
2. In the chat box, switch the mode dropdown from **Ask** to **Agent**.
3. Ask a question (see below). Copilot picks the right tool automatically.

**Cursor:**
1. Open the AI chat panel.
2. (Optional) Confirm the server appears under **Cursor → Settings → MCP** with a
   green dot.
3. Ask a question in chat.

**Claude Code (CLI):**
1. Open a new Claude Code session in your terminal (start it fresh so it re-reads its
   config).
2. Ask a question.

---

## 8. Prompts to try right away

Paste any of these into your AI chat (in Agent mode). Behind the scenes the AI calls
the matching tool:

| Try asking… | Tool it triggers |
|---|---|
| "What is the best pattern for async processing in Salesforce?" | `query_architect_db` |
| "I'm fetching 45,000 rows in a loop — will I hit the SOQL governor limit?" | `check_governor_limit` |
| "What will break if I refactor `AccountService.cls`?" | `analyze_local_blast_radius` |
| "Draw me the dependency diagram for the Order subsystem." | `generate_architecture_diagram` |
| "Score the architecture health of this project." | `score_architecture` |
| "Always generate draw.io diagrams from now on." | `set_deliverable_preference` |
| "Learn the patterns from this Salesforce docs page: `<url>`" | `sync_latest_patterns` |

> Tip: for file- or project-specific tools (blast radius, scoring), it helps to give the
> AI the **full path** to the Apex file or the SFDX project root. These tools work even
> if your Salesforce code is in a different folder than the one the editor has open.

---

## 9. Optional — try it from the terminal (no AI needed)

If you want to poke at the engine directly (no AI subscription required), the engine
ships a CLI. Once the extension has installed it, `sf-architect` is available:

```bash
# Check the environment is healthy
sf-architect doctor

# Lint an SFDX project for architectural issues (exit code 1 if issues found — CI-friendly)
sf-architect lint path/to/your/sfdx-project

# Print an architecture scorecard for a project
sf-architect score path/to/your/sfdx-project

# Print the version
sf-architect --version
```

> If your shell can't find `sf-architect`, it's installed under `uv`'s tool bin
> directory. Run `uv tool dir --bin` to see where, or just call it via
> `uv tool run --from sf-local-architect sf-architect doctor`.

---

## 10. Command Palette reference

Open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and type "Local SF Architect":

| Command | When to use it |
|---|---|
| **Run Setup (Install + Configure)** | The all-in-one first-time setup, or a fresh redo |
| **Install / Update Engine** | Pull the latest engine version from PyPI |
| **Download Model + Seed Knowledge Base** | Re-download the models and rebuild the knowledge base (e.g. on a new machine) |
| **Configure GitHub Copilot / VS Code** | Wire/re-wire Copilot only |
| **Configure Cursor** | Wire/re-wire Cursor only (`~/.cursor/mcp.json`) |
| **Configure Claude Code** | Wire/re-wire Claude Code only |
| **Configure All Detected Agents** | Wire everything at once |
| **Rebuild Local Stores** | Fix "schema mismatch" errors after an engine update |
| **Show Logs** | Open the detailed diagnostic output channel |
| **Show Status** | See the full status summary |

There's also a 3-step **"Get started with Local SF Architect"** walkthrough in the
editor's Welcome tab if you prefer a guided UI.

---

## 11. Settings you can change

Open Settings (`Cmd+,` / `Ctrl+,`) and search **"SF Architect"**:

| Setting | Default | What it does |
|---|---|---|
| `sfArchitect.enginePackage` | `sf-local-architect` | PyPI package name. Set to `sf-local-architect==0.2.1` to pin a specific version. |
| `sfArchitect.autoSetupOnActivate` | `true` | Show the "Set up now?" prompt on first launch. |
| `sfArchitect.autoConfigureAgents` | `true` | Wire detected agents automatically (no per-agent prompt). |
| `sfArchitect.autoDownloadModel` | `true` | Download the ~210 MB models during setup. **Turn off for air-gapped machines.** |
| `sfArchitect.uvPath` | *(empty)* | Absolute path to `uv` if it isn't on PATH when the editor launches. |

---

## 12. Troubleshooting

| Symptom | Fix |
|---|---|
| **"uv not found"** error | Install `uv` (see [Step 1](#3-step-1--install-uv-the-only-manual-dependency)), then **fully restart** the editor. Still failing? Find it with `which uv` (macOS/Linux) or `where uv` (Windows) and paste the full path into the `sfArchitect.uvPath` setting. |
| **Status bar stuck on a download/cloud icon** | Setup didn't finish. Run **`Local SF Architect: Show Status`** to see what's missing, then **`Install / Update Engine`** or **`Run Setup`**. |
| **Copilot shows no SF tools** | Make sure the Copilot Chat mode dropdown says **Agent** (not Ask or Edit). |
| **Cursor shows no tools after install** | Run **`Local SF Architect: Configure Cursor`**, then **restart Cursor**. Check **Cursor → Settings → MCP** for a green dot. |
| **Claude Code doesn't see the server** | Run **`Local SF Architect: Configure Claude Code`**, then start a **new** Claude Code session. |
| **"schema mismatch" error in chat** | Run **`Local SF Architect: Rebuild Local Stores`**. |
| **Model download failed / offline** | Reconnect to the internet and run **`Local SF Architect: Download Model + Seed Knowledge Base`**. |
| **Nothing happened after install** | The extension activates on startup or when it detects a Salesforce project. Open a folder, or just run **`Local SF Architect: Run Setup`** manually. Use **`Show Logs`** to see details. |

---

## 13. Privacy — what leaves your machine

- The engine runs **locally** and talks to your editor over stdio (no network port, no
  auth surface).
- **Your Salesforce code never leaves your machine.**
- The **only** outbound network calls happen during setup:
  1. Installing the engine from **PyPI**.
  2. Downloading the **embedding + reranker models (~210 MB)** from Hugging Face.
- After setup, the engine is fully offline. There is no telemetry and no "phone home".
- Optional web scraping (`sync_latest_patterns`) is off by default and can only reach
  an allow-listed set of official Salesforce documentation domains.
- All local state lives under `~/.sf-architect/` and is never committed to git.

---

## 14. Uninstalling cleanly

1. Uninstall the extension from the Extensions panel.
2. Remove the engine: `uv tool uninstall sf-local-architect`
3. Remove all local data: `rm -rf ~/.sf-architect`
4. (Optional) The extension backed up any MCP config it touched as timestamped `.bak`
   files next to the originals (`~/.cursor/mcp.json`, `~/.claude.json`, etc.) — delete
   those backups if you don't need them.

---

## 15. Quick checklist (copy/paste)

- [ ] Install `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and restart the editor
- [ ] Confirm the editor is VS Code **1.101+** or Cursor
- [ ] Install the extension — **VS Code:** search "Local SF Architect" in Extensions · **Cursor:** `Extensions: Install from VSIX…` using `extension/sf-local-architect-0.1.2.vsix`
- [ ] Click **"Set up now"** on the first-run prompt (or run **Run Setup** from the Command Palette)
- [ ] Wait ~3–5 min for engine install + ~210 MB model download + seeding
- [ ] Confirm the status bar shows **✓ SF Architect** (or run **Show Status**)
- [ ] Open your AI chat in **Agent mode**
- [ ] Ask: *"Will fetching 45,000 rows in a loop hit governor limits?"*
- [ ] 🎉 You're up and running

---

### Good to know (current state, as of this guide)

- **Engine:** `sf-local-architect` **v0.2.1** is live on **PyPI** — auto-install works out of the box.
- **VS Code Marketplace:** the extension **v0.1.2** is live — VS Code users can search & install directly.
- **Open VSX (used by Cursor):** **not published yet** — Cursor users must install from the `.vsix` file for now.
