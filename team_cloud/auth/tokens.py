"""PAT and service account token primitives."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import secrets
from typing import Callable, Iterable, Literal
from uuid import uuid4

from pydantic import SecretStr


HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 200_000
VALID_TOKEN_SCOPES = frozenset(
    {
        "admin:read",
        "admin:write",
        "chat:run",
        "memory:read",
        "memory:write",
        "service_accounts:manage",
        "service_accounts:use",
        "tools:use",
    }
)


class TokenAuthenticationError(RuntimeError):
    """Raised when a PAT or service account token cannot be authenticated."""


@dataclass(frozen=True, repr=False)
class IssuedToken:
    token_id: str
    token: SecretStr
    token_type: Literal["pat", "service_account"]
    org_id: str
    scopes: tuple[str, ...]
    expires_at: datetime | None

    def __repr__(self) -> str:
        return (
            "IssuedToken("
            f"token_id={self.token_id!r}, "
            "token='********', "
            f"token_type={self.token_type!r}, "
            f"org_id={self.org_id!r}, "
            f"scopes={self.scopes!r}, "
            f"expires_at={self.expires_at!r})"
        )

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "token_id": self.token_id,
            "token": "********",
            "token_type": self.token_type,
            "org_id": self.org_id,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass(frozen=True)
class TokenPrincipal:
    actor_type: Literal["human", "service_account"]
    org_id: str
    scopes: tuple[str, ...]
    token_id: str
    member_id: str | None = None
    service_account_id: str | None = None


def hash_token(token: str, *, salt: bytes | None = None) -> bytes:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    return "$".join(
        [
            HASH_ALGORITHM,
            str(HASH_ITERATIONS),
            _b64(salt),
            _b64(digest),
        ]
    ).encode("ascii")


def verify_token_hash(token: str, token_hash: bytes) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = token_hash.decode("ascii").split(
            "$",
            3,
        )
        if algorithm != HASH_ALGORITHM:
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            token.encode("utf-8"),
            _unb64(salt_b64),
            int(iterations),
        )
        return hmac.compare_digest(expected, _unb64(digest_b64))
    except (ValueError, UnicodeDecodeError):
        return False


class InMemoryTokenRepository:
    def __init__(self) -> None:
        self.service_accounts: dict[str, dict[str, object]] = {}
        self.api_tokens: dict[str, dict[str, object]] = {}
        self.audit_events: list[dict[str, object]] = []

    def create_service_account(
        self,
        *,
        org_id: str,
        owner_member_id: str,
        name: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        service_account_id = f"sa_{uuid4().hex}"
        service_account = {
            "id": service_account_id,
            "org_id": org_id,
            "owner_member_id": owner_member_id,
            "name": name,
            "status": "active",
            "created_at": now or _utcnow(),
        }
        self.service_accounts[service_account_id] = service_account
        return service_account

    def create_api_token(
        self,
        *,
        org_id: str,
        token_hash: bytes,
        scopes: tuple[str, ...],
        owner_member_id: str | None = None,
        service_account_id: str | None = None,
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, object]:
        if (owner_member_id is None) == (service_account_id is None):
            raise ValueError("api token requires exactly one token subject")
        token_id = f"tok_{uuid4().hex}"
        token = {
            "id": token_id,
            "org_id": org_id,
            "owner_member_id": owner_member_id,
            "service_account_id": service_account_id,
            "token_hash": token_hash,
            "scopes": scopes,
            "expires_at": expires_at,
            "last_used_at": None,
            "revoked_at": None,
            "created_at": created_at or _utcnow(),
        }
        self.api_tokens[token_id] = token
        return token

    def record_audit(
        self,
        *,
        action: str,
        org_id: str,
        actor_member_id: str | None = None,
        actor_type: str = "human",
        resource_type: str = "api_token",
        resource_id: str | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        event = {
            "action": action,
            "org_id": org_id,
            "actor_member_id": actor_member_id,
            "actor_type": actor_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "created_at": now or _utcnow(),
        }
        self.audit_events.append(event)
        return event

    def mark_token_used(self, token_id: str, *, now: datetime) -> None:
        self.api_tokens[token_id]["last_used_at"] = now

    def revoke_token(self, token_id: str, *, now: datetime) -> dict[str, object]:
        token = self.api_tokens[token_id]
        token["revoked_at"] = token["revoked_at"] or now
        return token


class TokenService:
    def __init__(
        self,
        *,
        repository: InMemoryTokenRepository | None = None,
        token_factory: Callable[[str], str] | None = None,
    ) -> None:
        self.repository = repository or InMemoryTokenRepository()
        self.token_factory = token_factory or _generate_token

    def create_service_account(
        self,
        *,
        org_id: str,
        owner_member_id: str,
        name: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        service_account = self.repository.create_service_account(
            org_id=org_id,
            owner_member_id=owner_member_id,
            name=name,
            now=now,
        )
        self.repository.record_audit(
            action="service_account.created",
            org_id=org_id,
            actor_member_id=owner_member_id,
            resource_type="service_account",
            resource_id=str(service_account["id"]),
            metadata={"name": name},
            now=now,
        )
        return service_account

    def issue_pat(
        self,
        *,
        org_id: str,
        owner_member_id: str,
        scopes: Iterable[str],
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> IssuedToken:
        return self._issue_token(
            token_type="pat",
            org_id=org_id,
            owner_member_id=owner_member_id,
            service_account_id=None,
            scopes=scopes,
            expires_at=expires_at,
            created_at=created_at,
        )

    def issue_service_account_token(
        self,
        *,
        org_id: str,
        service_account_id: str,
        scopes: Iterable[str],
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> IssuedToken:
        if service_account_id not in self.repository.service_accounts:
            raise ValueError(f"unknown service account: {service_account_id}")
        return self._issue_token(
            token_type="service_account",
            org_id=org_id,
            owner_member_id=None,
            service_account_id=service_account_id,
            scopes=scopes,
            expires_at=expires_at,
            created_at=created_at,
        )

    def authenticate(
        self,
        token: str,
        *,
        required_scopes: Iterable[str] = (),
        now: datetime | None = None,
    ) -> TokenPrincipal:
        now = now or _utcnow()
        required_scope_set = set(_normalize_required_scopes(required_scopes))
        for token_record in self.repository.api_tokens.values():
            if not verify_token_hash(token, token_record["token_hash"]):
                continue
            return self._authenticate_record(
                token_record,
                required_scope_set=required_scope_set,
                now=now,
            )
        raise TokenAuthenticationError("invalid_token")

    def revoke_token(
        self,
        *,
        token_id: str,
        actor_member_id: str | None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        now = now or _utcnow()
        token = self.repository.revoke_token(token_id, now=now)
        self.repository.record_audit(
            action="api_token.revoked",
            org_id=str(token["org_id"]),
            actor_member_id=actor_member_id,
            actor_type="human" if actor_member_id else "system",
            resource_id=token_id,
            metadata={"token_type": _token_type(token)},
            now=now,
        )
        return token

    def revoke_member_tokens(
        self,
        *,
        org_id: str,
        owner_member_id: str,
        now: datetime | None = None,
    ) -> int:
        now = now or _utcnow()
        revoked = 0
        for token_id, token in self.repository.api_tokens.items():
            if (
                token["org_id"] == org_id
                and token["owner_member_id"] == owner_member_id
                and token["revoked_at"] is None
            ):
                self.revoke_token(token_id=token_id, actor_member_id=None, now=now)
                revoked += 1
        return revoked

    def _issue_token(
        self,
        *,
        token_type: Literal["pat", "service_account"],
        org_id: str,
        owner_member_id: str | None,
        service_account_id: str | None,
        scopes: Iterable[str],
        expires_at: datetime | None,
        created_at: datetime | None,
    ) -> IssuedToken:
        normalized_scopes = _normalize_scopes(scopes)
        prefix = "hpat" if token_type == "pat" else "hsa"
        plaintext = self.token_factory(prefix)
        token = self.repository.create_api_token(
            org_id=org_id,
            owner_member_id=owner_member_id,
            service_account_id=service_account_id,
            token_hash=hash_token(plaintext),
            scopes=normalized_scopes,
            expires_at=expires_at,
            created_at=created_at,
        )
        token_id = str(token["id"])
        self.repository.record_audit(
            action="api_token.created",
            org_id=org_id,
            actor_member_id=owner_member_id,
            actor_type="human" if owner_member_id else "service_account",
            resource_id=token_id,
            metadata={"token_type": token_type, "scopes": list(normalized_scopes)},
            now=created_at,
        )
        return IssuedToken(
            token_id=token_id,
            token=SecretStr(plaintext),
            token_type=token_type,
            org_id=org_id,
            scopes=normalized_scopes,
            expires_at=expires_at,
        )

    def _authenticate_record(
        self,
        token_record: dict[str, object],
        *,
        required_scope_set: set[str],
        now: datetime,
    ) -> TokenPrincipal:
        if token_record["revoked_at"] is not None:
            raise TokenAuthenticationError("revoked")
        expires_at = token_record["expires_at"]
        if isinstance(expires_at, datetime) and expires_at <= now:
            raise TokenAuthenticationError("expired")
        scopes = token_record["scopes"]
        if not isinstance(scopes, tuple):
            raise TokenAuthenticationError("invalid_scope_record")
        if not required_scope_set.issubset(scopes):
            raise TokenAuthenticationError("insufficient_scope")
        token_id = str(token_record["id"])
        self.repository.mark_token_used(token_id, now=now)
        service_account_id = token_record["service_account_id"]
        owner_member_id = token_record["owner_member_id"]
        if service_account_id is not None:
            return TokenPrincipal(
                actor_type="service_account",
                org_id=str(token_record["org_id"]),
                token_id=token_id,
                service_account_id=str(service_account_id),
                scopes=scopes,
            )
        return TokenPrincipal(
            actor_type="human",
            org_id=str(token_record["org_id"]),
            token_id=token_id,
            member_id=str(owner_member_id),
            scopes=scopes,
        )


def _normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(scope).strip() for scope in scopes))
    if not normalized:
        raise ValueError("token requires at least one scope")
    _validate_scopes(normalized)
    return normalized


def _normalize_required_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(scope).strip() for scope in scopes))
    _validate_scopes(normalized)
    return normalized


def _validate_scopes(scopes: tuple[str, ...]) -> None:
    invalid = [scope for scope in scopes if scope not in VALID_TOKEN_SCOPES]
    if invalid:
        raise ValueError(f"invalid token scope: {invalid[0]}")


def _generate_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _token_type(token_record: dict[str, object]) -> str:
    if token_record.get("service_account_id"):
        return "service_account"
    return "pat"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _b64(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return urlsafe_b64decode(padded.encode("ascii"))
