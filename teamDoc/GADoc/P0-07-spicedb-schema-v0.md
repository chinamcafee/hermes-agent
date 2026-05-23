# P0-07 SpiceDB schema v0

日期：2026-05-22
状态：Validated for P0 execution
前置：`P0-06 Casdoor OIDC 验证`

## 目标

产出覆盖 `organization`、`team`、`project`、`session`、`memory`、`document`、`tool`、`backup` 的 SpiceDB schema v0，并提供可重复执行的 validation fixture，作为 P1 schema CI 和 Team Cloud AuthzClient 的起点。

## 工件

| 工件 | 用途 |
| --- | --- |
| [schema-v0.zed](artifacts/spicedb/schema-v0.zed) | SpiceDB schema v0。 |
| [schema-v0-validation.yaml](artifacts/spicedb/schema-v0-validation.yaml) | zed validation relationships 和正反断言。 |

## 资源覆盖

| Resource | 关键关系 | 关键权限 |
| --- | --- | --- |
| `organization` | `owner`、`admin`、`security_admin`、`member`、`guest` | `view`、`manage`、`manage_members`、`read_audit`、`export`、`delete`、`break_glass_approve` |
| `team` | `parent`、`admin`、`curator`、`developer`、`member`、`guest`、`service_account` | `read`、`manage`、`run_agent`、`propose_memory`、`read_memory`、`write_memory`、`review_memory` |
| `project` | `parent`、`admin`、`developer`、`member`、`guest`、`service_account` | `read`、`write`、`manage`、`run_agent`、`manage_session` |
| `session` | `parent_project`、`owner`、`participant` | `read`、`run`、`delete`、`export` |
| `memory` | `owner`、`parent_team`、`parent_project`、`curator`、`approved_break_glass_reader` | `read_personal`、`write_personal`、`backup_personal`、`read_team`、`write_team`、`review`、`archive`、`delete_team`、`break_glass_read_personal` |
| `document` | `parent_project`、`parent_team`、`uploader` | `read`、`write`、`ingest`、`delete` |
| `tool` | `parent_org`、risk-specific executor relations、`approver` | `safe_execute`、`network_execute`、`file_read_execute`、`file_write_execute`、`terminal_execute`、`destructive_execute`、`approve` |
| `backup` | `parent_org`、`owner`、`operator`、`approved_break_glass_reader` | `create`、`read`、`restore`、`delete`、`manage`、`break_glass_read`、`audit_read` |

## 权限命名映射

API 层可以继续使用产品动作名，例如 `memory.personal.read`、`tool.terminal.execute`；AuthzClient 负责映射到 SpiceDB permission：

| 产品动作 | SpiceDB permission |
| --- | --- |
| `chat.run` | `project#run_agent` 或 `session#run` |
| `memory.personal.read` | `memory#read_personal` |
| `memory.team.read` | `memory#read_team` |
| `memory.team.review` | `memory#review` |
| `tool.terminal.execute` | `tool#terminal_execute` |
| `tool.safe.execute` | `tool#safe_execute` |
| `backup.read` | `backup#read` |
| `backup.restore` | `backup#restore` |
| `org.audit.read` | `organization#read_audit` |

SpiceDB permission 名使用下划线，避免 schema 中使用点号。

## 安全边界

1. 个人记忆只允许 `owner` 读取、写入、删除、备份和恢复；团队 curator 不能读取个人记忆。
2. 团队共享记忆通过 `team`/`project` 关系授权，发布、审核、归档和删除与 curator/admin/project manager 绑定。
3. 个人备份 `backup#read` 只给 owner；管理员默认不能读取个人备份。
4. Break-glass 只通过显式 `approved_break_glass_reader` 关系放行，双人审批和时效由 Team Cloud workflow + audit 强制。
5. 工具权限按风险分层，`terminal`、`file_write`、`destructive` 与安全读工具分开授权。
6. Service account 是独立 subject 类型，必须通过项目/团队关系或 `service_account#use` 进入权限图。

## 验证命令

```bash
docker run --rm \
  -v "$PWD/teamDoc/GADoc/artifacts/spicedb:/work" \
  -w /work \
  authzed/zed:v1.1.1 \
  validate --type yaml schema-v0-validation.yaml
```

验证覆盖：

- schema 语法。
- organization owner/admin/security admin 分权。
- service account 使用权。
- project/session run/read。
- personal memory 与 team shared memory 隔离。
- tool terminal/safe execution 分层。
- backup owner-only read 和 audit read。

## P1 影响

- `P1-09 SpiceDB client` 必须基于本文 permission 名封装 `check`、`bulk check`、`lookup resources`。
- `P1-10 SpiceDB schema CI` 必须运行上述 validation fixture。
- `P1-11 Relationship outbox` 必须覆盖本文所有 relation 写入。
- `P2-20 隔离测试套件` 必须延伸本文 personal/team_shared 和 backup deny case。
- `P3-02 TeamToolPolicyHook` 必须使用 `tool#*_execute` permission，而不是平台 allowlist。
