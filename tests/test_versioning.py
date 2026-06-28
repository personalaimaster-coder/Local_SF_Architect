"""Knowledge versioning: supersession and version-correct retrieval (Gap 1)."""

from sf_architect.engines.patterns import (
    _scan_rows,
    open_table,
    query_architect_db,
    upsert_versioned,
)


def _pattern(version, text):
    return {
        "title": "Async pattern",
        "heading": "Async",
        "text": text,
        "api_version": version.lstrip("v") + ".0" if "." not in version else version,
        "knowledge_version": version,
        "source_type": "official_docs",
        "source_trust": 100,
        "provenance_url": "https://help.salesforce.com/async",
    }


def test_supersession_marks_prior_not_current(tmp_path) -> None:
    lance = tmp_path / "lance"
    upsert_versioned([_pattern("v62", "Use Queueable for v62 async work.")], lance_dir=lance)
    result = upsert_versioned(
        [_pattern("v63", "Use Queueable with finalizers for v63 async work.")],
        lance_dir=lance,
    )
    assert result["ingested"] == 1
    assert result["superseded"] == 1

    table = open_table(lance, create=False)
    rows = _scan_rows(table)
    current = [r for r in rows if r["is_current"]]
    superseded = [r for r in rows if not r["is_current"]]
    assert len(current) == 1
    assert current[0]["knowledge_version"] == "v63"
    assert len(superseded) == 1
    assert superseded[0]["valid_to"]
    assert superseded[0]["superseded_by"] == current[0]["id"]


def test_identical_content_skipped(tmp_path) -> None:
    lance = tmp_path / "lance"
    upsert_versioned([_pattern("v62", "Same content.")], lance_dir=lance)
    result = upsert_versioned([_pattern("v62", "Same content.")], lance_dir=lance)
    assert result["skipped"] == 1
    assert result["ingested"] == 0


def test_retrieval_prefers_current(tmp_path) -> None:
    lance = tmp_path / "lance"
    upsert_versioned([_pattern("v62", "Old async guidance about Queueable.")], lance_dir=lance)
    upsert_versioned([_pattern("v63", "New async guidance about Queueable.")], lance_dir=lance)
    results = query_architect_db("async queueable guidance", lance_dir=lance)
    assert results
    # Only the current (v63) record should surface.
    assert all(r["knowledge_version"] == "v63" for r in results)
