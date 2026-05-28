# GTC-88 Desktop Bridge profile scoping and team management endpoints

日期：2026-05-24 / 2026-05-25
状态：Implemented

## 背景

Hermes Desktop 的 Team Bridge、Soul Bridge 和 Cloud Backup IPC 会把当前 profile 作为 query 参数传给 Hermes Agent Bridge。此前 `/api/team/status`、`/api/soul/*`、`/api/cloud-backup/*` 端点接收该参数但未使用，导致多 profile 场景可能读写默认 `HERMES_HOME`。

## 实现

- `hermes_cli/web_server.py` 新增 `_call_with_profile_home()`，复用现有 profile 校验逻辑解析目标 profile，并通过 `hermes_constants.set_hermes_home_override()` 在单次调用内切换 `HERMES_HOME`。
- `/api/team/status`、`/api/soul/status`、`/api/soul/local`、`/api/soul/recompute`、`/api/cloud-backup/status`、`/api/cloud-backup/run`、`/api/cloud-backup/schedule` 均支持 `profile` query。
- 新增 `tests/hermes_cli/test_web_server_team_bridge_profiles.py`，覆盖 team、soul、cloud-backup 三类 Bridge endpoint 使用请求 profile。

## 2026-05-25 增量

为满足 Hermes Desktop 必须拥有和 Hermes CLI 完全一致的 `team` 一级入口能力，Hermes Agent Bridge 已补齐 Team 管理端点：

| Endpoint | CLI 等价能力 |
| --- | --- |
| `POST /api/team/connect` | `hermes team connect <url>` |
| `POST /api/team/login` | `hermes team login --org --user --password --team --project` |
| `POST /api/team/use` | `hermes team use --org --team --project --member` |
| `POST /api/team/off` | `hermes team off` |
| `POST /api/team/logout` | `hermes team logout` |
| `POST /api/team/token` | `hermes team token set <token>` |
| `GET /api/team/breaker` | `hermes team breaker status` |
| `POST /api/team/breaker` | `hermes team breaker open|close|auto` |

所有新增端点均使用 `_call_with_profile_home(profile, ...)`，确保 Desktop 传入当前 profile 后不会读写默认 profile。

`team_status()` 的结构化返回也做了语义校准：

- `remote`：Team Cloud URL，用于 Desktop 打开 `<remote>/dashboard/`。
- `remote_status`：Team Cloud 服务健康/初始化状态，例如 `ready`、`not_initialized`、`error:*`。

Desktop Renderer 不直接接触 Team Cloud Go 业务 API；Electron main process 只调用 Hermes Agent Bridge，Renderer 只通过 preload 暴露的受控方法发起操作。

## 验证

```bash
venv/bin/python -m pytest tests/hermes_cli/test_web_server_team_bridge_profiles.py tests/hermes_cli/test_team_cloud_cli.py -q
```

结果：`11 passed`。
