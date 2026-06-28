"""Embedding + retrieval caches (plan Gap 6).

- Embedding cache: query text -> vector. Embeddings are content-stable, so this
  is keyed purely by a content hash and never needs invalidation.
- Retrieval cache: (query + filters) -> result set. Invalidated whenever the
  knowledge base changes (ingest / version change) by bumping a generation token.

This is an optimization for repeated work, not a correctness fix — LanceDB is
already fast for a single user.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable
from typing import Any

_EMBED_CACHE_MAX = 2048
_RETRIEVAL_CACHE_MAX = 512

_embedding_cache: dict[str, list[float]] = {}
_retrieval_cache: dict[tuple[int, str], list[dict]] = {}
_generation: int = 0


def _content_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_embedding(text: str, compute: Callable[[str], list[float]]) -> list[float]:
    """Return a cached embedding for ``text`` or compute and cache it."""
    key = _content_key(text)
    cached = _embedding_cache.get(key)
    if cached is not None:
        return cached
    vector = compute(text)
    if len(_embedding_cache) >= _EMBED_CACHE_MAX:
        _embedding_cache.clear()
    _embedding_cache[key] = vector
    return vector


def retrieval_key(query: str, filters: dict[str, Any]) -> str:
    """Build a stable cache key from a query and its filters."""
    parts = [query] + [f"{k}={filters[k]}" for k in sorted(filters)]
    return _content_key("|".join(parts))


def get_retrieval(key: str) -> list[dict] | None:
    """Return cached results for the current generation, or None."""
    cached = _retrieval_cache.get((_generation, key))
    return copy.deepcopy(cached) if cached is not None else None


def put_retrieval(key: str, results: list[dict]) -> None:
    """Cache results under the current generation."""
    if len(_retrieval_cache) >= _RETRIEVAL_CACHE_MAX:
        _retrieval_cache.clear()
    _retrieval_cache[(_generation, key)] = copy.deepcopy(results)


def bump_generation() -> int:
    """Invalidate the retrieval cache after an ingest / version change."""
    global _generation
    _generation += 1
    _retrieval_cache.clear()
    return _generation


def clear() -> None:
    """Clear all caches (mainly for tests)."""
    _embedding_cache.clear()
    _retrieval_cache.clear()
