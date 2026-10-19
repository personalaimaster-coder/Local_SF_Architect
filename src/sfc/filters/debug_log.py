"""Apex debug log filter.

Phase 0 evidence: 3 real logs = 5.49M raw tokens, 99.3% noise
(SYSTEM_METHOD_ENTRY/EXIT, HEAP_ALLOCATE, ...). Keep only the signal lines.
"""

import re

VERSION = "1.0"

_KEEP = re.compile(
    r"USER_DEBUG|EXCEPTION|FATAL|SOQL_EXECUTE|DML_|LIMIT_USAGE|CODE_UNIT_STARTED"
)


def compress(lines):
    kept = [ln for ln in lines if _KEEP.search(ln)]
    dropped = sum(1 for ln in lines if ln.strip()) - len(kept)
    if dropped > 0:
        kept.append(
            "[sfc collapsed] {} log line(s) dropped (kept USER_DEBUG, exceptions, "
            "SOQL/DML, limits, code units)".format(dropped)
        )
    return "\n".join(kept)
