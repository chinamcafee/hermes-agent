# 15. MinIO 本地 memory/soul 云备份与恢复设计

## 1. 目标

成员能在 Hermes CLI 中自行定时备份个人记忆和本地人格，并在需要时列出历史或恢复。个人记忆和本地 `SOUL.md` 不进入 Team Cloud 云端 PostgreSQL，也不由 Dashboard 管理；备份目标是用户自己配置的 MinIO/S3-compatible 地址。

新主入口统一为 `/cloud-backup`。项目尚未上线部署，旧 `/memory-backup` 不保留兼容别名或迁移提示；后续实现必须直接删除旧入口，所有新文档、Desktop UI 和 release manual 均以 `/cloud-backup memory ...`、`/cloud-backup soul ...` 为准。

## 2. 备份包格式

```text
memory: <timestamp>-personal-memory.json
soul:   <timestamp>-local-soul.json
```

Memory JSON 根对象：

```json
{
  "format": "hermes-cloud-backup-memory-v1",
  "resource_type": "memory",
  "created_at": "...",
  "files": [
    {
      "path": "MEMORY.md",
      "content": "..."
    }
  ]
}
```

Soul JSON 根对象：

```json
{
  "format": "hermes-cloud-backup-soul-v1",
  "resource_type": "soul",
  "created_at": "...",
  "path": "SOUL.md",
  "content_base64": "...",
  "checksum_sha256": "..."
}
```

## 3. 加密

当前 CLI GA 版本使用用户自有对象存储的访问控制和传输层 TLS 保护备份对象。需要静态加密时，应使用 MinIO/S3 bucket-side encryption 或后续 CLI 客户端加密增强；Team Cloud 不保存成员个人备份、本地人格备份和 passphrase。

## 4. 调度

```text
cloud_backup:
  enabled
  endpoint
  bucket
  region
  root_prefix
  access_key_env
  secret_key_env
  resources:
    memory:
      prefix
      cadence
    soul:
      prefix
      cadence
```

worker：

- `/cloud-backup memory schedule hourly|daily|weekly|monthly|off` 创建或关闭个人记忆 cron no-agent job。
- `/cloud-backup soul schedule hourly|daily|weekly|monthly|off` 创建或关闭本地人格 cron no-agent job。
- cron job 分别执行 `hermes cloud-backup memory backup` 和 `hermes cloud-backup soul backup`。
- `/cloud-backup memory backup`、`/cloud-backup soul backup` 可随时手动触发。

对象 key 必须按 resource type 分目录：

```text
<root_prefix>/profiles/<profile_id>/memory/YYYY/MM/YYYYMMDDTHHMMSSZ-personal-memory.json
<root_prefix>/profiles/<profile_id>/soul/YYYY/MM/YYYYMMDDTHHMMSSZ-local-soul.json
```

## 5. 恢复冲突策略

| 冲突 | 默认策略 |
| --- | --- |
| 目标 profile 已有同名文件 | 覆盖前提示用户确认目标 profile |
| 备份格式不匹配 | 拒绝恢复 |
| resource type 不匹配 | 拒绝恢复，防止 memory 和 soul 交叉覆盖 |
| 对象 key 不存在 | 显示 object_not_found |

恢复模式：

- memory 主路径为整包恢复到当前 profile 的 `memories/` 目录。
- soul 主路径为恢复到当前 profile 的 `SOUL.md`。

## 6. 权限

- 成员拥有自己配置的对象存储凭据。
- Team Cloud 管理员不能通过 Dashboard 读取成员个人记忆备份或本地人格备份。
- 备份对象删除由用户在自己的 MinIO/S3 bucket 生命周期或对象管理工具中完成。

## 7. 验收

- `/cloud-backup config` 能写入 endpoint、bucket、region、root prefix 和 access/secret env key。
- `/cloud-backup memory schedule weekly` 能创建个人记忆 Hermes cron no-agent job。
- `/cloud-backup soul schedule weekly` 能创建本地人格 Hermes cron no-agent job。
- `/cloud-backup memory backup` 能上传当前 profile `memories/` 文件。
- `/cloud-backup soul backup` 能上传当前 profile `SOUL.md`。
- `/cloud-backup memory history` 和 `/cloud-backup soul history` 只列各自 prefix 下备份。
- `/cloud-backup memory restore <key>` 和 `/cloud-backup soul restore <key>` 能恢复到当前 profile，并拒绝 resource type 不匹配的备份。
