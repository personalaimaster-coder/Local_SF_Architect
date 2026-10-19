# sf-compress (`sfc`)

**A context/token optimizer for AI coding agents (Cursor, Claude Code, …) doing Salesforce development.**

Verbose Salesforce CLI output — deploy reports, `retrieve preview` tables, `--json`
payloads, Apex debug logs — is a large, highly compressible share of the tokens
that land in an agent's context window. `sfc` wraps your `sf` commands, stores the
**full** raw output on disk, and prints a compressed view (errors, failures,
summaries, counts) so a 200k-token deploy report or debug log doesn't flood the
context. Nothing is lost: every compressed output ends with an id you can expand
on demand (`sfc show <id>`).

Measured on real corpus data: `retrieve preview` 214k→~1.4k tokens (99.3%),
Apex debug logs ~99%, query `--json`→CSV ~83%. Generic tools (git/npm) are already
terse and pass through untouched.

> **Dev-support tool only.** Use it during active dev loops (deploy/validate, test
> runs, debug logs, retrieve/preview, data queries). Default is **ON**, so dev
> commands compress out of the box; run `sfc off` during analysis/architecture
> work, where full detail matters.

---

## Requirements

- Python **3.9+** (the core CLI is standard-library only — no runtime deps).
- Salesforce CLI (`sf`) for the commands you route through it.
- Optional: Node.js (`npx`) for the DX MCP benchmark; a `graphify-sf` install for
  the code-graph feature (see below).

## Install the CLI

The package isn't on PyPI yet, so install from a clone. `pipx` is recommended so
`sfc` is available on your PATH globally (independent of any project's venv):

```bash
git clone https://github.com/personalaimaster-coder/sf-compress.git
cd sf-compress

pipx install .            # global `sfc` command (recommended)
# or:
pip install .             # into the current environment
# or, for local development (edit-in-place):
pip install -e .
```

Optional exploration-graph extra (pulls in `graphify-sf`, which needs Python 3.10+):

```bash
pipx install '.[graph]'
```

Verify:

```bash
sfc --version
```

## Use it in an existing workspace / repo

`sfc` is **project-local**: all of its state lives in a `.sfc/` directory at your
project root, and that directory is auto-added to a local `.gitignore` so it never
pollutes your repo's git status.

### One-command setup (recommended)

Run the wizard once per project. It installs the Agent Skill, registers the sfc
**MCP server** with your coding agent, and seeds config — **no manual
copy-paste**. It leaves sfc **OFF** (dev-support only; you turn it on when you
start a dev loop):

```bash
cd /path/to/your-salesforce-project

sfc setup                 # interactive: detects Cursor / Claude Code, confirms each step
# or drive it non-interactively (e.g. from a coding agent or CI):
sfc setup --yes                 # auto-detect the agent, accept defaults
sfc setup --agent cursor --yes  # target a specific agent
sfc setup --yes --json          # machine-readable summary of what it did
```

Your agent can also run this itself — see [Make your AI agent use it](#make-your-ai-agent-use-it).
After setup, **reload/restart your agent** so it picks up the MCP server.

### Then, day to day

```bash
sfc on                    # activate for this project (creates ./.sfc/)
sfc status                # ACTIVE + current filter toggles

# route verbose Salesforce commands through the wrapper:
sfc run -- sf project deploy start -d force-app
sfc run -- sf apex run test --code-coverage --result-format human
sfc run -- sf apex get log -i <logId>
sfc run -- sf project retrieve preview
sfc run -- sf data query -q "SELECT Id, Name FROM Account LIMIT 200" --json

# the child command's exit code passes through unchanged.
# each run prints a footer, e.g.:
#   [sfc 20260921-...-ab12] sf-deploy filtered: ~52000 -> ~800 tokens (98.5% smaller). Full output: sfc show 20260921-...-ab12

# expand the full raw output when you need detail (narrow it, don't dump it):
sfc show <id> --grep "MyClass|Error"
sfc show <id> --head 100

sfc stats                 # raw vs emitted tokens saved, per family
sfc off                   # back to fully dormant (default)
```

When `sfc off`, `sfc run` refuses to execute (exit 3) — the off-path is completely
dormant, so you can cleanly A/B measure with vs without it.

## Make your AI agent use it

`sfc` ships an Agent Skill (bundled at
[`skills/sf-compress/SKILL.md`](skills/sf-compress/SKILL.md)) that tells the agent
to check `sfc status` and route `sf` commands through `sfc run` **only** when
active — and never during analysis/architecture work.

You don't copy any files by hand. `sfc setup` installs the skill and registers an
**MCP server** so the agent gets sfc as native tools:

- **`sfc setup`** — installs the skill into `.agents/skills/` (cross-tool
  convention) and each detected agent's own skills dir, and merges an
  `sf-compress` entry into the agent's MCP config (`.cursor/mcp.json` for Cursor,
  `.mcp.json` for Claude Code), preserving any servers you already have.
- **`sfc mcp`** — the MCP stdio server that `setup` registers. It exposes these
  tools to the agent:

  | MCP tool | purpose |
  |---|---|
  | `sfc_setup` | wire sfc into the project (skill + MCP + config); ON by default |
  | `sfc_install_skill` | (re)install just the skill |
  | `sfc_status` / `sfc_on` / `sfc_off` | check / change activation |
  | `sfc_run` | run a Salesforce command and get the compressed view |
  | `sfc_show` | expand a stored output by id (grep/head/tail) |
  | `sfc_stats` | token savings per family |
  | `sfc_graph` | query the graphify-sf code graph |

So a coding agent can bootstrap the whole thing itself: run `sfc setup --yes` (or
call the `sfc_setup` MCP tool once the server is registered), then use `sfc_run` /
`sfc_show` instead of raw `sf`. Skills use progressive loading — full instructions
load only when the task matches.

> The skill file is shipped inside the package, so `sfc setup` / `sfc
> install-skill` work from any install. Once this repo is published you can also
> use the skills CLI: `npx skills add personalaimaster-coder/sf-compress`.

## Command reference

| command | what it does |
|---|---|
| `sfc setup [--agent A] [--yes] [--activate] [--json]` | wizard: install skill, register MCP server, seed config |
| `sfc install-skill [--agent A] [--dest DIR]` | install/refresh just the Agent Skill |
| `sfc mcp` | run the MCP stdio server (registered by `sfc setup`) |
| `sfc on` / `sfc off` | activate / deactivate for this project (default on) |
| `sfc status` | show active state + per-family filter toggles |
| `sfc run -- <cmd…>` | run a command, store full output, print compressed view |
| `sfc show <id> [--grep P] [--head N] [--tail N]` | print / filter a stored full output |
| `sfc stats` | token savings per command family (from `.sfc/metrics.jsonl`) |
| `sfc graph <args…>` | query the graphify-sf code graph (needs `exploration-graph` on) |
| `sfc collect` | org workbench: re-collect real CLI fixtures (needs an org) |
| `sfc bench` | org workbench: benchmark raw CLI vs Salesforce DX MCP (needs an org) |

## Configuration

`.sfc/config.json` (created on first `sfc on`) — turn any component off to measure
its impact independently:

```json
{
  "filters": {
    "sf-deploy": true,
    "sf-apex-test": true,
    "sf-debug-log": true,
    "sf-json": true,
    "sf-table": true,
    "deltas": true
  },
  "store": { "retention": 50 },
  "exploration-graph": false,
  "dx-mcp-routing": false
}
```

`.sfc/` layout: `state.json` (on/off), `config.json` (toggles), `outputs/<id>.txt`
(full raw captures, pruned to `retention`), `metrics.jsonl` (per-call token
metering, only while active).

### Deploy-retry deltas

Re-running the same deploy/validate diffs against the previous run and shows only
**NEW / RESOLVED** errors plus an unchanged count (with a `sfc show <prev-id>`
pointer) instead of re-dumping the whole report. Toggle with `filters.deltas`.

### Exploration graph (`sfc graph`)

When you need to locate code or dependencies during a dev task, prefer the graph
over reading many large files. Requires `sfc on`, the `exploration-graph` toggle,
and a `graphify-sf` install (tested against **0.4.1**):

```bash
# enable once: set "exploration-graph": true in .sfc/config.json
sfc graph query "where is AccountTrigger used?"   # token-budgeted (default 2000)
sfc graph explain "AccountService"
```

**What it's good for vs. its limits.** graphify-sf builds a real, offline
structural map (classes ↔ methods ↔ objects ↔ triggers) and returns
**token-budgeted** answers — a big win over reading many 150k-token files just to
orient yourself. But its Apex extraction is heuristic and **incomplete for
reverse/caller lookups**: in testing (v0.4.1) a class that called
`AccountService.getActive()` was left as an isolated node (the call edge was
missed), and a `query "where is X used?"` returned the definition without all its
callers. So treat `sfc graph` as a **fast first-pass locator/hint**, not an
authoritative "who calls X" source — confirm edits against the actual file (which
the graph has now narrowed you to). This is why the toggle is **off by default**.

### Org workbench (run on a machine with an org)

`sfc collect` re-collects real fixture outputs, and `sfc bench` benchmarks raw CLI
vs the Salesforce DX MCP server. These are built to be run against a live org and
shared with your team — see the runbook at
[`docs/org-workbench.md`](docs/org-workbench.md). Org-side steps in `sfc collect`
are gated behind `--allow-org-writes`.

## How it works (and privacy)

- Filtering happens at **capture time**, before the output ever reaches the
  agent. The wrapper runs your command, saves the full raw output locally, and
  emits the compressed view. This is deliberately agent-agnostic:
  - **Agents that don't persist tool results** (e.g. Cursor re-sends/re-runs
    output each turn): capture-time compression is the *only* thing that works,
    since there is nothing to post-process later.
  - **Agents that do persist tool results** (e.g. Claude Code): the compressed
    view — plus the stable `<id>` — is what stays in the transcript across turns,
    so the saving compounds instead of a 200k-token dump lingering in context.
    Expansion is on demand via `sfc show <id>` (itself re-narrowable with
    `--grep/--head/--tail`).

  Either way the contract is the same: the agent only ever sees the compressed
  output + an id, and the full raw output is on disk. Nothing about the design
  assumes a particular agent's persistence behavior.
- **Everything stays local** under `.sfc/`. Nothing is sent anywhere.
- Token counts are `chars / 4` estimates, consistent across the project.

## Development

```bash
python3 -m unittest discover -s tests    # full suite (stdlib unittest, no deps)
```

Project memory and design decisions live in [`MEMORY.md`](MEMORY.md).

## License

MIT.
