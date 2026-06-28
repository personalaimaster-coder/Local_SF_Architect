"""Diagram rendering orchestrator (plan Phase 5 task 3).

Renders a layout with the chosen emitter, writes the file, and returns the
``{format, path, content}`` contract. Files are written under
``~/.sf-architect/diagrams/`` by default (never silently into the user's repo).
"""

from __future__ import annotations

import re
from pathlib import Path

from sf_architect.bootstrap import DIAGRAMS_DIR
from sf_architect.diagrams.drawio import to_drawio
from sf_architect.diagrams.mermaid import to_markdown

_SLUG_RE = re.compile(r"[^0-9a-zA-Z]+")

_EXT = {"mermaid": ".md", "drawio": ".drawio"}


def _slug(title: str) -> str:
    slug = _SLUG_RE.sub("-", title).strip("-").lower()
    return slug or "diagram"


def render_diagram(
    layout: dict, tool: str = "mermaid", output_path: str | Path | None = None
) -> dict[str, str]:
    """Render + write a diagram. Returns ``{format, path, content}``."""
    if tool not in _EXT:
        raise ValueError(f"unsupported tool: {tool!r}")

    content = to_markdown(layout) if tool == "mermaid" else to_drawio(layout)

    if output_path is not None:
        path = Path(output_path)
    else:
        title = layout.get("title", "diagram")
        DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
        path = DIAGRAMS_DIR / f"{_slug(title)}{_EXT[tool]}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"format": tool, "path": str(path), "content": content}
