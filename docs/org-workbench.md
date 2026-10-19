# sfc org workbench — runbook

The org workbench collects the real Salesforce data that this repo intentionally
does **not** ship. It is built and tested offline here, but you run it on a
machine that has an authenticated Salesforce org. The outputs are meant to be
reviewed and shared with the team.

Two commands:

- `sfc collect` — re-collect real CLI fixtures (test run, deploy validate,
  retrieve preview, query, describe) in the Phase 0 corpus format.
- `sfc bench` — benchmark raw `sf` CLI output vs the Salesforce DX MCP server,
  per command family, and write a token-comparison report.

Neither command modifies your project source or git state.

## Prerequisites

- Salesforce CLI (`sf`) installed and a **default org** set
  (`sf config set target-org <alias>` or run inside an SFDX project).
- Python 3.9+ and `sfc` installed (`pipx install sf-compress` or
  `pip install sf-compress`).
- For `sfc bench`: Node.js (for `npx`) to launch the Salesforce DX MCP server.

## 1. Collect fixtures

Read-only run (safe; org-side steps are skipped):

```
sfc collect --out collected
```

Include the org-side steps (runs an Apex test suite and a deploy **validate** —
a validate never deploys, but it does execute tests server-side):

```
sfc collect --allow-org-writes --out collected \
  --object Account \
  --query "SELECT Id, Name FROM Account LIMIT 200" \
  --deploy-dir force-app
```

What you get in `collected/`:

- one `<name>.txt` per step, with the exact command as the first line
  (`$ sf ...`) — same format as the Phase 0 corpus.
- `index.csv` with `chars, lines, est_tokens, filtered_tokens, reduction_pct`
  per step, so the compression ratios are visible immediately.

Steps and safety:

| step | command | org write? |
|---|---|---|
| retrieve-preview | `sf project retrieve preview` | no |
| list-metadata | `sf org list metadata --metadata-type ApexClass` | no |
| data-query-json | `sf data query -q <SOQL> --json` | no |
| describe-json | `sf sobject describe -s <obj> --json` | no |
| apex-run-test | `sf apex run test --code-coverage --synchronous` | yes (test exec) |
| deploy-validate | `sf project deploy validate -d <dir> --test-level RunLocalTests` | yes (server-side validate) |

## 2. Benchmark CLI vs DX MCP

```
sfc bench --out bench-report.md \
  --object Account \
  --query "SELECT Id, Name FROM Account LIMIT 200" \
  --mcp-cmd "npx -y @salesforce/mcp --orgs DEFAULT_TARGET_ORG --toolsets all"
```

- Adjust `--mcp-cmd` to match the DX MCP server flags for your version. The
  harness auto-discovers tool names via the MCP `tools/list` call, so it tolerates
  the (beta) server changing tool names.
- If the MCP server can't be launched, the report is still written with the CLI
  numbers and a note that the MCP side was unavailable.

`bench-report.md` has one row per family: `CLI raw`, `CLI filtered (sfc)`,
`MCP tool`, `MCP raw`, and which transport was terser. Use it to decide, per
family, whether to route through the DX MCP server or the CLI — and wrap
whichever transport is verbose with sfc's filters.

## 3. Feed results back

1. Review `collected/` for anything sensitive to your org/project before sharing.
   (This repo deliberately keeps proprietary data out — see `bundle/phase0-bundle/notes.md`.)
2. To use them as golden fixtures, adapt `tests/synth.py` shapes or point new
   tests at the collected files. Keep client-identifying content out of anything
   committed to a shared/public remote.
3. Share `bench-report.md` and the `index.csv` reduction numbers with the team.
