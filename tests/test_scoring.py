"""Architecture scoring: determinism, evidence citations, risk_score."""

from pathlib import Path

from sf_architect.engines.scoring import PILLARS, score_architecture

FIXTURES = Path(__file__).parent / "fixtures" / "lint"


def test_every_pillar_has_evidence_citation() -> None:
    result = score_architecture(FIXTURES / "Bad.cls")
    for pillar in PILLARS:
        card = result["pillars"][pillar]
        assert len(card["findings"]) >= 1  # every score is backed by evidence


def test_infractions_lower_score() -> None:
    result = score_architecture(FIXTURES / "Bad.cls")
    # Bad.cls has a missing-sharing (Security) and SOQL/DML-in-loop (Scalability).
    assert result["pillars"]["Security"]["score"] < 100
    assert result["pillars"]["Scalability"]["score"] < 100


def test_clean_scope_full_scores_zero_risk() -> None:
    result = score_architecture(FIXTURES / "Clean.cls")
    assert all(result["pillars"][p]["score"] == 100 for p in PILLARS)
    assert result["risk_score"] == 0.0


def test_risk_score_computed_and_nonnull() -> None:
    result = score_architecture(FIXTURES / "Bad.cls")
    assert result["risk_score"] is not None
    assert 0.0 < result["risk_score"] <= 1.0


def test_deterministic_for_same_input() -> None:
    first = score_architecture(FIXTURES / "Bad.cls")
    second = score_architecture(FIXTURES / "Bad.cls")
    assert first == second
