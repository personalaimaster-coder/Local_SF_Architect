"""Retrieval golden set (plan Gap 4): each question hits its expected pattern."""

from pathlib import Path

import yaml

from sf_architect.engines.patterns import query_architect_db

GOLDEN_PATH = Path(__file__).parent / "golden" / "retrieval.yaml"


def _cases():
    data = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8")) or {}
    return data.get("cases", [])


def test_golden_set_present() -> None:
    assert _cases(), "golden retrieval set must not be empty"


def test_golden_expected_heading_in_top_k(seeded_lance) -> None:
    failures = []
    for case in _cases():
        results = query_architect_db(case["question"], top_k=3, lance_dir=seeded_lance)
        headings = {r["heading"] for r in results}
        if case["expected_heading"] not in headings:
            failures.append((case["question"], case["expected_heading"], headings))
    assert not failures, f"golden retrieval misses: {failures}"
