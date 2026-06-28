"""Caching: embedding-cache hits skip compute; ingest invalidates retrieval cache."""

from sf_architect import cache


def setup_function() -> None:
    cache.clear()


def test_embedding_cache_skips_recompute() -> None:
    calls = {"n": 0}

    def compute(text):
        calls["n"] += 1
        return [0.1, 0.2, 0.3]

    cache.get_embedding("hello", compute)
    cache.get_embedding("hello", compute)
    assert calls["n"] == 1  # second call served from cache


def test_different_text_recomputes() -> None:
    calls = {"n": 0}

    def compute(text):
        calls["n"] += 1
        return [0.0]

    cache.get_embedding("a", compute)
    cache.get_embedding("b", compute)
    assert calls["n"] == 2


def test_retrieval_cache_hit_and_invalidation() -> None:
    key = cache.retrieval_key("query", {"top_k": 5})
    cache.put_retrieval(key, [{"id": "x"}])
    assert cache.get_retrieval(key) == [{"id": "x"}]

    cache.bump_generation()  # simulates ingest / version change
    assert cache.get_retrieval(key) is None


def test_retrieval_cache_returns_copy() -> None:
    key = cache.retrieval_key("q2", {})
    cache.put_retrieval(key, [{"id": "y"}])
    got = cache.get_retrieval(key)
    got[0]["id"] = "mutated"
    # Mutating the returned list must not corrupt the cached value.
    assert cache.get_retrieval(key) == [{"id": "y"}]
