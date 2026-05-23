from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


def test_issue_pat_hashes_token_validates_scopes_and_redacts_secret():
    from team_cloud.auth.tokens import (
        InMemoryTokenRepository,
        TokenService,
        verify_token_hash,
    )

    repository = InMemoryTokenRepository()
    token_values = iter(["hpat_plain-secret", "hpat_expired-secret"])
    service = TokenService(
        repository=repository,
        token_factory=lambda prefix: next(token_values),
    )

    issued = service.issue_pat(
        org_id="org-1",
        owner_member_id="member-1",
        scopes=["chat:run", "memory:read"],
        expires_at=datetime(2026, 5, 23, tzinfo=UTC),
    )

    stored = repository.api_tokens[issued.token_id]
    token = issued.token.get_secret_value()
    assert token.startswith("hpat_")
    assert stored["owner_member_id"] == "member-1"
    assert stored["service_account_id"] is None
    assert stored["scopes"] == ("chat:run", "memory:read")
    assert stored["token_hash"] != token.encode("utf-8")
    assert verify_token_hash(token, stored["token_hash"])
    assert repository.audit_events[-1]["action"] == "api_token.created"
    assert repository.audit_events[-1]["metadata"]["token_type"] == "pat"

    serialized = repr(issued) + json.dumps(issued.to_safe_dict(), sort_keys=True)
    assert "plain-secret" not in serialized
    assert stored["token_hash"].decode("ascii") not in serialized

    with pytest.raises(ValueError, match="invalid token scope"):
        service.issue_pat(
            org_id="org-1",
            owner_member_id="member-1",
            scopes=["admin:delete-everything"],
        )


def test_authenticate_token_enforces_expiry_revocation_and_scope():
    from team_cloud.auth.tokens import (
        InMemoryTokenRepository,
        TokenAuthenticationError,
        TokenService,
    )

    repository = InMemoryTokenRepository()
    token_values = iter(["hpat_plain-secret", "hpat_expired-secret"])
    service = TokenService(
        repository=repository,
        token_factory=lambda prefix: next(token_values),
    )
    now = datetime(2026, 5, 22, tzinfo=UTC)
    issued = service.issue_pat(
        org_id="org-1",
        owner_member_id="member-1",
        scopes=["chat:run", "memory:read"],
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )

    principal = service.authenticate(
        issued.token.get_secret_value(),
        required_scopes=["memory:read"],
        now=now + timedelta(minutes=5),
    )

    assert principal.actor_type == "human"
    assert principal.org_id == "org-1"
    assert principal.member_id == "member-1"
    assert principal.scopes == ("chat:run", "memory:read")
    assert repository.api_tokens[issued.token_id]["last_used_at"] == now + timedelta(
        minutes=5
    )

    with pytest.raises(TokenAuthenticationError, match="insufficient_scope"):
        service.authenticate(
            issued.token.get_secret_value(),
            required_scopes=["admin:read"],
            now=now + timedelta(minutes=6),
        )

    service.revoke_token(
        token_id=issued.token_id,
        actor_member_id="member-1",
        now=now + timedelta(minutes=10),
    )

    with pytest.raises(TokenAuthenticationError, match="revoked"):
        service.authenticate(
            issued.token.get_secret_value(),
            required_scopes=["memory:read"],
            now=now + timedelta(minutes=11),
        )

    expired = service.issue_pat(
        org_id="org-1",
        owner_member_id="member-1",
        scopes=["chat:run"],
        expires_at=now - timedelta(seconds=1),
        created_at=now - timedelta(hours=1),
    )
    with pytest.raises(TokenAuthenticationError, match="expired"):
        service.authenticate(expired.token.get_secret_value(), now=now)


def test_service_account_token_binds_to_service_account_and_audits():
    from team_cloud.auth.tokens import InMemoryTokenRepository, TokenService

    repository = InMemoryTokenRepository()
    service = TokenService(
        repository=repository,
        token_factory=lambda prefix: f"{prefix}_service-secret",
    )

    service_account = service.create_service_account(
        org_id="org-1",
        owner_member_id="member-owner",
        name="ci-runner",
    )
    issued = service.issue_service_account_token(
        org_id="org-1",
        service_account_id=service_account["id"],
        scopes=["service_accounts:use", "chat:run"],
    )
    principal = service.authenticate(
        issued.token.get_secret_value(),
        required_scopes=["service_accounts:use"],
    )

    stored = repository.api_tokens[issued.token_id]
    assert issued.token.get_secret_value().startswith("hsa_")
    assert stored["owner_member_id"] is None
    assert stored["service_account_id"] == service_account["id"]
    assert principal.actor_type == "service_account"
    assert principal.service_account_id == service_account["id"]
    assert repository.audit_events[-2]["action"] == "service_account.created"
    assert repository.audit_events[-1]["action"] == "api_token.created"
    assert "service-secret" not in json.dumps(issued.to_safe_dict(), sort_keys=True)


def test_repository_rejects_token_without_exactly_one_subject():
    from team_cloud.auth.tokens import InMemoryTokenRepository, hash_token

    repository = InMemoryTokenRepository()

    with pytest.raises(ValueError, match="exactly one token subject"):
        repository.create_api_token(
            org_id="org-1",
            token_hash=hash_token("plain"),
            scopes=("chat:run",),
        )

    with pytest.raises(ValueError, match="exactly one token subject"):
        repository.create_api_token(
            org_id="org-1",
            owner_member_id="member-1",
            service_account_id="service-account-1",
            token_hash=hash_token("plain"),
            scopes=("chat:run",),
        )
