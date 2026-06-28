"""Router: intent classification and limit-constrained advice."""

from sf_architect.engines.router import classify_intent, route


def test_classify_intent() -> None:
    assert classify_intent("How do I build a trigger framework?") == "build"
    assert classify_intent("What breaks if I change the Account object?") == "change"
    assert classify_intent("Is this safe at 2 million records?") == "volume"
    assert classify_intent("How do I build a batch job safe at high volume?") == "mixed"


def _fake_patterns(query, api_version=None, top_k=5):
    return [{"id": "p1", "score": 0.9, "text": "use batch apex", "provenance_url": "x"}]


def _fake_limits_breach(scenario):
    return {
        "limit": 50000,
        "unit": "rows",
        "projected": 80000,
        "headroom": -30000,
        "breaches": True,
        "last_verified": "2026-06-01",
    }


def _fake_limits_ok(scenario):
    return {
        "limit": 50000,
        "unit": "rows",
        "projected": 100,
        "headroom": 49900,
        "breaches": False,
        "last_verified": "2026-06-01",
    }


def test_mixed_query_invokes_both_engines() -> None:
    result = route(
        "How do I build a query safe at volume of 80000 rows?",
        scenario={"limit_key": "soql_query_rows", "projected_value": 80000, "api_version": "62.0"},
        patterns_fn=_fake_patterns,
        limits_fn=_fake_limits_breach,
    )
    assert result["intent"] == "mixed"
    assert result["results"]  # patterns engine called
    assert result["limit_check"] is not None  # limits engine called


def test_limit_breach_constrains_advice() -> None:
    result = route(
        "safe at volume 80000 rows",
        scenario={"limit_key": "soql_query_rows", "projected_value": 80000, "api_version": "62.0"},
        patterns_fn=_fake_patterns,
        limits_fn=_fake_limits_breach,
    )
    assert result["constrained"] is True
    assert any("overrides the pattern advice" in w for w in result["warnings"])


def test_no_breach_not_constrained() -> None:
    result = route(
        "safe at volume 100 rows",
        scenario={"limit_key": "soql_query_rows", "projected_value": 100, "api_version": "62.0"},
        patterns_fn=_fake_patterns,
        limits_fn=_fake_limits_ok,
    )
    assert result["constrained"] is False
