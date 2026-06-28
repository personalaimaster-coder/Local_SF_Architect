"""Audit log: one row written per tool call."""

import sqlite3

from sf_architect.obs import audit


def _count_rows(db_path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    finally:
        conn.close()


def test_log_call_writes_row(tmp_path) -> None:
    db = tmp_path / "audit.db"
    audit.init_db(db)
    audit.log_call(
        "query_architect_db",
        {"query": "x"},
        retrieved_ids=["a", "b"],
        confidence=0.8,
        risk_score=None,
        duration_ms=5,
        db_path=db,
    )
    assert _count_rows(db) == 1


def test_audited_decorator_logs_envelope(tmp_path, monkeypatch) -> None:
    db = tmp_path / "audit.db"
    monkeypatch.setattr(audit, "DB_PATH", db)

    @audit.audited
    def fake_tool(query: str):
        return {
            "ok": True,
            "tool": "fake_tool",
            "data": {"results": [{"id": "p1"}, {"id": "p2"}]},
            "confidence": {"score": 0.91},
        }

    fake_tool("hello")
    assert _count_rows(db) == 1

    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT tool, retrieved_ids, confidence FROM audit_log"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "fake_tool"
    assert "p1" in row[1]
    assert row[2] == 0.91
