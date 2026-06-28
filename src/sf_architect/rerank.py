"""Optional cross-encoder reranking stage (plan Section 10.2, Phase 1.5).

A cross-encoder re-scores the top-k LanceDB hits for higher precision. It is
gated by ``reranker_enabled`` in config; when off, retrieval falls back to the
vector score only. The rerank score also feeds the confidence calculation by
replacing the per-result ``similarity`` with a normalized rerank relevance.

The model (``BAAI/bge-reranker-v2-m3``, MIT) downloads on first use. The scorer
is injectable so tests can exercise the toggle without downloading weights.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache

from sf_architect.bootstrap import read_config

Scorer = Callable[[str, list[str]], list[float]]


@lru_cache(maxsize=1)
def _cross_encoder(model_name: str):
    """Lazy-load the cross-encoder (downloads on first use)."""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    return TextCrossEncoder(model_name=model_name)


def _default_scorer(query: str, texts: list[str]) -> list[float]:  # pragma: no cover
    config = read_config()
    model_name = config.get("reranker_model", "BAAI/bge-reranker-v2-m3")
    encoder = _cross_encoder(model_name)
    return [float(s) for s in encoder.rerank(query, texts)]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def rerank(
    query: str,
    results: list[dict],
    scorer: Scorer | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Re-score and re-order results with a cross-encoder.

    Stores ``rerank_score`` on each result and overwrites ``score`` /
    ``similarity`` with the normalized rerank relevance so downstream confidence
    reflects the reranker.
    """
    if not results:
        return results
    scorer = scorer or _default_scorer
    texts = [r.get("text", "") for r in results]
    scores = scorer(query, texts)
    for result, raw in zip(results, scores):
        normalized = round(_sigmoid(float(raw)), 4)
        result["rerank_score"] = round(float(raw), 4)
        result["similarity"] = normalized
        result["score"] = normalized
    results.sort(key=lambda r: r["rerank_score"], reverse=True)
    return results[:top_k] if top_k else results


def maybe_rerank(
    query: str,
    results: list[dict],
    config: dict | None = None,
    scorer: Scorer | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Apply reranking only if ``reranker_enabled`` is true in config."""
    config = config if config is not None else read_config()
    if not config.get("reranker_enabled", False):
        return results
    return rerank(query, results, scorer=scorer, top_k=top_k)
