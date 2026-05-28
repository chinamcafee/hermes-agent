# 2026-05-24 本地人格保存触发 LLM 合并规划日志

## 背景

用户补充要求：CLI 和 Desktop 本地不能保存团队父人格，但本地人格保存时，如果处于 team mode，需要主动触发团队父人格和本地人格的合并。合并由 Hermes 使用当前配置的大模型供应商完成；未配置或供应商不可用时，要优雅提示。

## 工作内容

- 更新团队父人格领域设计，补充 LLM effective soul 合并、缓存、失败状态和安全降级组合。
- 更新 Hermes Agent CLI/API 计划，新增 `/soul merge`、`agent/soul_merge.py` 和 save-and-merge 流程。
- 更新三方契约和测试验收，加入模型供应商缺失/不可用的失败场景。
- 更新 Desktop Soul UI 和 Bridge 消费文档，要求本地人格保存后通过 Hermes Agent Bridge 触发合并。
- 更新 release manual、README、目标架构和 progress tracker。
- 2026-05-24 追加实现：`hermes_cli/team_soul.py` 已接入 `agent.auxiliary_client.call_llm(task="team_soul_merge")`，配置 provider/model 时返回 LLM 合并结果；未配置或调用失败时保留本地保存并使用安全降级组合。

## 状态

已完成 Hermes Agent CLI/API 侧实现。Desktop 侧由后续 Bridge 改造消费 `/api/soul/*` 契约。

## 验证

- `venv/bin/python -m pytest tests/hermes_cli/test_team_soul.py -q`：4 passed。
