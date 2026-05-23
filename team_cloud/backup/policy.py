"""In-memory personal memory backup policy service."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any, Callable


VALID_CADENCES = {"daily", "weekly", "monthly"}
VALID_ENCRYPTION_MODES = {"org_managed", "user_passphrase"}
VALID_NOTIFICATION_CHANNELS = {"email", "in_app", "webhook"}


class BackupPolicyService:
    """Stores member backup preferences and exposes scheduler due lookups."""

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._counter = 0
        self._policies: dict[tuple[str, str], dict[str, Any]] = {}

    def get_policy(self, *, org_id: str, member_id: str) -> dict[str, Any]:
        key = (_required("org_id", org_id), _required("member_id", member_id))
        policy = self._policies.get(key)
        if policy is None:
            return _default_policy(org_id=key[0], member_id=key[1])
        return deepcopy(policy)

    def upsert_policy(
        self,
        *,
        org_id: str,
        member_id: str,
        cadence: str | None = None,
        enabled: bool | None = None,
        retention_count: int | None = None,
        include_archived: bool | None = None,
        include_deleted: bool | None = None,
        include_embeddings: bool | None = None,
        encryption_mode: str | None = None,
        notification_channels: list[str] | tuple[str, ...] | None = None,
        next_run_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        key = (_required("org_id", org_id), _required("member_id", member_id))
        existing = self._policies.get(key)
        if existing is None:
            self._counter += 1
            now = _timestamp(self._now())
            policy = _default_policy(org_id=key[0], member_id=key[1])
            policy.update(
                {
                    "id": f"backup-policy-{self._counter}",
                    "created_at": now,
                    "updated_at": now,
                }
            )
        else:
            policy = deepcopy(existing)
            policy["updated_at"] = _timestamp(self._now())

        if cadence is not None:
            policy["cadence"] = _validate_cadence(cadence)
        if enabled is not None:
            policy["enabled"] = bool(enabled)
        if retention_count is not None:
            policy["retention_count"] = _validate_retention_count(retention_count)
        if include_archived is not None:
            policy["include_archived"] = bool(include_archived)
        if include_deleted is not None:
            policy["include_deleted"] = bool(include_deleted)
        if include_embeddings is not None:
            policy["include_embeddings"] = bool(include_embeddings)
        if encryption_mode is not None:
            policy["encryption_mode"] = _validate_encryption_mode(encryption_mode)
        if notification_channels is not None:
            policy["notification_channels"] = _validate_notification_channels(
                notification_channels
            )
        if next_run_at is not None:
            policy["next_run_at"] = _timestamp(_coerce_datetime(next_run_at))
        elif policy["enabled"] and policy["next_run_at"] is None:
            policy["next_run_at"] = _timestamp(
                _next_run_from(self._now(), cadence=policy["cadence"])
            )
        if not policy["enabled"]:
            policy["next_run_at"] = None

        self._policies[key] = deepcopy(policy)
        return deepcopy(policy)

    def due_policies(self, *, at: datetime | str | None = None) -> list[dict[str, Any]]:
        cutoff = _coerce_datetime(at) if at is not None else self._now()
        due = []
        for policy in self._policies.values():
            if not policy["enabled"] or not policy["next_run_at"]:
                continue
            if _coerce_datetime(policy["next_run_at"]) <= cutoff:
                due.append(deepcopy(policy))
        return sorted(due, key=lambda policy: (policy["next_run_at"], policy["id"]))


def _default_policy(*, org_id: str, member_id: str) -> dict[str, Any]:
    return {
        "id": None,
        "org_id": org_id,
        "member_id": member_id,
        "cadence": "weekly",
        "next_run_at": None,
        "retention_count": 8,
        "enabled": False,
        "include_archived": False,
        "include_deleted": False,
        "include_embeddings": False,
        "encryption_mode": "org_managed",
        "notification_channels": ["in_app"],
        "created_at": None,
        "updated_at": None,
    }


def _required(field_name: str, value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name}_required")
    return normalized


def _validate_cadence(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_CADENCES:
        raise ValueError("invalid_cadence")
    return normalized


def _validate_retention_count(value: int) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retention_count") from exc
    if count <= 0:
        raise ValueError("invalid_retention_count")
    return count


def _validate_encryption_mode(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in VALID_ENCRYPTION_MODES:
        raise ValueError("invalid_encryption_mode")
    return normalized


def _validate_notification_channels(values: list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise ValueError("invalid_notification_channels")
    normalized: list[str] = []
    for value in values:
        channel = str(value or "").strip()
        if channel not in VALID_NOTIFICATION_CHANNELS:
            raise ValueError("invalid_notification_channels")
        if channel not in normalized:
            normalized.append(channel)
    return normalized


def _next_run_from(now: datetime, *, cadence: str) -> datetime:
    if cadence == "daily":
        return now + timedelta(days=1)
    if cadence == "weekly":
        return now + timedelta(days=7)
    if cadence == "monthly":
        return now + timedelta(days=30)
    raise ValueError("invalid_cadence")


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _coerce_datetime(value).isoformat().replace("+00:00", "Z")
