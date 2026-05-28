# 03. Hermes Agent 运行时、CLI 和云备份改造计划

日期：2026-05-24

## 当前入口

- 本地人格：profile 下的 `SOUL.md`，由 `agent.prompt_builder.load_soul_md()` 读取。
- 预设人格：`/personality <name>` 写入 `agent.system_prompt`，作为 ephemeral system prompt。
- 团队上下文：`hermes_cli/team_cloud.py` 解析 Team Cloud 登录状态并构造 `team_context`。
- 本地个人资源备份实现：`hermes_cli/cloud_backup.py` 提供 `/cloud-backup memory|soul ...`，分别备份 `memories/` 与 `SOUL.md`。旧 `/memory-backup` 已退役，不保留兼容入口。

## 新增模块落点

| 模块 | 职责 |
| --- | --- |
| `hermes_cli/team_soul.py` | Team Cloud team parent soul client、读取 local soul、生成 effective soul、调用 LLM merge、状态格式化。 |
| `agent/system_prompt.py` | team mode 下把 effective soul 注入系统提示，local mode 继续读取 `SOUL.md`。 |
| `hermes_cli/cloud_backup.py` | 通用 MinIO/S3 配置和 `memory`、`soul` 两类备份命令。 |
| `tests/hermes_cli/test_cloud_backup_cli.py` | 覆盖 memory/soul 备份、路径隔离、恢复和 schedule。 |
| `tests/run_agent/test_team_soul_runtime.py` | 覆盖 team mode prompt 合成和 local mode 回退。 |

## CLI 人格入口

新增一级命令 `/soul`，并提供非交互子命令 `hermes soul ...`。

team mode：

```bash
/soul status
/soul show team
/soul show local
/soul show effective
/soul merge
hermes soul status --json
hermes soul show effective --json
hermes soul merge --json
```

local mode：

```bash
/soul status
/soul show local
```

local mode 下不显示 team/effective 三段结构，只显示本地人格。`/personality` 继续保留为“预设人格选择”入口，但 `/soul` 是查看和解释人格来源的一等入口。`/soul merge` 仅在 team mode 下可用，用于模型供应商恢复后手动重新合并；local mode 下返回 `merge_not_required`。

## 运行时注入

`agent.system_prompt.build_system_prompt_parts()` 当前直接调用 `load_soul_md()`。改造后建议：

1. `AIAgent` 初始化时保留 `team_context`。
2. `build_system_prompt_parts()` 调用 `resolve_effective_soul(agent.team_context, local_soul)`.
3. `resolve_effective_soul()` 返回：

```json
{
  "mode": "local|team",
  "team_parent_available": true,
  "team_parent_version": 3,
  "team_parent_checksum": "sha256:...",
  "local_path": "~/.hermes/SOUL.md",
  "local_checksum": "sha256:...",
  "merge_status": "merged|failed|not_required",
  "merge_source": "llm|safe_fallback|local_only|cache",
  "provider": "openai",
  "model": "gpt-4.1",
  "error_code": "",
  "effective_content": "..."
}
```

4. system prompt stable tier 使用 `effective_content`，并避免 `build_context_files_prompt()` 再重复注入本地 `SOUL.md`。

## 本地人格保存和 LLM 合并

CLI 和 Desktop 均不能保存团队父人格；团队父人格只能由 Team Cloud Go Dashboard 管理。但在 team mode 下，任何本地人格变更都必须触发 Hermes Agent 的合并流程：

```text
save local SOUL.md
  -> resolve team_context
  -> fetch/cache Team Parent Soul
  -> call configured model provider
  -> write effective soul cache
  -> return merge_status to CLI/Desktop
```

触发点：

- CLI 编辑、重置或保存 `SOUL.md`。
- Desktop local/ssh 模式保存 `SOUL.md`。
- `/cloud-backup soul restore <object-key>` 恢复本地人格。

大模型调用规则：

- 使用当前 Hermes profile 已配置的 provider/model/base_url/api_key。
- 不在 Team Cloud Go 中新增模型供应商配置。
- 不把合并任务交给 Team Cloud Go；合并只发生在 Hermes Agent 本地或远端 Agent runtime 所在环境。
- 合并 prompt 必须明确：团队父人格优先，本地人格只能补充不冲突偏好。

失败策略：

- 未配置 provider、缺少 API key、供应商不可达、超时、模型拒绝或返回空内容时，返回 `merge_status=failed`。
- 本地 `SOUL.md` 保存仍成功，不回滚。
- CLI 显示：`本地人格已保存，但团队父人格合并失败：<reason>`。
- Desktop 显示非阻塞错误提示，并在 Effective Soul 面板标记“合并失败，已使用安全降级组合”。
- 运行时使用安全降级组合，避免 team mode 会话丢失团队父人格。
- 用户修复模型配置后，可执行 `/soul merge` 或重新保存本地人格触发重试。

## `/cloud-backup` 命令设计

新增配置：

```yaml
cloud_backup:
  enabled: false
  endpoint: ""
  bucket: "hermes-personal-cloud-backups"
  region: "us-east-1"
  root_prefix: "hermes"
  access_key_env: HERMES_CLOUD_BACKUP_MINIO_ACCESS_KEY
  secret_key_env: HERMES_CLOUD_BACKUP_MINIO_SECRET_KEY
  resources:
    memory:
      prefix: "personal-memory"
      schedule: "off"
      cron_job_id: ""
      last_backup_key: ""
    soul:
      prefix: "personal-soul"
      schedule: "off"
      cron_job_id: ""
      last_backup_key: ""
```

命令：

```bash
/cloud-backup status
/cloud-backup config --endpoint URL --bucket NAME [--access-key KEY] [--secret-key SECRET] [--region REGION] [--root-prefix PREFIX]
/cloud-backup memory schedule hourly|daily|weekly|monthly|off
/cloud-backup memory backup
/cloud-backup memory history
/cloud-backup memory restore <object-key>
/cloud-backup soul schedule hourly|daily|weekly|monthly|off
/cloud-backup soul backup
/cloud-backup soul history
/cloud-backup soul restore <object-key>
```

非交互：

```bash
hermes cloud-backup memory backup --json
hermes cloud-backup soul backup --json
```

## 对象路径

同一 bucket 下必须分 resource type：

```text
<root_prefix>/profiles/<profile_id>/memory/YYYY/MM/YYYYMMDDTHHMMSSZ-personal-memory.json
<root_prefix>/profiles/<profile_id>/soul/YYYY/MM/YYYYMMDDTHHMMSSZ-local-soul.json
```

`history` 默认只列对应 resource type 的 prefix。`restore` 必须校验备份格式和目标 resource type，防止用 memory 备份恢复 soul 或反向恢复。

## 备份格式

Memory：

```json
{
  "format": "hermes-cloud-backup-memory-v1",
  "resource_type": "memory",
  "profile": "default",
  "files": []
}
```

Soul：

```json
{
  "format": "hermes-cloud-backup-soul-v1",
  "resource_type": "soul",
  "profile": "default",
  "path": "SOUL.md",
  "content_base64": "...",
  "checksum_sha256": "..."
}
```

## `/memory-backup` 破坏性删除

项目尚未上线部署，不做兼容别名和迁移提示。当前实现已直接删除：

- `hermes_cli/memory_backup.py` 作为对外入口；可抽取可复用 S3 helper，但不能继续暴露 `memory-backup` 命令名。
- `hermes_cli/commands.py` 中的 `/memory-backup` slash command 注册。
- `cli.py` 中的 `/memory-backup` dispatch 分支和帮助文本。
- `hermes_cli/main.py` 中的 `hermes memory-backup` 顶层子命令。
- `hermes_cli/config.py` 和 `cli.py` 默认配置中的 `memory_backup` 配置段。
- `tests/hermes_cli/test_memory_backup_cli.py`，改为 `tests/hermes_cli/test_cloud_backup_cli.py`。
- 所有 release manual、Desktop UI、CLI help、TUI help 中的 `memory-backup` 文案。

新增实现只接受 `cloud_backup` 配置键和 `/cloud-backup`、`hermes cloud-backup` 命令。

## Cron 任务

每个 resource type 独立 cron：

- `Hermes personal memory cloud backup`，脚本 `cloud-backup-memory-cron.py`。
- `Hermes local soul cloud backup`，脚本 `cloud-backup-soul-cron.py`。

两者共享 MinIO/S3 配置，但 schedule 和 last backup key 独立。
