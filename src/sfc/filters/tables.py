"""Box-drawing table collapse (retrieve/deploy preview, org list metadata, org list).

Phase 0 evidence: one `sf project retrieve preview` = ~214k tokens, 2,333 table
rows -> 99.4% collapsible. Keep headers/summaries; collapse data rows to a count
plus per-first-column tallies (usually the metadata type or org row kind).
"""

VERSION = "1.0"

_BORDER_CHARS = set("┌┐└┘├┤┬┴┼─│=- ")
_HEADER_HINTS = ("Full Name", "Created By", "Type ", "ALIAS", "USERNAME", "Name ")


def compress(lines):
    kept, data_rows = [], 0
    tallies = {}
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        # pure border/rule lines -> drop
        if all(ch in _BORDER_CHARS for ch in s):
            continue
        # data rows start with the box-drawing pipe and are not the header row
        if s.startswith("│") and not any(h in ln for h in _HEADER_HINTS):
            data_rows += 1
            cells = [c.strip() for c in s.strip("│").split("│")]
            if cells and cells[0]:
                tallies[cells[0]] = tallies.get(cells[0], 0) + 1
            continue
        kept.append(ln)
    if data_rows:
        top = sorted(tallies.items(), key=lambda kv: -kv[1])[:8]
        summary = ", ".join("{}={}".format(k, v) for k, v in top if k)
        kept.append(
            "[sfc collapsed] {} table row(s){}".format(
                data_rows, "; top: " + summary if summary else ""
            )
        )
    return "\n".join(kept)
