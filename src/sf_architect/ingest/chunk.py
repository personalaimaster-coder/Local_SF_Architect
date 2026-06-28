"""Markdown chunker (plan Phase 3 task 2).

Splits clean markdown into chunks at H2/H3 headings, carrying the page title
(H1) and the section heading as metadata for each chunk.
"""

from __future__ import annotations

import re

_H1 = re.compile(r"^#\s+(.*)$")
_H2_H3 = re.compile(r"^(#{2,3})\s+(.*)$")


def chunk_markdown(markdown: str) -> list[dict[str, str]]:
    """Split markdown into ``{title, heading, text}`` chunks by H2/H3."""
    title = ""
    heading = ""
    body: list[str] = []
    chunks: list[dict[str, str]] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if text and heading:
            chunks.append({"title": title, "heading": heading, "text": text})

    for line in markdown.splitlines():
        h1 = _H1.match(line)
        if h1:
            flush()
            title = h1.group(1).strip()
            heading = ""
            body = []
            continue
        section = _H2_H3.match(line)
        if section:
            flush()
            heading = section.group(2).strip()
            body = []
            continue
        body.append(line)

    flush()
    return chunks
