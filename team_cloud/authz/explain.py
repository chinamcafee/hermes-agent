"""Minimal permission explain helpers."""

from __future__ import annotations

from typing import Any, Literal, cast

from .middleware import permission_cache_key
from .spicedb import (
    DEFAULT_CONSISTENCY,
    ResourceRef,
    SubjectRef,
    permission_for_action,
)


def explain_permission(
    *,
    authz_client: Any | None,
    subject_type: str,
    subject_id: str,
    resource_type: str,
    resource_id: str,
    action: str | None = None,
    permission: str | None = None,
    consistency: str = DEFAULT_CONSISTENCY,
    relationship_outbox_repository: Any | None = None,
) -> dict[str, Any]:
    subject = SubjectRef(_subject_type(subject_type), subject_id)
    resource = ResourceRef(resource_type, resource_id)
    resolved_permission = permission or _permission_from_action(
        action=action,
        resource_type=resource.type,
    )
    cache_key = permission_cache_key(subject, resource, resolved_permission)

    if authz_client is None:
        return _payload(
            allowed=False,
            reason="authz_client_not_configured",
            subject=subject,
            resource=resource,
            permission=resolved_permission,
            cache_key=cache_key,
            relationship_outbox_repository=relationship_outbox_repository,
        )

    try:
        decision = authz_client.check(
            subject=subject,
            resource=resource,
            action=action,
            permission=permission,
            consistency=consistency,
        )
    except Exception:
        return _payload(
            allowed=False,
            reason="authorization_unavailable",
            subject=subject,
            resource=resource,
            permission=resolved_permission,
            cache_key=cache_key,
            relationship_outbox_repository=relationship_outbox_repository,
        )

    resolved_cache_key = permission_cache_key(
        decision.subject,
        decision.resource,
        decision.permission,
    )
    return _payload(
        allowed=decision.allowed,
        reason=decision.reason,
        subject=decision.subject,
        resource=decision.resource,
        permission=decision.permission,
        cache_key=resolved_cache_key,
        relationship_outbox_repository=relationship_outbox_repository,
    )


def _payload(
    *,
    allowed: bool,
    reason: str,
    subject: SubjectRef,
    resource: ResourceRef,
    permission: str,
    cache_key: str,
    relationship_outbox_repository: Any | None = None,
) -> dict[str, Any]:
    relationship_paths = _relationship_paths(
        relationship_outbox_repository=relationship_outbox_repository,
        subject=subject,
        resource=resource,
    )
    recent_changes = _recent_relationship_changes(
        relationship_outbox_repository=relationship_outbox_repository,
        resource=resource,
    )
    return {
        "allowed": allowed,
        "reason": reason,
        "subject": subject.as_spicedb(),
        "resource": resource.as_spicedb(),
        "permission": permission,
        "cache_key": cache_key,
        "deny_reasons": _deny_reasons(
            allowed=allowed,
            reason=reason,
            relationship_paths=relationship_paths,
            recent_changes=recent_changes,
            subject=subject,
            resource=resource,
        ),
        "relationship_paths": relationship_paths,
        "recent_relationship_changes": recent_changes,
    }


def _relationship_paths(
    *,
    relationship_outbox_repository: Any | None,
    subject: SubjectRef,
    resource: ResourceRef,
) -> list[dict[str, Any]]:
    paths = []
    for item in _relationship_items(relationship_outbox_repository):
        if item.status != "applied":
            continue
        for relationship in item.relationships:
            if not _matches_relationship(
                relationship=relationship,
                subject=subject,
                resource=resource,
            ):
                continue
            paths.append(_relationship_payload(item=item, relationship=relationship))
    return paths


def _recent_relationship_changes(
    *,
    relationship_outbox_repository: Any | None,
    resource: ResourceRef,
    limit: int = 10,
) -> list[dict[str, Any]]:
    changes = []
    for item in _relationship_items(relationship_outbox_repository):
        for relationship in item.relationships:
            if not relationship.startswith(f"{resource.as_spicedb()}#"):
                continue
            changes.append(_relationship_payload(item=item, relationship=relationship))
    changes.sort(
        key=lambda change: (change.get("created_at") or "", change["relationship"]),
        reverse=True,
    )
    return changes[:limit]


def _deny_reasons(
    *,
    allowed: bool,
    reason: str,
    relationship_paths: list[dict[str, Any]],
    recent_changes: list[dict[str, Any]],
    subject: SubjectRef,
    resource: ResourceRef,
) -> list[str]:
    if allowed:
        return []
    reasons: list[str] = []
    if reason == "denied":
        reasons.append("spicedb_denied")
    elif reason:
        reasons.append(reason)
    subject_resource_changes = [
        change
        for change in recent_changes
        if _matches_relationship(
            relationship=change["relationship"],
            subject=subject,
            resource=resource,
        )
    ]
    if any(change["status"] in {"pending", "processing", "failed"} for change in subject_resource_changes):
        reasons.append("relationship_outbox_pending")
    if any(change["status"] == "dead_letter" for change in subject_resource_changes):
        reasons.append("relationship_outbox_dead_letter")
    if not relationship_paths:
        reasons.append("no_applied_relationship_path")
    return _dedupe(reasons)


def _relationship_items(relationship_outbox_repository: Any | None) -> list[Any]:
    items = getattr(relationship_outbox_repository, "items", None)
    if not isinstance(items, dict):
        return []
    return list(items.values())


def _matches_relationship(
    *,
    relationship: str,
    subject: SubjectRef,
    resource: ResourceRef,
) -> bool:
    return relationship.startswith(f"{resource.as_spicedb()}#") and relationship.endswith(
        f"@{subject.as_spicedb()}"
    )


def _relationship_payload(*, item: Any, relationship: str) -> dict[str, Any]:
    return {
        "relationship": relationship,
        "operation": item.operation,
        "status": item.status,
        "aggregate_type": item.aggregate_type,
        "aggregate_id": item.aggregate_id,
        "source": "relationship_outbox",
        **_optional_timestamp("created_at", item.created_at),
        **_optional_timestamp("processed_at", item.processed_at),
        **({"attempts": item.attempts} if getattr(item, "attempts", 0) else {}),
        **({"last_error": item.last_error} if getattr(item, "last_error", None) else {}),
    }


def _optional_timestamp(field_name: str, value: Any | None) -> dict[str, str]:
    if value is None:
        return {}
    return {field_name: value.isoformat() if hasattr(value, "isoformat") else str(value)}


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _subject_type(value: str) -> Literal["user", "service_account"]:
    if value not in {"user", "service_account"}:
        raise ValueError("subject_type must be user or service_account")
    return cast(Literal["user", "service_account"], value)


def _permission_from_action(*, action: str | None, resource_type: str) -> str:
    if not action:
        raise ValueError("permission or action is required")
    return permission_for_action(action, resource_type)
