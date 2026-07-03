"""LanceDB-backed pattern search (plan Sections 11.2, 12.1).

Embeds text with fastembed's ``bge-small`` (ONNX, CPU) and stores chunks in an
embedded LanceDB table. ``query_architect_db`` embeds the query, runs a vector
search, filters by ``is_current`` / ``api_version``, and ranks the results.
"""

from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import lancedb
import pyarrow as pa
import yaml

from sf_architect import cache
from sf_architect.bootstrap import EMBEDDING_MODEL, LANCE_DIR, VECTOR_DIM, read_config
from sf_architect.locking import write_lock

TABLE_NAME = "patterns"
PILLARS = {"Security", "Reliability", "Scalability", "Performance"}
MATURITIES = {"bleeding-edge", "emerging", "proven", "tried-and-true"}


def patterns_schema() -> pa.Schema:
    """The LanceDB ``patterns`` table schema (plan Section 12.1)."""
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
            pa.field("title", pa.string()),
            pa.field("heading", pa.string()),
            pa.field("api_version", pa.string()),
            pa.field("knowledge_version", pa.string()),
            pa.field("valid_from", pa.string()),
            pa.field("valid_to", pa.string()),
            pa.field("is_current", pa.bool_()),
            pa.field("superseded_by", pa.string()),
            pa.field("source_type", pa.string()),
            pa.field("source_trust", pa.int32()),
            pa.field("provenance_url", pa.string()),
            pa.field("scraped_at", pa.string()),
            pa.field("sanitized", pa.bool_()),
            pa.field("pillar", pa.string()),
            pa.field("maturity", pa.string()),
            pa.field("content_hash", pa.string()),
        ]
    )


@lru_cache(maxsize=1)
def _embedder():
    """Load the embedding model once per process (downloads on first use)."""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL)


def _raw_embed(text: str) -> list[float]:
    vectors = list(_embedder().embed([text]))
    return [float(x) for x in vectors[0]]


def embed(text: str) -> list[float]:
    """Embed a single string into a 384-dim float32 vector (cached)."""
    return cache.get_embedding(text, _raw_embed)


def _embed_many(texts: list[str]) -> list[list[float]]:
    return [[float(x) for x in v] for v in _embedder().embed(texts)]


def _connect(lance_dir: str | Path | None = None):
    lance_dir = Path(lance_dir) if lance_dir is not None else LANCE_DIR
    lance_dir.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(lance_dir))


def _table_exists(db, name: str) -> bool:
    """True if a table exists (tolerant of lancedb's ListTablesResponse)."""
    listing = db.list_tables()
    names = getattr(listing, "tables", listing)
    return name in names


def open_table(lance_dir: str | Path | None = None, *, create: bool = True):
    """Open (or create) the patterns table."""
    db = _connect(lance_dir)
    if _table_exists(db, TABLE_NAME):
        return db.open_table(TABLE_NAME)
    if not create:
        return None
    return db.create_table(TABLE_NAME, schema=patterns_schema())


def make_id(provenance_url: str, heading: str, knowledge_version: str) -> str:
    """Deterministic primary key (plan Section 12.1)."""
    raw = f"{provenance_url}{heading}{knowledge_version}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    """Stable content hash for dedupe and cache invalidation."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_source_trust(
    provenance_url: str, stored_trust: int, config: dict | None = None
) -> int:
    """Resolve effective source trust (plan Gap 3).

    Per-domain ``source_trust`` overrides from config take precedence; otherwise
    the stored trust is used, falling back to the config ``default``.
    """
    config = config if config is not None else read_config()
    trust_map = config.get("source_trust") or {}
    domain = urlparse(provenance_url).netloc.lower()
    if domain and domain in trust_map:
        return int(trust_map[domain])
    if stored_trust:
        return int(stored_trust)
    return int(trust_map.get("default", 60))


def _record_from_seed(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a seed-file entry into a full table row (without the vector)."""
    provenance_url = item.get("provenance_url", "")
    heading = item.get("heading", "")
    knowledge_version = item.get("knowledge_version", "")
    text = item["text"]
    return {
        "id": make_id(provenance_url, heading, knowledge_version),
        "text": text,
        "title": item.get("title", ""),
        "heading": heading,
        "api_version": str(item.get("api_version", "")),
        "knowledge_version": knowledge_version,
        "valid_from": str(item.get("valid_from", date.today().isoformat())),
        "valid_to": item.get("valid_to") or "",
        "is_current": bool(item.get("is_current", True)),
        "superseded_by": item.get("superseded_by") or "",
        "source_type": item.get("source_type", "hand_seeded"),
        "source_trust": int(item.get("source_trust", 60)),
        "provenance_url": provenance_url,
        "scraped_at": item.get("scraped_at") or "",
        "sanitized": bool(item.get("sanitized", True)),
        "pillar": item.get("pillar") or "",
        "maturity": item.get("maturity") or "",
        "content_hash": content_hash(text),
    }


def load_patterns_seed(
    yaml_path: str | Path, lance_dir: str | Path | None = None
) -> int:
    """Load hand-authored seed patterns into LanceDB.

    Rebuilds the table from the seed file so it is the single source of truth for
    bundled offline patterns. Returns the number of patterns loaded.
    """
    yaml_path = Path(yaml_path)
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    items = data.get("patterns", [])

    with write_lock("patterns"):
        db = _connect(lance_dir)
        if _table_exists(db, TABLE_NAME):
            db.drop_table(TABLE_NAME)
        table = db.create_table(TABLE_NAME, schema=patterns_schema())

        if not items:
            cache.bump_generation()
            return 0

        records = [_record_from_seed(item) for item in items]
        vectors = _embed_many([r["text"] for r in records])
        for record, vector in zip(records, vectors):
            record["vector"] = vector
        table.add(records)

    cache.bump_generation()  # invalidate stale retrieval results
    return len(records)


def _scan_rows(table) -> list[dict[str, Any]]:
    """Read all rows from a table without a vector query (pyarrow scan)."""
    try:
        return table.to_arrow().to_pylist()
    except Exception:
        return []


def upsert_versioned(
    items: list[dict[str, Any]],
    lance_dir: str | Path | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Insert records with knowledge-version supersession (plan Gap 1).

    For each incoming record, prior ``is_current`` records in the same lineage
    (same ``provenance_url`` + ``heading``) are marked ``is_current=false`` with a
    ``valid_to`` date and ``superseded_by`` pointer, instead of being overwritten.
    Identical content that is already current is skipped (dedupe via
    ``content_hash``). Returns ``{ingested, skipped, superseded}``.
    """
    today = date.today().isoformat()
    ingested = skipped = superseded = 0

    with write_lock("patterns"):
        table = open_table(lance_dir, create=True)
        # Scan the current rows ONCE, then maintain the working set in memory as we
        # process the batch (previously this re-scanned the whole table per item,
        # making ingestion O(n*m)).
        current = [r for r in _scan_rows(table) if r.get("is_current")]

        for item in items:
            rec = _record_from_seed(item)

            if not force and any(
                r.get("content_hash") == rec["content_hash"] for r in current
            ):
                skipped += 1
                continue

            lineage_ids = [
                r["id"]
                for r in current
                if r.get("provenance_url") == rec["provenance_url"]
                and r.get("heading") == rec["heading"]
                and r["id"] != rec["id"]
            ]
            for old_id in lineage_ids:
                table.update(
                    where=f"id = '{old_id}'",
                    values={
                        "is_current": False,
                        "valid_to": today,
                        "superseded_by": rec["id"],
                    },
                )
                superseded += 1
            if lineage_ids:
                superseded_set = set(lineage_ids)
                current = [r for r in current if r["id"] not in superseded_set]

            rec["vector"] = embed(rec["text"])
            table.add([rec])
            current.append(rec)  # reflect the insert for subsequent items in the batch
            ingested += 1

    cache.bump_generation()
    return {"ingested": ingested, "skipped": skipped, "superseded": superseded}


def gc_stale(lance_dir: str | Path | None = None) -> int:
    """Delete superseded (non-current) vectors and compact (plan additional gap #5).

    Returns the number of stale rows removed. Keeps the store from growing without
    bound as records are superseded across knowledge versions.
    """
    table = open_table(lance_dir, create=False)
    if table is None:
        return 0
    with write_lock("patterns"):
        rows = _scan_rows(table)
        stale = [r for r in rows if not r.get("is_current")]
        if stale:
            table.delete("is_current = false")
            try:
                table.optimize()
            except Exception:
                pass  # compaction is best-effort
    cache.bump_generation()
    return len(stale)


def _matches_version(stored: str, requested: str) -> bool:
    """Loose API-version match tolerant of the ``v`` prefix and ``.0`` suffix."""
    def norm(v: str) -> str:
        v = v.strip().lstrip("v")
        return v if "." in v else f"{v}.0"

    return norm(stored) == norm(requested)


def query_architect_db(
    query: str,
    api_version: str | None = None,
    top_k: int = 5,
    pillar: str | None = None,
    maturity: str | None = None,
    lance_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Semantic search over architecture patterns.

    Returns a ranked list of result dicts (each with ``score``, ``provenance_url``,
    ``source_trust``, ``pillar``, ``maturity``, ...). Filters to current records and,
    when provided, the requested API version / pillar / maturity.
    """
    cache_key = cache.retrieval_key(
        query,
        {
            "api_version": api_version,
            "top_k": top_k,
            "pillar": pillar,
            "maturity": maturity,
            "lance_dir": str(lance_dir) if lance_dir is not None else "",
        },
    )
    cached = cache.get_retrieval(cache_key)
    if cached is not None:
        return cached

    table = open_table(lance_dir, create=False)
    if table is None or table.count_rows() == 0:
        return []

    config = read_config()
    query_vector = embed(query)
    # Push structured, exact-match filters (pillar/maturity) into the vector
    # prefilter so they constrain the candidate set BEFORE the top-k cut. Filtering
    # these in Python after the fetch could return fewer than top_k results even
    # when matching rows exist (they may fall outside the over-fetched window).
    # api_version stays a Python filter because it needs tolerant v-prefix/.0
    # normalization that a plain SQL equality cannot express.
    clauses = ["is_current = true"]
    if pillar and pillar in PILLARS:
        clauses.append(f"pillar = '{pillar}'")
    if maturity and maturity in MATURITIES:
        clauses.append(f"maturity = '{maturity}'")
    where = " AND ".join(clauses)

    # Over-fetch, then apply tolerant filtering / trust-blended ranking in Python.
    fetch_k = max(top_k * 4, top_k)
    hits = (
        table.search(query_vector)
        .metric("cosine")
        .where(where, prefilter=True)
        .limit(fetch_k)
        .to_list()
    )

    results: list[dict[str, Any]] = []
    for hit in hits:
        if api_version and not _matches_version(hit.get("api_version", ""), api_version):
            continue
        if pillar and hit.get("pillar") != pillar:
            continue
        if maturity and hit.get("maturity") != maturity:
            continue
        distance = float(hit.get("_distance", 1.0))
        similarity = max(0.0, 1.0 - distance)
        trust = resolve_source_trust(
            hit.get("provenance_url", ""), hit.get("source_trust", 0), config
        )
        # Trust nudges ranking without overwhelming semantic similarity (Gap 3).
        score = similarity * (0.85 + 0.15 * (trust / 100.0))
        results.append(
            {
                "id": hit["id"],
                "title": hit.get("title", ""),
                "heading": hit.get("heading", ""),
                "text": hit.get("text", ""),
                "api_version": hit.get("api_version", ""),
                "knowledge_version": hit.get("knowledge_version", ""),
                "pillar": hit.get("pillar") or None,
                "maturity": hit.get("maturity") or None,
                "source_type": hit.get("source_type", ""),
                "source_trust": trust,
                "provenance_url": hit.get("provenance_url", ""),
                "similarity": round(similarity, 4),
                "score": round(score, 4),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:top_k]
    cache.put_retrieval(cache_key, results)
    return results
