"""Full raw-output store: .sfc/outputs/<id>.txt with the command as line one.

The store is the agent's escape hatch: compressed output always points back to
the complete raw capture (`sfc show <id>`), so filtering is never lossy.
"""

import os
import re
import time
import uuid
from pathlib import Path
from typing import Optional

from . import state


def outputs_dir(root: Optional[Path] = None) -> Path:
    return state.sfc_dir(root) / "outputs"


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]


def save(output_id: str, command: str, raw_text: str, retention: int,
         root: Optional[Path] = None) -> Path:
    d = outputs_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / (output_id + ".txt")
    with open(path, "w", errors="replace") as fh:
        fh.write("$ " + command + "\n")
        fh.write(raw_text)
    _prune(d, retention)
    return path


def _norm_cmd(command: str) -> str:
    return re.sub(r"\s+", " ", command or "").strip().lower()


def find_prev(command: str, exclude_id: str,
              root: Optional[Path] = None) -> Optional[tuple]:
    """Most recent prior stored output for the same (normalized) command.

    Returns (prev_id, prev_body_text) or None. Used by the deploy-retry delta so
    a re-run diffs against its predecessor instead of re-emitting a full report.
    """
    d = outputs_dir(root)
    if not d.is_dir():
        return None
    want = _norm_cmd(command)
    candidates = []
    for p in d.glob("*.txt"):
        if p.stem == exclude_id:
            continue
        try:
            with open(p, "r", errors="replace") as fh:
                first = fh.readline()
        except OSError:
            continue
        if first.startswith("$ ") and _norm_cmd(first[2:]) == want:
            candidates.append(p)
    if not candidates:
        return None
    latest = max(candidates, key=os.path.getmtime)
    text = latest.read_text(errors="replace")
    body = text.split("\n", 1)[1] if text.startswith("$ ") else text
    return latest.stem, body


def load_path(output_id: str, root: Optional[Path] = None) -> Optional[Path]:
    # accept full ids and unambiguous prefixes
    d = outputs_dir(root)
    if not d.is_dir():
        return None
    exact = d / (output_id + ".txt")
    if exact.is_file():
        return exact
    matches = [p for p in d.glob("*.txt") if p.name.startswith(output_id)]
    return matches[0] if len(matches) == 1 else None


def _prune(d: Path, retention: int) -> None:
    if retention <= 0:
        return
    files = sorted(d.glob("*.txt"), key=os.path.getmtime, reverse=True)
    for old in files[retention:]:
        try:
            old.unlink()
        except OSError:
            pass
