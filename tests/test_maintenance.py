"""Maintenance routines: stale-vector GC and CLI wiring."""

from click.testing import CliRunner

from sf_architect.cli import main
from sf_architect.engines.patterns import _scan_rows, gc_stale, open_table, upsert_versioned


def _pattern(version, text):
    return {
        "title": "Async",
        "heading": "Async",
        "text": text,
        "api_version": "62.0",
        "knowledge_version": version,
        "source_type": "official_docs",
        "source_trust": 100,
        "provenance_url": "https://help.salesforce.com/async",
    }


def test_gc_removes_superseded(tmp_path) -> None:
    lance = tmp_path / "lance"
    upsert_versioned([_pattern("v62", "Old guidance.")], lance_dir=lance)
    upsert_versioned([_pattern("v63", "New guidance.")], lance_dir=lance)

    table = open_table(lance, create=False)
    assert any(not r["is_current"] for r in _scan_rows(table))  # one stale row exists

    removed = gc_stale(lance_dir=lance)
    assert removed == 1

    remaining = _scan_rows(open_table(lance, create=False))
    assert all(r["is_current"] for r in remaining)


def test_score_cli_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["score", "tests/fixtures/lint/Bad.cls"])
    assert result.exit_code == 0
    assert "risk_score:" in result.output
