"""Mermaid diagram emitter (plan Phase 5 task 1).

Turns a layout description into Mermaid ``flowchart`` or ``sequenceDiagram``
syntax embedded in a markdown fenced block.

Layout shape::

    {
      "title": "Order Flow",
      "type": "flow" | "sequence",
      "nodes": [{"id": "a", "label": "Account"}],
      "edges": [{"from": "a", "to": "b", "label": "uses"}]
    }
"""

from __future__ import annotations

import re

_ID_RE = re.compile(r"[^0-9a-zA-Z_]")


def _safe_id(node_id: str) -> str:
    cleaned = _ID_RE.sub("_", str(node_id)).strip("_")
    return cleaned or "n"


def _flow(layout: dict) -> str:
    lines = ["flowchart TD"]
    for node in layout.get("nodes", []):
        nid = _safe_id(node["id"])
        label = str(node.get("label", node["id"])).replace('"', "'")
        lines.append(f'    {nid}["{label}"]')
    for edge in layout.get("edges", []):
        src = _safe_id(edge["from"])
        dst = _safe_id(edge["to"])
        label = edge.get("label")
        if label:
            safe = str(label).replace('"', "'")
            lines.append(f'    {src} -->|"{safe}"| {dst}')
        else:
            lines.append(f"    {src} --> {dst}")
    return "\n".join(lines)


def _sequence(layout: dict) -> str:
    lines = ["sequenceDiagram"]
    for node in layout.get("nodes", []):
        nid = _safe_id(node["id"])
        label = str(node.get("label", node["id"]))
        lines.append(f"    participant {nid} as {label}")
    for edge in layout.get("edges", []):
        src = _safe_id(edge["from"])
        dst = _safe_id(edge["to"])
        label = str(edge.get("label", "")).replace("\n", " ")
        lines.append(f"    {src}->>{dst}: {label}")
    return "\n".join(lines)


def to_mermaid(layout: dict) -> str:
    """Render a layout to Mermaid source (flow or sequence)."""
    if layout.get("type") == "sequence":
        return _sequence(layout)
    return _flow(layout)


def to_markdown(layout: dict) -> str:
    """Wrap Mermaid source in a titled markdown document."""
    title = layout.get("title", "Architecture Diagram")
    body = to_mermaid(layout)
    return f"# {title}\n\n```mermaid\n{body}\n```\n"
