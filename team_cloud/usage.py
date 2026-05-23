"""Organization usage and quota primitives for Team Cloud."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


USAGE_METRICS = (
    "run_count",
    "message_count",
    "token_count",
    "tool_call_count",
    "backup_size_bytes",
)
QUOTA_METRICS = (
    "run_count",
    "token_count",
    "tool_call_count",
    "backup_size_bytes",
)


class UsageQuotaService:
    """Summarize org usage and evaluate in-memory quota policies."""

    def __init__(
        self,
        *,
        cloud_session_repository: Any | None = None,
        chat_run_service: Any | None = None,
        object_manifest_service: Any | None = None,
        audit_log: Any | None = None,
    ) -> None:
        self.cloud_session_repository = cloud_session_repository
        self.chat_run_service = chat_run_service
        self.object_manifest_service = object_manifest_service
        self.audit_log = audit_log
        self._quotas: dict[str, dict[str, int | None]] = {}

    def get_org_quotas(self, org_id: str) -> dict[str, int | None]:
        org_id = _required("org_id", org_id)
        quotas = {metric: None for metric in QUOTA_METRICS}
        quotas.update(self._quotas.get(org_id, {}))
        return quotas

    def set_org_quotas(
        self,
        org_id: str,
        *,
        run_count: int | None = None,
        token_count: int | None = None,
        tool_call_count: int | None = None,
        backup_size_bytes: int | None = None,
        actor_member_id: str | None = None,
    ) -> dict[str, int | None]:
        org_id = _required("org_id", org_id)
        current = self.get_org_quotas(org_id)
        updates = {
            "run_count": run_count,
            "token_count": token_count,
            "tool_call_count": tool_call_count,
            "backup_size_bytes": backup_size_bytes,
        }
        for metric, value in updates.items():
            if value is not None:
                current[metric] = _non_negative_int(metric, value)
        self._quotas[org_id] = current
        self._audit_quota_update(org_id=org_id, quotas=current, actor_member_id=actor_member_id)
        return deepcopy(current)

    def org_summary(self, org_id: str) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        usage = self._collect_usage(org_id)
        quotas = self.get_org_quotas(org_id)
        violations = _quota_violations(usage=usage, quotas=quotas)
        return {
            "org_id": org_id,
            "usage": usage,
            "quotas": quotas,
            "quota_status": "over_quota" if violations else "within_quota",
            "violations": violations,
        }

    def check_next_run(self, org_id: str) -> dict[str, Any]:
        org_id = _required("org_id", org_id)
        usage = self._collect_usage(org_id)
        quotas = self.get_org_quotas(org_id)
        run_limit = quotas.get("run_count")
        next_count = usage["run_count"] + 1
        violations = []
        if run_limit is not None and next_count > run_limit:
            violations.append(
                {
                    "code": "run_count_quota_exceeded",
                    "metric": "run_count",
                    "limit": run_limit,
                    "actual": next_count,
                }
            )
        return {"allowed": not violations, "violations": violations}

    def _collect_usage(self, org_id: str) -> dict[str, int]:
        sessions = _repository_sessions(self.cloud_session_repository)
        org_sessions = [
            session for session in sessions if str(session.get("org_id") or "") == org_id
        ]
        usage = {
            "run_count": _run_count(self.chat_run_service, org_id, org_sessions),
            "message_count": sum(len(session.get("messages", [])) for session in org_sessions),
            "token_count": sum(
                _int_or_zero(message.get("token_count"))
                for session in org_sessions
                for message in session.get("messages", [])
            ),
            "tool_call_count": sum(
                len(session.get("tool_calls", [])) for session in org_sessions
            ),
            "backup_size_bytes": _backup_size_bytes(self.object_manifest_service, org_id),
        }
        return usage

    def _audit_quota_update(
        self,
        *,
        org_id: str,
        quotas: dict[str, int | None],
        actor_member_id: str | None,
    ) -> None:
        if self.audit_log is None:
            return
        self.audit_log.record(
            action="usage.quota.updated",
            org_id=org_id,
            actor_member_id=actor_member_id,
            actor_type="human" if actor_member_id else "system",
            resource_type="organization",
            resource_id=org_id,
            decision="recorded",
            metadata={"quotas": deepcopy(quotas)},
        )


def _repository_sessions(repository: Any | None) -> list[dict[str, Any]]:
    if repository is None:
        return []
    sessions = getattr(repository, "_sessions", {})
    if not isinstance(sessions, dict):
        return []
    return list(sessions.values())


def _run_count(
    chat_run_service: Any | None,
    org_id: str,
    org_sessions: list[dict[str, Any]],
) -> int:
    runs = getattr(chat_run_service, "_runs", None)
    if isinstance(runs, dict):
        return sum(
            1 for run in runs.values() if str(run.get("org_id") or "") == org_id
        )
    run_ids = {
        str(message.get("run_id"))
        for session in org_sessions
        for message in session.get("messages", [])
        if message.get("run_id")
    }
    run_ids.update(
        str(tool_call.get("run_id"))
        for session in org_sessions
        for tool_call in session.get("tool_calls", [])
        if tool_call.get("run_id")
    )
    return len(run_ids)


def _backup_size_bytes(object_manifest_service: Any | None, org_id: str) -> int:
    manifests = getattr(object_manifest_service, "manifests", None)
    if not isinstance(manifests, dict):
        return 0
    return sum(
        _int_or_zero(manifest.get("size_bytes"))
        for manifest in manifests.values()
        if manifest.get("org_id") == org_id
        and manifest.get("object_type") == "personal_backup"
        and manifest.get("status") == "active"
    )


def _quota_violations(
    *,
    usage: dict[str, int],
    quotas: dict[str, int | None],
) -> list[dict[str, int | str]]:
    violations = []
    for metric, limit in quotas.items():
        if limit is None:
            continue
        actual = usage.get(metric, 0)
        if actual > limit:
            violations.append(
                {
                    "code": f"{metric}_quota_exceeded",
                    "metric": metric,
                    "limit": limit,
                    "actual": actual,
                }
            )
    return violations


def _int_or_zero(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 0
    return max(normalized, 0)


def _non_negative_int(field_name: str, value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name}_quota_invalid") from exc
    if normalized < 0:
        raise ValueError(f"{field_name}_quota_invalid")
    return normalized


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def build_cost_quota_tuning() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-cost-quotas-v0",
        "default_quotas": {
            "run_count": 2000,
            "token_count": 2_000_000,
            "tool_call_count": 10_000,
            "backup_size_bytes": 10 * 1024 * 1024 * 1024,
        },
        "alert_thresholds": {
            "warning_ratio": 0.8,
            "critical_ratio": 0.95,
        },
        "dashboard_signals": [
            "run_count",
            "token_count",
            "tool_call_count",
            "backup_size_bytes",
            "quota_status",
        ],
        "limit_alerts": {
            "quota_exceeded": ["email", "in_app"],
            "warning_threshold_crossed": ["in_app"],
            "critical_threshold_crossed": ["email", "in_app"],
        },
    }


__all__ = [
    "QUOTA_METRICS",
    "USAGE_METRICS",
    "UsageQuotaService",
    "build_cost_quota_tuning",
]
