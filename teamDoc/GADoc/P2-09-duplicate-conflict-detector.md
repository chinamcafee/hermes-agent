# P2-09 去重和冲突检测

日期：2026-05-22
状态：Implemented
前置：`P2-07 Memory extraction worker`

## 目标

本步骤实现 memory review queue 的去重和冲突检测切片。detector 扫描 pending review item，对照同组织、同 scope、同 team/project 的 active memory，优先识别 checksum duplicate，其次识别 semantic duplicate，最后识别 contradiction，并把结果写回 review item。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/detectors.py` | checksum/semantic duplicate 和 contradiction detector。 |
| `team_cloud/memory/__init__.py` | 导出 detector primitive。 |
| `tests/team_cloud/test_memory_duplicate_conflict_detector.py` | duplicate/conflict detector 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 detector 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-09 测试纳入本地 smoke 回归。 |

## 行为

- 只处理 pending review item。
- 只对照同 `org_id/scope/team_id/project_id` 的 active memory。
- 分类优先级：
  - `checksum_duplicate`：候选 memory checksum 与 active memory 一致。
  - `semantic_duplicate`：注入的 similarity provider 返回分数超过阈值。
  - `contradiction`：注入的 contradiction provider 返回冲突原因。
- 命中 duplicate 时：
  - `review_kind=duplicate`
  - `reason=checksum_duplicate` 或 `semantic_duplicate`
  - `candidate_payload.duplicate_memory_id` 记录重复对象。
- 命中 conflict 时：
  - `review_kind=conflict`
  - `reason=contradiction`
  - `candidate_payload.conflict_memory_id` 和 `conflict_reason` 记录冲突对象和原因。

## 非目标

- 不自动 approve/reject review item。
- 不接入真实 embedding/vector repository。
- 不实现 detector 调度器。
- 不实现 PII/secret detector；P2-10 承接。

## 后续衔接

- P2-08 Review Queue API 可以继续处理被标记为 duplicate/conflict 的 item。
- P2-10 在同一 review item 模型上追加 PII/secret 处理。
- P2-21 用真实向量检索和相似度模型记录性能基线。
