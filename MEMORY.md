# sf-compress — Project Memory

> Single source of truth for what this project is, what Phase 0 produced, and
> what we build next. Written from the Phase 0 instructions + the delivered
> `phase0-bundle` (both now committed under `bundle/`).

---

## 1. What we're building

An **open-source context/token optimizer for AI coding agents** (Cursor, Claude
Code), focused on **Salesforce development**.

The thesis: verbose, templated, tabular Salesforce CLI output (deploy reports,
metadata listings, `--json` payloads, debug logs) is a huge, highly-compressible
share of the tokens that land in an agent's context window. A filtering layer that
sits between the tool and the model can strip the noise (progress lines, passing
tests, "Succeeded" rows, box-drawing tables, boilerplate XML) while keeping the
signal (final status, errors, failures, low-coverage classes, limit usage).

**Core question Phase 0 set out to answer:** *Is ≥30% of a Salesforce agent
session's tokens compressible tool output?* → **Answer: Yes, comfortably; likely
much higher.** (See §4.)

### Hard rules (carried forward into every phase)
- **Do NOT modify** the Salesforce project, its git state, or any org. Read-only
  operations and metadata retrievals only. No deploys unless the user explicitly
  approves a **no-op validate**.
- **Everything stays local.** Bundles may contain code/log/metadata snippets and
  org usernames/IDs — review before sharing off-machine.
- If a step fails, record it in `notes.md` and move on. Partial data is fine.

---

## 2. Phase 0 = data collection (DONE, bundle delivered)

Phase 0 was a pure data-mining exercise, run on a macOS dev machine
(sf CLI 2.137.7) against **a large, real multi-package Salesforce project**
(sourceApiVersion 64.0, multi-package layout — note: **no `force-app` dir**,
several package directories including a SOQL library). The specific project and
its org were only a data source for Phase 0 and are intentionally not named or
retained here (see §5).

Four tasks:
1. **Mine existing agent transcripts** (Cursor + Claude Code) → session/tool-call
   stats.
2. **Collect a corpus of raw Salesforce CLI outputs** (the most important task).
3. **First-pass compressibility estimate** — crude regex/line-collapse filters
   per command family.
4. **Write `report.md`** with findings + judgment on the ≥30% question.

Deliverable = one `phase0-bundle/` folder (zipped). We now keep it at
`bundle/phase0-bundle.zip` (canonical archive) **and** extracted at
`bundle/phase0-bundle/` (browsable + re-runnable).

---

## 3. Bundle contents (`bundle/phase0-bundle/`)

> **Sanitized in Phase 2 (2026-09-21).** The raw, client-derived inputs were
> removed because they cannot be reliably de-identified (see §5 / §10). What
> remains are the de-identified aggregates and findings:

```
manifest.json          machine, dates, tool versions (identifiers redacted)
analyze.py             the analysis script (Tasks 1 & 3) — re-runnable, path-relative
report.md              human-readable findings (de-identified)
notes.md               failures, caveats, adaptations (+ Phase 2 data-retention note)
transcripts/
  cursor/              4 non-proprietary JSONL transcripts (proprietary project removed)
  claude-code/         3 non-proprietary JSONL transcripts
stats/
  claude_turns.csv     per-turn billed usage + cache splits (Claude only)
  summary.json         machine-readable aggregates (no project identifiers)
```

**Removed in Phase 2** (were the raw measuring inputs, purpose served):
`phase0-bundle.zip`, `corpus/` (all sf-outputs, the ~22 MB debug logs, the
metadata size-listing, `index.csv`), `stats/sessions.csv`, `stats/tool_calls.csv`,
and the one proprietary cursor-project transcript directory. Also purged from git
history (branch reset to the clean initial commit + `gc --prune`), so the
proprietary blobs were never pushed.

The golden filter tests no longer depend on this corpus; they run against
synthetic fixtures in `tests/synth.py` (same ratios, zero client data).
`est_tokens = chars / 4` throughout.

### `analyze.py` — how it works (so we can extend it)
- **command_family()** classifies Shell/Bash commands: `sf-deploy`,
  `sf-apex-test`, `sf-data-query`, `sf-org`, `sf-other`, `git`, `npm/node`,
  `grep/find/cat`, `other`.
- **Cursor parser**: reads `role` + `message.content` blocks (`text`, `thinking`,
  `tool_use`). Cursor does **not** persist tool results → `result_chars` empty.
  Non-shell self-truncation detected via `head_limit`/`limit` on Read/Grep.
- **Claude parser**: also reads `toolUseResult` + `tool_result` blocks (counted
  once, preferring top-level payload) and `message.usage` cache splits;
  de-dupes consecutive identical streaming `usage` rows (46 raw → 24 real turns).
- **Self-truncation regex**: pipes to `head`/`tail`/`grep` or `--json | jq`.
- **Compressibility filters** (crude, per family):
  - deploy/validate → collapse "Succeeded" rows to a count; keep errors/status.
  - apex-test → keep failures, summary, classes < 75% coverage.
  - debug-log → keep only lines matching
    `USER_DEBUG|EXCEPTION|FATAL|SOQL_EXECUTE|DML_|LIMIT_USAGE|CODE_UNIT_STARTED`.
  - json → whitespace-minify + estimate a CSV/tabular projection of `records`.
  - retrieve-preview / org-metadata → collapse box-drawing table rows to a count.
  - git/npm → drop progress/unchanged/"up to date"/"deduped" noise.

---

## 4. Key findings (the evidence base)

**Scale mined:** 127 sessions (124 Cursor + 3 Claude Code), 7,187 tool calls,
542 `sf` commands, ~2.06M visible est. tokens.

### Where tokens go
- **Cursor hides tool results** — the single biggest real token sink is invisible
  in Cursor transcripts. Of visible tokens: agent text/thinking 54.3%, tool-call
  **arguments** 44.8% (dominated by `Write`/`StrReplace` file bodies), results
  0.9% (only the 3 Claude sessions). → The corpus is the honest measuring stick.
- **Claude Code (real billed usage, 24 turns):** input=124,
  cache-creation=87,774, cache-read=749,412, output=7,966. **89.5% cache-hit
  rate.** The cached prefix is the cost center → trimming bloated output that
  lands in the prefix compounds across every later turn. ≈ $0.67 for 3 sessions.

### Top command families (by call count, all sessions)
`grep/find/cat` 422 · **`sf-deploy` 325** · `git` 313 · `sf-other` 81 ·
`sf-org` 72 · `sf-apex-test` 40 · `sf-data-query` 24. (41/127 sessions touched
`sf`; 542 `sf` invocations total.)

### Compressibility (prototype filters over corpus)
| family | raw tokens | filtered | reduction |
|---|---:|---:|---:|
| `sf project retrieve preview` (1 file) | 214,168 | 1,260 | **99.4%** |
| `sf org list metadata` / org (3) | 51,331 | 563 | **98.9%** |
| **debug logs (3 files)** | **5,490,299** | **36,494** | **99.3%** |
| json describe+query (3, minify) | 175,664 | 118,792 | 32.4% |
| ↳ query→CSV projection | 40,809 | ~7,246 | **~82%** |
| deploy validate (partial) | 176 | 31 | 82.4% (not representative) |
| apex-test (single-class artifact) | 13,594 | 13,350 | 1.8% (not representative) |
| git log/diff (2) | 17,246 | 16,811 | 2.5% (terse baseline) |
| npm ls (1) | 7,785 | 7,784 | 0.0% (terse baseline) |

**Headlines:**
- A **single `sf project retrieve preview` = ~214k tokens** — larger than most
  models' whole context window — and **99.4% collapsible** (2,333 table rows → a
  count + a few summary lines).
- **Debug logs are the biggest prize**: 5.49M raw tokens across 3 logs, **99.3%
  noise** (SYSTEM_METHOD_ENTRY/EXIT, HEAP_ALLOCATE) vs. the few USER_DEBUG /
  exception / LIMIT_USAGE lines that matter.
- **Generic tools (git/npm) are already terse (0–2.5%)** → the opportunity is
  specifically Salesforce's verbose templated output, not tooling in general.

### Behavioral findings
- **Self-truncation: 2,124 / 7,187 tool calls (29.6%)** pipe through
  `head`/`tail`/`grep`/`jq` or use `head_limit`/`limit` — **~1 in 3 tool calls is
  the agent pre-emptively defending its own context.** Direct evidence agents
  already pay a tax for output bloat.
- **Deploy-retry loops: 295 repeated `sf project deploy`** within sessions. One
  session re-ran deploy **72 times** (91 sf commands, 225 self-truncations).
  Each retry re-emits a full, highly-compressible report into context.

**Judgment:** ≥30% of session tokens are compressible tool output — **yes,
comfortably**, for any Salesforce-touching session, and likely much higher.

---

## 5. Caveats, gaps & a data discrepancy to remember

- **Raw data removed (Phase 2, 2026-09-21):** the corpus, debug logs, per-session
  and per-tool-call stats, the zipped bundle, and the proprietary project's
  transcripts were **deleted from the repo and purged from git history** because
  they embed hundreds of proprietary class/field/method names that cannot be
  reliably scrubbed. They were only ever measuring inputs; the findings below and
  the de-identified aggregates (`report.md`, `summary.json`) are preserved. Golden
  tests now use synthetic fixtures (`tests/synth.py`). See §10.
- **Historical discrepancy (kept for the record):** `report.md`/`notes.md` (dated
  2026-09-04) said debug logs were **NOT** collected (org had none; generating one
  conflicted with the read-only rule), but the later 2026-09-05 pass **did** capture
  3 real Apex debug logs (~22 MB, 5.49M tokens, 99.3% compressible). Those logs
  were the strongest compressibility result; they have since been removed per the
  point above, but the 99.3% figure stands as the measured result.
- **apex-test 1.8%** = sample artifact: `--synchronous` allows only ONE class, so
  it ran a single test class alone → almost every class at 0% coverage, so
  "drop classes ≥75%" had nothing to drop. A real full run compresses heavily.
- **deploy-validate** capture is only a partial header/pending snippet: the first
  attempt kicked off the full 2,960-test suite server-side (7 MB, ~99% ANSI
  spinner repaint, stopped); the retry got queued behind it. `--test-level
  NoTestRun` is rejected by `deploy validate`. Ratio (82%) not representative.
- **Query default:** no user query supplied, so used
  `SELECT Id, Name, NamespacePrefix, Status, ApiVersion FROM ApexClass LIMIT 500`.
- **Custom object:** the namespaced describe target was NOT_FOUND (packaging
  org, no namespace prefix); re-ran against the un-namespaced object name.
- **Env quirks:** `sf` run with `SF_DISABLE_LOG_FILE=true SFDX_DISABLE_LOG_FILE=true`
  and outside the sandbox (needs network); macOS has no `timeout`/`gtimeout`.

---

## 6. Expanded scope & product thesis (added 2026-09-20)

Phase 0's CLI-output filtering is **necessary but not sufficient**. The tool must
take a **holistic, session-level approach to context management**, not just
per-output truncation between chats. Four pillars:

### Pillar A — Tool-output compression (Phase 0's proven core)
Highest-leverage targets, in order of proven payoff:
1. **Debug logs** (99.3%) — keep USER_DEBUG/EXCEPTION/FATAL/SOQL_EXECUTE/DML_/
   LIMIT_USAGE/CODE_UNIT_STARTED; drop METHOD_ENTRY/EXIT, HEAP_ALLOCATE.
2. **`retrieve preview` / `org list metadata`** (≈99%) — collapse table rows to
   counts + per-type tallies; keep summaries.
3. **Deploy/validate reports** (esp. the 295 retry re-emissions) — collapse
   "Succeeded" components to a count; surface only errors + final status.
   For retries, consider emitting a **diff vs. the previous run** instead of the
   full report again.
4. **`--json` payloads** — reproject query results to CSV/tabular (~82%),
   minify describes (~32%).
5. Leave git/npm alone (already terse).

### Pillar B — Exploration/analysis bloat (NEW, must-have)
When given a direction, an agent reads **many classes/files up-front** and can
blow the context in a single burst. Our own data supports this: `tool:Read` was
the **#1 tool by call count (2,230 calls)**, and the sampled project had monster
files (a 626 KB Apex class ≈ 156k tokens, another at 557 KB — one Read of one
class can rival a retrieve-preview). Directions to explore:
- **Apex/LWC outline views** instead of full reads: method signatures, doc
  comments, SOQL/DML/callout markers, field references — expand a method body
  only on demand.
- **Dependency-aware retrieval — DECIDED: include `graphify-sf` and build upon
  it** (see §7). We bundle it as our exploration foundation (offline SFDX →
  knowledge graph, provenance-tagged, token-budgeted queries) rather than
  rebuilding a graph. Our value-add on top: wire its graph into the outline/
  read-budget flow ("graph query first, outline second, full read last"), and
  extend it where SF-runtime knowledge is missing.
- **Read budgets**: cap tokens per exploration burst, forcing outline-first,
  body-on-demand behavior.

### Pillar C — Holistic session-level management
- Filter at **capture time** (Cursor doesn't persist tool results, so post-hoc
  is impossible) via a wrapper/interceptor or MCP tool layer.
- Always keep an **expand-on-demand** path to the full raw output (agents
  self-truncate 29.6% of the time — give them a trustworthy summary + reliable
  escape hatch so they stop paying that tax).
- **Dedupe across turns**: repeated deploy/test runs should emit deltas, not
  full re-reports; cache-aware (89.5% cache-read rate means everything written
  into the prefix is re-paid every turn).

### Pillar D — Ride the skills ecosystem (see §7)
Ship our capability **as an agent skill / MCP server** so it works across
Cursor, Claude Code, Codex, etc., and composes with Salesforce's official
skills instead of competing with them.

### Pillar E — Salesforce DX MCP Server in the loop (DECIDED)
Include the **Salesforce DX MCP Server (beta)** + hosted API-context MCP tools
as a first-class part of the plan, not just landscape:
- Evaluate per command family whether the MCP tool's output is terser than raw
  CLI; where it is, our layer recommends/routes to MCP instead of shell.
- Where MCP output is still verbose, our filters wrap it the same as CLI output
  (one filtering core, two transports: shell wrapper + MCP proxy).
- Benchmark task: same operations (query, describe, retrieve preview, test run)
  via raw CLI vs DX MCP, record token counts into the corpus methodology.

### Architecture principle — every module is toggleable (DECIDED)
The tool must be built so **any component can be switched off at runtime** to
measure real usage with vs. without it:
- Central config (env vars / config file / per-session flag) with independent
  switches: `output-filters` (per family), `exploration-graph` (graphify-sf),
  `outline-reads`, `dx-mcp-routing`, `dedupe/deltas`.
- **Pass-through mode**: when off, the layer transparently forwards raw output —
  zero behavior change, so on/off comparisons are clean.
- **Built-in metering always on** (even when filters are off): log per tool call
  raw_tokens, emitted_tokens, family, filter_version, session id — this gives us
  the A/B evidence (tokens & dollars saved) that Phase 0 could only estimate,
  and doubles as our own telemetry corpus for tuning filters.
  - **SUPERSEDED (2026-09-20):** when the tool is OFF it is **fully dormant** —
    no execution, no metering, nothing written. Metering runs only while the
    tool is active. (User decision; see §8 scope rules.)

### Data gaps to backfill
Re-collect a **full apex test run** and a **complete deploy-validate** on a
machine where running a test/log is acceptable, to replace the two artifact
ratios (apex-test 1.8%, deploy-validate 82.4%).

---

## 7. Competitive / ecosystem landscape (researched 2026-09-20)

### graphify-sf (PyPI, v0.4.1) & graphify-sfdx (v0.1.1) — closest neighbor
- **What it does:** parses a local SFDX project **offline** (no org connection)
  into a queryable knowledge graph — Apex, triggers, Flows, objects/fields,
  LWC/Aura, Profiles/PermSets — with every edge provenance-tagged **EXTRACTED**
  (fact from XML) or **INFERRED** (guessed from source patterns).
- **Agent integration:** installable `/graphify-sf` skill across 15+ IDEs
  (`npx skills add raykuonz/graphify-sf`), an **MCP stdio server** (9 tools:
  `query_graph`, `get_neighbors`, `shortest_path`, `god_nodes`...), and it can
  write **AGENTS.md enforcement rules** telling agents to "use the graph
  instead of grep".
- **Token features:** token-budgeted queries (`--budget`, default 2,000 tokens),
  "token-minimized" graph views, Leiden community clustering. `graphify-sfdx`
  adds SF-aware analysis passes (order-of-execution, governor limits, recursive
  triggers, CPQ loops) exposed as MCP tools (`sf_impact`, `sf_ooe`, ...).
- **How we compare:** graphify attacks **Pillar B** (static exploration bloat)
  and does it well. It does **NOT** touch **Pillar A/C at all** — no filtering
  of live CLI output, deploy reports, test results, debug logs, or org-connected
  `--json` payloads (it's explicitly offline/static). That runtime-output lane is
  ours and is where Phase 0 proved 99% waste.
- **DECISION (2026-09-20): include graphify-sf in our tool and build upon it.**
  It becomes the exploration-graph module (behind its own toggle, per the
  architecture principle). We add the runtime-output filtering, session-level
  dedupe, and DX-MCP routing it lacks, and wire its graph into our outline-first
  read flow. Also copy its distribution playbook (skill + MCP + AGENTS.md
  rules) — it's exactly right. License: **MIT (verified)**, so bundling/vendoring
  is fine. Watch: it's a young third-party package (v0.4.x) — pin versions and
  keep our integration behind an interface so we can swap or vendor it if it
  stalls.

### Salesforce official skills — `forcedotcom/sf-skills` (200+ skills)
- Curated Agent Skills library for SF development (`npx skills add
  forcedotcom/sf-skills`); optimized for Agentforce Vibes, works in Cursor/
  Claude Code/Codex. Follows the open Agent Skills spec (SKILL.md +
  references/ + assets/, **progressive loading** — full instructions load only
  when relevant, which is itself context-friendly).
- Most relevant to us: `platform-apex-logs-debug`, `platform-apex-test-run`,
  `platform-metadata-deploy`/`-retrieve`, `platform-soql-query`,
  `dx-org-analyze`, `dx-apexguru-scan`, `platform-apex-generate`.
- **Verdict — yes, adopt them, but they don't solve our problem.** They encode
  *workflow expertise* (which commands, what order, how to interpret results,
  e.g. the debug-log skill's severity triage and governor-limit playbook), which
  reduces wasted exploration turns and deploy-retry flailing. But they do
  **not compress output** — the debug-log skill literally points agents at
  "CLI grep patterns", i.e. the manual self-truncation tax we measured at 29.6%
  of tool calls. Skills = better *behavior*; sf-compress = smaller *observations*.
  They compose: our filter should be **distributed as a skill in the same
  ecosystem**, reference the official skills, and potentially be proposed
  upstream to `sf-skills` once proven.
- Caveat: Salesforce warns skills change frequently with no backward-compat
  guarantee; treat the GitHub repo as source of truth.

### Salesforce hosted/DX MCP servers
Salesforce ships MCP servers (Salesforce DX MCP Server beta, hosted API-context
MCP tools like `get_metadata_type_context`). These make org operations agent-
callable but, again, don't address output volume.
**DECISION (2026-09-20): the DX MCP Server is part of our plan (Pillar E).**
Benchmark its output verbosity vs raw CLI per command family; route to whichever
is terser, and wrap whichever is verbose — behind its own `dx-mcp-routing`
toggle so its contribution can be measured independently.

---

## 8. Phase 1 — `sfc` dev-support CLI (BUILT 2026-09-20)

Plan: `.cursor/plans/phase_1_sfc_tool_c955fa46.plan.md`. Implemented and tested.

### Scope decisions (user-set, binding)
- **Dev-support tool ONLY**: used during active dev loops (deploy/validate,
  test runs, debug logs, retrieve/preview, data queries). It must **NOT run
  during analysis or architecture work** — full detail matters there.
- **Activation**: `sfc on` / `sfc off` / `sfc status`; default **ON** (dev-support
  compression works out of the box). `sfc off` writes an explicit opt-out; state is
  project-local (`.sfc/state.json`). *(Updated from the original default-OFF
  decision at the user's request when sf-compress was merged into the engine.)*
- **Fully dormant when off**: `sfc run` refuses to execute (exit 3), nothing is
  stored or metered. This supersedes the earlier "metering always on" principle.
- **Python** (3.9+, stdlib-only, `pyproject.toml`, console script `sfc`) —
  chosen because graphify-sf is Python and the Phase 0 filters ported directly.

### What exists
- `src/sfc/` — `cli.py` (on/off/status/run/show/stats), `state.py` (state +
  per-family config toggles), `runner.py` (subprocess capture, child exit code
  passthrough), `store.py` (full raw outputs in `.sfc/outputs/<id>.txt`,
  retention 50), `metering.py` (`.sfc/metrics.jsonl`), `filters/` (classify +
  5 families: deploy, apex-test, debug-log, json→CSV/minify, table-collapse;
  ANSI/spinner normalization; unknown families pass through untouched).
- `skills/sf-compress/SKILL.md` — sf-skills-convention skill: TRIGGER only on
  dev-support tasks when `sfc status` is ACTIVE; DO NOT TRIGGER for analysis/
  architecture; never activates sfc itself; "don't re-truncate" rule; expand
  via `sfc show <id> [--grep|--head|--tail]`.
- `tests/` — 19 unittest tests (stdlib, `python3 -m unittest discover tests`):
  golden tests (originally the real Phase 0 corpus, now synthetic fixtures —
  see §10) + signal-preservation (errors/failures/USER_DEBUG never dropped) +
  CLI lifecycle/dormancy.

### Measured (Phase 1, on the then-present real corpus; reproduces Phase 0)
retrieve preview 214k→1.4k tok (99.3%) · debug log 660k→1.5k (99.8%) ·
query JSON→CSV 83.1% · describe minify 33.1% · apex-test 1.3% (known
single-class artifact) · git/npm pass through untouched. (The corpus has since
been removed; the synthetic fixtures reproduce the same thresholds.)

### Config toggles (`.sfc/config.json`)
`filters.{sf-deploy,sf-apex-test,sf-debug-log,sf-json,sf-table,deltas}` (bool each),
`store.retention`, `exploration-graph` (graphify-sf, Phase 2), `dx-mcp-routing`
(reserved; the `sfc bench` workbench measures MCP verbosity to decide routing).

### Phase 2 backlog → status (see §10)
graphify-sf `sfc graph` (DONE) · deploy-retry delta output (DONE) · DX MCP
routing *benchmark* shipped as `sfc bench` (DONE; live routing still reserved) ·
re-collect full apex-test + deploy-validate fixtures → shipped as the portable
`sfc collect` workbench, to be **run by the user on an org machine** (org
execution deliberately not done here).

---

## 9. Repo layout

```
sf-compress/
  README.md
  MEMORY.md                    <- this file (living project memory)
  pyproject.toml               sfc package (console script: sfc; [graph] extra)
  docs/org-workbench.md        runbook for sfc collect / sfc bench (Phase 2)
  src/sfc/                     CLI + modules (see §8, §10)
    delta.py                   deploy-retry delta output (Phase 2)
    graph.py                   graphify-sf adapter (Phase 2)
    workbench/                 collect.py, bench.py, mcp_client.py (Phase 2)
  skills/sf-compress/SKILL.md  agent skill (dev-support-only trigger rules)
  tests/                       unittest suite (synthetic golden + lifecycle +
                               delta + graph + workbench); tests/synth.py fixtures
  bundle/
    phase0-bundle/             de-identified findings + aggregates (see §3)
```

---

## 10. Phase 2 — scrub, deltas, graph, org workbench (BUILT 2026-09-21)

Plan: `.cursor/plans/phase_2_sfc_plan_419bfa22.plan.md`. All todos implemented
and tested (`python3 -m unittest discover tests` → 36 tests, all pass).

### Scope decisions (user-set, binding)
- **Offline only for the tool; no org execution on this machine.** The org-work
  capability is built and tested here via shims, then **run by the user on an
  org-connected machine and shared with others** (not executed in this repo).
- **Remove every reference to the proprietary source project everywhere** —
  prose, comments, corpus data, class names — because it was only a Phase 0 data
  source. Done + verified: a repo-wide grep for the project name and its class
  prefixes returns nothing outside `.git`, and git history was rebuilt from the
  clean initial commit (old proprietary blobs purged via `gc --prune`, never pushed).

### What shipped
1. **Proprietary-data scrub (§3/§5).** Deleted client-derived raw data (corpus incl. 22 MB
   debug logs, sessions/tool_calls CSVs, the proprietary transcript dir, the zip);
   scrubbed prose/manifest; kept de-identified aggregates. Rationale: multi-MB
   execution traces embed hundreds of proprietary identifiers and can't be
   reliably sed-sanitized, so deletion (not masking) was the only safe route.
2. **Golden tests → synthetic.** `tests/synth.py` generates family-shaped fixtures
   reproducing the Phase 0 ratios (retrieve/table >99%, debug-log >99% + signal
   preserved, query→CSV >80%, describe minify >25%, deploy >50%, apex-test summary
   kept). No client data in the repo; tests are hermetic.
3. **Deploy-retry deltas** (`src/sfc/delta.py`). On a re-run of the same deploy
   command, diff the error set vs the previous stored run and emit only NEW /
   RESOLVED errors + an unchanged count with a `sfc show <prev-id>` pointer.
   Toggle `filters.deltas` (default on); metrics rows gain `delta_of`. Wired in
   `runner.py`; `store.find_prev()` matches on normalized command.
4. **graphify-sf adapter** (`src/sfc/graph.py`, `sfc graph`). Subprocess adapter
   (not a hard dep — graphify-sf needs 3.10+) behind the `exploration-graph`
   toggle (default off) and requiring `sfc on`. Verified against **graphify-sf
   0.4.1** (real CLI: `query "..." --budget N`, `path`, `explain`, `stats`,
   `serve`). Auto-detects PATH binary / uvx / pipx; injects a default
   `--budget 2000` for queries; meters as family `graph`. Pinned via the
   `[graph]` extra in `pyproject.toml` and `TESTED_VERSION`.
5. **Portable org workbench** (`src/sfc/workbench/`, `sfc collect` + `sfc bench`,
   runbook `docs/org-workbench.md`). `collect` re-collects real fixtures in Phase 0
   corpus format with an `index.csv` of reduction ratios; read-only by default,
   org-side steps (apex test, deploy validate) gated behind `--allow-org-writes`.
   `bench` compares raw CLI vs the Salesforce DX MCP server per family (minimal
   stdlib JSON-RPC stdio client in `mcp_client.py`, tools discovered at runtime)
   and writes `bench-report.md`. Both are exercised offline with fake `sf`/MCP
   shims; the user runs them for real on an org machine.
6. **Skill + memory.** `SKILL.md` (v0.2) adds graph-first exploration guidance and
   the delta behavior note; this section records Phase 2.

### Still deferred (needs the user's org run)
- Real apex-test + deploy-validate fixtures (produce via `sfc collect --allow-org-writes`).
- Live DX MCP **routing** (`dx-mcp-routing` toggle) — decide per family from the
  `sfc bench` numbers, then wrap/route. Benchmark harness is ready; routing not wired.

## 11. Two design questions answered (2026-09-21)

### Q1: "Cursor doesn't persist tool results but others may — must work for them."
Confirmed the design is already agent-agnostic, because compression happens at
**capture time** (before output reaches the agent), not as a post-hoc transcript
pass. So:
- **Non-persisting agents (Cursor):** capture-time is the *only* viable point —
  there's nothing to post-process later. Works.
- **Persisting agents (Claude Code, etc.):** the compressed view + stable `<id>`
  is what lingers across turns (saving compounds), and `sfc show <id>` gives
  on-demand expansion. Works, and strictly better.
Nothing in the code assumes non-persistence. Documented this explicitly in the
README "How it works" section (previously it was framed Cursor-only).

### Q2: "Will graphify do its job as required?" — hands-on probe of v0.4.1
Built a throwaway 3-file SFDX project (AccountService, OrderService calling it,
AccountTrigger calling it) and ran the real CLI. Findings:
- **Works and is genuinely useful for orientation:** builds an offline graph
  (nodes/edges/communities), `explain`/`stats` give a structural map, and `query`
  output is **token-budgeted** (`--budget`, default we inject = 2000). This is the
  intended win vs. reading many 150k-token classes.
- **BUT reverse/caller extraction is incomplete (heuristic):**
  - `OrderService`, which explicitly calls `AccountService.getActive()`, was left
    an **isolated node (degree 0)** — the call edge was missed entirely. (The
    trigger's call *was* captured, so extraction is inconsistent.)
  - `query "where is AccountService used?"` returned only the definition
    (`AccountService.getActive()`), **not its callers**.
- **Conclusion:** graphify is a good **first-pass locator/hint**, not an
  authoritative "who calls X" source. Correct call: keep it **opt-in, off by
  default** (already the case), and instruct the agent to narrow with the graph
  then **verify callers/usages in the actual file** before relying on them.
  Updated `SKILL.md` (graph section) and README with this caveat. No code change
  needed — the adapter already forwards to the real CLI and meters it.

## 12. Seamless setup: wizard + MCP server (BUILT 2026-09-21)

User ask: stop telling people to copy-paste the skill; let a coding **agent add
it**, expose it as an **MCP command**, and make setup a **multi-step wizard**
runnable from an agent or manually. Make it seamless.

### What shipped (stdlib-only, tests: 56 pass)
1. **Skill bundled as package data** (`src/sfc/assets/skills/sf-compress/SKILL.md`,
   v0.3). `pyproject` `package-data` ships it in the wheel; `agents.skill_text()`
   reads it via `importlib.resources` with a source-tree fallback. Repo-root
   `skills/sf-compress/SKILL.md` kept for browsing / `npx skills add` and guarded
   against drift by `tests/test_setup.py::test_repo_copy_in_sync_with_packaged`.
2. **`src/sfc/agents.py`** — small data-driven registry (`cursor`, `claude`,
   universal `agents`) with per-agent `skills_subdir`, `mcp_config`, and `detect`
   hints. Functions: `install_skill`, `skill_targets` (universal + per-agent,
   deduped), `detect_agents`, `register_mcp` (merges `sf-compress` into the
   agent's MCP JSON, preserving existing servers), `mcp_launch_command` (prefers
   `sfc` on PATH, else `python -m sfc mcp`).
3. **`src/sfc/setup_wizard.py`** — `run_setup()` pure orchestration (returns a
   summary dict) + a CLI front-end. Multi-step and **dual-mode**: interactive
   prompts on a TTY, non-interactive with `--yes/--non-interactive/--json` (how an
   agent/CI drives it). Installs skill(s), registers MCP, seeds config via
   `state.ensure_config()`, and **leaves sfc OFF** unless `--activate` (hard rule).
4. **`src/sfc/mcp_server.py`** — minimal MCP stdio server (line-delimited JSON-RPC
   2.0, protocolVersion 2024-11-05), launched by `sfc mcp`. Tools: `sfc_setup`,
   `sfc_install_skill`, `sfc_status`, `sfc_on`, `sfc_off`, `sfc_run`, `sfc_show`,
   `sfc_stats`, `sfc_graph`. CLI-output tools are implemented by capturing
   `cli.main(argv)` so behavior is identical to the shell. Tool errors are
   returned as `isError` results (not protocol errors), per spec.
5. **CLI wiring** (`cli.py`): `sfc setup`, `sfc install-skill`, `sfc mcp`. Added
   `src/sfc/__main__.py` so `python -m sfc` works (the MCP launch fallback).
6. **Tests**: `tests/test_setup.py` (registry, detection, skill install, MCP merge,
   wizard summary, activate, drift guard) + `tests/test_mcp_server.py` (initialize,
   tools/list, tools/call, notifications, unknown-method error, end-to-end serve
   loop). Full suite 36 → **56**, all pass.
7. **Docs**: README "Use it in an existing repo" now leads with `sfc setup`; the
   old copy-paste "Make your AI agent use it" section replaced with the wizard +
   MCP tool table; command reference updated. `state.ensure_config()` added so
   setup can seed `.sfc/` without activating.

### Verified end-to-end (outside sandbox)
`sfc setup --agent cursor --yes --json` → skill written to `.agents/skills` +
`.cursor/skills`, `sf-compress` merged into `.cursor/mcp.json`, config seeded,
`active=false`. `sfc mcp` handshake: `initialize` → serverInfo, `tools/list` →
all tools, `tools/call sfc_status` → "OFF". Note: sandbox blocks creating
`.cursor`/`.claude` dirs, so setup/MCP tests run outside the sandbox.

### Not done / notes
- Wheel-packaging spot-check of the bundled skill was left unrun (the isolated
  `python -m build` wedged the dev shell); `package-data` glob is standard and the
  `skill_text()` source fallback covers source installs regardless.
- `mcp_launch_command` records the resolved interpreter path when `sfc` isn't on
  PATH; after a `pipx install` it resolves to the `sfc` shim instead.
