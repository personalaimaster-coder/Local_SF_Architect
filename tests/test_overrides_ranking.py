"""Override + semantic-anchor ranking application."""

from sf_architect.memory.overrides import apply_overrides
from sf_architect.memory.ranking import apply_semantic_anchors, is_integration_query

OVERRIDES = {
    "banned": [{"pattern": "Platform Events", "use_instead": "AWS EventBridge"}],
    "preferred": [{"pattern": "config over code", "weight_boost": 0.5}],
}


def test_banned_pattern_demoted() -> None:
    results = [
        {"id": "a", "title": "Use Platform Events", "text": "events", "score": 0.9},
        {"id": "b", "title": "Use a Flow", "text": "config over code wins", "score": 0.7},
    ]
    ranked = apply_overrides(results, OVERRIDES)
    # Preferred ("config over code", +0.5) should now outrank demoted banned (0.9*0.5).
    assert ranked[0]["id"] == "b"
    banned = next(r for r in ranked if r["id"] == "a")
    assert banned["override"] == "banned"


def test_preferred_pattern_boosted() -> None:
    results = [{"id": "x", "title": "config over code", "text": "", "score": 0.4}]
    ranked = apply_overrides(results, OVERRIDES)
    assert ranked[0]["score"] > 0.4
    assert ranked[0]["override"] == "preferred"


def test_integration_query_detection() -> None:
    assert is_integration_query("How do I build an integration callout?") is True
    assert is_integration_query("How do I write a validation rule?") is False


def test_semantic_anchor_boosts_scalability_for_integration() -> None:
    results = [
        {"id": "s", "pillar": "Scalability", "maturity": "tried-and-true", "score": 0.6},
        {"id": "p", "pillar": "Performance", "maturity": "proven", "score": 0.62},
    ]
    ranked = apply_semantic_anchors("integration with external api", results)
    # Scalability + tried-and-true gets +0.10, overtaking the Performance result.
    assert ranked[0]["id"] == "s"


def test_semantic_anchor_noop_for_non_integration() -> None:
    results = [{"id": "s", "pillar": "Scalability", "maturity": "proven", "score": 0.6}]
    ranked = apply_semantic_anchors("how to write a trigger", results)
    assert ranked[0]["score"] == 0.6
