"""First-class Hermes CLI integration for Team Cloud."""

from __future__ import annotations

import getpass
import json
import os
import shlex
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib import error, request

from hermes_cli.config import (
    ensure_hermes_home,
    get_config_path,
    load_config,
    load_env,
    read_raw_config,
    remove_env_value,
    save_env_value,
)

TEAM_CLOUD_TOKEN_ENV = "HERMES_TEAM_CLOUD_SESSION_TOKEN"
BREAKER_AUTO = "auto"
BREAKER_MANUAL_OPEN = "manual_open"
BREAKER_MANUAL_CLOSED = "manual_closed"


class TeamCloudError(RuntimeError):
    """Raised when Team Cloud CLI operations cannot be completed."""


def default_team_cloud_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "url": "",
        "default_org_id": "",
        "default_team_id": "",
        "default_project_id": "",
        "default_member_id": "",
        "token_env": TEAM_CLOUD_TOKEN_ENV,
        "circuit_breaker": default_circuit_breaker_config(),
    }


def default_circuit_breaker_config() -> dict[str, Any]:
    return {
        "mode": BREAKER_AUTO,
        "state": "closed",
        "failure_count": 0,
        "failure_threshold": 3,
        "recovery_after_seconds": 60,
        "opened_until": "",
        "last_error": "",
    }


@dataclass
class TeamCloudClient:
    base_url: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        self.base_url = normalize_team_cloud_url(self.base_url)

    def bootstrap_status(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/bootstrap/status")

    def login(self, *, org_id: str, user_id: str, password: str) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/v1/auth/login",
            {
                "org_id": org_id,
                "user_id": user_id,
                "password": password,
                "client": "cli",
            },
        )

    def session(self, token: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/v1/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = None
        request_headers = {"Accept": "application/json", **(headers or {})}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            record_team_cloud_failure(f"team_cloud_http_{exc.code}: {detail}")
            raise TeamCloudError(f"team_cloud_http_{exc.code}: {detail}") from exc
        except error.URLError as exc:
            record_team_cloud_failure(f"team_cloud_unreachable: {exc.reason}")
            raise TeamCloudError(f"team_cloud_unreachable: {exc.reason}") from exc
        if not body:
            record_team_cloud_success()
            return {}
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            record_team_cloud_failure(f"team_cloud_invalid_json: {exc}")
            raise TeamCloudError(f"team_cloud_invalid_json: {exc}") from exc
        if not isinstance(decoded, dict):
            record_team_cloud_failure("team_cloud_invalid_response")
            raise TeamCloudError("team_cloud_invalid_response")
        record_team_cloud_success()
        return decoded


def normalize_team_cloud_url(url: str) -> str:
    normalized = str(url or "").strip().rstrip("/")
    if not normalized:
        raise TeamCloudError("team_cloud_url_required")
    if not normalized.startswith(("http://", "https://")):
        normalized = "http://" + normalized
    return normalized


def _merged_team_cloud_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    base = default_team_cloud_config()
    source = config if config is not None else load_config()
    value = source.get("team_cloud", {}) if isinstance(source, Mapping) else {}
    if isinstance(value, Mapping):
        base.update(value)
        breaker = default_circuit_breaker_config()
        if isinstance(value.get("circuit_breaker"), Mapping):
            breaker.update(value["circuit_breaker"])
        base["circuit_breaker"] = breaker
    if not base.get("token_env"):
        base["token_env"] = TEAM_CLOUD_TOKEN_ENV
    return base


def _write_team_cloud_config(updates: Mapping[str, Any]) -> dict[str, Any]:
    ensure_hermes_home()
    raw = read_raw_config()
    if not isinstance(raw, dict):
        raw = {}
    current = raw.get("team_cloud")
    if not isinstance(current, dict):
        current = {}
    merged = {**current, **dict(updates)}
    raw["team_cloud"] = merged

    from utils import atomic_yaml_write

    atomic_yaml_write(get_config_path(), raw, sort_keys=False)
    return _merged_team_cloud_config(load_config())


def _parse_time(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _breaker_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return dict(_merged_team_cloud_config(config).get("circuit_breaker") or default_circuit_breaker_config())


def _write_breaker(updates: Mapping[str, Any]) -> dict[str, Any]:
    breaker = _breaker_config()
    breaker.update(dict(updates))
    return _write_team_cloud_config({"circuit_breaker": breaker}).get("circuit_breaker", breaker)


def _refresh_breaker_if_due(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    breaker = _breaker_config(config)
    if breaker.get("mode") != BREAKER_AUTO:
        return breaker
    if breaker.get("state") != "open":
        return breaker
    opened_until = _parse_time(str(breaker.get("opened_until") or ""))
    if opened_until and opened_until > datetime.now(timezone.utc):
        return breaker
    return _write_breaker({"state": "half_open", "opened_until": ""})


def team_breaker_status(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    breaker = _refresh_breaker_if_due(config)
    return {
        "mode": str(breaker.get("mode") or BREAKER_AUTO),
        "state": str(breaker.get("state") or "closed"),
        "failure_count": int(breaker.get("failure_count") or 0),
        "failure_threshold": int(breaker.get("failure_threshold") or 3),
        "opened_until": str(breaker.get("opened_until") or ""),
        "last_error": str(breaker.get("last_error") or ""),
    }


def team_breaker_allows(config: Mapping[str, Any] | None = None) -> bool:
    status = team_breaker_status(config)
    if status["mode"] == BREAKER_MANUAL_OPEN:
        return False
    if status["mode"] == BREAKER_MANUAL_CLOSED:
        return True
    return status["state"] != "open"


def team_cli_status_label(config: Mapping[str, Any] | None = None, env: Mapping[str, str] | None = None) -> dict[str, str]:
    team_config = _merged_team_cloud_config(config)
    if not bool(team_config.get("enabled")):
        return {"mode": "local", "label": "Local"}
    status = team_breaker_status(config)
    if not team_breaker_allows(config):
        return {"mode": "paused", "label": "Team API paused", "breaker": f"{status['mode']}/{status['state']}"}
    context = resolve_cli_team_context(config=config, env=env)
    if not context:
        return {"mode": "local", "label": "Local"}
    member_id = str(context.get("member_id") or "").strip()
    org_id = str(context.get("org_id") or "").strip()
    identity = member_id or org_id or "connected"
    return {"mode": "team", "label": f"Team {identity}", "breaker": f"{status['mode']}/{status['state']}"}


def record_team_cloud_success() -> None:
    breaker = _breaker_config()
    if breaker.get("mode") == BREAKER_MANUAL_OPEN:
        return
    _write_breaker({"state": "closed", "failure_count": 0, "opened_until": "", "last_error": ""})


def record_team_cloud_failure(error_text: str) -> None:
    breaker = _breaker_config()
    if breaker.get("mode") != BREAKER_AUTO:
        _write_breaker({"last_error": error_text})
        return
    count = int(breaker.get("failure_count") or 0) + 1
    threshold = int(breaker.get("failure_threshold") or 3)
    updates: dict[str, Any] = {"failure_count": count, "last_error": error_text}
    if count >= threshold:
        recovery = int(breaker.get("recovery_after_seconds") or 60)
        updates["state"] = "open"
        updates["opened_until"] = _format_time(datetime.now(timezone.utc) + timedelta(seconds=max(1, recovery)))
    _write_breaker(updates)


def team_breaker_open(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    breaker = _write_breaker({"mode": BREAKER_MANUAL_OPEN, "state": "open", "opened_until": ""})
    print_fn("Team Cloud API breaker: open")
    return breaker


def team_breaker_close(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    breaker = _write_breaker({"mode": BREAKER_MANUAL_CLOSED, "state": "closed", "failure_count": 0, "opened_until": "", "last_error": ""})
    print_fn("Team Cloud API breaker: closed")
    return breaker


def team_breaker_auto(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    breaker = _write_breaker({"mode": BREAKER_AUTO, "state": "closed", "failure_count": 0, "opened_until": "", "last_error": ""})
    print_fn("Team Cloud API breaker: auto")
    return breaker


def connect_team_cloud(url: str, *, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    normalized = normalize_team_cloud_url(url)
    config = _write_team_cloud_config({"url": normalized})
    print_fn(f"Team Cloud connected: {normalized}")
    return config


def login_team_cloud(
    *,
    org_id: str,
    user_id: str,
    password: str,
    team_id: str = "",
    project_id: str = "",
    client: Any | None = None,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    config = _merged_team_cloud_config()
    url = str(config.get("url") or "").strip()
    if client is None:
        if not url:
            raise TeamCloudError("team_cloud_url_required")
        client = TeamCloudClient(url)
    org_id = org_id.strip()
    user_id = user_id.strip()
    if not org_id or not user_id or not password:
        raise TeamCloudError("org_id_user_id_password_required")

    response = client.login(org_id=org_id, user_id=user_id, password=password)
    token = str(response.get("token") or "").strip()
    member = response.get("member") if isinstance(response.get("member"), dict) else {}
    member_id = str(member.get("id") or member.get("member_id") or f"{org_id}:{user_id}").strip()
    resolved_org_id = str(member.get("org_id") or org_id).strip()
    resolved_team_id = (team_id or resolved_org_id).strip()
    resolved_project_id = project_id.strip()
    if not token:
        raise TeamCloudError("team_cloud_login_token_missing")

    token_env = str(config.get("token_env") or TEAM_CLOUD_TOKEN_ENV)
    save_env_value(token_env, token)
    saved = _write_team_cloud_config(
        {
            "enabled": True,
            "default_org_id": resolved_org_id,
            "default_team_id": resolved_team_id,
            "default_project_id": resolved_project_id,
            "default_member_id": member_id,
            "token_env": token_env,
        }
    )
    print_fn(f"Logged in as {member_id}")
    return saved


def team_use(
    *,
    org_id: str,
    team_id: str = "",
    project_id: str = "",
    member_id: str = "",
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    org_id = org_id.strip()
    if not org_id:
        raise TeamCloudError("org_id_required")
    saved = _write_team_cloud_config(
        {
            "enabled": True,
            "default_org_id": org_id,
            "default_team_id": (team_id or org_id).strip(),
            "default_project_id": project_id.strip(),
            "default_member_id": member_id.strip(),
        }
    )
    print_fn(
        "Team Cloud context selected: "
        f"org={saved.get('default_org_id')} "
        f"team={saved.get('default_team_id') or saved.get('default_org_id')} "
        f"project={saved.get('default_project_id') or '-'}"
    )
    return saved


def team_off(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    saved = _write_team_cloud_config({"enabled": False})
    print_fn("Team Cloud disabled for Hermes CLI.")
    return saved


def team_logout(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    config = _merged_team_cloud_config()
    token_env = str(config.get("token_env") or TEAM_CLOUD_TOKEN_ENV)
    remove_env_value(token_env)
    saved = _write_team_cloud_config({"enabled": False})
    print_fn(f"Team Cloud session token removed from {token_env}.")
    return saved


def team_token_set(token: str, *, print_fn: Callable[[str], None] = print) -> None:
    token = token.strip()
    if not token:
        raise TeamCloudError("token_required")
    config = _merged_team_cloud_config()
    token_env = str(config.get("token_env") or TEAM_CLOUD_TOKEN_ENV)
    save_env_value(token_env, token)
    _write_team_cloud_config({"enabled": True, "token_env": token_env})
    print_fn(f"Team Cloud token saved to {token_env}.")


def team_cloud_token(
    *,
    config: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    team_config = _merged_team_cloud_config(config)
    token_env = str(team_config.get("token_env") or TEAM_CLOUD_TOKEN_ENV)
    env_source = env if env is not None else load_env()
    token = str(env_source.get(token_env) or "").strip()
    if token:
        return token
    return str(os.environ.get(token_env) or "").strip()


def resolve_cli_team_context(
    *,
    config: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    team_config = _merged_team_cloud_config(config)
    if not bool(team_config.get("enabled")):
        return None
    if not team_breaker_allows(config):
        return None
    if not str(team_config.get("url") or "").strip():
        return None
    if not team_cloud_token(config=config, env=env):
        return None

    org_id = str(team_config.get("default_org_id") or "").strip()
    member_id = str(team_config.get("default_member_id") or "").strip()
    if not org_id or not member_id:
        return None
    team_id = str(team_config.get("default_team_id") or org_id).strip()
    project_id = str(team_config.get("default_project_id") or "").strip()
    return {
        "org_id": org_id,
        "team_id": team_id,
        "project_id": project_id,
        "member_id": member_id,
    }


def resolve_team_cloud_client(config: Mapping[str, Any] | None = None) -> TeamCloudClient | None:
    team_config = _merged_team_cloud_config(config)
    url = str(team_config.get("url") or "").strip()
    if not url:
        return None
    return TeamCloudClient(url)


def team_status(
    *,
    client: Any | None = None,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    config = load_config()
    team_config = _merged_team_cloud_config(config)
    token = team_cloud_token(config=config)
    saved_context = resolve_cli_team_context(config=config, env=load_env())
    breaker = team_breaker_status(config)
    connection_configured = bool(str(team_config.get("url") or "").strip())
    token_configured = bool(token)
    remote_status = "not_configured"
    session: dict[str, Any] | None = None

    if client is None:
        client = resolve_team_cloud_client(config)
    if client is not None:
        try:
            status = client.bootstrap_status()
            remote_status = str(status.get("status") or ("ready" if status.get("initialized") else "not_initialized"))
        except Exception as exc:
            remote_status = f"error:{exc}"
        if token:
            try:
                session = client.session(token)
            except Exception as exc:
                session = {"error": str(exc)}

    account_authenticated = bool(
        saved_context
        and token_configured
        and session is not None
        and not session.get("error")
    )
    login_required = connection_configured and not account_authenticated
    context = saved_context if account_authenticated else None
    mode = "team" if account_authenticated else "local"

    print_fn(f"mode: {mode}")
    print_fn(f"remote: {remote_status}")
    print_fn(f"url: {team_config.get('url') or '-'}")
    print_fn(f"org: {team_config.get('default_org_id') or '-'}")
    print_fn(f"team: {team_config.get('default_team_id') or team_config.get('default_org_id') or '-'}")
    print_fn(f"project: {team_config.get('default_project_id') or '-'}")
    print_fn(f"member: {(session or {}).get('member_id') or team_config.get('default_member_id') or '-'}")
    print_fn(
        "breaker: "
        f"{breaker['mode']}/{breaker['state']} "
        f"failures={breaker['failure_count']}/{breaker['failure_threshold']}"
    )
    if isinstance(session, dict) and session.get("role"):
        print_fn(f"role: {session.get('role')}")
    return {
        "mode": mode,
        "remote": str(team_config.get("url") or ""),
        "remote_status": remote_status,
        "context": context,
        "saved_context": saved_context,
        "session": session,
        "breaker": breaker,
        "connection_configured": connection_configured,
        "token_configured": token_configured,
        "account_authenticated": account_authenticated,
        "login_required": login_required,
    }


def print_team_help(print_fn: Callable[[str], None] = print) -> None:
    print_fn("Usage:")
    print_fn("  hermes team connect <url>")
    print_fn("  hermes team login --org <org> --user <user> [--team <team>] [--project <project>]")
    print_fn("  hermes team status")
    print_fn("  hermes team use --org <org> [--team <team>] [--project <project>] [--member <member>]")
    print_fn("  hermes team off")
    print_fn("  hermes team logout")
    print_fn("  hermes team breaker [status|open|close|auto]")


def handle_team_slash(command: str, *, print_fn: Callable[[str], None] = print) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        print_fn(f"Team Cloud command parse error: {exc}")
        return True
    args = parts[1:]
    if not args or args[0] in {"help", "-h", "--help"}:
        print_team_help(print_fn)
        return True

    action = args[0]
    try:
        if action == "status":
            team_status(print_fn=print_fn)
        elif action == "connect" and len(args) >= 2:
            connect_team_cloud(args[1], print_fn=print_fn)
        elif action == "login" and len(args) >= 3:
            password = getpass.getpass("Team Cloud password: ")
            team_id = args[3] if len(args) >= 4 else ""
            project_id = args[4] if len(args) >= 5 else ""
            login_team_cloud(
                org_id=args[1],
                user_id=args[2],
                password=password,
                team_id=team_id,
                project_id=project_id,
                print_fn=print_fn,
            )
        elif action == "use" and len(args) >= 2:
            team_use(
                org_id=args[1],
                team_id=args[2] if len(args) >= 3 else "",
                project_id=args[3] if len(args) >= 4 else "",
                member_id=args[4] if len(args) >= 5 else "",
                print_fn=print_fn,
            )
        elif action == "off":
            team_off(print_fn=print_fn)
        elif action == "logout":
            team_logout(print_fn=print_fn)
        elif action == "token" and len(args) >= 3 and args[1] == "set":
            team_token_set(args[2], print_fn=print_fn)
        elif action == "breaker":
            breaker_action = args[1] if len(args) >= 2 else "status"
            if breaker_action == "status":
                status = team_breaker_status()
                print_fn(
                    "Team Cloud API breaker: "
                    f"{status['mode']}/{status['state']} "
                    f"failures={status['failure_count']}/{status['failure_threshold']}"
                )
                if status.get("last_error"):
                    print_fn(f"last_error: {status['last_error']}")
            elif breaker_action == "open":
                team_breaker_open(print_fn=print_fn)
            elif breaker_action == "close":
                team_breaker_close(print_fn=print_fn)
            elif breaker_action == "auto":
                team_breaker_auto(print_fn=print_fn)
            else:
                print_team_help(print_fn)
        else:
            print_team_help(print_fn)
    except TeamCloudError as exc:
        print_fn(f"Team Cloud error: {exc}")
    return True


def cmd_team(args: Any) -> None:
    action = getattr(args, "team_action", None)
    try:
        if action == "connect":
            connect_team_cloud(args.url)
        elif action == "login":
            password = getattr(args, "password", None) or getpass.getpass("Team Cloud password: ")
            login_team_cloud(
                org_id=args.org,
                user_id=args.user,
                password=password,
                team_id=getattr(args, "team", "") or "",
                project_id=getattr(args, "project", "") or "",
            )
        elif action == "status":
            team_status()
        elif action == "use":
            team_use(
                org_id=args.org,
                team_id=getattr(args, "team", "") or "",
                project_id=getattr(args, "project", "") or "",
                member_id=getattr(args, "member", "") or "",
            )
        elif action == "off":
            team_off()
        elif action == "logout":
            team_logout()
        elif action == "token":
            if getattr(args, "token_action", None) == "set":
                team_token_set(args.token)
            else:
                print_team_help()
        elif action == "breaker":
            breaker_action = getattr(args, "breaker_action", None) or "status"
            if breaker_action == "status":
                status = team_breaker_status()
                print(
                    "Team Cloud API breaker: "
                    f"{status['mode']}/{status['state']} "
                    f"failures={status['failure_count']}/{status['failure_threshold']}"
                )
            elif breaker_action == "open":
                team_breaker_open()
            elif breaker_action == "close":
                team_breaker_close()
            elif breaker_action == "auto":
                team_breaker_auto()
            else:
                print_team_help()
        else:
            print_team_help()
    except TeamCloudError as exc:
        raise SystemExit(f"Team Cloud error: {exc}") from exc


__all__ = [
    "TeamCloudClient",
    "TeamCloudError",
    "TEAM_CLOUD_TOKEN_ENV",
    "cmd_team",
    "connect_team_cloud",
    "default_team_cloud_config",
    "handle_team_slash",
    "login_team_cloud",
    "normalize_team_cloud_url",
    "record_team_cloud_failure",
    "record_team_cloud_success",
    "resolve_cli_team_context",
    "team_breaker_auto",
    "team_breaker_close",
    "team_breaker_open",
    "team_breaker_status",
    "team_cli_status_label",
    "team_cloud_token",
    "team_status",
]
