"""Shared filter utilities: token estimation, ANSI/spinner normalization."""

import re
from typing import List

# chars/4 -- same estimator used throughout Phase 0 so numbers stay comparable
def est_tokens(chars: int) -> int:
    return round(chars / 4)


# CSI/OSC escape sequences (colors, cursor movement, erase-line spinner tricks)
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[()][0-9A-B]")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def normalize_lines(text: str) -> List[str]:
    """ANSI-strip and flatten spinner repaints.

    Progress spinners redraw the same line with bare carriage returns; a stopped
    `sf project deploy validate` produced a 7 MB file that was ~99% repaint
    (Phase 0 notes.md). We keep only the final segment of each \r-repainted line
    and collapse consecutive duplicate lines.
    """
    text = strip_ansi(text).replace("\r\n", "\n")
    lines = []
    for raw_line in text.split("\n"):
        if "\r" in raw_line:
            raw_line = raw_line.rsplit("\r", 1)[-1]
            # collapse repaint frames only; genuine repeated \n lines are kept
            # so downstream filters can count them honestly
            if lines and raw_line == lines[-1]:
                continue
        lines.append(raw_line)
    return lines


def collapsed_note(dropped: int, what: str) -> str:
    return "[sfc collapsed] {} {}".format(dropped, what)
