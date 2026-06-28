"""Envelope shape on success and failure (plan Section 11.1)."""

from sf_architect.contracts import Confidence, ConfidenceFactors, fail, ok


def test_ok_envelope_shape() -> None:
    env = ok("query_architect_db", {"results": []})
    assert env["ok"] is True
    assert env["tool"] == "query_architect_db"
    assert env["data"] == {"results": []}
    assert env["error"] is None
    assert env["warnings"] == []
    assert env["confidence"] is None


def test_ok_envelope_with_confidence_and_warnings() -> None:
    conf = Confidence(score=0.8, factors=ConfidenceFactors(similarity=0.8, source_trust=95))
    env = ok("query_architect_db", {"results": [1]}, confidence=conf, warnings=["w"])
    assert env["confidence"]["score"] == 0.8
    assert env["confidence"]["factors"]["source_trust"] == 95
    assert env["warnings"] == ["w"]


def test_fail_envelope_shape() -> None:
    env = fail("check_governor_limit", "LIMIT_NOT_FOUND", "no such limit")
    assert env["ok"] is False
    assert env["data"] is None
    assert env["confidence"] is None
    assert env["error"] == {"code": "LIMIT_NOT_FOUND", "message": "no such limit"}
