# 04. Team Cloud Go 团队父人格 API、Dashboard 和备份计划

日期：2026-05-24

## 数据库规划

新增表：

```sql
create table tcg_team_souls (
  id text primary key,
  org_id text not null references tcg_organizations(id) on delete cascade,
  team_id text not null default '',
  status text not null default 'active' check (status in ('active', 'archived')),
  content text not null default '',
  version integer not null default 1 check (version > 0),
  checksum_sha256 text not null default '',
  updated_by_member_id text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, team_id, status) where status = 'active'
);
```

备份可以复用并扩展 `tcg_backup_policies`、`tcg_backup_jobs`：

- 增加 `resource_type`，取值 `team_memory`、`team_soul`。
- `member_id='__team_soul__'` 可作为兼容哨兵值，但更推荐使用显式 `resource_type`。
- `object_key` 区分 `team-memory` 和 `team-soul`。

如果为了避免破坏既有实现，也可以新增 `tcg_cloud_backup_policies` 和 `tcg_cloud_backup_jobs`，将 memory/soul 统一建模。由于当前未上线生产，允许破坏性 schema 收敛。

## API 规划

Dashboard 管理 API：

```http
GET  /v1/team-soul?org_id=<org>
PUT  /v1/team-soul
GET  /v1/team-soul/history?org_id=<org>
POST /v1/team-soul/restore-version
```

CLI/Runtime 只读 API：

```http
GET /v1/runtime/team-soul?org_id=<org>&team_id=<team>
```

备份 API：

```http
GET  /v1/team-soul-backup-policy?org_id=<org>
PUT  /v1/team-soul-backup-policy
GET  /v1/backups/team-soul?org_id=<org>
POST /v1/backups/team-soul/run
POST /v1/backups/team-soul/{backup_id}/restore-preview
POST /v1/backups/team-soul/{backup_id}/restore-execute
```

## Dashboard 页面

新增一级 Tab：`人格治理`。

页面结构：

- 团队父人格当前状态：版本、更新时间、编辑者、checksum。
- Markdown 编辑器：只允许 `super_admin/admin` 保存。
- 只读预览：展示父人格如何覆盖本地人格。
- 版本历史：按版本查看差异和恢复。
- 备份管理：查看策略、立即备份、历史、恢复预览、执行恢复。

现有 `备份管理` Tab 需要拆分资源类型：

- 团队记忆备份。
- 团队父人格备份。

两种备份共享对象存储配置，但策略、历史、恢复按钮分开展示。

## 权限和审计

权限：

- `read_team_soul`：所有 active 成员。
- `write_team_soul`：`super_admin/admin`。
- `backup_team_soul`：`super_admin/admin`。
- `restore_team_soul`：`super_admin/admin`。

审计：

- `team_soul.read`
- `team_soul.update`
- `team_soul.version_restore`
- `team_soul.backup.run`
- `team_soul.restore.preview`
- `team_soul.restore.execute`

## 备份对象格式

对象 key：

```text
org/<org_id>/team-soul/YYYY/MM/<backup_id>.json.enc
```

明文 JSON 结构（加密前）：

```json
{
  "format": "hermes-team-soul-backup-v1",
  "resource_type": "team_soul",
  "org_id": "hermes-labs",
  "team_id": "hermes-labs",
  "soul": {
    "id": "soul-hermes-labs",
    "content": "...",
    "version": 4,
    "checksum_sha256": "..."
  }
}
```

恢复规则：

- 以 `org_id + team_id` 为唯一键 insert-or-update active soul。
- 恢复时版本号递增，不回退数据库自增语义。
- 重复恢复同一个备份不会创建多条 active soul。
- 恢复必须写审计事件。

## Runtime 返回格式

```json
{
  "org_id": "hermes-labs",
  "team_id": "hermes-labs",
  "status": "active",
  "content": "团队统一人格内容",
  "version": 4,
  "checksum_sha256": "..."
}
```

Hermes Agent 不需要知道 Dashboard 内部历史，只使用 active 内容、version 和 checksum。
