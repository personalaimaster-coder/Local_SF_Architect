# Agent Skills

This project ships a project-native **Agent Skill** that makes AI coding agents
reliably use the Local SF Architect engine. This page explains what it is, how to
install it, and how to add compatible third-party Salesforce skill libraries
alongside it.

---

## What is an Agent Skill?

An [Agent Skill](https://developer.salesforce.com/docs/platform/agentforcevibes/guide/afv-skills.html)
is a small, directory-based instruction package: a required `SKILL.md` (with YAML
frontmatter) plus optional `references/`, `scripts/`, and `assets/` folders. Skills
load **on demand** — the agent reads each skill's name + description at startup and
only pulls the full body when your request matches. The format is an open spec
supported by Claude Code, Cursor, Codex, VS Code Copilot, Agentforce Vibes, and many
other tools.

## The bundled skill: `local-sf-architect`

Lives at [`skills/local-sf-architect/`](../skills/local-sf-architect/):

- [`SKILL.md`](../skills/local-sf-architect/SKILL.md) — a **router** skill. It tells
  the agent to act as a senior Salesforce architect and, crucially, **when to call
  which of this engine's MCP tools** (`query_architect_db`, `check_governor_limit`,
  `analyze_local_blast_radius`, `score_architecture`,
  `generate_architecture_diagram`, `set_deliverable_preference`,
  `sync_latest_patterns`) instead of guessing.
- [`references/tools.md`](../skills/local-sf-architect/references/tools.md) — the exact
  inputs, outputs, and shared response envelope for each tool (loaded only when
  needed).

### How it complements the MCP engine

The MCP engine gives the agent *grounded tools*; this skill gives the agent the
*judgment to use them at the right moment*. Without it, an agent only calls the tools
if it happens to decide to. With it, architecture questions reliably route through the
local, offline engine — and the skill enforces the engine's core rules (config over
code, security first, hard governor limits override soft advice, retrieved content is
untrusted data, always surface confidence + warnings).

It is the portable, cross-tool evolution of the opt-in persona files the engine can
already write (`.cursor/rules/architect.mdc` and `AGENTS.md`; see
[`src/sf_architect/memory/persona.py`](../src/sf_architect/memory/persona.py)).

> **Prerequisite:** the skill assumes the `sf-local-architect` MCP server is installed
> and wired into your agent. Set that up first (see the main
> [README](../README.md) or the companion VS Code / Cursor extension). The skill only
> directs the agent to tools that the MCP server provides.

---

## Installing the skill

### Easiest: `sf-architect install-skill` (recommended)

The engine ships an installer that copies the skill into every agent's skills
directory **and** writes an always-on architect rule + `AGENTS.md`, so Salesforce
requests route through the engine's tools even on hosts that don't support on-demand
skills:

```bash
# from your Salesforce project root (installs for Cursor, Claude Code, Agentforce Vibes)
sf-architect install-skill .

# limit to specific agents, or skip the always-on rule
sf-architect install-skill . --agents cursor,claude
sf-architect install-skill . --no-persona
```

This writes `.cursor/skills/`, `.claude/skills/`, `.vibes/skills/`
(`local-sf-architect/`), plus `.cursor/rules/architect.mdc` and `AGENTS.md`. Restart
your agent afterward. If you use the **VS Code / Cursor extension**, this runs
automatically during setup ("Run Setup" / "Configure All Detected Agents") for the
open workspace.

### Manual paths

Pick the path for your tool. In every case you are copying the
`skills/local-sf-architect/` folder into the location your agent scans.

### `npx skills add` (Claude Code, Cursor, Codex, and 50+ tools)

The cross-tool installer understands the open spec:

```bash
# from your Salesforce project root
npx skills add personalaimaster-coder/Local_SF_Architect
```

### Cursor

Copy the skill into your project (or user) skills directory:

```bash
mkdir -p .cursor/skills
cp -R skills/local-sf-architect .cursor/skills/
```

### Claude Code

```bash
mkdir -p .claude/skills
cp -R skills/local-sf-architect .claude/skills/
```

### Agentforce Vibes

Project-scoped skills live under `.vibes/skills/`:

```bash
mkdir -p .vibes/skills
cp -R skills/local-sf-architect .vibes/skills/
```

Commit the copied folder to version control so your whole team gets it.

---

## Adding compatible external skill libraries

The bundled skill is architecture/review-focused. You can install generation-focused
Salesforce skill libraries alongside it — they are complementary. Review the license
of each before adding it to your project.

| Library | License | Notes |
| --- | --- | --- |
| [forcedotcom/sf-skills](https://github.com/forcedotcom/sf-skills) | Apache-2.0 | Salesforce's official code-generation skills (Apex, LWC, Flow, metadata deploy). Install: `npx skills add forcedotcom/sf-skills`. Changes frequently — prefer installing over vendoring. |
| [Clientell-Ai/salesforce-skills](https://github.com/Clientell-Ai/salesforce-skills) | Apache-2.0 | 18 community skills (apex, test, flow, lwc, soql, security, deploy, data, schema…). Install: `npx skills add Clientell-Ai/salesforce-skills`. |
| [PranavNagrecha/AwesomeSalesforceSkills](https://github.com/PranavNagrecha/AwesomeSalesforceSkills) | PolyForm Small Business 1.0.0 | Large library + its own MCP server. **Source-available, NOT open source** — do not copy its content into this Apache-2.0 repo. Use it only via its own documented install, and check the license thresholds for your org. |
| [salesforce/salesforce-skills](https://github.com/salesforce/salesforce-skills) | Apache-2.0 | "Knowledge Work Plugins" for Claude Cowork (sales-rep workflows), **not** developer tooling — out of scope for this engine. |

Why this project does not vendor copies of the above: the official libraries change
constantly (copies go stale), and the PolyForm-licensed one is license-incompatible
with this repo. Installing them yourself keeps them current and keeps licenses clear.

---

## Verifying it works

1. Confirm the MCP server is connected in your agent (it should list
   `sf-local-architect` tools).
2. Ask an architecture question in Agent mode, e.g. *"What's the best pattern for
   async processing of 50k records, and will it hit SOQL limits?"*
3. The agent should call `query_architect_db` and `check_governor_limit` and report
   the cited pattern plus the hard-limit headroom — that is the skill routing working.
