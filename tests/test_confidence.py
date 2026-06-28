"""Confidence scoring: monotonic factors and low-confidence labeling."""

from sf_architect.confidence import LOW_CONFIDENCE_THRESHOLD, compute_confidence


def _result(similarity, trust=60, api_version="62.0"):
    return {"similarity": similarity, "source_trust": trust, "api_version": api_version}


def test_empty_results_no_confidence() -> None:
    conf, warnings = compute_confidence([], api_version="62.0")
    assert conf is None
    assert warnings == []


def test_higher_similarity_higher_score() -> None:
    low, _ = compute_confidence([_result(0.3)], api_version=None)
    high, _ = compute_confidence([_result(0.95)], api_version=None)
    assert high.score > low.score


def test_source_trust_increases_score() -> None:
    low_trust, _ = compute_confidence([_result(0.8, trust=40)], api_version=None)
    high_trust, _ = compute_confidence([_result(0.8, trust=100)], api_version=None)
    assert high_trust.score > low_trust.score


def test_version_match_factor() -> None:
    conf, _ = compute_confidence([_result(0.8, api_version="62.0")], api_version="62.0")
    assert conf.factors.version_match is True
    no_match, _ = compute_confidence([_result(0.8, api_version="62.0")], api_version=None)
    assert no_match.factors.version_match is False
    assert conf.score > no_match.score


def test_low_confidence_labeled() -> None:
    conf, warnings = compute_confidence([_result(0.1, trust=10)], api_version=None)
    assert conf.score < LOW_CONFIDENCE_THRESHOLD
    assert any("low confidence" in w.lower() for w in warnings)
