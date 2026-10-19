"""Deploy / validate report filter.

Phase 0 evidence: `sf project deploy` was the #2 command family (325 calls,
295 retry re-emissions); per-component "Succeeded" rows are pure noise.
Keep: errors, failures, warnings, status/summary lines, test results, deploy id.
Collapse: every component row that succeeded -> one count line.
"""

import re

VERSION = "1.0"

_SUCCEEDED = re.compile(r"\bsucceed(ed)?\b", re.IGNORECASE)
_KEEP = re.compile(
    r"error|fail|warning|status|elapsed|components|deploy id|deployed source|"
    r"test results|code coverage|pass rate|run tests|=== |───|conflict",
    re.IGNORECASE,
)


def compress(lines):
    kept, succeeded = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        low = ln.lower()
        if _SUCCEEDED.search(low) and "error" not in low and "fail" not in low:
            succeeded += 1
            continue
        if _KEEP.search(low) or re.match(r"\s*\d+\.", ln):
            kept.append(ln)
    kept = _collapse_repeats(kept)
    if succeeded:
        kept.append("[sfc collapsed] {} component/row(s) Succeeded".format(succeeded))
    return "\n".join(kept)


def _collapse_repeats(lines):
    """Fold consecutive identical kept lines (e.g. 'Status: Pending' polling spam)
    into one line with an explicit repeat count, so nothing is silently lost."""
    out = []
    for ln in lines:
        if out and out[-1][0] == ln:
            out[-1][1] += 1
        else:
            out.append([ln, 1])
    return [ln if n == 1 else "{}  [sfc: repeated {}x]".format(ln, n) for ln, n in out]
