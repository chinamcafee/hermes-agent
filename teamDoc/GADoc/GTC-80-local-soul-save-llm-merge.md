# GTC-80 本地人格保存触发 LLM 合并规划

日期：2026-05-24

## 需求

CLI 和 Desktop 本地没有权限保存团队父人格，但在 team mode 下保存本地人格时，需要主动触发“团队父人格 + 本地人格”的合并。合并由 Hermes 调用当前 profile 配置的大模型供应商完成。

## 决策

- Team Cloud Go 仍是团队父人格唯一权威源。
- CLI/Desktop 只能保存本地 `SOUL.md`，不能写团队父人格。
- team mode 下，本地 `SOUL.md` 保存、恢复、重置后必须触发 LLM 合并。
- local mode 下不触发合并。
- LLM 合并使用当前 Hermes profile 的模型供应商配置，不新增 Team Cloud Go 服务端模型配置。
- 未配置供应商、缺少 API key、供应商不可达、超时或返回空内容时，本地保存不回滚。
- 合并失败必须返回结构化错误，CLI/Desktop 显示优雅失败提示。
- 合并失败时运行时使用安全降级组合，保证团队父人格仍优先于本地人格。

## 实现落点

- `hermes_cli/team_soul.py` 负责读取团队父人格、本地 `SOUL.md`、生成安全降级组合，并在配置了模型供应商时调用 `agent.auxiliary_client.call_llm(task="team_soul_merge")`。
- `hermes soul merge` 与 `/soul merge` 触发当前本地人格的重新合并。
- `hermes_cli/web_server.py` 暴露 `/api/soul/status`、`/api/soul/local`、`/api/soul/recompute` 给 Desktop Bridge 消费。
- `agent/system_prompt.py` 在 team mode 下优先使用 effective soul，local mode 继续使用本地 `SOUL.md`。

## 后续实现要点

- Desktop `writeSoul` 需要改为调用 Hermes Agent Bridge 的 save-and-merge 契约。
- `/cloud-backup soul restore` 成功后，如果当前 profile 是 team mode，也要触发合并。

## 验收

- team mode 保存本地人格后，返回 `saved=true` 和 `merge.status=ok`，`effective_soul.merge_status=llm`。
- 未配置模型供应商时，返回 `saved=true`、`merge.status=failed`、`error_code=model_provider_unavailable`。
- 供应商不可用时，返回可读错误，并使用安全降级组合。
- Desktop 不直接调用 Team Cloud Go 或模型供应商。

## 验证

- `venv/bin/python -m pytest tests/hermes_cli/test_team_soul.py tests/run_agent/test_team_soul_runtime.py -q`
