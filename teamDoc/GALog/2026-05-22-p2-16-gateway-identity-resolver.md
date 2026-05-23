# P2-16 Gateway identity resolver 工作日志

日期：2026-05-22
状态：Done

## 目标

- 在 Gateway 进入 Agent 前调用 Team Cloud external identity resolve。
- 未绑定平台用户返回绑定提示，不创建 Agent。
- 对已解析团队身份的 Gateway session key 增加 org/team 前缀，隔离跨团队会话和 agent cache。
- 将 `team_context` 透传给 Gateway 创建的 `AIAgent`，并在 shared group session 中显式标记个人记忆禁用语义。

## 执行记录

- 2026-05-22：确认 P2-16 前置 P2-15 已完成；规划要求来自 `teamDoc/GAStep/03-phase-2-memory-runtime-steps.md` 的 Hermes Core 和 Gateway 第 5-8 项。
- 2026-05-22：读取 `gateway/run.py`、`gateway/session.py`、`gateway/platforms/base.py`、`team_cloud/api.py`、`team_cloud/sql_migrations/001_schema_v0.sql`，确认最小实现切面为 Team Cloud resolve API + Gateway resolver + session key prefix + AIAgent `team_context` 透传。
- 2026-05-22：新增 `team_cloud/identity.py`，提供 `InMemoryExternalIdentityResolver`、`ExternalIdentityBinding` 和 `team_session_key_prefix()`。
- 2026-05-22：新增 `gateway/team_identity.py`，提供 Gateway resolve client、配置/env 解析、响应归一化、绑定提示和 session key prefix helper。
- 2026-05-22：更新 `gateway/run.py`，在 allowlist/pairing 通过后、agent 创建前调用 resolver；未绑定用户直接返回绑定提示；已解析用户向 `_run_agent()`、proxy 和 `AIAgent(...)` 透传 `team_context`。
- 2026-05-22：更新 `gateway/session.py`，让 `SessionSource` 保存 `team_context` 并在 session key 中加入 `team:<org>:<team>:` 前缀。
- 2026-05-22：更新 `team_cloud/api.py`、`team_cloud/memory/prefetch.py`、`team_cloud/memory/provider.py`，支持 shared multi-user session 通过 `include_personal=false` 禁用个人记忆召回。
- 2026-05-22：将 P2-16 纳入 `scripts/team-cloud-foundation-smoke.sh` 和 `platform-foundation-smoke-v0.json`。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_external_identity_resolver.py tests/gateway/test_gateway_team_identity_resolver.py`
  - 结果：2 files, 7 failed。
  - 失败点：缺少 `team_cloud.identity`、缺少 `gateway.team_identity`、`GatewayRunner._run_agent()` 不接受 `team_context`。
- 补充红灯：`scripts/run_tests.sh tests/team_cloud/test_memory_prefetch_pipeline.py`
  - 结果：2 passed, 1 failed。
  - 失败点：`MemoryPrefetchPipeline.prefetch()` 不接受 `include_personal`，shared group session 无法在 prefetch 层禁用 personal partition。

## 回归验证

- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_external_identity_resolver.py tests/gateway/test_gateway_team_identity_resolver.py tests/team_cloud/test_memory_prefetch_pipeline.py tests/team_cloud/test_team_memory_provider.py`
  - 结果：`4 files, 14 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/gateway/test_gateway_team_identity_resolver.py tests/gateway/test_api_server_team_headers.py tests/gateway/test_fast_command.py tests/team_cloud/test_external_identity_resolver.py tests/team_cloud/test_memory_prefetch_pipeline.py tests/team_cloud/test_team_memory_provider.py`
  - 结果：`6 files, 22 tests passed, 0 failed`。
- 回归：`venv/bin/ruff check gateway/team_identity.py gateway/session.py gateway/run.py team_cloud/identity.py team_cloud/api.py team_cloud/memory/prefetch.py team_cloud/memory/provider.py tests/gateway/test_gateway_team_identity_resolver.py tests/team_cloud/test_external_identity_resolver.py tests/team_cloud/test_memory_prefetch_pipeline.py tests/team_cloud/test_team_memory_provider.py`
  - 结果：`All checks passed!`。
- 回归：`venv/bin/python -m py_compile gateway/team_identity.py gateway/session.py gateway/run.py team_cloud/identity.py team_cloud/api.py team_cloud/memory/prefetch.py team_cloud/memory/provider.py`
  - 结果：退出码 0。
- 回归：`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  - 结果：退出码 0。
- 回归：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
- 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`40 files, 152 tests passed, 0 failed`。
