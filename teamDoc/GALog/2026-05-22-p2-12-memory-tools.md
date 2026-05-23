# P2-12 Memory tools 工作日志

## 目标

- 按 `GAStep` 顺序推进 P2-12。
- 在 TeamMemoryProvider core 上实现 search、remember、propose、promote、forget、backup_now 工具 schema 和 JSON-string routing。

## 执行记录

- 2026-05-22：启动 P2-12，读取 P2-11 provider core 和 P2 runtime tools 规划。
- 2026-05-22：确认本步骤只补 provider tool schemas 和 handler routing，真实 AuthZ 细化由后续 P2/P3 与 SpiceDB middleware 承接。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_team_memory_provider_tools.py`，覆盖工具 schema、search 路由、remember 写入权限检查和 propose deny。
- 2026-05-22：补齐 `TeamMemoryProvider.get_tool_schemas()`、`handle_tool_call()`、permission checker hook 和 Team Cloud HTTP 路由。
- 2026-05-22：新增 `teamDoc/GADoc/P2-12-memory-tools.md`，并将 P2-12 测试纳入 smoke matrix 与 `scripts/team-cloud-foundation-smoke.sh`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_team_memory_provider_tools.py`
  - 结果：`4 tests failed, 0 passed`。
  - 失败点：`TeamMemoryProvider.__init__() got an unexpected keyword argument 'permission_checker'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_team_memory_provider_tools.py`
  - 结果：`4 tests passed, 0 failed`。
- 回归：`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`
  - 结果：JSON artifact 可解析。
- 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`35 files, 134 tests passed, 0 failed`。
- 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 回归：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
