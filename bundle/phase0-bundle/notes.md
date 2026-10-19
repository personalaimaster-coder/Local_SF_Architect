# Phase 0 — notes, failures, caveats

## Data retention (Phase 2 update)
The raw inputs that Phase 0 analysed came from a private, real Salesforce
project and were used **only** as a data source. They have been removed from the
repo because they cannot be reliably de-identified (execution logs and metadata
listings embed hundreds of proprietary class/field/method names):
- deleted: `corpus/` (all CLI outputs + debug logs + metadata listing),
  `stats/sessions.csv`, `stats/tool_calls.csv`, the proprietary project's cursor transcripts,
  and the zipped bundle snapshot.
- kept (de-identified aggregates only): this file, `report.md`, `manifest.json`,
  `stats/summary.json`, `stats/claude_turns.csv`, `analyze.py`, and the
  non-proprietary transcripts.
The findings below are unchanged; the golden filter tests now run against
synthetic fixtures (`tests/synth.py`) instead of the removed corpus.

## Environment / setup
- Bundle was built **inside the repo** at `phase0-bundle/` because the agent sandbox only
  permits writes under the workspace. It is added to `.git/info/exclude` so it does **not**
  appear in `git status` and does **not** touch tracked files, history, or the org.
  Delete the folder (and the `phase0-bundle/` line in `.git/info/exclude`) to fully clean up.
- The `sf` CLI could not write its log to `~/.sf/` under the sandbox; all `sf` commands were
  run with `SF_DISABLE_LOG_FILE=true SFDX_DISABLE_LOG_FILE=true` and outside the sandbox
  (needed for network access to Salesforce). All were read-only except the two the user
  explicitly approved (see below).
- macOS has no `timeout`/`gtimeout`; command time-boxing was done via the agent harness.

## Task 1 — transcript mining
- 124 Cursor + 3 Claude Code JSONL transcripts copied into `transcripts/`.
- **Cursor transcripts do not persist tool results** (confirmed) — so `result_chars` is empty
  for all Cursor rows in `tool_calls.csv`; only the 3 Claude Code sessions have real result sizes.
- Claude Code logs the **same assistant message multiple times while streaming**; identical
  consecutive `usage` rows were de-duplicated (46 raw usage lines -> 24 real turns) so cache
  aggregates aren't inflated.
- A Claude result entry carries **both** a top-level `toolUseResult` and a `tool_result`
  content block (they co-occur); result chars are counted **once** (preferring the richer
  top-level payload) to avoid double counting.

## Task 2 — corpus (what worked / what didn't)
Captured OK (read-only):
- 01 org list, 02 org display, 03 project retrieve preview (**856 KB / ~214k tokens**),
  05 data query (ApexClass, --json), 06 list metadata ApexClass, 07a describe Account,
  07b describe a large custom object, 09a git log, 09b git diff, 09c npm ls.

Adaptations / failures:
- **No `force-app` dir** in this repo (multi-package layout). Metadata size-listing scanned
  the several package directories instead; deploy-validate targeted the default package dir
  (21 files).
- **07b custom object**: the namespaced describe target returned NOT_FOUND (this is the
  packaging org, no namespace prefix). Re-ran successfully against the un-namespaced name.
- **Query (Task 2.5)**: instructions asked for "a SELECT the user suggests, ~200+ rows".
  No query was supplied, so a safe read-only default was used:
  `SELECT Id, Name, NamespacePrefix, Status, ApiVersion FROM ApexClass LIMIT 500` (returned 500 rows).
- **Debug logs (Task 2 / highest value): NOT collected.** `sf apex list log` returned
  "No debug logs found in org". Generating one would require executing anonymous Apex
  (org-side activity), which conflicts with the strict "read-only" hard rule and was blocked
  by the safety reviewer — so it was skipped. `corpus/debug-logs/` is empty. To get one later,
  run any Apex (e.g. a test) with a trace flag enabled, then `sf apex get log`.
- **Apex test run (Task 2.4)**: user-approved. `--synchronous` allows only ONE class, so it was
  run as a single test class with `--code-coverage`. Output (04) includes
  the full org-wide coverage table (738 lines).
- **Deploy validate (Task 2.8)**: user-approved, but only a **PARTIAL** capture exists.
  - First attempt (`RunLocalTests` default) kicked off the **entire 2960-test suite**
    server-side (5+ min, 1 test already failing) and produced a 7 MB file that was ~99% ANSI
    spinner repaint. It was stopped.
  - `--test-level NoTestRun` is rejected by `deploy validate` (must run tests).
  - Second attempt (`RunSpecifiedTests` + one class) got **queued behind the still-running
    server-side full-suite validation** (org deploy queue congested) and sat at `Status: Pending`
    for 6+ min, so the local CLI was stopped. `08-sf-deploy-validate.txt` therefore contains only
    the header/pending lines, not the component-by-component "Succeeded" rows.
  - The safety reviewer blocked `sf project deploy cancel` (an org mutation) so the server-side
    validations were left to self-expire (validations never deploy anything, so this is harmless).

## Task 3 — compressibility caveats
- Filters are crude prototypes (regex/line collapse), as instructed. Ratios are estimates.
- **apex-test shows only ~1.8% reduction** — this is a *sample artifact*: a single-class run
  leaves almost every class at 0% coverage, so the "drop classes >=75%" filter has nothing to
  drop and almost nothing passes. On a real full test run (mostly passing tests + many
  high-coverage classes) this family compresses far more.
- **JSON**: whitespace-minify alone = ~32%. Converting the query result to CSV/tabular form is
  far better (~7.2k vs ~40.8k tokens for file 05 => ~82% smaller). Included as `csv_tokens`.
- **deploy-validate ratio (82%)** is computed on the tiny partial capture — not representative.
- git/npm are near-incompressible baselines here (already terse), which is the intended contrast.
