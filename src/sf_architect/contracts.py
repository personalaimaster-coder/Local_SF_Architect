"""Shared MCP response envelope and error types (plan Section 11.1).

Every MCP tool returns the same envelope so the IDE can render results and
confidence consistently. Raw exceptions must never cross the MCP boundary;
tools convert failures into :func:`fail` envelopes instead.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfidenceFactors(BaseModel):
    """The explainable signals that produce a confidence score (Gap 2)."""

    similarity: float = 0.0
    source_trust: int = 0
    version_match: bool = False
    corroboration: int = 0


class Confidence(BaseModel):
    """A confidence score plus the factor breakdown that produced it."""

    score: float = 0.0
    factors: ConfidenceFactors = Field(default_factory=ConfidenceFactors)


class ToolError(BaseModel):
    """Structured error returned on failure (never a raw exception)."""

    code: str
    message: str


class ResponseEnvelope(BaseModel):
    """Common response shape for every MCP tool (plan Section 11.1)."""

    ok: bool
    tool: str
    data: Any | None = None
    confidence: Confidence | None = None
    warnings: list[str] = Field(default_factory=list)
    error: ToolError | None = None


def ok(
    tool: str,
    data: Any,
    *,
    confidence: Confidence | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a success envelope as a JSON-serializable dict.

    ``confidence`` is only attached for retrieval/advice tools; deterministic
    tools (e.g. ``check_governor_limit``) omit it.
    """
    envelope = ResponseEnvelope(
        ok=True,
        tool=tool,
        data=data,
        confidence=confidence,
        warnings=warnings or [],
        error=None,
    )
    return envelope.model_dump(mode="json")


def fail(tool: str, code: str, message: str) -> dict[str, Any]:
    """Build a failure envelope as a JSON-serializable dict."""
    envelope = ResponseEnvelope(
        ok=False,
        tool=tool,
        data=None,
        confidence=None,
        warnings=[],
        error=ToolError(code=code, message=message),
    )
    return envelope.model_dump(mode="json")
