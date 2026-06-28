"""Explainable confidence scoring (plan Gap 2).

confidence = f(similarity, source_trust, version_match, corroboration)

The score is derived only from real, inspectable signals; the factor breakdown
is always returned so the number is defensible rather than invented. Low-confidence
answers are labeled explicitly.
"""

from __future__ import annotations

from sf_architect.contracts import Confidence, ConfidenceFactors

WEIGHTS = {
    "similarity": 0.50,
    "source_trust": 0.25,
    "version_match": 0.15,
    "corroboration": 0.10,
}

CORROBORATION_SIMILARITY_FLOOR = 0.45
CORROBORATION_TARGET = 3
LOW_CONFIDENCE_THRESHOLD = 0.5


def _corroboration_count(results: list[dict]) -> int:
    """How many results independently agree (similarity above the floor)."""
    return sum(1 for r in results if r.get("similarity", 0.0) >= CORROBORATION_SIMILARITY_FLOOR)


def compute_confidence(
    results: list[dict],
    api_version: str | None = None,
) -> tuple[Confidence | None, list[str]]:
    """Compute a confidence score + factor breakdown for a result set.

    Returns ``(confidence, warnings)``. ``confidence`` is ``None`` for an empty
    result set. A low-confidence warning is appended when the score is below the
    threshold so callers can label the answer.
    """
    if not results:
        return None, []

    top = results[0]
    similarity = float(top.get("similarity", 0.0))
    source_trust = int(top.get("source_trust", 0))
    version_match = bool(api_version) and _matches(top.get("api_version", ""), api_version)
    corroboration = _corroboration_count(results)

    score = (
        WEIGHTS["similarity"] * similarity
        + WEIGHTS["source_trust"] * (source_trust / 100.0)
        + WEIGHTS["version_match"] * (1.0 if version_match else 0.0)
        + WEIGHTS["corroboration"] * min(corroboration / CORROBORATION_TARGET, 1.0)
    )
    score = round(min(max(score, 0.0), 1.0), 4)

    confidence = Confidence(
        score=score,
        factors=ConfidenceFactors(
            similarity=round(similarity, 4),
            source_trust=source_trust,
            version_match=version_match,
            corroboration=corroboration,
        ),
    )

    warnings: list[str] = []
    if score < LOW_CONFIDENCE_THRESHOLD:
        warnings.append(
            f"Low confidence ({score:.2f}). Treat this guidance as a starting point and "
            "verify against the cited source."
        )
    return confidence, warnings


def _matches(stored: str, requested: str | None) -> bool:
    if not requested:
        return False

    def norm(v: str) -> str:
        v = v.strip().lstrip("v")
        return v if "." in v else f"{v}.0"

    return norm(stored) == norm(requested)
