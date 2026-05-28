"""Profile-scoped cloud backup commands for Hermes CLI.

Team Cloud manages only team-owned memory and team parent soul data. This
module backs up local profile data owned by the current Hermes user: personal
memory files and the local ``SOUL.md`` file. Both resources share one
MinIO/S3-compatible target but are stored under separate object-key paths.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import hmac
import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib import error, parse, request
from xml.etree import ElementTree

from hermes_constants import get_hermes_home
from hermes_cli.config import (
    ensure_hermes_home,
    get_config_path,
    load_config,
    load_env,
    read_raw_config,
    save_env_value,
)

ACCESS_KEY_ENV = "HERMES_CLOUD_BACKUP_MINIO_ACCESS_KEY"
SECRET_KEY_ENV = "HERMES_CLOUD_BACKUP_MINIO_SECRET_KEY"
RESOURCE_MEMORY = "memory"
RESOURCE_SOUL = "soul"
SUPPORTED_RESOURCES = {RESOURCE_MEMORY, RESOURCE_SOUL}
BACKUP_FORMATS = {
    RESOURCE_MEMORY: "hermes-cloud-backup-memory-v1",
    RESOURCE_SOUL: "hermes-cloud-backup-soul-v1",
}


class CloudBackupError(RuntimeError):
    """Raised when local profile cloud backup cannot complete."""


def default_cloud_backup_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "endpoint": "",
        "bucket": "hermes-personal-cloud-backups",
        "region": "us-east-1",
        "prefix": "profiles",
        "access_key_env": ACCESS_KEY_ENV,
        "secret_key_env": SECRET_KEY_ENV,
        "schedules": {
            RESOURCE_MEMORY: "off",
            RESOURCE_SOUL: "off",
        },
        "cron_job_ids": {
            RESOURCE_MEMORY: "",
            RESOURCE_SOUL: "",
        },
        "last_backup_keys": {
            RESOURCE_MEMORY: "",
            RESOURCE_SOUL: "",
        },
    }


def _resource_type(value: str) -> str:
    resource_type = str(value or "").strip().lower()
    if resource_type not in SUPPORTED_RESOURCES:
        raise CloudBackupError("unsupported_cloud_backup_resource")
    return resource_type


def _merged_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = config if config is not None else load_config()
    merged = default_cloud_backup_config()
    section = source.get("cloud_backup", {}) if isinstance(source, Mapping) else {}
    if isinstance(section, Mapping):
        for key, value in section.items():
            if key in {"schedules", "cron_job_ids", "last_backup_keys"} and isinstance(value, Mapping):
                nested = dict(merged[key])
                nested.update(value)
                merged[key] = nested
            else:
                merged[key] = value
    if not merged.get("access_key_env"):
        merged["access_key_env"] = ACCESS_KEY_ENV
    if not merged.get("secret_key_env"):
        merged["secret_key_env"] = SECRET_KEY_ENV
    return merged


def _write_config(updates: Mapping[str, Any]) -> dict[str, Any]:
    ensure_hermes_home()
    raw = read_raw_config()
    if not isinstance(raw, dict):
        raw = {}
    current = raw.get("cloud_backup")
    if not isinstance(current, dict):
        current = {}
    merged = dict(current)
    for key, value in dict(updates).items():
        if key in {"schedules", "cron_job_ids", "last_backup_keys"} and isinstance(value, Mapping):
            nested = dict(merged.get(key) or {})
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    raw["cloud_backup"] = merged

    from utils import atomic_yaml_write

    atomic_yaml_write(get_config_path(), raw, sort_keys=False)
    return _merged_config(load_config())


def configure_cloud_backup(
    *,
    endpoint: str,
    bucket: str,
    access_key: str = "",
    secret_key: str = "",
    region: str = "us-east-1",
    root_prefix: str = "profiles",
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    endpoint = endpoint.strip().rstrip("/")
    bucket = bucket.strip()
    if not endpoint or not bucket:
        raise CloudBackupError("endpoint_and_bucket_required")
    if access_key:
        save_env_value(ACCESS_KEY_ENV, access_key)
    if secret_key:
        save_env_value(SECRET_KEY_ENV, secret_key)
    saved = _write_config(
        {
            "enabled": True,
            "endpoint": endpoint,
            "bucket": bucket,
            "region": region.strip() or "us-east-1",
            "prefix": root_prefix.strip().strip("/") or "profiles",
            "access_key_env": ACCESS_KEY_ENV,
            "secret_key_env": SECRET_KEY_ENV,
        }
    )
    print_fn(f"Cloud backup MinIO configured: {bucket} at {endpoint}")
    return saved


@dataclass
class MinioObjectStore:
    endpoint: str
    bucket: str
    region: str
    access_key: str
    secret_key: str

    def __post_init__(self) -> None:
        self.endpoint = self.endpoint.strip().rstrip("/")
        if not self.endpoint.startswith(("http://", "https://")):
            self.endpoint = "http://" + self.endpoint
        self.bucket = self.bucket.strip()
        self.region = self.region.strip() or "us-east-1"
        if not self.endpoint or not self.bucket or not self.access_key or not self.secret_key:
            raise CloudBackupError("minio_configuration_incomplete")

    def put_object(self, key: str, body: bytes, content_type: str = "application/json") -> None:
        headers = {"content-type": content_type}
        self._request("PUT", key, body=body, headers=headers)

    def get_object(self, key: str) -> bytes:
        return self._request("GET", key)

    def list_objects(self, prefix: str) -> list[dict[str, object]]:
        query = {"list-type": "2", "prefix": prefix}
        raw = self._request("GET", "", query=query)
        return _parse_list_bucket(raw)

    def _request(
        self,
        method: str,
        key: str,
        *,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> bytes:
        parsed = parse.urlparse(self.endpoint)
        host = parsed.netloc
        encoded_key = "/".join(parse.quote(part, safe="") for part in key.split("/") if part)
        canonical_uri = f"/{parse.quote(self.bucket, safe='')}"
        if encoded_key:
            canonical_uri += f"/{encoded_key}"
        query = dict(query or {})
        canonical_query = "&".join(
            f"{parse.quote(str(k), safe='-_.~')}={parse.quote(str(v), safe='-_.~')}"
            for k, v in sorted(query.items())
        )
        url = f"{self.endpoint}{canonical_uri}"
        if canonical_query:
            url += f"?{canonical_query}"

        now = _dt.datetime.now(_dt.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        signed_headers = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            **{str(k).lower(): str(v).strip() for k, v in (headers or {}).items()},
        }
        canonical_headers = "".join(f"{k}:{signed_headers[k]}\n" for k in sorted(signed_headers))
        signed_header_names = ";".join(sorted(signed_headers))
        canonical_request = "\n".join(
            [method, canonical_uri, canonical_query, canonical_headers, signed_header_names, payload_hash]
        )
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signing_key = _aws_v4_signing_key(self.secret_key, date_stamp, self.region)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_header_names}, Signature={signature}"
        )
        request_headers = {k: v for k, v in signed_headers.items() if k != "host"}
        request_headers["Authorization"] = authorization
        req = request.Request(url, data=body if method in {"PUT", "POST"} else None, headers=request_headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as response:  # noqa: S310
                return response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CloudBackupError(f"minio_http_{exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise CloudBackupError(f"minio_unreachable: {exc.reason}") from exc


def _aws_v4_signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    key = ("AWS4" + secret_key).encode("utf-8")
    for value in (date_stamp, region, "s3", "aws4_request"):
        key = hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()
    return key


def _parse_list_bucket(payload: bytes) -> list[dict[str, object]]:
    root = ElementTree.fromstring(payload)
    ns_prefix = ""
    if root.tag.startswith("{"):
        ns_prefix = root.tag.split("}", 1)[0] + "}"
    out: list[dict[str, object]] = []
    for item in root.findall(f"{ns_prefix}Contents"):
        key = (item.findtext(f"{ns_prefix}Key") or "").strip()
        if not key:
            continue
        size_text = item.findtext(f"{ns_prefix}Size") or "0"
        out.append(
            {
                "key": key,
                "size": int(size_text) if size_text.isdigit() else 0,
                "last_modified": item.findtext(f"{ns_prefix}LastModified") or "",
            }
        )
    return out


def _client_from_config(config: Mapping[str, Any] | None = None) -> MinioObjectStore:
    backup_config = _merged_config(config)
    env = load_env()
    access_env = str(backup_config.get("access_key_env") or ACCESS_KEY_ENV)
    secret_env = str(backup_config.get("secret_key_env") or SECRET_KEY_ENV)
    access_key = str(env.get(access_env) or os.environ.get(access_env) or "").strip()
    secret_key = str(env.get(secret_env) or os.environ.get(secret_env) or "").strip()
    return MinioObjectStore(
        endpoint=str(backup_config.get("endpoint") or ""),
        bucket=str(backup_config.get("bucket") or ""),
        region=str(backup_config.get("region") or "us-east-1"),
        access_key=access_key,
        secret_key=secret_key,
    )


def _iter_memory_files() -> list[Path]:
    memory_dir = get_hermes_home() / "memories"
    if not memory_dir.exists():
        return []
    files = []
    for path in sorted(memory_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith((".lock", ".tmp")) or ".bak." in path.name:
            continue
        files.append(path)
    return files


def _iter_soul_files() -> list[Path]:
    soul_path = get_hermes_home() / "SOUL.md"
    return [soul_path] if soul_path.exists() and soul_path.is_file() else []


def _iter_resource_files(resource_type: str) -> list[Path]:
    resource_type = _resource_type(resource_type)
    if resource_type == RESOURCE_MEMORY:
        return _iter_memory_files()
    return _iter_soul_files()


def _backup_payload(resource_type: str, now: _dt.datetime) -> dict[str, Any]:
    resource_type = _resource_type(resource_type)
    hermes_home = get_hermes_home()
    files = []
    for path in _iter_resource_files(resource_type):
        rel = path.relative_to(hermes_home).as_posix()
        files.append(
            {
                "path": rel,
                "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        )
    return {
        "format": BACKUP_FORMATS[resource_type],
        "resource_type": resource_type,
        "created_at": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile_id": hermes_home.name,
        "hermes_home_name": hermes_home.name,
        "files": files,
    }


def _key_prefix(resource_type: str, config: Mapping[str, Any]) -> str:
    resource_type = _resource_type(resource_type)
    root_prefix = str(config.get("prefix") or "profiles").strip().strip("/")
    profile_id = get_hermes_home().name
    parts = [part for part in (root_prefix, "profiles", profile_id, resource_type) if part]
    return "/".join(parts)


def _object_suffix(resource_type: str) -> str:
    if resource_type == RESOURCE_MEMORY:
        return "personal-memory"
    return "local-soul"


def run_cloud_backup_now(
    resource_type: str,
    *,
    client: Any | None = None,
    config: Mapping[str, Any] | None = None,
    now: _dt.datetime | None = None,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    resource_type = _resource_type(resource_type)
    backup_config = _merged_config(config)
    if client is None:
        client = _client_from_config(backup_config)
    now = now or _dt.datetime.now(_dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_dt.timezone.utc)
    payload = _backup_payload(resource_type, now)
    key = (
        f"{_key_prefix(resource_type, backup_config)}/"
        f"{now.astimezone(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_object_suffix(resource_type)}.json"
    )
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    client.put_object(key, body, "application/json")
    _write_config({"last_backup_keys": {resource_type: key}})
    result = {"resource_type": resource_type, "object_key": key, "file_count": len(payload["files"]), "bytes": len(body)}
    print_fn(f"{resource_type.capitalize()} cloud backup uploaded: {key} ({len(payload['files'])} files)")
    return result


def restore_cloud_backup(
    resource_type: str,
    object_key: str,
    *,
    client: Any | None = None,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    resource_type = _resource_type(resource_type)
    object_key = object_key.strip()
    if not object_key:
        raise CloudBackupError("object_key_required")
    if client is None:
        client = _client_from_config()
    payload = json.loads(client.get_object(object_key).decode("utf-8"))
    if payload.get("resource_type") and payload.get("resource_type") != resource_type:
        raise CloudBackupError("cloud_backup_resource_mismatch")
    if payload.get("format") != BACKUP_FORMATS[resource_type]:
        raise CloudBackupError("unsupported_cloud_backup_format")
    if payload.get("resource_type") != resource_type:
        raise CloudBackupError("cloud_backup_resource_mismatch")
    hermes_home = get_hermes_home()
    restored = 0
    for item in payload.get("files", []):
        rel = str(item.get("path") or "")
        target = (hermes_home / rel).resolve()
        try:
            target.relative_to(hermes_home.resolve())
        except ValueError as exc:
            raise CloudBackupError(f"unsafe_backup_path:{rel}") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(str(item.get("content_base64") or "")))
        restored += 1
    print_fn(f"{resource_type.capitalize()} cloud backup restored: {object_key} ({restored} files)")
    return {"resource_type": resource_type, "object_key": object_key, "restored_count": restored}


def list_cloud_backups(resource_type: str, *, client: Any | None = None) -> list[dict[str, object]]:
    resource_type = _resource_type(resource_type)
    backup_config = _merged_config()
    if client is None:
        client = _client_from_config(backup_config)
    return client.list_objects(_key_prefix(resource_type, backup_config))


def _write_cron_script(resource_type: str) -> Path:
    resource_type = _resource_type(resource_type)
    scripts_dir = get_hermes_home() / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / f"cloud-backup-{resource_type}-cron.py"
    repo_root = Path(__file__).resolve().parents[1]
    script_path.write_text(
        "\n".join(
            [
                "import sys",
                f"sys.path.insert(0, {str(repo_root)!r})",
                "from hermes_cli.cloud_backup import run_cloud_backup_now",
                f"run_cloud_backup_now({resource_type!r})",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def schedule_cloud_backup(
    resource_type: str,
    cadence: str,
    *,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    resource_type = _resource_type(resource_type)
    cadence = cadence.strip().lower()
    name = f"Hermes cloud backup: {resource_type}"
    if cadence == "off":
        config = _merged_config()
        job_id = str((config.get("cron_job_ids") or {}).get(resource_type) or "")
        if job_id:
            from cron.jobs import pause_job

            pause_job(job_id, f"{resource_type} cloud backup schedule disabled")
        saved = _write_config({"schedules": {resource_type: "off"}})
        print_fn(f"{resource_type.capitalize()} cloud backup schedule disabled.")
        return {"name": name, "id": job_id, "enabled": False, "config": saved}
    schedule_map = {
        "hourly": "every 1h",
        "daily": "every 1d",
        "weekly": "0 3 * * 0",
        "monthly": "0 3 1 * *",
    }
    if cadence not in schedule_map:
        raise CloudBackupError("unsupported_backup_schedule")
    _write_cron_script(resource_type)
    config = _merged_config()
    existing_id = str((config.get("cron_job_ids") or {}).get(resource_type) or "")
    from cron.jobs import create_job, get_job, update_job

    script = f"cloud-backup-{resource_type}-cron.py"
    if existing_id and get_job(existing_id):
        job = update_job(
            existing_id,
            {
                "schedule": schedule_map[cadence],
                "name": name,
                "script": script,
                "no_agent": True,
                "enabled": True,
                "state": "scheduled",
            },
        )
    else:
        job = create_job(
            prompt="",
            schedule=schedule_map[cadence],
            name=name,
            script=script,
            no_agent=True,
            deliver="local",
        )
    if not job:
        raise CloudBackupError("cloud_backup_cron_job_failed")
    _write_config({"schedules": {resource_type: cadence}, "cron_job_ids": {resource_type: job["id"]}})
    print_fn(f"{resource_type.capitalize()} cloud backup scheduled: {cadence} ({job['id']})")
    return job


def cloud_backup_status(*, print_fn: Callable[[str], None] = print) -> dict[str, Any]:
    config = _merged_config()
    status = {
        "enabled": bool(config.get("enabled")),
        "endpoint": config.get("endpoint") or "",
        "bucket": config.get("bucket") or "",
        "prefix": config.get("prefix") or "",
        "memory_schedule": (config.get("schedules") or {}).get(RESOURCE_MEMORY) or "off",
        "soul_schedule": (config.get("schedules") or {}).get(RESOURCE_SOUL) or "off",
        "last_memory_backup_key": (config.get("last_backup_keys") or {}).get(RESOURCE_MEMORY) or "",
        "last_soul_backup_key": (config.get("last_backup_keys") or {}).get(RESOURCE_SOUL) or "",
    }
    for key, value in status.items():
        print_fn(f"{key}: {value or '-'}")
    return status


def print_cloud_backup_help(print_fn: Callable[[str], None] = print) -> None:
    print_fn("Usage:")
    print_fn("  /cloud-backup status")
    print_fn("  /cloud-backup config --endpoint URL --bucket NAME [--access-key KEY] [--secret-key SECRET] [--region REGION] [--prefix PREFIX]")
    print_fn("  /cloud-backup memory schedule [hourly|daily|weekly|monthly|off]")
    print_fn("  /cloud-backup memory backup")
    print_fn("  /cloud-backup memory history")
    print_fn("  /cloud-backup memory restore <object-key>")
    print_fn("  /cloud-backup soul schedule [hourly|daily|weekly|monthly|off]")
    print_fn("  /cloud-backup soul backup")
    print_fn("  /cloud-backup soul history")
    print_fn("  /cloud-backup soul restore <object-key>")


def _parse_options(args: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        item = args[i]
        if item.startswith("--"):
            key = item[2:].replace("-", "_")
            value = "true"
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                value = args[i + 1]
                i += 1
            out[key] = value
        i += 1
    return out


def _handle_resource_action(resource_type: str, args: list[str], print_fn: Callable[[str], None]) -> None:
    resource_type = _resource_type(resource_type)
    if not args:
        print_cloud_backup_help(print_fn)
        return
    action = args[0]
    if action == "schedule" and len(args) >= 2:
        schedule_cloud_backup(resource_type, args[1], print_fn=print_fn)
    elif action == "backup":
        run_cloud_backup_now(resource_type, print_fn=print_fn)
    elif action == "history":
        for item in list_cloud_backups(resource_type):
            print_fn(f"{item.get('key')}  {item.get('size')} bytes  {item.get('last_modified', '')}")
    elif action == "restore" and len(args) >= 2:
        restore_cloud_backup(resource_type, args[1], print_fn=print_fn)
    else:
        print_cloud_backup_help(print_fn)


def handle_cloud_backup_slash(command: str, *, print_fn: Callable[[str], None] = print) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        print_fn(f"Cloud backup command parse error: {exc}")
        return True
    args = parts[1:]
    if not args or args[0] in {"help", "-h", "--help"}:
        print_cloud_backup_help(print_fn)
        return True
    action = args[0]
    try:
        if action == "status":
            cloud_backup_status(print_fn=print_fn)
        elif action == "config":
            opts = _parse_options(args[1:])
            configure_cloud_backup(
                endpoint=opts.get("endpoint", ""),
                bucket=opts.get("bucket", ""),
                access_key=opts.get("access_key", ""),
                secret_key=opts.get("secret_key", ""),
                region=opts.get("region", "us-east-1"),
                root_prefix=opts.get("prefix", "profiles"),
                print_fn=print_fn,
            )
        elif action in SUPPORTED_RESOURCES:
            _handle_resource_action(action, args[1:], print_fn)
        else:
            print_cloud_backup_help(print_fn)
    except CloudBackupError as exc:
        print_fn(f"Cloud backup error: {exc}")
    return True


def cmd_cloud_backup(args: Any) -> None:
    action = getattr(args, "cloud_backup_action", None)
    try:
        if action == "status":
            cloud_backup_status()
        elif action == "config":
            configure_cloud_backup(
                endpoint=args.endpoint,
                bucket=args.bucket,
                access_key=getattr(args, "access_key", "") or "",
                secret_key=getattr(args, "secret_key", "") or "",
                region=getattr(args, "region", "us-east-1") or "us-east-1",
                root_prefix=getattr(args, "prefix", "profiles") or "profiles",
            )
        elif action in SUPPORTED_RESOURCES:
            resource_action = getattr(args, "resource_action", None)
            if resource_action == "schedule":
                schedule_cloud_backup(action, args.cadence)
            elif resource_action == "backup":
                run_cloud_backup_now(action)
            elif resource_action == "history":
                for item in list_cloud_backups(action):
                    print(f"{item.get('key')}  {item.get('size')} bytes  {item.get('last_modified', '')}")
            elif resource_action == "restore":
                restore_cloud_backup(action, args.object_key)
            else:
                print_cloud_backup_help()
        else:
            print_cloud_backup_help()
    except CloudBackupError as exc:
        raise SystemExit(f"Cloud backup error: {exc}") from exc


__all__ = [
    "CloudBackupError",
    "MinioObjectStore",
    "cloud_backup_status",
    "cmd_cloud_backup",
    "configure_cloud_backup",
    "default_cloud_backup_config",
    "handle_cloud_backup_slash",
    "list_cloud_backups",
    "restore_cloud_backup",
    "run_cloud_backup_now",
    "schedule_cloud_backup",
]
