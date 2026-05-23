"""SpiceDB authorization client abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Protocol


DEFAULT_CONSISTENCY = "minimize_latency"

PRODUCT_PERMISSION_MAP: dict[str, dict[str, str]] = {
    "backup.read": {"backup": "read"},
    "backup.restore": {"backup": "restore"},
    "chat.run": {"project": "run_agent", "session": "run"},
    "memory.personal.read": {"memory": "read_personal"},
    "memory.personal.write": {"memory": "write_personal"},
    "memory.team.read": {"memory": "read_team"},
    "memory.team.review": {"memory": "review"},
    "org.audit.read": {"organization": "read_audit"},
    "tool.safe.execute": {"tool": "safe_execute"},
    "tool.terminal.execute": {"tool": "terminal_execute"},
}


class SpiceDBTransport(Protocol):
    def check_permission(
        self,
        *,
        subject: str,
        resource: str,
        permission: str,
        consistency: str,
    ) -> bool: ...

    def lookup_resources(
        self,
        *,
        subject: str,
        resource_type: str,
        permission: str,
        consistency: str,
    ) -> list[str] | tuple[str, ...]: ...

    def write_relationships(
        self,
        *,
        relationships: list[str],
        operation: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, order=True)
class SubjectRef:
    type: Literal["user", "service_account"]
    id: str

    def as_spicedb(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass(frozen=True, order=True)
class ResourceRef:
    type: str
    id: str

    def as_spicedb(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass(frozen=True)
class Relationship:
    resource: ResourceRef
    relation: str
    subject: SubjectRef

    def as_spicedb(self) -> str:
        return (
            f"{self.resource.as_spicedb()}"
            f"#{self.relation}@{self.subject.as_spicedb()}"
        )


@dataclass(frozen=True)
class PermissionCheck:
    subject: SubjectRef
    resource: ResourceRef
    action: str | None = None
    permission: str | None = None
    consistency: str = DEFAULT_CONSISTENCY


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    subject: SubjectRef
    resource: ResourceRef
    permission: str


class SpiceDBClient:
    def __init__(self, *, transport: SpiceDBTransport, fail_closed: bool = True):
        self.transport = transport
        self.fail_closed = fail_closed

    def check(
        self,
        *,
        subject: SubjectRef,
        resource: ResourceRef,
        action: str | None = None,
        permission: str | None = None,
        consistency: str = DEFAULT_CONSISTENCY,
    ) -> PermissionDecision:
        resolved_permission = _resolve_permission(
            action=action,
            permission=permission,
            resource_type=resource.type,
        )
        try:
            allowed = self.transport.check_permission(
                subject=subject.as_spicedb(),
                resource=resource.as_spicedb(),
                permission=resolved_permission,
                consistency=consistency,
            )
        except Exception:
            if self.fail_closed:
                return PermissionDecision(
                    allowed=False,
                    reason="spicedb_error",
                    subject=subject,
                    resource=resource,
                    permission=resolved_permission,
                )
            raise
        return PermissionDecision(
            allowed=bool(allowed),
            reason="allowed" if allowed else "denied",
            subject=subject,
            resource=resource,
            permission=resolved_permission,
        )

    def batch_check(self, checks: Iterable[PermissionCheck]) -> tuple[PermissionDecision, ...]:
        return tuple(
            self.check(
                subject=check.subject,
                resource=check.resource,
                action=check.action,
                permission=check.permission,
                consistency=check.consistency,
            )
            for check in checks
        )

    def lookup_resources(
        self,
        *,
        subject: SubjectRef,
        resource_type: str,
        action: str | None = None,
        permission: str | None = None,
        consistency: str = DEFAULT_CONSISTENCY,
    ) -> tuple[ResourceRef, ...]:
        resolved_permission = _resolve_permission(
            action=action,
            permission=permission,
            resource_type=resource_type,
        )
        try:
            resources = self.transport.lookup_resources(
                subject=subject.as_spicedb(),
                resource_type=resource_type,
                permission=resolved_permission,
                consistency=consistency,
            )
        except Exception:
            if self.fail_closed:
                return ()
            raise
        return tuple(_parse_resource_ref(resource) for resource in resources)

    def write_relationships(
        self,
        relationships: Iterable[Relationship],
        *,
        operation: Literal["touch", "create", "delete"],
    ) -> dict[str, Any]:
        formatted = [relationship.as_spicedb() for relationship in relationships]
        return self.transport.write_relationships(
            relationships=formatted,
            operation=operation,
        )


def permission_for_action(action: str, resource_type: str) -> str:
    permission_by_resource = PRODUCT_PERMISSION_MAP.get(action)
    if not permission_by_resource or resource_type not in permission_by_resource:
        raise ValueError(
            f"unknown product permission mapping: {action} for {resource_type}"
        )
    return permission_by_resource[resource_type]


def _resolve_permission(
    *,
    action: str | None,
    permission: str | None,
    resource_type: str,
) -> str:
    if permission:
        return permission
    if action:
        return permission_for_action(action, resource_type)
    raise ValueError("check requires either action or permission")


def _parse_resource_ref(value: str) -> ResourceRef:
    resource_type, separator, resource_id = value.partition(":")
    if not separator or not resource_type or not resource_id:
        raise ValueError(f"invalid SpiceDB resource reference: {value}")
    return ResourceRef(resource_type, resource_id)
