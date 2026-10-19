"""Per-call token metering -> .sfc/metrics.jsonl.

Only written while sfc is active (fully dormant when off, by design).
This is the A/B evidence base: raw vs emitted tokens per family per call.
"""

import json
import time
from pathlib import Path
from typing import Optional

from . import state
from .filters.common import est_tokens


def log_call(command: str, family, output_id: str, raw_chars: int, emitted_chars: int,
             filter_version, exit_code: int, duration_s: float,
             root: Optional[Path] = None, delta_of=None) -> dict:
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": output_id,
        "family": family or "other",
        "command": command[:120],
        "raw_chars": raw_chars,
        "emitted_chars": emitted_chars,
        "raw_tokens": est_tokens(raw_chars),
        "emitted_tokens": est_tokens(emitted_chars),
        "filter_version": filter_version,   # None = pass-through
        "delta_of": delta_of,               # prev run id when this was a deploy delta
        "exit_code": exit_code,
        "duration_s": round(duration_s, 2),
    }
    path = state.sfc_dir(root) / "metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def read_rows(root: Optional[Path] = None):
    path = state.sfc_dir(root) / "metrics.jsonl"
    rows = []
    if path.is_file():
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    return rows
