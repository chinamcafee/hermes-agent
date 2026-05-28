# 05. 三方契约、路线图和测试验收

日期：2026-05-24

## 契约总览

```text
Team Cloud Go
  -> 提供 active team parent soul、team soul backup API
Hermes Agent
  -> 同步 team parent soul、合成 effective soul、提供 /soul 和 /cloud-backup JSON CLI
Hermes Desktop
  -> 调用 Hermes Agent Bridge，展示三段人格和云备份 UI
```

## CLI JSON 契约

```bash
hermes soul status --json
hermes soul show team --json
hermes soul show local --json
hermes soul show effective --json
hermes soul merge --json
hermes cloud-backup status --json
hermes cloud-backup config ... --json
hermes cloud-backup memory backup --json
hermes cloud-backup memory history --json
hermes cloud-backup memory restore <key> --json
hermes cloud-backup soul backup --json
hermes cloud-backup soul history --json
hermes cloud-backup soul restore <key> --json
```

`hermes soul status --json` 示例：

```json
{
  "mode": "team",
  "team_parent": {
    "available": true,
    "version": 4,
    "checksum_sha256": "sha256:...",
    "updated_at": "2026-05-24T12:00:00Z"
  },
  "local": {
    "path": "~/.hermes/SOUL.md",
    "exists": true,
    "checksum_sha256": "sha256:..."
  },
  "effective": {
    "available": true,
    "precedence": "team_parent_over_local",
    "merge_status": "merged",
    "merge_source": "llm",
    "provider": "openai",
    "model": "gpt-4.1",
    "error_code": ""
  }
}
```

本地人格保存后的合并失败示例：

```json
{
  "ok": false,
  "code": "soul_merge_provider_unavailable",
  "message": "本地人格已保存，但无法调用当前 Hermes 模型供应商完成团队父人格合并。",
  "local_saved": true,
  "effective": {
    "available": true,
    "merge_status": "failed",
    "merge_source": "safe_fallback",
    "precedence": "team_parent_over_local"
  }
}
```

## API Server capability

`GET /v1/capabilities` 增加：

```json
{
  "team_bridge": {
    "enabled": true,
    "team_parent_soul": true,
    "effective_soul": true,
    "local_soul_save_triggers_merge": true
  },
  "cloud_backup": {
    "resources": ["memory", "soul"],
    "shared_minio_config": true
  }
}
```

## Desktop IPC 契约

Desktop 不直接调用 Team Cloud Go，新增 IPC 只包 Hermes Agent Bridge：

```ts
teamBridgeSoulStatus(profile?: string): Promise<SoulStatus>
teamBridgeSoulShow(kind: "team" | "local" | "effective", profile?: string): Promise<SoulContent>
teamBridgeSoulSaveLocal(content: string, profile?: string): Promise<SoulSaveResult>
teamBridgeSoulMerge(profile?: string): Promise<SoulMergeResult>
cloudBackupStatus(profile?: string): Promise<CloudBackupStatus>
cloudBackupConfigure(input, profile?: string): Promise<ActionResult>
cloudBackupRun(resource: "memory" | "soul", profile?: string): Promise<BackupRunResult>
cloudBackupHistory(resource: "memory" | "soul", profile?: string): Promise<BackupObject[]>
cloudBackupRestore(resource: "memory" | "soul", objectKey: string, profile?: string): Promise<ActionResult>
```

## 阶段路线图

### P0：文档和契约冻结

- 固定三方边界。
- 将 Desktop 中涉及 CLI/Team Cloud Go 的联动专题迁移到 Agent 文档目录。
- 更新旧文档，并规划破坏性删除 `/memory-backup` slash command、顶层 CLI subcommand、旧配置键和旧测试路径。

### P1：Team Cloud Go 团队父人格

- schema 增加 `tcg_team_souls`。
- API 增加 `GET/PUT /v1/team-soul` 和 runtime read endpoint。
- Dashboard 增加人格治理页面。
- 权限和审计补齐。

### P2：Hermes Agent effective soul

- 新增 soul resolver。
- 新增 LLM soul merge service，使用当前 Hermes profile 的模型供应商。
- team mode 下运行时注入 effective soul。
- `/soul` CLI 和 JSON 输出。
- team mode 下本地人格保存、恢复、重置后主动触发 LLM 合并。
- 模型供应商未配置或不可用时返回优雅失败，并使用安全降级组合。
- CLI/TUI/oneshot/API Server 路径一致。

### P3：`/cloud-backup`

- 新增通用 MinIO/S3 配置。
- memory 备份迁移到 `/cloud-backup memory`。
- soul 备份实现 `/cloud-backup soul`。
- 破坏性删除 `/memory-backup` 和 `hermes memory-backup`，不提供隐藏别名。
- Cron 分 resource type 管理。

### P4：Desktop UI

- Soul 页面 team mode 展示三段人格。
- Cloud Backup 页面支持 memory/soul。
- Chat `/persona` 或 `/soul` 本地命令展示三段人格。
- remote HTTP 依赖 API Server capability，缺失则显示升级提示。

### P5：回归和发布文档

- release manual 更新。
- minikube 手册增加团队父人格和团队父人格备份验收。
- Desktop teamDoc 与 Agent teamDoc 链接检查。

## 测试验收

Agent：

- local mode 下 `hermes soul status --json` 只返回 local。
- team mode 下 effective soul 包含 team parent、冲突规则和 local soul。
- team mode 下保存本地 `SOUL.md` 会调用配置中的模型供应商生成 effective soul。
- 未配置模型供应商时，本地保存成功，返回 `merge_status=failed` 和可读错误提示。
- 模型供应商不可用时，运行时不丢失团队父人格，使用安全降级组合。
- Team Cloud Go 不可用时按配置 fail open 或 fail closed。
- `/cloud-backup memory backup` 和 `/cloud-backup soul backup` 生成不同 object key 前缀。
- 用 memory 备份执行 soul restore 必须失败。

Team Cloud Go：

- 普通成员只能 read team soul。
- admin/super_admin 可以 update team soul。
- 团队父人格备份、历史、恢复 preview、恢复 execute 闭环。
- 重复恢复不产生多条 active team soul。

Desktop：

- local mode Soul 页面只显示本地人格。
- team mode Soul 页面显示团队父人格、本地人格、合并人格。
- team mode 保存本地人格后显示合并中、合并成功或合并失败状态。
- Cloud Backup 页面 memory/soul 操作调用 Hermes Agent Bridge。
- Desktop 不出现直连 Team Cloud Go team soul API 的主路径客户端。
