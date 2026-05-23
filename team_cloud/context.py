"""Request context primitives for Team Cloud."""

from __future__ import annotations

from typing import Literal, Mapping
from uuid import uuid4

from pydantic import BaseModel, Field

ActorType = Literal["user", "service_account", "system"]


class RequestContext(BaseModel):
    request_id: str = Field(min_length=1)
    trace_id: str | None = None
    org_id: str | None = None
    member_id: str | None = None
    actor_type: ActorType = "user"

    @classmethod
    def from_headers(cls, headers: Mapping[str, str]) -> "RequestContext":
        normalized = {key.lower(): value for key, value in headers.items()}
        return cls(
            request_id=normalized.get("x-request-id") or f"req-{uuid4().hex}",
            trace_id=normalized.get("x-trace-id"),
            org_id=normalized.get("x-hermes-org-id"),
            member_id=normalized.get("x-hermes-member-id"),
            actor_type=normalized.get("x-hermes-actor-type", "user"),
        )
