# P2-07 Memory extraction worker

日期：2026-05-22
状态：Implemented
前置：`P2-01 记忆迁移表`、`P2-06 Embedding worker`

## 目标

本步骤实现 conversation observation 到 memory candidate 的运行时抽取切片。worker 从 pending observation 中读取对话观察，调用 extractor 生成候选，写入 personal/team_shared memory，并为 team_shared 候选创建 pending review item，同时在 observation 上记录 confidence、source trace 和处理状态。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/extraction.py` | observation/review item 内存 repository、candidate 模型、extraction worker。 |
| `team_cloud/memory/service.py` | memory item 增加 `source_type` 和 `source_ref` 字段。 |
| `team_cloud/memory/__init__.py` | 导出 extraction worker primitives。 |
| `tests/team_cloud/test_memory_extraction_worker.py` | personal/team candidate、ignored 和 error 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 extraction worker 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-07 测试纳入本地 smoke 回归。 |

## 行为

- Observation：
  - `pending` observation 进入 worker。
  - 处理前标记为 `processing`。
  - 无候选时标记为 `ignored`，trace 为 `{"candidate_count": 0}`。
  - extractor 异常时标记为 `error` 并写 `error` 字段。
- Candidate：
  - personal candidate 写入 `scope=personal`，默认绑定 observation 的 `member_id`。
  - team_shared candidate 写入 `scope=team_shared`，默认继承 observation 的 `team_id/project_id`，状态保持 P2-03 默认 `pending_review`。
  - memory 写入 `source_type=observation` 和 `source_ref.observation_id`。
- Review：
  - team_shared candidate 创建 pending review item。
  - review item 保存 `review_kind`、`confidence` 和候选 payload。
- Trace：
  - extracted observation 写 `candidate_count`、`created_memory_ids`、`review_item_ids`。
  - observation confidence 使用候选 confidence 平均值。

## 非目标

- 不实现 `/v1/memory/observations`；P2-13 承接 sync_turn observation。
- 不实现 Review Queue API；P2-08 承接 approve/reject/edit-before-approve。
- 不接入真实 LLM extractor。
- 不实现重复/冲突/PII detector；P2-09/P2-10 承接。

## 后续衔接

- P2-08：基于 review item 实现审核 API。
- P2-09：对 candidate_payload 做 duplicate/contradiction review。
- P2-10：对 observation/candidate 做 PII/secret 检测。
- P2-13：Hermes memory provider 通过 observations API 写入 turn observation。
