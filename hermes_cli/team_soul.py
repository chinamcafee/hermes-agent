"""Local/team soul state for Hermes team mode."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib import error, parse, request

from hermes_constants import get_hermes_home
from hermes_cli.config import load_config, load_env
from hermes_cli.team_cloud import (
    TeamCloudError,
    normalize_team_cloud_url,
    resolve_cli_team_context,
    team_breaker_status,
    team_cloud_token,
)


class TeamSoulError(RuntimeError):
    """Raised when team soul state cannot be resolved."""


class TeamSoulClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = normalize_team_cloud_url(base_url)
        self.timeout_seconds = timeout_seconds

    def get_runtime_team_soul(self, *, token: str, org_id: str, team_id: str) -> dict[str, Any]:
        query = parse.urlencode({"org_id": org_id, "team_id": team_id})
        return self._get_json(f"/v1/runtime/team-soul?{query}", token=token)

    def _get_json(self, path: str, *, token: str) -> dict[str, Any]:
        req = request.Request(
            f"{self.base_url}{path}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TeamSoulError(f"team_soul_http_{exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise TeamSoulError(f"team_soul_unreachable: {exc.reason}") from exc
        if not body:
            return {}
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise TeamSoulError("team_soul_invalid_response")
        return decoded


def _local_soul_path() -> Path:
    return get_hermes_home() / "SOUL.md"


def read_local_soul() -> dict[str, Any]:
    path = _local_soul_path()
    if not path.exists():
        return {"exists": False, "content": "", "path": str(path), "last_modified": None}
    stat = path.stat()
    return {
        "exists": True,
        "content": path.read_text(encoding="utf-8"),
        "path": str(path),
        "last_modified": stat.st_mtime,
    }


def _team_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    cfg = config if config is not None else load_config()
    section = cfg.get("team_cloud", {}) if isinstance(cfg, Mapping) else {}
    return dict(section) if isinstance(section, Mapping) else {}


def _team_client(config: Mapping[str, Any] | None, client: Any | None) -> Any | None:
    if client is not None:
        return client
    section = _team_config(config)
    url = str(section.get("url") or "").strip()
    if not url:
        return None
    return TeamSoulClient(url)


def _fetch_team_parent_soul(
    *,
    config: Mapping[str, Any] | None,
    env: Mapping[str, str] | None,
    client: Any | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    context = resolve_cli_team_context(config=config, env=env)
    if not context:
        return None, None, "local"
    token = team_cloud_token(config=config, env=env)
    resolved_client = _team_client(config, client)
    if not token or resolved_client is None:
        return context, None, "local"
    try:
        payload = resolved_client.get_runtime_team_soul(
            token=token,
            org_id=str(context.get("org_id") or ""),
            team_id=str(context.get("team_id") or context.get("org_id") or ""),
        )
    except (TeamCloudError, TeamSoulError, Exception) as exc:
        return context, {"error": str(exc)}, "paused"
    return context, payload, "team"


def safe_fallback_effective_soul(team_parent: str, local_soul: str) -> str:
    team_parent = team_parent.strip()
    local_soul = local_soul.strip()
    if team_parent and local_soul:
        return (
            "团队父人格（最高优先级，和本地人格冲突时必须以本段为准）：\n"
            f"{team_parent}\n\n"
            "本地人格（仅在不冲突时补充团队父人格）：\n"
            f"{local_soul}\n"
        )
    if team_parent:
        return team_parent
    return local_soul


def resolve_soul_state(
    *,
    config: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else load_env()
    local = read_local_soul()
    context, team_parent, mode = _fetch_team_parent_soul(config=config, env=env_source, client=client)
    if isinstance(team_parent, dict) and team_parent.get("error"):
        effective_content = str(local.get("content") or "")
        return {
            "mode": mode,
            "context": context,
            "local_soul": local,
            "team_parent_soul": None,
            "effective_soul": {
                "content": effective_content,
                "merge_status": "team_unavailable",
            },
            "merge": {"status": "failed", "error_code": "team_parent_soul_unavailable", "error": team_parent["error"]},
            "breaker": team_breaker_status(config),
        }
    parent_payload = team_parent if isinstance(team_parent, dict) else None
    parent_content = str((parent_payload or {}).get("content") or "")
    effective = safe_fallback_effective_soul(parent_content, str(local.get("content") or ""))
    team_mode = bool(context)
    parent_missing = team_mode and not parent_content
    return {
        "mode": "team" if team_mode else "local",
        "context": context,
        "local_soul": local,
        "team_parent_soul": parent_payload if team_mode else None,
        "effective_soul": {
            "content": effective,
            "merge_status": "safe_fallback" if parent_content else ("team_parent_missing" if parent_missing else "local"),
            "version": (parent_payload or {}).get("version") if isinstance(parent_payload, Mapping) else None,
            "checksum": (parent_payload or {}).get("checksum_sha256") if isinstance(parent_payload, Mapping) else None,
        },
        "merge": {"status": "ok" if parent_content else ("team_parent_missing" if parent_missing else "local"), "error_code": ""},
        "breaker": team_breaker_status(config),
    }


def _llm_merge_available(config: Mapping[str, Any] | None = None) -> bool:
    cfg = config if config is not None else load_config()
    model_cfg = cfg.get("model", {}) if isinstance(cfg, Mapping) else {}
    if not isinstance(model_cfg, Mapping):
        return False
    return bool(str(model_cfg.get("model") or "").strip() and str(model_cfg.get("provider") or "").strip())


def _extract_llm_content(response: Any) -> str:
    try:
        choices = getattr(response, "choices")
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content.strip()
    except Exception:
        return ""
    return ""


def _merge_souls_with_llm(parent_content: str, local_content: str, config: Mapping[str, Any] | None) -> str:
    cfg = config if config is not None else load_config()
    model_cfg = cfg.get("model", {}) if isinstance(cfg, Mapping) else {}
    provider = str(model_cfg.get("provider") or "").strip() if isinstance(model_cfg, Mapping) else ""
    model = str(model_cfg.get("model") or "").strip() if isinstance(model_cfg, Mapping) else ""
    if not provider or not model:
        raise TeamSoulError("model_provider_unavailable")

    from agent.auxiliary_client import call_llm

    response = call_llm(
        task="team_soul_merge",
        provider=provider,
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你负责合并 Hermes 团队模式的人格设定。输出必须只包含合并后的人格正文。"
                    "团队父人格优先级最高；当团队父人格和本地人格冲突时，必须保留团队父人格，"
                    "本地人格只能作为不冲突的补充。不要解释合并过程。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "团队父人格：\n"
                    f"{parent_content.strip()}\n\n"
                    "本地人格：\n"
                    f"{local_content.strip()}\n\n"
                    "请给出合并后的人格。"
                ),
            },
        ],
        temperature=0,
        max_tokens=1200,
    )
    merged = _extract_llm_content(response)
    if not merged:
        raise TeamSoulError("model_merge_empty_response")
    return merged


def save_local_soul(
    content: str,
    *,
    client: Any | None = None,
    config: Mapping[str, Any] | None = None,
    merge_with_llm: bool = True,
) -> dict[str, Any]:
    path = _local_soul_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    state = resolve_soul_state(config=config, client=client)
    parent = state.get("team_parent_soul")
    if parent and merge_with_llm:
        if _llm_merge_available(config):
            try:
                merged = _merge_souls_with_llm(str(parent.get("content") or ""), content, config)
                state["effective_soul"]["content"] = merged
                state["effective_soul"]["merge_status"] = "llm"
                state["merge"] = {"status": "ok", "error_code": ""}
                return {"saved": True, **state}
            except Exception as exc:
                state["merge"] = {
                    "status": "failed",
                    "error_code": "model_merge_failed",
                    "message": f"本地人格已保存，但大模型合并失败，团队父人格合并使用安全降级结果：{exc}",
                }
                state["effective_soul"]["merge_status"] = "safe_fallback"
                return {"saved": True, **state}
        state["merge"] = {
            "status": "failed",
            "error_code": "model_provider_unavailable",
            "message": "本地人格已保存，但未配置可用大模型供应商，团队父人格合并使用安全降级结果。",
        }
        state["effective_soul"]["merge_status"] = "safe_fallback"
    return {"saved": True, **state}


def effective_soul_for_runtime(agent: Any) -> str | None:
    if not getattr(agent, "team_context", None):
        return None
    try:
        state = resolve_soul_state()
    except Exception:
        return None
    effective = state.get("effective_soul")
    if isinstance(effective, Mapping):
        content = str(effective.get("content") or "").strip()
        if content:
            return content
    return None


def print_soul_help(print_fn: Callable[[str], None] = print) -> None:
    print_fn("Usage:")
    print_fn("  /soul status")
    print_fn("  /soul show [team|local|effective]")
    print_fn("  /soul merge")


def handle_soul_slash(command: str, *, print_fn: Callable[[str], None] = print) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        print_fn(f"Soul command parse error: {exc}")
        return True
    args = parts[1:]
    if not args or args[0] in {"help", "-h", "--help"}:
        print_soul_help(print_fn)
        return True
    action = args[0]
    state = resolve_soul_state()
    if action == "status":
        print_fn(f"mode: {state.get('mode')}")
        print_fn(f"local_soul: {'exists' if state.get('local_soul', {}).get('exists') else 'missing'}")
        print_fn(f"team_parent_soul: {'exists' if state.get('team_parent_soul') else 'missing'}")
        print_fn(f"merge: {state.get('merge', {}).get('status')}")
        return True
    if action == "show":
        target = args[1] if len(args) > 1 else "effective"
        if target == "team":
            print_fn(str((state.get("team_parent_soul") or {}).get("content") or ""))
        elif target == "local":
            print_fn(str((state.get("local_soul") or {}).get("content") or ""))
        else:
            print_fn(str((state.get("effective_soul") or {}).get("content") or ""))
        return True
    if action == "merge":
        result = save_local_soul(str(state.get("local_soul", {}).get("content") or ""))
        print_fn(f"merge: {result.get('merge', {}).get('status')}")
        return True
    print_soul_help(print_fn)
    return True


__all__ = [
    "TeamSoulClient",
    "TeamSoulError",
    "effective_soul_for_runtime",
    "handle_soul_slash",
    "read_local_soul",
    "resolve_soul_state",
    "safe_fallback_effective_soul",
    "save_local_soul",
]
