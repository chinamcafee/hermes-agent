# P2-23 记忆和 runtime 文档

日期：2026-05-22
状态：Implemented
前置：`P2-20 隔离测试套件`、`P2-21 记忆性能基线`、`P2-22 SessionDB 迁移工具`

## API

P2 交付的 runtime API 分为 memory、chat、cloud session 和 runtime event 四组：

| API | 用途 | 关键边界 |
| --- | --- | --- |
| `POST /v1/memory` | 创建 personal 或 team_shared memory。 | 由 memory service 校验 scope/status/sensitivity。 |
| `GET /v1/memory` | 按 org/scope/status/type/sensitivity 查询 memory。 | 不跨 org 返回。 |
| `POST /v1/memory/prefetch` | 为 agent turn 召回 personal 与 team_shared 两重记忆。 | personal 可关闭；team_shared 必须经过 `spicedb batch_check(memory#read_team)`。 |
| `POST /v1/memory/observations` | 写入 `sync_turn` observation。 | 记录 turn metadata、tool summaries 和 source trace。 |
| `POST /api/chat/runs` | Web Chat 创建 run 和 cloud session。 | 先校验 `project#run_agent`。 |
| `GET /api/chat/runs/{run_id}/events` | 查看 run event stream。 | 缺失 run 返回 404。 |
| `GET /api/cloud/sessions` | 按 org/project/member/query 查询 cloud session。 | 返回 summary，不泄漏其他 org/project。 |
| `GET /api/cloud/sessions/{session_id}` | 查看 cloud session messages/tool_calls。 | 未知 session 返回 404。 |
| `POST /api/cloud/sessions/{session_id}/tool-calls` | 写入 cloud tool call audit record。 | risk/decision 使用固定枚举。 |
| `POST /api/runtime/events` | runtime bridge 写入 message/tool event。 | 未知 cloud session 或 run fail closed。 |

相关设计：

- `P2-03-memory-crud-api.md`
- `P2-04-prefetch-pipeline.md`
- `P2-13-sync-turn-observation.md`
- `P2-17-web-chat-entry.md`
- `P2-18-cloud-session-history.md`
- `P2-19-runtime-event-bridge.md`

## Provider

`team_cloud/memory/provider.py` 是 TeamMemoryProvider 的 runtime 适配层，保持在 Team Cloud 包内，避免新增 in-tree `plugins/memory/*` provider。

核心行为：

- `initialize` 读取 `team_context`，需要 `org_id`、`team_id`、`project_id`、`member_id`。
- `prefetch` 调用 Team Cloud prefetch pipeline，默认同时召回 `personal` 和 `team_shared`。
- Gateway shared session 可设置 `personal_memory_enabled=False`，只召回 `team_shared`。
- `sync_turn` 将 user/assistant/tool summaries 写成 observation，后续由 extraction worker 生成候选 memory。
- Memory tools 覆盖 search/remember/propose/promote/forget/backup_now，继续复用 provider 的 Team Cloud 边界。

关键文档：

- `P2-11-team-memory-provider.md`
- `P2-12-memory-tools.md`
- `P2-14-aiagent-team-context.md`
- `P2-15-api-server-identity-headers.md`
- `P2-16-gateway-identity-resolver.md`

## Migration

`scripts/team-cloud-import-sessiondb.py` 提供本地 `SessionDB` 导入入口，底层调用 `team_cloud/sessiondb_import.py`。

迁移输入：

```json
{
  "alice-local-user-id": "team-cloud-member-id"
}
```

命令示例：

```bash
scripts/team-cloud-import-sessiondb.py \
  --db ~/.hermes/state.db \
  --org-id org-1 \
  --team-id team-1 \
  --project-id project-1 \
  --identity-map identity-map.json \
  --dry-run
```

迁移规则：

- `identity_map` 是本地 `SessionDB.sessions.user_id` 到 Team Cloud `member_id` 的显式映射。
- 未映射 identity 不导入，报告 `identity_not_mapped`。
- `--dry-run` 不创建 cloud session，只输出 imported/unmapped report。
- 成功导入的 session 使用 `source_platform=sessiondb:<local source>`。
- message content 保留 `text`、`local_message_id`、`tool_call_id`、`tool_name` 和 `tool_calls`。

相关文档：

- `P2-22-sessiondb-import.md`
- `P2-18-cloud-session-history.md`

## Operations

P2 运行期最小运维检查：

| 检查 | 命令或工件 | 目标 |
| --- | --- | --- |
| Foundation smoke | `scripts/team-cloud-foundation-smoke.sh` | 覆盖 P1/P2 API、runtime、memory、迁移和文档验收。 |
| Isolation smoke | `scripts/team-cloud-isolation-smoke.sh` | 验证 Alice/Bob、org A/B、team/project 隔离和 Gateway identity prefix。 |
| Performance baseline | `teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json` | 固定 prefetch P95 目标、top-k、candidate_limit 和 query plan。 |
| Baseline generator | `scripts/team-cloud-memory-perf-baseline.py` | 可重复生成 memory performance artifact。 |
| SessionDB dry-run | `scripts/team-cloud-import-sessiondb.py --dry-run` | 在导入前审计 unmapped identity。 |

当前 P2 performance target：

- `prefetch_p95_ms <= 500`
- `top_k = 8`
- `candidate_limit <= 64`
- `team_shared` query plan 必须包含 `spicedb batch_check(memory#read_team)`

P3 衔接：

- 工具风险 taxonomy 和 TeamToolPolicyHook 接管 tool permission hardening。
- personal backup policy、exporter、restore preview/execute 接管本地记忆定时备份。
- audit 高级能力和 Permission Explorer GA 接管运营侧排障。

相关文档：

- `P2-20-isolation-test-suite.md`
- `P2-21-memory-performance-baseline.md`
