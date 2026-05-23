# P2-10 PII/secret detector

日期：2026-05-22
状态：Implemented
前置：`P2-03 Memory CRUD API`

## 目标

本步骤实现 memory review queue 的 PII/secret 安全检测切片。detector 扫描 pending review item，调用 safety classifier 判断候选内容的敏感级别；PII 候选留在审核队列并提升 memory sensitivity，secret 候选直接拒绝。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/safety.py` | `SafetyDetection`、正则 classifier、PII/secret detector。 |
| `team_cloud/memory/__init__.py` | 导出 safety detector primitives。 |
| `tests/team_cloud/test_memory_pii_secret_detector.py` | PII 标记、secret 拒绝、normal unchanged 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 safety detector 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-10 测试纳入本地 smoke 回归。 |

## 行为

- 只处理 pending review item。
- `normal` 且无 findings：保持 review item 和 memory 不变。
- PII：
  - memory `sensitivity` 更新为 `pii`。
  - review item 保持 pending。
  - review item `review_kind=pii`，`reason=pii_detected`。
  - `candidate_payload.safety_findings` 记录命中类型。
- Secret：
  - memory `sensitivity=secret` 且 `status=rejected`。
  - review item `status=rejected`。
  - review item `review_kind=pii`，`reason=secret_detected`。
  - `candidate_payload.safety_findings` 记录命中类型。

## 非目标

- 不实现完整 DLP/PII 分类模型。
- 不暴露 detector API。
- 不自动通知 reviewer。
- 不处理已 approve/rejected 的 review item。

## 后续衔接

- P2-11/P2-12：TeamMemoryProvider tools 写入前可复用该 detector。
- P3-16：高级 audit 可增加 sensitive review 查询和导出。
- P4/P5：替换为企业 DLP provider 时保持 `SafetyDetection` 契约。
