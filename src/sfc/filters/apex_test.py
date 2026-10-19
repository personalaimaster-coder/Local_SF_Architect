"""Apex test run filter.

Keep: failures/errors, outcome + summary lines, and coverage rows below 75%.
Drop: passing test rows and classes at healthy coverage.
"""

import re

VERSION = "1.0"

_KEEP = re.compile(
    r"fail|error|pass rate|tests ran|outcome|summary|skip|=== |test run id|"
    r"time elapsed|org wide coverage",
    re.IGNORECASE,
)
_PCT = re.compile(r"(\d{1,3})\s*%")


def compress(lines):
    kept, dropped = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        low = ln.lower()
        if _KEEP.search(low):
            kept.append(ln)
            continue
        m = _PCT.search(ln)
        if m and int(m.group(1)) < 75:
            kept.append(ln)  # low-coverage class: actionable, keep
            continue
        dropped += 1
    if dropped:
        kept.append(
            "[sfc collapsed] {} passing/healthy row(s) dropped "
            "(kept failures, summary, classes <75% coverage)".format(dropped)
        )
    return "\n".join(kept)
