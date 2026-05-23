"""Correlation helpers for request, run, audit, and trace events."""

from __future__ import annotations

from typing import Any


CORRELATION_FIELDS = (
    "request_id",
    "run_id",
    "audit_event_id",
    "trace_id",
    "correlation_id",
)


def build_correlation_context(
    *,
    request_id: Any = None,
    run_id: Any = None,
    audit_event_id: Any = None,
    trace_id: Any = None,
    correlation_id: Any = None,
) -> dict[str, str | None]:
    """Return normalized correlation fields with one stable correlation id."""

    normalized_request_id = _normalize(request_id)
    normalized_run_id = _normalize(run_id)
    normalized_audit_event_id = _normalize(audit_event_id)
    normalized_trace_id = _normalize(trace_id)
    normalized_correlation_id = (
        _normalize(correlation_id)
        or normalized_trace_id
        or normalized_run_id
        or normalized_request_id
        or normalized_audit_event_id
    )
    return {
        "request_id": normalized_request_id,
        "run_id": normalized_run_id,
        "audit_event_id": normalized_audit_event_id,
        "trace_id": normalized_trace_id,
        "correlation_id": normalized_correlation_id,
    }


def attach_correlation_fields(
    target: dict[str, Any],
    *,
    request_id: Any = None,
    run_id: Any = None,
    audit_event_id: Any = None,
    trace_id: Any = None,
    correlation_id: Any = None,
) -> dict[str, Any]:
    """Attach normalized correlation fields to target and return it."""

    target.update(
        build_correlation_context(
            request_id=request_id,
            run_id=run_id,
            audit_event_id=audit_event_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
    )
    return target


def _normalize(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


__all__ = [
    "CORRELATION_FIELDS",
    "attach_correlation_fields",
    "build_correlation_context",
]
