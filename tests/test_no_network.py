"""Privacy guardrail: tools make no outbound network calls (except scraping).

Blocks socket creation, then exercises the deterministic tools to prove they
never reach the network. ``sync_latest_patterns`` is the only sanctioned network
path, and even it refuses non-allowlisted domains before any fetch.
"""

import socket

import pytest

from sf_architect.diagrams.render import render_diagram
from sf_architect.engines.limits import check_governor_limit
from sf_architect.security.allowlist import DomainNotAllowedError


def _block_outbound(monkeypatch) -> None:
    """Block outbound connections without breaking local socketpair/asyncio."""

    def _blocked(*args, **kwargs):
        raise AssertionError("outbound network connection attempted")

    monkeypatch.setattr(socket.socket, "connect", _blocked, raising=True)
    monkeypatch.setattr(socket, "create_connection", _blocked, raising=True)


def test_offline_tools_make_no_network_calls(monkeypatch, seeded_limits, tmp_path) -> None:
    _block_outbound(monkeypatch)

    result = check_governor_limit(
        {"limit_key": "dml_rows", "projected_value": 5, "api_version": "62.0"},
        db_path=seeded_limits,
    )
    assert result["limit"] == 10000

    diagram = render_diagram(
        {"title": "T", "nodes": [{"id": "a", "label": "A"}], "edges": []},
        "mermaid",
        output_path=tmp_path / "d.md",
    )
    assert diagram["format"] == "mermaid"


def test_scraping_refuses_before_network(monkeypatch) -> None:
    _block_outbound(monkeypatch)
    from sf_architect.ingest.embed import sync_latest_patterns

    # Non-allowlisted: must refuse before attempting any socket/fetch.
    with pytest.raises(DomainNotAllowedError):
        sync_latest_patterns(
            "https://evil.example.com",
            fetcher=lambda url: "# x\n## h\nbody",
            config={"scrape_allowlist": []},
        )
