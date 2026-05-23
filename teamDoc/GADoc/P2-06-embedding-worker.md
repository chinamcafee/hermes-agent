# P2-06 Embedding worker

日期：2026-05-22
状态：Implemented
前置：`P2-01 记忆迁移表`

## 目标

本步骤实现 memory embedding worker 的最小可测试运行时切片。worker 扫描需要 embedding 的 memory，按批调用 embedding provider，按 `(memory_id, embedding_model)` 存储结果，并支持失败重试、最大尝试跳过、模型版本隔离和内容变更回填。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/embedding.py` | embedding record、失败状态、内存 repository、worker。 |
| `team_cloud/memory/__init__.py` | 导出 embedding worker primitives。 |
| `tests/team_cloud/test_memory_embedding_worker.py` | 批处理、失败重试、模型版本和回填测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 embedding worker 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-06 测试纳入本地 smoke 回归。 |

## 行为

- Pending 选择：
  - 只处理 `active` 和 `pending_review` memory。
  - 跳过 `archived`、`deleted`、`rejected` 等非召回状态。
  - 同一 `embedding_model` 已存在且 checksum 未变化时跳过。
  - 同一 `embedding_model` checksum 变化时重新写入，保留原 record id。
  - 新 `embedding_model` 会为已有 memory 补建新 record。
- 批处理：
  - worker 按 `batch_size` 调用 `embedding_provider.embed_many()`。
  - provider 返回数量与 batch 不一致时视为失败。
- 重试：
  - provider 异常时对 batch 内每条 memory 记录 attempts 和 last_error。
  - attempts 达到 `max_attempts` 后跳过该 memory，避免无限重试。
  - 成功写入 embedding 后清除该模型下的失败状态。

## 非目标

- 不连接真实 PostgreSQL。
- 不接入真实 embedding provider。
- 不实现 worker 调度器或分布式锁。
- 不实现 performance baseline；`P2-21` 承接。

## 后续衔接

- P2-07：extraction worker 写入 memory 后触发或等待 P2-06 批处理。
- P2-09：duplicate/conflict detector 可复用 embedding record。
- P2-21：用真实 provider 和 pgvector repository 记录 P95 及吞吐基线。
