"""Governor limits engine: math, version filtering, missing-key error."""

import pytest

from sf_architect.engines.limits import LimitNotFoundError, check_governor_limit


def test_headroom_no_breach(seeded_limits) -> None:
    result = check_governor_limit(
        {"limit_key": "soql_query_rows", "projected_value": 40000, "api_version": "62.0"},
        db_path=seeded_limits,
    )
    assert result["limit"] == 50000
    assert result["unit"] == "rows"
    assert result["headroom"] == 10000
    assert result["breaches"] is False
    assert result["last_verified"] == "2026-06-20"


def test_breach_flagged(seeded_limits) -> None:
    result = check_governor_limit(
        {"limit_key": "dml_rows", "projected_value": 12000, "api_version": "62.0"},
        db_path=seeded_limits,
    )
    assert result["breaches"] is True
    assert result["headroom"] == -2000


def test_version_prefix_tolerant(seeded_limits) -> None:
    # Seed stores "v62.0"; callers may pass "62.0", "v62.0", or "62".
    for version in ("62.0", "v62.0", "62"):
        result = check_governor_limit(
            {"limit_key": "heap_size", "projected_value": 1, "api_version": version},
            db_path=seeded_limits,
        )
        assert result["limit"] == 6000000


def test_missing_key_raises(seeded_limits) -> None:
    with pytest.raises(LimitNotFoundError):
        check_governor_limit(
            {"limit_key": "does_not_exist", "projected_value": 1, "api_version": "62.0"},
            db_path=seeded_limits,
        )
