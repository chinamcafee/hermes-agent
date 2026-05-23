"""Lightweight observability primitives for Team Cloud."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from team_cloud.correlation import attach_correlation_fields


METRICS_CATALOG: tuple[dict[str, str], ...] = (
    {
        "name": "team_cloud_http_requests_total",
        "domain": "team_api",
        "type": "counter",
        "description": "HTTP requests handled by Team Cloud.",
    },
    {
        "name": "team_cloud_spicedb_check_latency_ms",
        "domain": "spicedb",
        "type": "histogram",
        "description": "SpiceDB permission check latency in milliseconds.",
    },
    {
        "name": "team_cloud_spicedb_denies_total",
        "domain": "spicedb",
        "type": "counter",
        "description": "Denied SpiceDB authorization decisions.",
    },
    {
        "name": "team_cloud_pgvector_query_latency_ms",
        "domain": "pgvector",
        "type": "histogram",
        "description": "pgvector memory query latency in milliseconds.",
    },
    {
        "name": "team_cloud_minio_operation_latency_ms",
        "domain": "minio",
        "type": "histogram",
        "description": "MinIO upload and download latency in milliseconds.",
    },
    {
        "name": "team_cloud_worker_lag_seconds",
        "domain": "worker",
        "type": "gauge",
        "description": "Queue lag for Team Cloud workers in seconds.",
    },
    {
        "name": "team_cloud_audit_events_total",
        "domain": "audit_security",
        "type": "counter",
        "description": "Audit and security events emitted by Team Cloud.",
    },
)


@dataclass
class InMemoryObservability:
    request_counts: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    events: list[dict[str, Any]] = field(default_factory=list)

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str | None,
        run_id: str | None = None,
        audit_event_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.request_counts[(method, path, status_code)] += 1
        self.events.append(
            attach_correlation_fields(
                {
                    "event": "http.request",
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 3),
                },
                request_id=request_id,
                run_id=run_id,
                audit_event_id=audit_event_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
            )
        )

    def render_prometheus(self) -> str:
        lines = [
            "# HELP team_cloud_http_requests_total HTTP requests handled by Team Cloud.",
            "# TYPE team_cloud_http_requests_total counter",
        ]
        for (method, path, status_code), value in sorted(self.request_counts.items()):
            labels = f'method="{method}",path="{path}",status="{status_code}"'
            lines.append(f"team_cloud_http_requests_total{{{labels}}} {value}")
        return "\n".join(lines) + "\n"
