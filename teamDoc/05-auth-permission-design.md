# 05. Casdoor + SpiceDB 身份权限设计

本方案把身份认证和业务授权严格拆开：

- Casdoor 负责用户是谁、如何登录、是否通过 MFA、是否属于某个外部组织或组。
- SpiceDB 负责用户能对哪个 Team Cloud 资源执行什么动作。
- Team Cloud 负责把 Casdoor identity 映射为产品实体，并把产品关系同步到 SpiceDB。

## 1. 身份实体

```text
casdoor_user
  owner / organization
  id / name
  email
  displayName
  groups
  roles
  status

team_cloud_user
  id uuid
  casdoor_subject text unique
  primary_email text
  display_name text
  avatar_url text
  status text -- active | suspended | deleted

organization
  id uuid
  casdoor_org text unique
  slug text unique
  name text
  plan text
  status text
  created_at timestamptz

member
  id uuid
  org_id uuid
  user_id uuid
  status text -- invited | active | suspended | removed
  default_team_id uuid null
  joined_at timestamptz
  removed_at timestamptz null

team
  id uuid
  org_id uuid
  slug text
  name text
  visibility text -- private | org_visible

project
  id uuid
  org_id uuid
  team_id uuid
  slug text
  name text
  status text
```

## 2. Casdoor 登录与同步

### Web 登录

```text
1. Web Console -> Casdoor authorize。
2. Casdoor 完成登录、MFA、外部 IdP federation。
3. Web Console 拿到 authorization code。
4. Web Console/Team API 换取 id_token/access_token。
5. Team API 校验 issuer、audience、signature、exp、nonce。
6. Team API upsert user/member。
7. Team API 写入 login audit event。
```

### API token

Team Cloud 不直接使用 Casdoor 用户密码。API 调用有两类：

- Human PAT：由已登录用户创建，绑定 `member_id`，可设置 scope、过期时间、IP allowlist。
- Service Account Token：绑定 `service_account_id`，必须在 SpiceDB 中授予资源关系。

API token 表只保存 hash：

```text
api_tokens (
  id uuid primary key,
  org_id uuid not null,
  owner_member_id uuid null,
  service_account_id uuid null,
  token_hash bytea not null,
  scopes text[] not null,
  expires_at timestamptz,
  last_used_at timestamptz,
  revoked_at timestamptz
)
```

### Gateway 平台绑定

```text
1. 成员在 Web Console 生成一次性绑定码。
2. 成员在 Telegram/Slack/Discord/Feishu/WeCom 私聊 bot 输入绑定码。
3. Gateway 调 Team API 完成 bind。
4. Team API 写 external_identity。
5. Gateway 后续消息通过 platform + external_user_id 映射 member。
```

```text
external_identities (
  id uuid primary key,
  org_id uuid not null,
  member_id uuid not null,
  platform text not null,
  external_user_id text not null,
  external_team_id text null,
  external_channel_id text null,
  metadata jsonb not null default '{}',
  status text not null,
  unique(platform, external_user_id, external_team_id)
)
```

## 3. 默认产品角色

| 角色 | 默认权限 |
| --- | --- |
| Owner | 组织删除、账单、所有管理、break-glass 发起 |
| Admin | 成员、团队、项目、connector、服务账号管理 |
| Security Admin | 审计、权限解释、高危工具策略、break-glass 审批 |
| Memory Curator | 团队共享记忆审核、提升、归档、恢复 |
| Developer | 使用开发工具、项目级文档和代码相关工具 |
| Member | 聊天、读团队共享记忆、管理自己的个人记忆 |
| Guest | 限定项目/频道访问，只能使用安全读工具 |
| Service Account | 自动化/API 调用，按 relationship 和 token scope 授权 |

角色只是授权输入，最终允许与否由 SpiceDB permission 计算。

## 4. 权限动作清单

```text
org.admin
org.billing.manage
org.audit.read
org.export
org.delete

team.read
team.manage
team.member.manage

project.read
project.write
project.manage

chat.run
chat.read
chat.delete

session.read
session.read_team
session.delete
session.export

memory.personal.read
memory.personal.write
memory.personal.delete
memory.personal.backup
memory.personal.restore
memory.personal.break_glass_read

memory.team.read
memory.team.propose
memory.team.write
memory.team.review
memory.team.archive
memory.team.delete

document.read
document.write
document.ingest
document.delete

tool.safe.execute
tool.network.execute
tool.file_read.execute
tool.file_write.execute
tool.terminal.execute
tool.destructive.execute
tool.approve

connector.read
connector.manage
api_token.manage
service_account.manage
backup.read
backup.restore
```

## 5. SpiceDB Schema 草案

```zed
definition user {}

definition service_account {
  relation owner: user
}

definition organization {
  relation owner: user
  relation admin: user
  relation security_admin: user
  relation member: user
  relation guest: user

  permission manage = owner + admin
  permission read_audit = owner + admin + security_admin
  permission export = owner + admin
  permission delete = owner
}

definition team {
  relation parent: organization
  relation admin: user
  relation curator: user
  relation member: user
  relation guest: user

  permission manage = admin + parent->manage
  permission read = member + guest + admin + parent->manage
  permission write_memory = curator + admin + parent->manage
  permission review_memory = curator + admin + parent->manage
}

definition project {
  relation parent: team
  relation admin: user
  relation developer: user
  relation member: user
  relation guest: user

  permission manage = admin + parent->manage
  permission read = member + guest + developer + admin + parent->read
  permission run_agent = member + developer + admin + parent->read
  permission write = developer + admin + parent->manage
}

definition session {
  relation parent_project: project
  relation owner: user
  relation participant: user

  permission read = owner + participant + parent_project->read
  permission delete = owner + parent_project->manage
  permission export = owner + parent_project->manage
}

definition memory {
  relation owner: user
  relation parent_team: team
  relation parent_project: project
  relation curator: user

  permission read_personal = owner
  permission write_personal = owner
  permission delete_personal = owner
  permission read_team = parent_team->read + parent_project->read
  permission write_team = curator + parent_team->write_memory + parent_project->manage
  permission review = curator + parent_team->review_memory + parent_project->manage
}

definition document {
  relation parent_project: project
  relation uploader: user

  permission read = uploader + parent_project->read
  permission write = uploader + parent_project->write
  permission delete = uploader + parent_project->manage
}

definition tool {
  relation allowed_user: user
  relation allowed_team: team
  relation allowed_project: project
  relation approver: user

  permission execute = allowed_user + allowed_team->read + allowed_project->run_agent
  permission approve = approver
}

definition backup {
  relation owner: user
  relation parent_org: organization
  relation break_glass_approver: user

  permission read = owner
  permission restore = owner
  permission break_glass_read = break_glass_approver & parent_org->read_audit
}
```

## 6. Relationship 写入规则

成员加入组织：

```text
organization:{org_id}#member@user:{user_id}
```

成员成为团队管理员：

```text
team:{team_id}#admin@user:{user_id}
team:{team_id}#parent@organization:{org_id}
```

个人记忆创建：

```text
memory:{memory_id}#owner@user:{user_id}
```

团队记忆发布：

```text
memory:{memory_id}#parent_team@team:{team_id}
memory:{memory_id}#curator@user:{curator_id}
```

项目工具授权：

```text
tool:terminal#allowed_project@project:{project_id}
tool:terminal#approver@user:{security_admin_id}
```

## 7. Outbox 一致性

PostgreSQL 事务内写：

```text
business row
spicedb_outbox(
  id,
  org_id,
  aggregate_type,
  aggregate_id,
  operation,
  relationship,
  idempotency_key,
  status = pending
)
```

worker 处理：

```text
1. SELECT pending FOR UPDATE SKIP LOCKED。
2. 调 SpiceDB WriteRelationships。
3. 成功标记 applied。
4. 失败指数退避。
5. 超过阈值进入 dead letter，相关资源 fail closed。
```

## 8. 工具权限策略

工具风险分级：

| 等级 | 示例 | 默认策略 |
| --- | --- | --- |
| safe_read | search/read/session lookup | Member 可用 |
| network | web/browser/remote MCP | 项目授权后可用 |
| file_read | read_file/search_files | Developer 或项目授权 |
| file_write | patch/write_file | Developer + workspace allowlist |
| terminal | shell/docker/git | Developer + approval |
| destructive | rm/reset/cloud mutation | Security Admin approval |
| secret | env/auth/key 操作 | 默认禁用，break-glass |

执行流程：

```text
pre_tool_call
  -> classify tool risk
  -> SpiceDB check tool:{tool_name} execute
  -> path/workspace policy check
  -> if high risk, require Hermes approval
  -> write audit event
```

## 9. Break-glass

管理员读取成员个人记忆或个人备份必须使用 break-glass：

- 需要 Owner/Security Admin 双人审批。
- 必须选择原因、工单号、时间窗口。
- 只生成短期读取授权 relationship。
- 所有读取写入 `audit_events`，并通知被访问成员，除非法律/安全策略明确延迟通知。

## 10. GA 验收

- Casdoor token 校验覆盖 issuer/audience/signature/expiry/key rotation。
- SpiceDB schema 有 CI 校验和回归测试。
- 任意 `memory.personal.*` 权限均不能跨 member 成功。
- 任意跨 org 资源访问均返回 deny，并产生 audit。
- 管理台每个页面都有 permission gate。
- Gateway 绑定、解绑、转移和禁用流程都有审计。
- Outbox 延迟、失败、dead letter 有告警。
