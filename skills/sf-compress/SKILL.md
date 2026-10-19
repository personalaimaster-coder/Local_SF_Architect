---
name: sf-compress
description: "Compress verbose Salesforce CLI output before it enters the agent context, via the sfc dev-support wrapper. TRIGGER when: sfc is ACTIVE and you are doing Salesforce DEV-SUPPORT work - deploying or validating source, running Apex tests, fetching or analyzing debug logs, retrieving metadata, previewing retrieve/deploy, or running SOQL data queries from the shell. DO NOT TRIGGER when: doing analysis, architecture, or codebase-exploration work (sfc must stay off there), when sfc status is OFF, or for non-Salesforce commands (git, npm, generic shell)."
metadata:
  version: "0.3"
  domains: ["Platform", "DX"]
  relatedSkills:
    - "platform-apex-test-run"
    - "platform-apex-logs-debug"
    - "platform-metadata-deploy"
    - "platform-soql-query"
  cliTools:
    - tool: ["sfc"]
      semver: ">=0.1.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# sf-compress: Salesforce Dev-Support Context Compressor

`sfc` wraps Salesforce dev commands, stores the FULL raw output on disk, and
prints a compressed view (errors, failures, summaries, counts) so a 200k-token
deploy report or debug log does not flood your context. Nothing is lost: every
compressed output ends with an id you can expand on demand.

## Hard scope rule (read first)

`sfc` is a **dev-support tool only**. It must be used ONLY during active
development loops: deploy/validate, test runs, debug-log fetching, metadata
retrieve/preview, data queries.

It must **NOT run during analysis or architecture work** (code reviews, org
exploration, impact analysis, design discussions) - full raw detail matters
there. For that work, leave `sfc off` and run raw commands.

sfc is **ON by default**, so dev-support commands get compressed out of the box:

```
sfc status    # check the gate before routing anything through sfc
sfc off       # make it fully dormant (e.g. during analysis/architecture work)
sfc on        # re-activate for dev-support work
```

## Setup (one time, if `sfc` is not wired up yet)

If `sfc status` errors with "command not found", or the user asks you to install
or set up sfc, run the setup wizard - it installs this skill, registers the MCP
server, and seeds config, without any manual copy-paste:

```
sfc setup --yes            # non-interactive; auto-detects the agent/IDE
sfc setup --agent cursor   # or target a specific agent
```

sfc is ON by default, so no activation step is needed after setup. Run `sfc off`
when you move to analysis/architecture work where full raw detail matters.

## Workflow

1. **Check the gate**: run `sfc status`. If OFF (exit code 1) — e.g. the user
   opted out — use raw commands and do not mention sfc again. If ACTIVE (the
   default), route dev-support commands through the wrapper as below.
2. **Route verbose Salesforce commands through the wrapper** when ACTIVE:

   ```
   sfc run -- sf project deploy start -d force-app
   sfc run -- sf project deploy validate -d force-app
   sfc run -- sf apex run test --code-coverage --result-format human
   sfc run -- sf apex get log -i <logId>
   sfc run -- sf project retrieve preview
   sfc run -- sf org list metadata --metadata-type ApexClass
   sfc run -- sf data query -q "SELECT ..." --json
   ```

   The child command's exit code is passed through, so success/failure
   handling is unchanged.
3. **Read the compressed view.** What each family keeps:
   - deploy/validate: errors, failures, warnings, status, counts ("N components Succeeded" collapsed to one line)
   - apex tests: failures, run summary, classes below 75% coverage
   - debug logs: USER_DEBUG, exceptions, SOQL/DML, LIMIT_USAGE, code units
   - `--json`: query records reprojected to CSV; other payloads minified
   - retrieve/deploy preview and org listings: table rows collapsed to counts per type
   - **repeat deploys emit a delta**: when you re-run the same deploy/validate,
     sfc diffs it against the previous run and shows only NEW / RESOLVED errors
     plus an unchanged count, e.g. `[sfc delta] vs run <prev-id>: 1 new, 2 resolved, ...`.
     For the full previous report, use `sfc show <prev-id>`. (Toggle: `filters.deltas`.)
4. **Expand only when needed.** Every output footer looks like:
   `[sfc <id>] sf-deploy filtered: ~52000 -> ~800 tokens (98.5% smaller). Full output: sfc show <id>`
   To dig in, prefer narrow expansion over full dumps:

   ```
   sfc show <id> --grep "MyClass|Error"
   sfc show <id> --head 100
   sfc show <id> --tail 50
   ```

5. **Do not re-truncate.** Never pipe `sfc run` output through `head`/`tail`/
   `grep` - it is already compressed and doing so risks dropping the footer id.
6. **Savings report**: `sfc stats` shows raw vs emitted tokens per family;
   useful when the user asks what sfc saved.

## Locating code: prefer the graph over bulk reads

When you are in a dev-support task and need to find where something lives or what
depends on it (before editing a class, tracing a trigger, etc.), do NOT open many
full files - a single large Apex class can be 150k+ tokens. If sfc is ACTIVE and
the `exploration-graph` toggle is on, use the offline code graph first:

```
sfc graph query "where is AccountTrigger used?"
sfc graph path "AccountService" "AccountTrigger"
sfc graph explain "AccountService"
```

Queries are token-budgeted (default 2000). Only open a specific file once the
graph has narrowed it down. If `sfc graph` reports it is disabled or graphify-sf
is not installed, fall back to normal reads; do not enable the toggle yourself.

Treat the graph as a **first-pass locator, not ground truth**. Its Apex
call-graph extraction is heuristic and can miss callers (reverse/"where used"
results may be incomplete). Use it to narrow down which file(s) to open, then
confirm callers/usages in the actual source before relying on them for an edit.

Note: this is targeted, dev-support lookup. A full standalone analysis or
architecture session is still out of scope - leave sfc off there (hard rule).

## What NOT to route through sfc

- git, npm, node, generic shell commands (already terse; sfc passes them
  through anyway, but routing them adds no value)
- `sf apex get log --json` - fetch logs WITHOUT `--json` so the debug-log
  filter can work line-by-line
- interactive commands or anything needing a TTY/stdin
- anything during analysis/architecture sessions (see hard scope rule)

## Troubleshooting

- `[sfc] inactive` (exit 3): sfc is off. Use the raw command; only the user
  decides to activate.
- Filter kept no lines: the run had no errors/signal; use `sfc show <id>` if
  you still need detail.
- Per-family toggles live in `.sfc/config.json` (`"filters"` map); the user
  can disable a single family without turning sfc off.
