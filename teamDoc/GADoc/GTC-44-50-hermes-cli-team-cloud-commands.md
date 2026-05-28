# GTC-44 到 GTC-50 Hermes CLI Team Cloud 一等命令实现记录

日期：2026-05-24

## 范围

本次把 Team Cloud 从“只有服务端和 Dashboard 管理面”补齐到本地 Hermes CLI 的一等能力：

- 当前 Hermes profile 可保存 Team Cloud URL 和默认团队上下文。
- 成员可用帐号密码登录 Team Cloud Go，获取 Redis-backed session token。
- CLI 可查询 Team Cloud 远端状态和当前成员会话。
- CLI/TUI/oneshot/background 创建 `AIAgent` 时自动注入 `team_context`。

## 代码产物

| 文件 | 变更 |
| --- | --- |
| `hermes_cli/team_cloud.py` | 新增 Team Cloud HTTP client、`connect/login/status/use/off/logout/token` 命令实现、`resolve_cli_team_context()`。 |
| `hermes_cli/config.py` | 新增 `team_cloud` 默认配置段和 `HERMES_TEAM_CLOUD_SESSION_TOKEN` env 识别。 |
| `hermes_cli/commands.py` | 注册 `/team` slash command。 |
| `hermes_cli/main.py` | 注册顶层 `hermes team` 子命令。 |
| `cli.py` | 交互式 CLI 创建 `AIAgent` 时注入 `team_context`，并分发 `/team`。 |
| `hermes_cli/oneshot.py` | oneshot 模式创建 `AIAgent` 时注入 `team_context`。 |
| `tui_gateway/server.py` | TUI 和 TUI background agent 创建 `AIAgent` 时注入 `team_context`，`/team` 后同步 live agent 状态。 |
| `team_cloud/internal/httpapi/server.go` | `/v1/auth/login` 支持 `client=cli`，新增 `/v1/auth/session`。 |

## 配置边界

非敏感配置写入当前 Hermes profile 的 `config.yaml`：

```yaml
team_cloud:
  enabled: true
  url: http://127.0.0.1:8780
  default_org_id: hermes-labs
  default_team_id: hermes-labs
  default_project_id: platform
  default_member_id: hermes-labs:alice
  token_env: HERMES_TEAM_CLOUD_SESSION_TOKEN
  circuit_breaker:
    mode: auto
    state: closed
```

敏感 token 写入当前 Hermes profile 的 `.env`：

```bash
HERMES_TEAM_CLOUD_SESSION_TOKEN=hcs_...
```

## 命令行为

```bash
hermes team connect http://127.0.0.1:8780
hermes team login --org hermes-labs --user alice --project platform
hermes team status
hermes team use --org hermes-labs --project platform --member hermes-labs:alice
hermes team off
hermes team logout
```

交互式 CLI 中对应：

```text
/team connect http://127.0.0.1:8780
/team login hermes-labs alice hermes-labs platform
/team status
/team use hermes-labs hermes-labs platform hermes-labs:alice
/team breaker status
/team breaker open
/team breaker close
/team breaker auto
/team off
/team logout
```

## 安全模型

- Dashboard 默认登录仍只允许 `super_admin/admin`。
- CLI 登录请求显式传 `client=cli`，服务端允许 `super_admin/admin/user/member` 登录 CLI。
- CLI 不再使用部署级 service token。
- Team Cloud CLI provider 只访问团队记忆，个人记忆和本地人格由本地 Hermes profile 和 `/cloud-backup memory|soul` 管理。
- API 熔断默认自动启用，连续失败达到阈值会暂停 Team Cloud 调用，冷却后自动尝试恢复。
- `team_context` 只有在本地配置完整且 session token 存在时才传入 Agent；`team status` 会调用 `/v1/auth/session` 展示远端验证结果。

## 验证

- `venv/bin/python -m pytest -q tests/hermes_cli/test_team_cloud_cli.py`
- `cd team_cloud && go test ./internal/httpapi -run TestCLIAuthLoginAllowsUserMemberAndSessionIntrospection -count=1`
- `venv/bin/python -m py_compile hermes_cli/team_cloud.py cli.py hermes_cli/main.py hermes_cli/oneshot.py tui_gateway/server.py`
- `venv/bin/python -m pytest -q tests/run_agent/test_memory_provider_init.py tests/hermes_cli/test_team_cloud_cli.py`
- `cd team_cloud && go test ./internal/httpapi -count=1`
- `HERMES_HOME="$(mktemp -d)" venv/bin/python hermes_cli/main.py team --help`
- `HERMES_HOME="$(mktemp -d)" venv/bin/python hermes_cli/main.py team status`
