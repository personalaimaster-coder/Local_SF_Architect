"""Semantic anchor ranking (plan Phase 4 task 3).

Boosts results tagged Scalability or with proven/tried-and-true maturity when the
query is integration-related, reflecting the architect bias toward battle-tested
patterns for integration work.
"""

from __future__ import annotations

INTEGRATION_KEYWORDS = (
    "integration",
    "integrate",
    "callout",
    "api",
    "event",
    "middleware",
    "external system",
    "webhook",
    "mulesoft",
)

SCALABILITY_BOOST = 0.05
MATURITY_BOOST = 0.05
MATURE_LABELS = {"proven", "tried-and-true"}


def is_integration_query(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in INTEGRATION_KEYWORDS)


def apply_semantic_anchors(query: str, results: list[dict]) -> list[dict]:
    """Boost Scalability / mature patterns for integration queries; re-sort a copy."""
    if not is_integration_query(query):
        return [dict(r) for r in results]

    ranked = [dict(r) for r in results]
    for result in ranked:
        score = float(result.get("score", 0.0))
        if result.get("pillar") == "Scalability":
            score += SCALABILITY_BOOST
        if result.get("maturity") in MATURE_LABELS:
            score += MATURITY_BOOST
        result["score"] = round(score, 4)
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked
