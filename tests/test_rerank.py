"""Reranker toggle: on/off changes ordering and confidence input."""

from sf_architect.rerank import maybe_rerank, rerank


def _results():
    return [
        {"id": "a", "text": "alpha", "similarity": 0.6, "score": 0.6},
        {"id": "b", "text": "beta", "similarity": 0.5, "score": 0.5},
    ]


def _reverse_scorer(query, texts):
    # Score later texts higher so ordering flips relative to vector order.
    return [float(i) for i in range(len(texts))]


def test_rerank_changes_order_and_similarity() -> None:
    reranked = rerank("q", _results(), scorer=_reverse_scorer)
    assert reranked[0]["id"] == "b"  # order flipped
    # rerank score feeds confidence by overwriting similarity
    assert reranked[0]["similarity"] == reranked[0]["score"]
    assert "rerank_score" in reranked[0]


def test_maybe_rerank_off_is_noop() -> None:
    original = _results()
    out = maybe_rerank("q", original, config={"reranker_enabled": False}, scorer=_reverse_scorer)
    assert [r["id"] for r in out] == ["a", "b"]


def test_maybe_rerank_on_applies() -> None:
    out = maybe_rerank(
        "q", _results(), config={"reranker_enabled": True}, scorer=_reverse_scorer
    )
    assert out[0]["id"] == "b"
