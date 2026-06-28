"""Local audit log (plan Sections 6, 12.3).

One SQLite row per tool call (tool, request, retrieved ids, confidence,
risk_score, duration). Everything stays on the machine; nothing is ever sent
anywhere. ``audited`` wraps a tool function so dispatch is logged automatically.
"""

from __future__ import annotations

import functools
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from sf_architect.bootstrap import AUDIT_DB_PATH

# Module-level so tests can point the log at a temp database.
DB_PATH: Path = AUDIT_DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts            TEXT NOT NULL,
  tool          TEXT NOT NULL,
  request_json  TEXT NOT NULL,
  retrieved_ids TEXT,
  confidence    REAL,
  risk_score    REAL,
  duration_ms   INTEGER
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(CREATE_TABLE_SQL)
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create the audit table if it does not exist."""
    conn = _connect(db_path)
    conn.commit()
    conn.close()


def log_call(
    tool: str,
    request: Any,
    *,
    retrieved_ids: list[str] | None = None,
    confidence: float | None = None,
    risk_score: float | None = None,
    duration_ms: int | None = None,
    db_path: Path | None = None,
) -> None:
    """Write one audit row."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO audit_log "
            "(ts, tool, request_json, retrieved_ids, confidence, risk_score, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                tool,
                json.dumps(request, default=str),
                json.dumps(retrieved_ids) if retrieved_ids is not None else None,
                confidence,
                risk_score,
                duration_ms,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _extract_from_envelope(result: Any) -> tuple[list[str] | None, float | None, float | None]:
    """Pull retrieved ids / confidence / risk_score out of a response envelope."""
    if not isinstance(result, dict):
        return None, None, None
    data = result.get("data") or {}
    retrieved_ids = None
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            retrieved_ids = [r.get("id") for r in results if isinstance(r, dict) and r.get("id")]
    confidence = None
    conf = result.get("confidence")
    if isinstance(conf, dict):
        confidence = conf.get("score")
    risk_score = data.get("risk_score") if isinstance(data, dict) else None
    return retrieved_ids, confidence, risk_score


def audited(fn):
    """Decorator: time a tool call and write an audit row for it."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = fn(*args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        retrieved_ids, confidence, risk_score = _extract_from_envelope(result)
        request = {"args": list(args), "kwargs": kwargs}
        try:
            log_call(
                fn.__name__,
                request,
                retrieved_ids=retrieved_ids,
                confidence=confidence,
                risk_score=risk_score,
                duration_ms=duration_ms,
            )
        except Exception:  # auditing must never break a tool call
            pass
        return result

    return wrapper
