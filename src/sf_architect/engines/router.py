"""Intent router (plan Sections 2 Part 3, 6).

Classifies a query into an intent and orchestrates the engines. For mixed /
"safe at volume" queries it calls BOTH the patterns engine (soft advice) and the
limits engine (hard math), then constrains the advice with the limits result:
a hard governor-limit breach always wins over a soft recommendation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sf_architect.engines import limits as limits_engine
from sf_architect.engines import patterns as patterns_engine

BUILD_KEYWORDS = ("how do i build", "how to", "implement", "create", "design", "build a")
CHANGE_KEYWORDS = ("if i change", "what breaks", "impact of", "blast radius", "refactor")
VOLUME_KEYWORDS = (
    "at volume",
    "safe at",
    "scale",
    "records",
    "rows",
    "governor",
    "limit",
    "bulk",
    "million",
    "large data",
)


def classify_intent(query: str) -> str:
    """Return one of ``build`` / ``change`` / ``volume`` / ``mixed``."""
    q = query.lower()
    build = any(k in q for k in BUILD_KEYWORDS)
    change = any(k in q for k in CHANGE_KEYWORDS)
    volume = any(k in q for k in VOLUME_KEYWORDS)

    flags = sum([build, change, volume])
    if flags >= 2:
        return "mixed"
    if volume:
        return "volume"
    if change:
        return "change"
    return "build"


def route(
    query: str,
    api_version: str | None = None,
    scenario: dict | None = None,
    top_k: int = 5,
    *,
    patterns_fn: Callable[..., list[dict]] | None = None,
    limits_fn: Callable[..., dict] | None = None,
) -> dict[str, Any]:
    """Orchestrate engines for a query and constrain advice with hard limits.

    ``patterns_fn`` / ``limits_fn`` are injectable for testing. When a governor
    limit is breached, ``constrained`` is set and a warning is attached so the
    soft pattern advice can never override the hard platform rule.
    """
    patterns_fn = patterns_fn or patterns_engine.query_architect_db
    limits_fn = limits_fn or limits_engine.check_governor_limit

    intent = classify_intent(query)
    result: dict[str, Any] = {
        "intent": intent,
        "results": [],
        "limit_check": None,
        "constrained": False,
        "warnings": [],
    }

    if intent in ("build", "volume", "mixed", "change"):
        result["results"] = patterns_fn(query, api_version=api_version, top_k=top_k)

    if scenario is not None and intent in ("volume", "mixed"):
        try:
            check = limits_fn(scenario)
            result["limit_check"] = check
            if check.get("breaches"):
                result["constrained"] = True
                result["warnings"].append(
                    f"Hard governor limit breached for '{scenario.get('limit_key')}': "
                    f"projected {check['projected']} exceeds limit {check['limit']} "
                    f"{check['unit']}. This constraint overrides the pattern advice above."
                )
        except limits_engine.LimitNotFoundError as exc:
            result["warnings"].append(f"Limit check skipped: {exc}")

    return result
