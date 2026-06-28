"""draw.io (mxGraphModel) emitter (plan Phase 5 task 2).

Emits an uncompressed ``.drawio`` document (``mxfile > diagram > mxGraphModel``)
built with lxml so the output is always well-formed XML. Compression is optional
and intentionally omitted (uncompressed XML opens fine in draw.io).
"""

from __future__ import annotations

from lxml import etree

_NODE_W = 160
_NODE_H = 40
_X = 40
_Y0 = 40
_Y_STEP = 80


def to_drawio(layout: dict) -> str:
    """Render a layout to a draw.io XML document string."""
    mxfile = etree.Element("mxfile", host="sf-local-architect")
    diagram = etree.SubElement(
        mxfile, "diagram", name=layout.get("title", "Architecture Diagram")
    )
    model = etree.SubElement(
        diagram,
        "mxGraphModel",
        dx="800",
        dy="600",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        page="1",
        pageScale="1",
        math="0",
        shadow="0",
    )
    root = etree.SubElement(model, "root")
    etree.SubElement(root, "mxCell", id="0")
    etree.SubElement(root, "mxCell", id="1", parent="0")

    id_map: dict[str, str] = {}
    for index, node in enumerate(layout.get("nodes", [])):
        cell_id = f"node{index}"
        id_map[str(node["id"])] = cell_id
        cell = etree.SubElement(
            root,
            "mxCell",
            id=cell_id,
            value=str(node.get("label", node["id"])),
            style="rounded=1;whiteSpace=wrap;html=1;",
            vertex="1",
            parent="1",
        )
        etree.SubElement(
            cell,
            "mxGeometry",
            x=str(_X),
            y=str(_Y0 + index * _Y_STEP),
            width=str(_NODE_W),
            height=str(_NODE_H),
            **{"as": "geometry"},
        )

    for index, edge in enumerate(layout.get("edges", [])):
        source = id_map.get(str(edge["from"]))
        target = id_map.get(str(edge["to"]))
        if source is None or target is None:
            continue
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"edge{index}",
            value=str(edge.get("label", "")),
            style="endArrow=block;html=1;",
            edge="1",
            parent="1",
            source=source,
            target=target,
        )
        etree.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

    return etree.tostring(
        mxfile, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")
