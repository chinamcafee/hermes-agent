# 13. Casdoor 与 SpiceDB 集成细节

## 1. 集成原则

- Casdoor 是身份来源，不是资源授权引擎。
- SpiceDB 是资源授权来源，不保存登录凭据。
- Team Cloud 是同步和编排层，负责把身份生命周期转换成授权关系。

## 2. Token Claims

Team API 至少需要：

```text
iss
sub
aud
exp
iat
email
name
groups
roles
organization
```

校验规则：

- `iss` 必须等于配置的 Casdoor issuer。
- `aud` 必须包含 Team Cloud client id。
- `exp/nbf` 必须有效。
- `sub` 必须能映射到 `team_cloud_user`。
- `member.status` 必须为 active。

## 3. 同步策略

同步来源：

- 登录时 lazy upsert。
- Casdoor webhook。
- SCIM provisioning。
- 定时 reconcile。

同步输出：

```text
team_cloud_user
member
membership
spicedb_outbox
audit_events
```

禁用用户：

```text
Casdoor user disabled
  -> Team Cloud member suspended
  -> revoke active sessions
  -> revoke PAT if policy enabled
  -> delete or caveat SpiceDB relationships
  -> audit
```

## 4. Relationship Mapping

| Team Cloud 事件 | SpiceDB relationship |
| --- | --- |
| 创建组织 owner | `organization:org#owner@user:user` |
| 邀请成员 | 暂不写 member，待 accepted |
| 成员接受邀请 | `organization:org#member@user:user` |
| 设置 Admin | `organization:org#admin@user:user` |
| 加入 team | `team:team#member@user:user` |
| 设置 curator | `team:team#curator@user:user` |
| 加入 project | `project:project#member@user:user` |
| 创建 personal memory | `memory:mem#owner@user:user` |
| 发布 team memory | `memory:mem#parent_team@team:team` |
| 创建 backup | `backup:backup#owner@user:user` |

## 5. Permission Check Pattern

```python
decision = authz.check(
    subject=f"user:{member_id}",
    resource=f"memory:{memory_id}",
    permission="read_personal",
    consistency="fully_consistent_for_sensitive"
)
```

一致性选择：

- 敏感读取、删除、权限变更：更强一致性。
- 普通列表、低风险读取：允许低延迟一致性。
- Outbox 未应用：相关资源 fail closed。

## 6. 权限解释

权限解释页面显示：

- actor。
- resource。
- permission。
- decision。
- 命中的关系路径。
- Casdoor identity 信息。
- 最近 relationship 变更。
- 相关 audit events。

## 7. CI

- SpiceDB schema format check。
- schema compile。
- permission test fixtures。
- migration compatibility。
- backward-compatible permission names。
- denied case 覆盖率。
