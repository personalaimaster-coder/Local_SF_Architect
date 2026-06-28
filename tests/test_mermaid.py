"""Mermaid emitter: valid flow/sequence syntax and file rendering."""

from pathlib import Path

from sf_architect.diagrams.mermaid import to_mermaid
from sf_architect.diagrams.render import render_diagram

FLOW = {
    "title": "Order Flow",
    "type": "flow",
    "nodes": [{"id": "acct", "label": "Account"}, {"id": "ord", "label": "Order"}],
    "edges": [{"from": "acct", "to": "ord", "label": "places"}],
}


def test_flow_syntax() -> None:
    src = to_mermaid(FLOW)
    assert src.startswith("flowchart TD")
    assert 'acct["Account"]' in src
    assert 'acct -->|"places"| ord' in src


def test_sequence_syntax() -> None:
    seq = dict(FLOW, type="sequence")
    src = to_mermaid(seq)
    assert src.startswith("sequenceDiagram")
    assert "participant acct as Account" in src
    assert "acct->>ord: places" in src


def test_node_id_sanitized() -> None:
    layout = {"type": "flow", "nodes": [{"id": "Account Service", "label": "X"}], "edges": []}
    src = to_mermaid(layout)
    assert "Account Service" not in src  # spaces sanitized out of the id
    assert "Account_Service" in src


def test_render_writes_md(tmp_path) -> None:
    out = tmp_path / "diagram.md"
    result = render_diagram(FLOW, "mermaid", output_path=out)
    assert result["format"] == "mermaid"
    assert Path(result["path"]).exists()
    assert "```mermaid" in out.read_text(encoding="utf-8")
