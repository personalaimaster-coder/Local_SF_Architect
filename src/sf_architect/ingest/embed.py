"""Ingestion pipeline: sanitize -> guard -> tag -> embed -> versioned upsert.

Runs the security gate (sanitizer + injection guard) before any write, then
tags each chunk with a pillar/maturity heuristic and performs a knowledge-version
aware upsert (plan Phase 3 tasks 3-4; Gap 1 / Gap 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sf_architect.bootstrap import read_config
from sf_architect.engines.patterns import resolve_source_trust, upsert_versioned
from sf_architect.ingest.chunk import chunk_markdown
from sf_architect.security.guard import Classifier, screen
from sf_architect.security.sanitize import sanitize_text

PILLAR_KEYWORDS = {
    "Security": ("security", "sharing", "crud", "fls", "permission", "encrypt", "auth"),
    "Scalability": ("bulk", "volume", "batch", "scale", "async", "queueable", "large data"),
    "Performance": ("cache", "index", "selective", "performance", "latency", "optimi"),
    "Reliability": ("retry", "idempotent", "rollback", "callout", "error", "exception"),
}

MATURITY_KEYWORDS = {
    "bleeding-edge": ("beta", "pilot", "developer preview"),
    "emerging": ("new in", "recently", "generally available"),
}


def assign_tags(text: str) -> tuple[str | None, str]:
    """Heuristic pillar + maturity tagging (plan Phase 3 task 4)."""
    lowered = text.lower()
    best_pillar = None
    best_hits = 0
    for pillar, keywords in PILLAR_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in lowered)
        if hits > best_hits:
            best_hits = hits
            best_pillar = pillar

    maturity = "proven"
    for label, keywords in MATURITY_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            maturity = label
            break
    return best_pillar, maturity


def _source_type(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if domain in ("help.salesforce.com", "developer.salesforce.com"):
        return "official_docs"
    if domain == "architect.salesforce.com":
        return "architect_site"
    if "release" in url.lower():
        return "release_notes"
    return "community_blog"


def ingest_markdown(
    url: str,
    markdown: str,
    api_version: str = "67.0",
    knowledge_version: str = "v67",
    force: bool = False,
    config: dict | None = None,
    classifier: Classifier | None = None,
    lance_dir: str | Path | None = None,
) -> dict[str, int]:
    """Sanitize, screen, tag, and version-upsert markdown chunks.

    Returns ``{ingested, skipped, superseded, blocked}``. Chunks flagged by the
    injection guard are counted in ``blocked`` and never written.
    """
    config = config if config is not None else read_config()
    scraped_at = datetime.now(timezone.utc).isoformat()
    source_type = _source_type(url)
    trust = resolve_source_trust(url, 0, config)

    items: list[dict] = []
    blocked = 0
    for chunk in chunk_markdown(markdown):
        # Guard screens the RAW chunk first so an injection attempt is detected
        # and blocked before the sanitizer would otherwise redact the evidence.
        if screen(chunk["text"], classifier).blocked:
            blocked += 1
            continue
        clean, _findings = sanitize_text(chunk["text"])
        pillar, maturity = assign_tags(clean)
        items.append(
            {
                "title": chunk["title"],
                "heading": chunk["heading"],
                "text": clean,
                "api_version": api_version,
                "knowledge_version": knowledge_version,
                "source_type": source_type,
                "source_trust": trust,
                "provenance_url": url,
                "scraped_at": scraped_at,
                "sanitized": True,
                "pillar": pillar,
                "maturity": maturity,
            }
        )

    result = upsert_versioned(items, lance_dir=lance_dir, force=force)
    result["blocked"] = blocked
    return result


def sync_latest_patterns(
    url: str,
    force: bool = False,
    fetcher=None,
    config: dict | None = None,
    api_version: str = "67.0",
    knowledge_version: str = "v67",
    classifier: Classifier | None = None,
    lance_dir: str | Path | None = None,
) -> dict[str, int]:
    """Fetch an allowlisted URL and ingest it (plan Section 11.2).

    Returns ``{ingested, skipped, superseded, blocked}``. The fetch is gated by the
    allowlist and SSRF validation in :func:`scraper.fetch_markdown`.
    """
    from sf_architect.ingest.scraper import fetch_markdown

    config = config if config is not None else read_config()
    markdown = fetch_markdown(url, fetcher=fetcher, config=config)
    return ingest_markdown(
        url,
        markdown,
        api_version=api_version,
        knowledge_version=knowledge_version,
        force=force,
        config=config,
        classifier=classifier,
        lance_dir=lance_dir,
    )
