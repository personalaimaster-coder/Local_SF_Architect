"""draw.io emitter: well-formed mxGraphModel XML."""

from pathlib import Path

from lxml import etree

from sf_architect.diagrams.drawio import to_drawio
from sf_architect.diagrams.render import render_diagram

LAYOUT = {
    "title": "Integration",
    "nodes": [{"id": "a", "label": "Salesforce"}, {"id": "b", "label": "AWS"}],
    "edges": [{"from": "a", "to": "b", "label": "callout"}],
}


def test_well_formed_xml_with_mxgraphmodel() -> None:
    xml = to_drawio(LAYOUT)
    root = etree.fromstring(xml.encode("utf-8"))  # raises if malformed
    models = root.iter("mxGraphModel")
    assert next(models, None) is not None


def test_nodes_and_edges_present() -> None:
    xml = to_drawio(LAYOUT)
    root = etree.fromstring(xml.encode("utf-8"))
    vertices = [c for c in root.iter("mxCell") if c.get("vertex") == "1"]
    edges = [c for c in root.iter("mxCell") if c.get("edge") == "1"]
    assert len(vertices) == 2
    assert len(edges) == 1
    assert edges[0].get("source") and edges[0].get("target")


def test_render_writes_drawio(tmp_path) -> None:
    out = tmp_path / "d.drawio"
    result = render_diagram(LAYOUT, "drawio", output_path=out)
    assert result["format"] == "drawio"
    assert Path(result["path"]).exists()
    etree.fromstring(out.read_bytes())  # file is parseable
