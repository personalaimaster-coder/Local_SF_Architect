"""Governor limits engine backed by SQLite (plan Sections 11.2, 12.2).

Deterministic: given a scenario, it does exact math against curated limits.
No semantic search, no confidence score.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from sf_architect.bootstrap import LIMITS_DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS limits (
  api_version   TEXT NOT NULL,
  limit_key     TEXT NOT NULL,
  description   TEXT NOT NULL,
  value         INTEGER NOT NULL,
  unit          TEXT NOT NULL,
  last_verified TEXT NOT NULL,
  PRIMARY KEY (api_version, limit_key)
);
"""


class LimitNotFoundError(Exception):
    """Raised when a (api_version, limit_key) pair is not in the limits DB."""


def _normalize_version(api_version: str) -> list[str]:
    """Return candidate spellings of an API version (handles the ``v`` prefix)."""
    raw = api_version.strip()
    candidates = [raw]
    if raw.startswith("v"):
        candidates.append(raw[1:])
    else:
        candidates.append(f"v{raw}")
    # Common shorthand: "62" -> "62.0" / "v62.0".
    if "." not in raw.lstrip("v"):
        base = raw.lstrip("v")
        candidates += [f"{base}.0", f"v{base}.0"]
    seen: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    return seen


def compile_seed(yaml_path: str | Path, db_path: str | Path | None = None) -> Path:
    """Compile ``limits_seed.yaml`` into the SQLite ``limits.db``.

    Returns the path to the compiled database. Rebuilds the table from scratch so
    the seed file is the single source of truth.
    """
    yaml_path = Path(yaml_path)
    db_path = Path(db_path) if db_path is not None else LIMITS_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    api_versions = data.get("api_versions", {})

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS limits")
        conn.execute(CREATE_TABLE_SQL)
        rows: list[tuple] = []
        for api_version, payload in api_versions.items():
            last_verified = str(payload.get("last_verified", ""))
            for limit_key, spec in (payload.get("limits") or {}).items():
                rows.append(
                    (
                        api_version,
                        limit_key,
                        str(spec.get("description", "")),
                        int(spec["value"]),
                        str(spec.get("unit", "")),
                        last_verified,
                    )
                )
        conn.executemany(
            "INSERT INTO limits "
            "(api_version, limit_key, description, value, unit, last_verified) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def check_governor_limit(scenario: dict, db_path: str | Path | None = None) -> dict:
    """Check a projected value against a curated governor limit.

    ``scenario`` = ``{"limit_key": str, "projected_value": number, "api_version": str}``.
    Returns ``{limit, unit, projected, headroom, breaches, last_verified}``.
    Raises :class:`LimitNotFoundError` if the limit is unknown for the version.
    """
    db_path = Path(db_path) if db_path is not None else LIMITS_DB_PATH
    limit_key = scenario["limit_key"]
    projected = scenario["projected_value"]
    api_version = scenario["api_version"]

    if not db_path.exists():
        raise LimitNotFoundError(
            f"limits database not found at {db_path}; run 'sf-architect seed' first"
        )

    conn = sqlite3.connect(db_path)
    try:
        row = None
        for candidate in _normalize_version(api_version):
            row = conn.execute(
                "SELECT value, unit, last_verified FROM limits "
                "WHERE api_version = ? AND limit_key = ?",
                (candidate, limit_key),
            ).fetchone()
            if row is not None:
                break
    finally:
        conn.close()

    if row is None:
        raise LimitNotFoundError(
            f"no limit '{limit_key}' for api_version '{api_version}'"
        )

    value, unit, last_verified = row
    headroom = value - projected
    return {
        "limit": value,
        "unit": unit,
        "projected": projected,
        "headroom": headroom,
        "breaches": projected > value,
        "last_verified": last_verified,
    }
