# P2-22 SessionDB 迁移工具

日期：2026-05-22
状态：Implemented
前置：`P2-18 云会话历史`

## 目标

本步骤提供本地 Hermes `SessionDB` 到 Team Cloud `cloud_sessions/messages` 的迁移工具。迁移必须 fail closed：只有显式映射到 Team Cloud member 的本地 `user_id` 才会导入，未映射身份只进入报告。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/sessiondb_import.py` | 读取 SQLite `sessions/messages` 并导入 cloud session repository。 |
| `scripts/team-cloud-import-sessiondb.py` | 命令行 dry-run/report 入口。 |
| `tests/team_cloud/test_sessiondb_import.py` | 映射导入、未映射身份、脚本 dry-run 测试。 |

## 行为

- 读取 `sessions`，按 `started_at` 和 session id 升序迁移。
- 使用 `identity_map` 将本地 `user_id` 映射为 Team Cloud `member_id`。
- 未映射身份不导入，输出 `identity_not_mapped` 报告项。
- 导入后的 cloud session 使用：
  - `org_id`、`team_id`、`project_id`：由迁移命令显式指定。
  - `owner_member_id`：映射后的 member id。
  - `source_platform`: `sessiondb:<local source>`。
- message content 统一写入 dict，保留 `text`、`local_message_id`、`tool_call_id`、`tool_name` 和 `tool_calls`。
- `--dry-run` 只生成报告，不创建 cloud session，便于迁移前审计 unmapped 身份。

## 非目标

- 不在本步骤连接生产 Team Cloud 数据库。
- 不自动创建成员或绑定外部身份。
- 不迁移 legacy memory provider 的内部状态；P5 migration guide 承接。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_sessiondb_import.py
venv/bin/ruff check team_cloud/sessiondb_import.py scripts/team-cloud-import-sessiondb.py tests/team_cloud/test_sessiondb_import.py
venv/bin/python -m py_compile team_cloud/sessiondb_import.py scripts/team-cloud-import-sessiondb.py tests/team_cloud/test_sessiondb_import.py
scripts/team-cloud-foundation-smoke.sh
```
