# P2-17 Web Chat 入口工作日志

日期：2026-05-22
状态：Done

## 目标

- 按 `GAStep` 顺序推进 P2-17。
- Team Web Console 增加 Chat 页面入口。
- Chat submit 先走 SpiceDB `chat.run` 权限校验。
- 提供 submit、stream/event viewer 和错误态的最小可测试闭环。

## 执行记录

- 2026-05-22：在 P2-16 完成并通过 foundation smoke 后启动 P2-17。
- 2026-05-22：确认 P2-17 规划来自 `teamDoc/GAStep/03-phase-2-memory-runtime-steps.md` 的 “Web Chat 和云会话” 第 1-4 项；云会话持久化第 5-7 项由 P2-18/P2-19 承接。
- 2026-05-22：新增 `team_cloud/chat.py`，提供本地 `InMemoryChatRunService`、run 创建和事件列表。
- 2026-05-22：更新 `team_cloud/api.py`，新增 `POST /api/chat/runs` 和 `GET /api/chat/runs/{run_id}/events`，submit 前 fail-closed 校验 `chat.run`。
- 2026-05-22：更新 `deploy/team-cloud/web-shell/index.html`，新增 Chat tab、submit form、run status、event viewer 和 `chat-error`。
- 2026-05-22：将 `tests/team_cloud/test_web_chat_entry.py` 纳入 foundation smoke script 和 smoke matrix。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_web_chat_entry.py`
  - 结果：`1 files, 0 tests passed, 4 failed`。
  - 失败点：`POST /api/chat/runs` 返回 404、事件查看缺少 run id、Web Shell 缺少 Chat tab/form/event surfaces。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_web_chat_entry.py`
  - 结果：`1 files, 4 tests passed, 0 failed`。

## 回归验证

- 回归：`scripts/run_tests.sh tests/team_cloud/test_web_chat_entry.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_web_admin_pages.py tests/team_cloud/test_permission_explorer_minimal.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_platform_foundation_suite.py`
  - 结果：`6 files, 20 tests passed, 0 failed`。
- 回归：`venv/bin/python -m py_compile team_cloud/chat.py team_cloud/api.py tests/team_cloud/test_web_chat_entry.py tests/team_cloud/test_platform_foundation_suite.py`
  - 结果：退出码 0。
- 回归：`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  - 结果：退出码 0。
- 回归：`venv/bin/ruff check team_cloud/chat.py team_cloud/api.py tests/team_cloud/test_web_chat_entry.py tests/team_cloud/test_platform_foundation_suite.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/team_cloud/test_web_chat_entry.py tests/team_cloud/test_platform_foundation_suite.py tests/team_cloud/test_deployment_docs.py`
  - 结果：`3 files, 9 tests passed, 0 failed`。
- 回归：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
- 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`41 files, 156 tests passed, 0 failed`。
