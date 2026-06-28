"""Tenant overrides: banned/preferred team rules (plan Sections 12.5, additional gap #6).

Phase 1.5 introduces conflict surfacing: if a retrieved pattern matches a
``banned`` override, a warning is attached naming the conflict and the
``use_instead`` alternative. Phase 4 extends this with ranking application.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sf_architect.bootstrap import OVERRIDES_PATH

DEFAULT_OVERRIDES: dict[str, list] = {"banned": [], "preferred": []}


def load_overrides(path: str | Path | None = None) -> dict[str, Any]:
    """Load tenant_overrides.json, returning empty banned/preferred lists if absent."""
    path = Path(path) if path is not None else OVERRIDES_PATH
    if not path.exists():
        return dict(DEFAULT_OVERRIDES)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("banned", [])
    data.setdefault("preferred", [])
    return data


def save_overrides(overrides: dict[str, Any], path: str | Path | None = None) -> None:
    """Persist tenant_overrides.json."""
    path = Path(path) if path is not None else OVERRIDES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, indent=2), encoding="utf-8")


def _result_text(result: dict) -> str:
    return " ".join(
        str(result.get(field, "")) for field in ("title", "heading", "text")
    ).lower()


BANNED_DEMOTION = 0.5


def apply_overrides(
    results: list[dict], overrides: dict[str, Any] | None = None
) -> list[dict]:
    """Re-rank results by team overrides (plan Phase 4 task 2).

    Banned patterns are demoted (so preferred alternatives outrank them) while
    still being surfaced by :func:`conflict_warnings`; preferred patterns get
    their configured ``weight_boost``. Returns a re-sorted copy.
    """
    overrides = overrides if overrides is not None else load_overrides()
    banned = [str(b.get("pattern", "")).lower() for b in overrides.get("banned", [])]
    preferred = overrides.get("preferred", [])

    ranked = [dict(r) for r in results]
    for result in ranked:
        text = _result_text(result)
        score = float(result.get("score", 0.0))
        if any(b and b in text for b in banned):
            score *= BANNED_DEMOTION
            result["override"] = "banned"
        for pref in preferred:
            needle = str(pref.get("pattern", "")).lower()
            if needle and needle in text:
                score += float(pref.get("weight_boost", 0.0))
                result["override"] = "preferred"
        result["score"] = round(score, 4)

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked


def conflict_warnings(
    results: list[dict], overrides: dict[str, Any] | None = None
) -> list[str]:
    """Return warnings for any retrieved pattern that matches a banned rule."""
    overrides = overrides if overrides is not None else load_overrides()
    warnings: list[str] = []
    for ban in overrides.get("banned", []):
        needle = str(ban.get("pattern", "")).lower()
        if not needle:
            continue
        for result in results:
            if needle in _result_text(result):
                use_instead = ban.get("use_instead")
                reason = ban.get("reason", "team override")
                msg = (
                    f"Conflict: a recommended pattern references banned "
                    f"'{ban['pattern']}' ({reason})."
                )
                if use_instead:
                    msg += f" Use instead: {use_instead}."
                warnings.append(msg)
                break
    return warnings
