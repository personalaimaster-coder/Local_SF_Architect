"""Architecture scoring engine (plan Gap 8, Phase 6.5).

Emits an explainable per-pillar scorecard (Security / Reliability / Scalability /
Performance) over the dependency-graph + lint findings. Every score CITES the
findings that produced it -- never an invented number. Scores are deterministic
for the same input.

Also defines ``risk_score`` (plan task 2): a single 0-1 number derived from the
weighted pillar deductions, used to populate the audit log's ``risk_score`` column.
"""

from __future__ import annotations

from pathlib import Path

from sf_architect.lint import scan_path

PILLARS = ["Security", "Reliability", "Scalability", "Performance"]
START_SCORE = 100
DEDUCTION_PER_FINDING = 15


def _empty_card() -> dict[str, dict]:
    return {pillar: {"score": START_SCORE, "findings": []} for pillar in PILLARS}


def score_architecture(scope: str | Path, repo_root: str | Path | None = None) -> dict:
    """Score the architecture in ``scope`` (a file, directory, or repo root).

    Returns ``{scope, pillars: {Pillar: {score, findings}}, risk_score}``. Each
    pillar score is backed by cited findings; pillars with no infractions carry an
    explicit "no findings" citation so every number is defensible.
    """
    infractions = sorted(
        scan_path(scope), key=lambda i: (i.pillar, i.file, i.line, i.rule)
    )
    pillars = _empty_card()

    for infraction in infractions:
        pillar = infraction.pillar if infraction.pillar in pillars else "Reliability"
        card = pillars[pillar]
        card["score"] = max(0, card["score"] - DEDUCTION_PER_FINDING)
        card["findings"].append(
            {
                "rule": infraction.rule,
                "file": infraction.file,
                "line": infraction.line,
                "message": infraction.message,
            }
        )

    for pillar, card in pillars.items():
        if not card["findings"]:
            card["findings"].append(
                {
                    "rule": "no_findings",
                    "message": f"No {pillar} infractions detected in scope.",
                    "scope": str(scope),
                }
            )

    risk_score = compute_risk_score(pillars)
    return {"scope": str(scope), "pillars": pillars, "risk_score": risk_score}


def compute_risk_score(pillars: dict[str, dict]) -> float:
    """Derive a 0-1 risk score from per-pillar deductions (plan task 2).

    0.0 = no infractions anywhere; 1.0 = every pillar fully penalized. This is the
    value written to the audit log's ``risk_score`` column for scored calls.
    """
    total_deduction = sum(START_SCORE - card["score"] for card in pillars.values())
    max_possible = START_SCORE * len(pillars)
    return round(total_deduction / max_possible, 4) if max_possible else 0.0
