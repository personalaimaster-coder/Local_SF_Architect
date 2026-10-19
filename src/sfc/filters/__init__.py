"""Command-family classification and filter dispatch.

Families (aligned with Phase 0 analyze.py, refined for filtering):
  sf-debug-log   sf apex get/tail log        -> keep signal lines only (99.3% cut)
  sf-json        any command with --json     -> CSV reprojection / minify
  sf-table       retrieve/deploy preview, org list [metadata] -> collapse table rows
  sf-deploy      project deploy/validate     -> collapse Succeeded rows
  sf-apex-test   apex run test               -> failures + summary + low coverage
  (None)         everything else (git, npm, unknown) -> pass through untouched
"""

import re
from typing import List, Optional, Tuple

from . import apex_test, debug_log, deploy, json_out, tables
from .common import normalize_lines

_SF = r"\b(sf|sfdx)\b"

_RULES = [
    # order matters: most specific first
    ("sf-debug-log", re.compile(_SF + r".*\bapex\b.*\b(get|tail|list)\s+log\b|" + _SF + r".*\bforce:apex:log\b")),
    ("sf-table", re.compile(_SF + r".*\b(retrieve|deploy)\s+preview\b|" + _SF + r".*\borg\s+list\b")),
    ("sf-json", re.compile(_SF + r".*--json\b")),
    ("sf-deploy", re.compile(_SF + r".*\b(project\s+deploy|project:deploy|force:source:deploy)\b")),
    ("sf-apex-test", re.compile(_SF + r".*\bapex\b.*\b(run\s+test|test\s+run)\b|" + _SF + r".*\bforce:apex:test\b")),
]

# line-based filters get normalized lines; text-based get the raw string
_LINE_FILTERS = {
    "sf-debug-log": debug_log,
    "sf-table": tables,
    "sf-deploy": deploy,
    "sf-apex-test": apex_test,
}
_TEXT_FILTERS = {
    "sf-json": json_out,
}


def classify(command: str) -> Optional[str]:
    low = (command or "").strip().lower()
    for family, rx in _RULES:
        if rx.search(low):
            return family
    return None


def apply(family: Optional[str], text: str) -> Tuple[str, Optional[str]]:
    """Return (emitted_text, filter_version). filter_version=None means pass-through."""
    if family in _LINE_FILTERS:
        mod = _LINE_FILTERS[family]
        return mod.compress(normalize_lines(text)), mod.VERSION
    if family in _TEXT_FILTERS:
        mod = _TEXT_FILTERS[family]
        return mod.compress(text), mod.VERSION
    return text, None


def list_families() -> List[str]:
    return [fam for fam, _ in _RULES]
