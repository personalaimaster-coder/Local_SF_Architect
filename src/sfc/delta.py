"""Deploy-retry delta output.

Phase 0 evidence: `sf project deploy` was the #2 command family with 295 retry
re-emissions in-session (one session re-ran deploy 72x). Each retry dumps a full,
highly-compressible report into context even when almost nothing changed.

When a deploy command is re-run, this module diffs the current error/failure set
against the previous run of the same command and emits only what changed, with a
pointer back to the full previous report (`sfc show <prev-id>`). The first run of
a command has no predecessor and falls back to the normal filtered report.
"""

import re
from typing import List, Optional, Tuple

from . import store

VERSION = "delta-1.0"

# lines that indicate a real error/failure...
_ERROR_RE = re.compile(r"error|fail", re.IGNORECASE)
# ...but not these (status/summary lines that merely contain the word, and
# "0 errors"/"no errors" success phrasing)
_STATUS_RE = re.compile(r"^\s*(status|deploy id|elapsed|components|=== )", re.IGNORECASE)
_NONERROR_RE = re.compile(r"\b(0 errors|no errors|error id)\b|errors?\s*[:=]\s*0",
                          re.IGNORECASE)


def extract_errors(text: str) -> List[str]:
    errs = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("[sfc"):
            continue
        if _STATUS_RE.search(s) or _NONERROR_RE.search(s):
            continue
        if _ERROR_RE.search(s):
            errs.append(s)
    return errs


def status_lines(text: str) -> List[str]:
    out = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.lower().startswith("status") or s.lower().startswith("deploy id"):
            out.append(s)
    return out


def compute(prev_text: str, curr_text: str) -> Tuple[List[str], List[str], List[str]]:
    """Return (new, resolved, unchanged) error-line lists."""
    prev = extract_errors(prev_text)
    curr = extract_errors(curr_text)
    pset, cset = set(prev), set(curr)
    new = [e for e in curr if e not in pset]
    resolved = [e for e in prev if e not in cset]
    unchanged = [e for e in curr if e in pset]
    return new, resolved, unchanged


def render(prev_id: str, curr_text: str,
           new: List[str], resolved: List[str], unchanged: List[str]) -> str:
    lines = ["[sfc delta] vs run {}: {} new, {} resolved, {} unchanged".format(
        prev_id, len(new), len(resolved), len(unchanged))]
    lines.extend(status_lines(curr_text))
    if new:
        lines.append("NEW error(s):")
        lines.extend("  " + e for e in new)
    if resolved:
        preview = "; ".join(resolved[:3]) + (" ..." if len(resolved) > 3 else "")
        lines.append("RESOLVED {} error(s): {}".format(len(resolved), preview))
    if unchanged:
        lines.append(
            "[sfc] {} unchanged error(s) - full previous report: sfc show {}".format(
                len(unchanged), prev_id))
    if not (new or resolved or unchanged):
        lines.append("[sfc] no errors in either run")
    return "\n".join(lines)


def build(command: str, curr_text: str, curr_id: str,
          root=None) -> Tuple[Optional[str], Optional[str]]:
    """Return (delta_text, prev_id), or (None, None) if there is no prior run."""
    prev = store.find_prev(command, curr_id, root)
    if prev is None:
        return None, None
    prev_id, prev_text = prev
    new, resolved, unchanged = compute(prev_text, curr_text)
    return render(prev_id, curr_text, new, resolved, unchanged), prev_id
