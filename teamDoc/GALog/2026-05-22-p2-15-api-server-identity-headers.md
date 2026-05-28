# P2-15 API Server identity headers 工作日志

> 2026-05-24 更新：Team Cloud Go 已取消部署级 service token。本文记录的是 P2 阶段 API Server trusted headers 的历史实现；后续 CLI / Gateway / API Server 身份透传应改用成员级 token、OIDC/JWT 或 PAT。

## 目标

- 按 `GAStep` 顺序推进 P2-15。
- API Server 支持 Team Cloud 可信 identity headers。
- 只有 Team Cloud service token 校验通过后，才接受 `X-Hermes-Org-Id`、`X-Hermes-Team-Id`、`X-Hermes-Member-Id` 和可选 `X-Hermes-Project-Id`。
- 将解析出的 `team_context` 透传到 `_run_agent()` 和 `_create_agent()`。

## 执行记录

- 2026-05-22：启动 P2-15，读取 `gateway/platforms/api_server.py`、`tests/gateway/test_api_server.py` 和 `teamDoc` 中 API Server trusted headers 约束。
- 2026-05-22：确认 `X-Hermes-Session-Key` 只是 memory scope，不是企业授权主体；P2-15 需要独立可信 header + service token gate。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/gateway/test_api_server_team_headers.py`
  - 结果：`4 tests failed, 0 passed`。
  - 失败点：identity headers 被忽略、`team_context` 未传给 `_run_agent()`、`APIServerAdapter._create_agent()` 不接受 `team_context`。
- 绿灯：`scripts/run_tests.sh tests/gateway/test_api_server_team_headers.py`
  - 结果：`4 tests passed, 0 failed`。
- 2026-05-22：新增 `teamDoc/GADoc/P2-15-api-server-identity-headers.md`，并准备将 P2-15 gateway 测试纳入 smoke matrix 与 `scripts/team-cloud-foundation-smoke.sh`。
- 回归：`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`
  - 结果：JSON artifact 可解析。
- 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`38 files, 144 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/gateway/test_api_server.py tests/gateway/test_api_server_team_headers.py`
  - 结果：`2 files, 153 tests passed, 0 failed`。
- 回归：`venv/bin/ruff check gateway/platforms/api_server.py tests/gateway/test_api_server_team_headers.py run_agent.py agent/agent_init.py team_cloud tests/team_cloud tests/run_agent/test_memory_provider_init.py`
  - 结果：`All checks passed!`。
- 回归：`venv/bin/python -m py_compile gateway/platforms/api_server.py run_agent.py agent/agent_init.py`
  - 结果：退出码 0。
- 回归：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
