"""Content sanitization at ingestion (plan Gap 5).

Strips/escapes content that should never be treated as instructions: script
blocks, HTML tags, hidden/zero-width characters, and instruction-like phrases
("ignore previous instructions", "system prompt", ...). Returns the cleaned text
plus a list of findings so the pipeline can record what was neutralized.
"""

from __future__ import annotations

import re

# Zero-width and bidi/control characters used to hide injected instructions.
HIDDEN_CHARS = (
    "\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff\u2060"
)
_HIDDEN_RE = re.compile(f"[{HIDDEN_CHARS}]")
_SCRIPT_RE = re.compile(r"<\s*script\b.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<\s*style\b.*?<\s*/\s*style\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

INSTRUCTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?)",
    r"system\s+prompt",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+(an?\s+)?",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"forget\s+(everything|all)\b",
    r"new\s+instructions?\s*:",
]
_INSTRUCTION_RES = [re.compile(p, re.IGNORECASE) for p in INSTRUCTION_PATTERNS]

REDACTION = "[REDACTED-INSTRUCTION]"


def sanitize_text(text: str) -> tuple[str, list[str]]:
    """Return ``(clean_text, findings)`` for a raw content string."""
    findings: list[str] = []

    if _HIDDEN_RE.search(text):
        findings.append("hidden/zero-width characters removed")
        text = _HIDDEN_RE.sub("", text)

    if _SCRIPT_RE.search(text):
        findings.append("script block removed")
        text = _SCRIPT_RE.sub(" ", text)
    if _STYLE_RE.search(text):
        findings.append("style block removed")
        text = _STYLE_RE.sub(" ", text)

    if _TAG_RE.search(text):
        findings.append("html tags stripped")
        text = _TAG_RE.sub(" ", text)

    for regex in _INSTRUCTION_RES:
        if regex.search(text):
            findings.append(f"instruction-like phrase neutralized: {regex.pattern}")
            text = regex.sub(REDACTION, text)

    text = re.sub(r"[ \t]+", " ", text).strip()
    return text, findings
