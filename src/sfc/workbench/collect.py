"""`sfc collect` - guided re-collection of real Salesforce CLI fixtures.

Runs a scripted sequence against the authenticated default org, captures each
raw output in the Phase 0 corpus format (`$ command` as line one), and writes an
index.csv with size + per-family filtered reduction (reusing sfc's own filters).
Read-only by default; org-side steps require --allow-org-writes.
"""

import csv
import subprocess
from pathlib import Path

from .. import filters
from ..filters.common import est_tokens

DEFAULT_QUERY = "SELECT Id, Name FROM Account LIMIT 200"

INDEX_COLS = [
    "name", "command", "family", "requires_write", "ran", "exit_code",
    "chars", "lines", "est_tokens", "filtered_tokens", "reduction_pct",
]


def _steps(args):
    q = args.query or DEFAULT_QUERY
    obj = args.object or "Account"
    ddir = args.deploy_dir or "force-app"
    return [
        {"name": "retrieve-preview", "family": "sf-table", "write": False,
         "argv": ["sf", "project", "retrieve", "preview"]},
        {"name": "list-metadata", "family": "sf-table", "write": False,
         "argv": ["sf", "org", "list", "metadata", "--metadata-type", "ApexClass"]},
        {"name": "data-query-json", "family": "sf-json", "write": False,
         "argv": ["sf", "data", "query", "-q", q, "--json"]},
        {"name": "describe-json", "family": "sf-json", "write": False,
         "argv": ["sf", "sobject", "describe", "-s", obj, "--json"]},
        {"name": "apex-run-test", "family": "sf-apex-test", "write": True,
         "argv": ["sf", "apex", "run", "test", "--code-coverage",
                  "--result-format", "human", "--synchronous"]},
        {"name": "deploy-validate", "family": "sf-deploy", "write": True,
         "argv": ["sf", "project", "deploy", "validate", "-d", ddir,
                  "--test-level", "RunLocalTests"]},
    ]


def _exec(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    except FileNotFoundError as exc:
        return "[sfc collect] command not found: {}".format(exc), 127
    raw = p.stdout or ""
    if p.stderr:
        raw += ("\n" if raw and not raw.endswith("\n") else "") + p.stderr
    return raw, p.returncode


def _row(name, argv, fam, needs_write, ran, code=None, raw=""):
    rt = est_tokens(len(raw))
    ft = 0
    if ran and raw:
        emitted, _ = filters.apply(fam, raw)
        ft = est_tokens(len(emitted))
    return {
        "name": name,
        "command": " ".join(argv),
        "family": fam,
        "requires_write": needs_write,
        "ran": ran,
        "exit_code": "" if code is None else code,
        "chars": len(raw),
        "lines": raw.count("\n") + 1 if raw else 0,
        "est_tokens": rt,
        "filtered_tokens": ft,
        "reduction_pct": round(100 * (1 - ft / rt), 1) if rt else 0.0,
    }


def run(args):
    out_dir = Path(args.out or "collected")
    out_dir.mkdir(parents=True, exist_ok=True)
    print("[sfc collect] output -> {}/ (default org; project source untouched)".format(out_dir))
    if not args.allow_org_writes:
        print("[sfc collect] READ-ONLY mode: org-side steps (apex test, deploy "
              "validate) are SKIPPED. Re-run with --allow-org-writes to include them.")

    rows = []
    for st in _steps(args):
        name, argv, fam, needs_write = st["name"], st["argv"], st["family"], st["write"]
        if needs_write and not args.allow_org_writes:
            print("  - {:<16} SKIPPED (needs --allow-org-writes)".format(name))
            rows.append(_row(name, argv, fam, needs_write, ran=False))
            continue
        tag = "RUNNING org-side:" if needs_write else "running:"
        print("  - {:<16} {} {}".format(name, tag, " ".join(argv)))
        raw, code = _exec(argv)
        (out_dir / (name + ".txt")).write_text(
            "$ " + " ".join(argv) + "\n" + raw, errors="replace")
        rows.append(_row(name, argv, fam, needs_write, ran=True, code=code, raw=raw))

    with open(out_dir / "index.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    ran = sum(1 for r in rows if r["ran"])
    print("[sfc collect] wrote {} output(s) + index.csv to {}/".format(ran, out_dir))
    print("[sfc collect] to use as fixtures: review for anything sensitive, then "
          "share the folder. See docs/org-workbench.md.")
    return 0
