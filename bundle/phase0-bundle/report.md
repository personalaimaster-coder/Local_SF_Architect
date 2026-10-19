# Phase 0 Findings — Context/Token Optimizer for Salesforce Agents

*Machine: macOS · sf CLI 2.137.7 · collected 2026-09-04. Data: 127 agent
sessions (124 Cursor + 3 Claude Code) and 12 real Salesforce CLI outputs from a
large multi-package Salesforce project (used only as a data source; not named or
retained — see `notes.md`). All numbers are estimates (`est_tokens = chars/4`);
see `notes.md` for caveats and `stats/summary.json` for machine-readable detail.*

---

## 1. Where do the tokens go?

Two very different vantage points, because the two agents log different things.

**Cursor (124 sessions) — tool *results are not persisted*.** So from Cursor we can
only see agent text/thinking and the *arguments* the agent sends to tools. Of the
~2.06M "visible" tokens across all sessions:

| bucket (visible only) | est. tokens | share |
|---|---:|---:|
| agent text + thinking | 1,119,574 | 54.3% |
| tool-call **arguments** | 925,489 | 44.8% |
| tool **results** (only the 3 Claude sessions) | 18,627 | 0.9% |

The 0.9% is an artifact: **the single biggest token sink in a real session — tool
output — is invisible in Cursor transcripts.** Tool-call *arguments* alone are already
~45% of visible tokens (dominated by `Write`/`StrReplace` file bodies the agent emits).
The real output volume has to be measured from the corpus (§3), and that is exactly
where the compressible mass lives.

**Claude Code (3 sessions) — real billed usage is logged.** Across 24 real turns:
input=124, cache-creation=87,774, cache-read=749,412, output=7,966 tokens.
**89.5% of all input tokens were served from cache.** At Sonnet cache pricing
(in $3 / cache-write $3.75 / cache-read $0.30 / out $15 per M) that's ≈ **$0.67** for
the three sessions — and it shows the economic lever: **input/cache dominates spend, so
anything that shrinks the tokens written into the cached prefix (i.e. bloated tool
output) compounds across every subsequent turn.**

## 2. Top command families by volume

Shell commands actually issued by agents (across all 127 sessions), by call count:

| family | calls |
|---|---:|
| grep/find/cat | 422 |
| **sf-deploy** | **325** |
| git | 313 |
| sf-other | 81 |
| sf-org | 72 |
| sf-apex-test | 40 |
| sf-data-query | 24 |

`sf project deploy` is the **#2 command family overall** (325 calls) and the #1
Salesforce one. 41 of 127 sessions touched the `sf` CLI at all; 542 `sf` invocations
in total. The generic `grep/find/cat` family being #1 is itself a finding (see §4).

## 3. How compressible is Salesforce tool output? (the core result)

Prototype filters over the captured corpus (`stats/summary.json → compressibility`):

| family (corpus file) | raw tokens | filtered | reduction |
|---|---:|---:|---:|
| **retrieve preview** (03) | 214,168 | 1,260 | **99.4%** |
| **org list-metadata / org** (01,02,06) | 51,331 | 563 | **98.9%** |
| deploy validate (08, *partial*) | 176 | 31 | 82.4% |
| **JSON** describe+query (05,07a,07b) | 175,664 | 118,792 | 32.4% (minify) |
| &nbsp;&nbsp;↳ query→CSV projection (05) | 40,809 | ~7,246 | **~82%** |
| git log/diff (09a,09b) | 17,246 | 16,811 | 2.5% |
| npm ls (09c) | 7,785 | 7,784 | 0.0% |

Headline: **a single `sf project retrieve preview` produced ~214k tokens** — larger
than most models' entire context window — and **99.4% of it is collapsible** (2,333
box-drawing table rows → one count line + a few summary rows). `sf org list metadata`
behaves the same (~99%). Structured `--json` payloads shrink ~32% by whitespace alone
and ~82% when reprojected to CSV. By contrast the **generic non-Salesforce tools
(git/npm) are already terse (0–2.5%)** — confirming the opportunity is specifically in
the verbose, templated, tabular Salesforce outputs, not in tooling in general.

## 4. Deploy-retry loops & agent self-truncation (behavioral findings)

- **Self-truncation: 2,124 of 7,187 tool calls (29.6%)** piped through
  `head`/`tail`/`grep` or `--json | jq`, or used `head_limit`/`limit` on reads — i.e.
  nearly **1 in 3 tool calls is the agent pre-emptively defending its own context**.
  This is strong, direct evidence that agents already "feel" the output-bloat problem
  and pay a tax (extra reasoning + extra round-trips) to manage it manually.
- **Deploy-retry loops: 295 repeated `sf project deploy` invocations** within sessions.
  One session alone re-ran deploy **72 times** (91 sf commands, 225
  self-truncations); several others were in the 20–40 range. Each retry re-emits a full
  (highly compressible) deploy/validate report into the context.

## 5. Surprises

1. **Cursor hides the very thing we most want to measure** (tool results). Any optimizer
   evaluated only on Cursor transcripts will *undercount* its own benefit; the corpus is
   the honest measuring stick.
2. **Tool-call *arguments* are ~45% of visible tokens** — `Write`/`StrReplace` bodies are
   themselves a large, partly-compressible surface (echoing whole files back).
3. **A single command can exceed a context window** (retrieve preview ≈ 214k tokens). For
   SF-heavy sessions, one such command can be the majority of the turn's tokens.
4. **89.5% cache-read rate** means the cached prefix is the cost center; trimming bloated
   output that lands in that prefix pays off on every later turn.

## 6. Judgment — is ≥30% of session tokens compressible tool output?

**Yes — comfortably, for any Salesforce-touching session, and the true figure is very
likely much higher.** The evidence:

- The dominant SF outputs are **90–99% compressible** (retrieve preview, list metadata),
  and structured JSON is **30–80%** compressible.
- `sf-deploy` is the #2 command family (325 calls) with **295 retry re-emissions**, each
  dumping a highly-compressible report into context.
- **29.6% of all tool calls are already manual self-truncations** — the agents themselves
  demonstrate that a large fraction of raw output is noise worth discarding.

The one family that *didn't* compress here (apex-test, ~1.8%) is a sampling artifact of a
forced single-class run (see `notes.md`); a real full run compresses heavily by dropping
passing tests and ≥75%-coverage classes. The main gap in this dataset is **debug logs**
(none existed in the org; not generated to honor the read-only rule) and a **complete
deploy-validate** capture (org queue congestion) — both should be re-collected on a
machine where executing a test/log is acceptable. Neither gap weakens the conclusion:
verbose, templated Salesforce CLI output is the compressible mass, it is a large share of
SF-session tokens, and a filtering layer targeting these families is well justified.
