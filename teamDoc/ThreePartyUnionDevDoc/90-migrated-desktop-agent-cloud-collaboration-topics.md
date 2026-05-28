# 90. 迁移文档：Desktop / Agent / Team Cloud Go 联动专题

日期：2026-05-24

来源：原 `hermes-desktop/teamDoc/05-agent-cloud-collaboration-topics.md`。

本文件已从 Desktop 文档目录迁移到 Agent 文档目录。原因是内容主要描述 `hermes-agent` CLI/API Server 与 `team_cloud` 需要补齐的契约，属于 Agent/Team Cloud Go 权威规划，而不是 Desktop 自身 UI 方案。

## 总体边界

Desktop 不直连 Team Cloud Go 业务 API。Desktop 只调用 Hermes Agent Runtime Bridge；Team Cloud Go 是 Hermes Agent Runtime Bridge 的上游团队服务。

新增团队父人格和 `/cloud-backup` 后，Bridge contract 需要覆盖：

- Team Cloud 连接、登录、上下文和熔断。
- Team parent soul 同步和 effective soul 展示。
- memory/soul 两类本地个人资源云备份。
- API Server remote HTTP 能力探测。

## 专题 A：Hermes Agent Team Bridge 契约

`hermes-agent` 提供 Desktop-friendly bridge contract：

```bash
hermes team status --json
hermes team connect <url> --json
hermes team login --org <org> --user <user> --password <password> --json
hermes team use --org <org> --team <team> --project <project> --json
hermes team off --json
hermes team logout --json
hermes team breaker status|open|close|auto --json
hermes soul status --json
hermes soul show team|local|effective --json
hermes cloud-backup status --json
hermes cloud-backup memory backup|history|restore --json
hermes cloud-backup soul backup|history|restore --json
```

Hermes API Server 增加等价 bridge capability，服务 remote HTTP 模式。Desktop 按连接模式选择：

- local：调用本机 CLI。
- ssh：调用远端 CLI。
- remote HTTP：调用远端 Hermes API Server bridge endpoint。

## 专题 B：API Server 支持普通成员 Team session

API Server 增加普通成员 token 模式：

```http
X-Hermes-Team-Session-Token: hcs_...
```

处理流程：

1. API Server 从当前 Hermes profile 或 bridge 请求上下文读取 `team_cloud.url`。
2. 收到 `X-Hermes-Team-Session-Token` 后，调用 Team Cloud Go `GET /v1/auth/session`。
3. Team Cloud Go 返回 `org_id`、`member_id`、`role`、默认 `team_id` 和 `project_id`。
4. API Server 构造 `team_context`。
5. `AIAgent(team_context=...)` 启动后自动挂载 TeamMemoryProvider，并解析 team parent soul。

安全要求：

- 不信任 Desktop 传入的 org/team/member 字段。
- org/team/member 只能由 Team Cloud session 验证结果派生。
- token 失效时返回 401，并让 Desktop 触发 Team API 熔断或要求重新登录。
- Desktop 不能使用服务级 `X-Hermes-Team-Cloud-Token`。

## 专题 C：API Server capabilities

`GET /v1/capabilities` 增加字段：

```json
{
  "team_bridge": {
    "enabled": true,
    "cli_json_contract": true,
    "api_bridge_contract": true,
    "remote_http_supported": true,
    "team_parent_soul": true,
    "effective_soul": true
  },
  "cloud_backup": {
    "resources": ["memory", "soul"],
    "shared_minio_config": true
  }
}
```

Desktop 据此决定：

- fast path 是否可进入团队模式。
- remote HTTP 模式是否可用 Team。
- 是否可展示 team parent soul 和 effective soul。
- 是否可展示 memory/soul 云备份 UI。
- 是否提示用户升级远端 Hermes Agent。

## 专题 D：Team Cloud Go session context 增强

`GET /v1/auth/session` 推荐返回：

```json
{
  "member_id": "hermes-labs:alice",
  "org_id": "hermes-labs",
  "team_id": "hermes-labs",
  "project_id": "",
  "role": "user",
  "display_name": "Alice",
  "email": "alice@example.com",
  "team_parent_soul_version": 4,
  "team_parent_soul_checksum": "sha256:..."
}
```

这样 API Server 和 Desktop 不需要信任客户端传入默认 team/project，也能判断父人格缓存是否过期。

## 专题 E：团队记忆和团队父人格事件

API Server SSE 推荐增加 structured event：

```text
event: hermes.team.memory.extracted
data: {"id":"mem_...","content":"...","source_member_id":"..."}

event: hermes.team.soul.changed
data: {"version":4,"checksum_sha256":"sha256:..."}
```

Desktop 可用于刷新 Team badge、Soul 页面和当前会话状态。

## 专题 F：Session metadata

`hermes-agent` session 存储增加 team metadata：

```json
{
  "team_context": {
    "org_id": "hermes-labs",
    "team_id": "hermes-labs",
    "project_id": "",
    "member_id": "hermes-labs:alice"
  },
  "effective_soul": {
    "team_parent_version": 4,
    "team_parent_checksum": "sha256:..."
  }
}
```

恢复团队会话时，如果当前 team context 或 team parent soul 版本不同，Desktop 应提示用户确认。

## 专题 G：远程 HTTP 模式最小可用路径

远程 HTTP 模式下，Desktop 不能修改远端文件，也不能安全运行远端 CLI。要支持团队模式，远端 Hermes API Server 必须独立完成：

- 暴露 team bridge capability。
- 接收或解析用户级 Team session。
- 验证 Team Cloud session。
- 派生 `team_context`。
- 同步 team parent soul，并在本地人格保存后调用当前模型供应商生成 effective soul。
- 启用 TeamMemoryProvider。
- 暴露 `/cloud-backup` memory/soul capability。

否则 Desktop 在 remote HTTP 模式下只能展示 Team Cloud Dashboard 链接和升级提示。
