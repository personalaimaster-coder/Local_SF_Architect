"""Prompt-injection guard (plan Gap 5, P0).

Screens content twice: scraped pages before ingestion, and retrieved chunks
before they reach the LLM. Blocked items are counted by the caller.

The default classifier is a fast, dependency-free heuristic so the core package
stays light and fully offline. The permissive ML model
``protectai/deberta-v3-base-prompt-injection-v2`` is an opt-in upgrade (downloaded
on first use) and can be supplied via the ``classifier`` hook.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

# Signals strongly associated with indirect prompt injection.
INJECTION_SIGNALS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?)",
    r"system\s+prompt",
    r"you\s+are\s+now\b",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"forget\s+(everything|all)\b",
    r"new\s+instructions?\s*:",
    r"do\s+anything\s+now",
    r"\bDAN\b",
    r"exfiltrate|leak\s+(the\s+)?(secret|key|token)",
]
_SIGNAL_RES = [re.compile(p, re.IGNORECASE) for p in INJECTION_SIGNALS]

BLOCK_THRESHOLD = 0.5


@dataclass
class GuardResult:
    """Outcome of screening one piece of content."""

    blocked: bool
    score: float
    reasons: list[str]


# A classifier maps text -> probability that it is an injection attempt.
Classifier = Callable[[str], float]


def _heuristic_classifier(text: str) -> float:
    """Score injection likelihood from matched signals (0.0 - 1.0)."""
    matches = [r.pattern for r in _SIGNAL_RES if r.search(text)]
    if not matches:
        return 0.0
    # Each distinct signal contributes; a single strong signal already blocks.
    return min(1.0, 0.5 + 0.25 * (len(matches) - 1) + 0.25)


def screen(text: str, classifier: Classifier | None = None) -> GuardResult:
    """Screen content for prompt injection."""
    classifier = classifier or _heuristic_classifier
    score = float(classifier(text))
    reasons = [r.pattern for r in _SIGNAL_RES if r.search(text)]
    return GuardResult(blocked=score >= BLOCK_THRESHOLD, score=round(score, 4), reasons=reasons)


def is_safe(text: str, classifier: Classifier | None = None) -> bool:
    """Convenience wrapper: True if content is not flagged as injection."""
    return not screen(text, classifier).blocked
