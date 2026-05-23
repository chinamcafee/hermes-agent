# 15. MinIO 个人记忆备份与恢复设计

## 1. 目标

成员能自行定时备份个人记忆，并在需要时下载、恢复或删除。备份不替代 PostgreSQL canonical memory，而是用户可控的数据可携带能力。

## 2. 备份包格式

```text
backup.zip.enc
  manifest.json
  memories.jsonl
  memory_events.jsonl
  README.md
```

`manifest.json`：

```json
{
  "version": 1,
  "org_id": "...",
  "member_id": "...",
  "backup_id": "...",
  "created_at": "...",
  "item_count": 120,
  "checksum_sha256": "...",
  "encryption": "org_managed",
  "embedding_included": false
}
```

## 3. 加密

默认：

- 服务端 envelope encryption。
- 每个备份一个 data key。
- data key 由 org key 加密。
- `encryption_key_id` 写入 object manifest。

可选：

- 用户 passphrase 加密。
- Team Cloud 不保存 passphrase。
- passphrase 丢失则无法恢复。

## 4. 调度

```text
backup_policies
  member_id
  cadence
  next_run_at
  retention_count
  enabled
```

worker：

- 按 `next_run_at` 扫描。
- 使用 advisory lock 防止重复运行。
- 失败重试 3 次。
- 超过阈值通知成员。

## 5. 恢复冲突策略

| 冲突 | 默认策略 |
| --- | --- |
| checksum 相同 | skip |
| normalized_content 相同但版本不同 | keep newer |
| 内容相似但来源不同 | review |
| 当前已删除 | ask user |
| sensitivity 更高 | preserve higher sensitivity |

恢复模式：

- `preview_only`
- `merge`
- `overwrite`
- `archive_current_then_restore`

## 6. 权限

- 成员拥有自己的 backup。
- Admin 默认不能读取 backup。
- break-glass 需要 Security Admin + Owner 双人审批。
- 删除 backup 只允许 owner 或合规删除流程。

## 7. 验收

- weekly backup 自动生成。
- 下载 URL 过期后不可用。
- checksum mismatch 阻止恢复。
- restore preview 能展示新增、跳过、冲突、覆盖数量。
- 删除成员时可选择 export then delete。
