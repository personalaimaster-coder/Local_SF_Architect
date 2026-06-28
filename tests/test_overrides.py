"""Override-conflict surfacing: banned patterns raise a visible warning."""

from sf_architect.memory.overrides import conflict_warnings, load_overrides, save_overrides

OVERRIDES = {
    "banned": [
        {
            "pattern": "Platform Events",
            "reason": "Standardized on AWS EventBridge",
            "use_instead": "AWS EventBridge",
        }
    ],
    "preferred": [],
}


def test_banned_pattern_warns() -> None:
    results = [
        {"title": "Use Platform Events for async", "heading": "Events", "text": "..."},
    ]
    warnings = conflict_warnings(results, OVERRIDES)
    assert len(warnings) == 1
    assert "Platform Events" in warnings[0]
    assert "AWS EventBridge" in warnings[0]


def test_no_conflict_no_warning() -> None:
    results = [{"title": "Bulkify Apex", "heading": "Bulkification", "text": "collections"}]
    assert conflict_warnings(results, OVERRIDES) == []


def test_load_save_roundtrip(tmp_path) -> None:
    path = tmp_path / "tenant_overrides.json"
    save_overrides(OVERRIDES, path)
    loaded = load_overrides(path)
    assert loaded["banned"][0]["pattern"] == "Platform Events"


def test_load_missing_returns_defaults(tmp_path) -> None:
    loaded = load_overrides(tmp_path / "absent.json")
    assert loaded == {"banned": [], "preferred": []}
