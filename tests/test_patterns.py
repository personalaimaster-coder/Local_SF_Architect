"""Patterns engine: embedding dimension, retrieval, filters."""

from sf_architect.bootstrap import VECTOR_DIM
from sf_architect.engines.patterns import embed, query_architect_db


def test_embedding_dimension() -> None:
    vector = embed("bulkify apex")
    assert len(vector) == VECTOR_DIM
    assert all(isinstance(x, float) for x in vector)


def test_known_query_returns_pattern(seeded_lance) -> None:
    results = query_architect_db(
        "how to process many records safely at volume", lance_dir=seeded_lance
    )
    assert len(results) >= 1
    assert results[0]["score"] >= results[-1]["score"]  # ranked descending
    assert "provenance_url" in results[0]


def test_pillar_filter(seeded_lance) -> None:
    results = query_architect_db(
        "enforce field level security", pillar="Security", lance_dir=seeded_lance
    )
    assert results
    assert all(r["pillar"] == "Security" for r in results)


def test_top_k_respected(seeded_lance) -> None:
    results = query_architect_db("salesforce best practice", top_k=2, lance_dir=seeded_lance)
    assert len(results) <= 2
