# P3-06 加密 JSONL exporter

日期：2026-05-22
状态：Implemented
前置：`P3-05 Personal backup policy`

## 目标

本步骤把个人记忆备份从“policy contract”推进到“可生成加密备份包”。Exporter 从 personal memory 中筛选当前成员的数据，生成 `manifest.json`、`memories.jsonl`、`memory_events.jsonl` 和 `README.md` 的 zip 包，然后加密为 `backup.zip.enc` bytes 并生成外部 manifest/checksum。MinIO upload、object manifest 持久化和恢复预览仍由 P3-07/P3-08 承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/exporter.py` | `PersonalMemoryBackupExporter`、envelope encryption、passphrase KDF、decrypt helper。 |
| `tests/team_cloud/test_backup_exporter.py` | 覆盖 encrypted zip、manifest checksum、include flags、passphrase 模式。 |
| `teamDoc/GALog/2026-05-22-p3-06-encrypted-jsonl-exporter.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `backup_exporter` domain。 |

## Package Contract

解密后的 `backup.zip.enc` 是标准 zip：

```text
manifest.json
memories.jsonl
memory_events.jsonl
README.md
```

`memories.jsonl` 只包含 `scope=personal` 且 `subject_member_id=<member_id>` 的记忆。`include_deleted`、`include_archived` 和 `include_embeddings` 由 P3-05 policy 控制；默认不包含 deleted、archived 和 embedding 字段。`memory_events.jsonl` 只包含已导出 memory id 对应的事件。

外部 manifest 用于 P3-07 上传与对象索引：

| 字段 | 说明 |
| --- | --- |
| `object_type` | 固定为 `personal_backup`。 |
| `object_id` / `backup_id` | 本次备份 ID。 |
| `checksum_sha256` | 加密后 bytes 的 SHA-256。 |
| `plaintext_checksum_sha256` | 解密后 zip bytes 的 SHA-256。 |
| `size_bytes` | 加密后 bytes 大小。 |
| `item_count` / `event_count` | 导出的 memory/event 数量。 |
| `retention.retention_count` | 来源于 backup policy。 |

## Encryption

`org_managed` 模式：

- 每个备份生成 32-byte data key。
- 使用 data key 通过 AES-256-GCM 加密 zip payload。
- 使用组织 wrapping key 通过 AES-256-GCM 加密 data key。
- manifest 保存 `key_id`、`encrypted_data_key`、`data_key_nonce` 和 `payload_nonce`。

`user_passphrase` 模式：

- Team Cloud 不保存 passphrase。
- 使用 PBKDF2-HMAC-SHA256 派生 32-byte key。
- 使用 AES-256-GCM 加密 zip payload。
- manifest 只保存 KDF 参数和 `payload_nonce`，不保存可恢复 passphrase 的材料。

两种模式都使用 `hermes-team-cloud:personal-backup:<org>:<member>:<backup>` 作为 AES-GCM AAD。`decrypt_backup_package()` 会先校验 encrypted checksum，再解密，并校验 plaintext checksum。

## 非目标

- 不上传 MinIO，不生成 object key。
- 不写 `object_manifests` 或 `backup_jobs`。
- 不调度 due policy。
- 不实现 restore preview/execute。
- 不发送通知。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_backup_exporter.py
scripts/run_tests.sh tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/backup/exporter.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
