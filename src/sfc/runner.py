"""`sfc run -- <command...>`: execute, capture, compress, meter.

Contract:
- Inactive -> refuse to execute (exit 3) so the off-path is unmistakably dormant.
- Active   -> run the command, store the FULL raw output, print the compressed
  view plus a one-line footer with the expand pointer, exit with the child's
  return code.
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional

from . import delta, filters, metering, state, store
from .filters.common import est_tokens

INACTIVE_EXIT = 3
INACTIVE_MSG = (
    "[sfc] inactive - run the raw command directly (dev-support compression is off). "
    "Activate with: sfc on"
)


def run(argv: List[str], root: Optional[Path] = None) -> int:
    if not argv:
        print("[sfc] nothing to run. Usage: sfc run -- <command...>")
        return 2
    if not state.is_active(root):
        print(INACTIVE_MSG)
        return INACTIVE_EXIT

    # sfc is ON by default, so a run can be the first thing to touch `.sfc/`.
    # Seed it (config + the `*`-gitignore) idempotently so stored outputs and
    # metrics never leak into the host project's git status.
    state.ensure_config(root)

    command = " ".join(argv)
    config = state.load_config(root)

    start = time.time()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    except FileNotFoundError as exc:
        print("[sfc] command not found: {}".format(exc))
        return 127
    duration = time.time() - start

    raw = proc.stdout or ""
    if proc.stderr:
        raw = raw + ("\n" if raw and not raw.endswith("\n") else "") + proc.stderr

    family = filters.classify(command)
    output_id = store.new_id()
    retention = int(config.get("store", {}).get("retention", 50))
    store.save(output_id, command, raw, retention, root)

    delta_of = None
    if family is not None and state.filter_enabled(family, config):
        emitted, version = filters.apply(family, raw)
        if not emitted.strip() and raw.strip():
            emitted = "[sfc] filter kept no lines (no errors/signal found)"
        # deploy-retry delta: diff against the previous run of the same command
        if family == "sf-deploy" and config.get("filters", {}).get("deltas", True):
            dtext, prev_id = delta.build(command, raw, output_id, root)
            if dtext is not None:
                emitted, version, delta_of = dtext, delta.VERSION, prev_id
    else:
        emitted, version = raw, None

    if emitted:
        print(emitted)

    raw_tok, out_tok = est_tokens(len(raw)), est_tokens(len(emitted))
    if version is not None and raw_tok > 0:
        pct = round(100 * (1 - out_tok / raw_tok), 1) if raw_tok else 0.0
        label = "delta vs {}".format(delta_of) if delta_of else "{} filtered".format(family)
        print(
            "[sfc {id}] {label}: ~{r} -> ~{e} tokens ({p}% smaller). "
            "Full output: sfc show {id}".format(
                id=output_id, label=label, r=raw_tok, e=out_tok, p=pct
            )
        )
    else:
        print("[sfc {id}] pass-through (~{r} tokens). Full output: sfc show {id}".format(
            id=output_id, r=raw_tok))

    metering.log_call(command, family, output_id, len(raw), len(emitted),
                      version, proc.returncode, duration, root, delta_of=delta_of)
    return proc.returncode
