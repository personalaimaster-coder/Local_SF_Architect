"""Dependency graph + blast radius against a fixture DX repo."""

from pathlib import Path

from sf_architect.engines.depgraph import (
    analyze_local_blast_radius,
    parse_apex,
    parse_metadata,
)
from sf_architect.memory.env_context import read_source_api_version

FIXTURE = Path(__file__).parent / "fixtures" / "sfdx"
CLASSES = FIXTURE / "force-app" / "main" / "default" / "classes"


def test_parse_apex_defines_and_references() -> None:
    node = parse_apex(CLASSES / "AccountService.cls")
    assert "AccountService" in node.defines
    assert "ContactHelper" in node.references
    assert "Contact" in node.references  # from SOQL FROM clause


def test_immediate_blast_radius() -> None:
    result = analyze_local_blast_radius(CLASSES / "ContactHelper.cls", repo_root=FIXTURE)
    immediate_files = {Path(r["file"]).name for r in result["immediate"]}
    assert "AccountService.cls" in immediate_files


def test_transitive_blast_radius() -> None:
    result = analyze_local_blast_radius(
        CLASSES / "ContactHelper.cls", repo_root=FIXTURE, depth=2
    )
    transitive_files = {Path(r["file"]).name for r in result["transitive"]}
    # OrderProcessor -> AccountService -> ContactHelper (1-hop transitive)
    assert "OrderProcessor.cls" in transitive_files


def test_dynamic_references_surfaced() -> None:
    result = analyze_local_blast_radius(CLASSES / "DynamicQuery.cls", repo_root=FIXTURE)
    assert "Database.query" in result["unresolved"]
    assert any("dynamic" in u.lower() for u in result["unresolved"])
    assert result["limitations"]  # limitations always documented


def test_metadata_object_defines() -> None:
    obj = FIXTURE / "force-app/main/default/objects/Account/Account.object-meta.xml"
    node = parse_metadata(obj)
    assert "Account" in node.defines


def test_sfdx_api_version_read() -> None:
    assert read_source_api_version(FIXTURE) == "62.0"
    assert read_source_api_version(CLASSES / "AccountService.cls") == "62.0"
