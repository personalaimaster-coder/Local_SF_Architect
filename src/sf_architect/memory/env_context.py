"""Salesforce DX project context (plan Phase 2 task 4).

Reads ``sourceApiVersion`` from ``sfdx-project.json`` so retrieval and limit
checks can be filtered to the project's API version.
"""

from __future__ import annotations

import json
from pathlib import Path


def find_sfdx_project(start: str | Path) -> Path | None:
    """Walk up from ``start`` to locate the nearest ``sfdx-project.json``."""
    start = Path(start).resolve()
    if start.is_file():
        start = start.parent
    for directory in [start, *start.parents]:
        candidate = directory / "sfdx-project.json"
        if candidate.exists():
            return candidate
    return None


def read_source_api_version(repo_root: str | Path) -> str | None:
    """Return the project's ``sourceApiVersion`` (e.g. ``"62.0"``) or None."""
    project = find_sfdx_project(repo_root)
    if project is None:
        return None
    try:
        data = json.loads(project.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    version = data.get("sourceApiVersion")
    return str(version) if version is not None else None
