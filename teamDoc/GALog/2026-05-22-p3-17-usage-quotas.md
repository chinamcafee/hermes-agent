# P3-17 Usage/quotas 工作日志

日期：2026-05-22
状态：Done

## 目标

- 按 `GAStep` 顺序推进 P3-17。
- 汇总组织级 runs、token、tool calls 和 personal backup object size。
- 支持组织配额设置和配额评估。
- 在 chat run 创建入口执行 run quota fail-closed。
- Web Admin 壳提供 Usage tab，用于查看摘要和配置配额。

## 执行记录

- 2026-05-22：P3-16 完成并通过 foundation smoke 后启动 P3-17。
- 2026-05-22：读取工作包登记、云数据管理方案、现有 `cloud_sessions`、`chat`、`runtime_events`、`storage/minio`、`backup/storage` 和观测基线，确认本步骤以现有 in-memory repositories 为用量来源，不引入新数据库迁移。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_usage_quotas.py`
  失败符合预期，4 个测试全部失败；失败原因为 `team_cloud.usage`
  模块不存在，Usage/Quota API 尚未接入，Web Admin 壳缺少 Usage tab 和配额控件。
- 绿灯：新增 `team_cloud/usage.py`，扩展 `team_cloud/api.py` 和 Web Admin 壳后重跑
  `scripts/run_tests.sh tests/team_cloud/test_usage_quotas.py`，1 个测试文件、
  4 个测试通过、0 失败。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_usage_quotas.py
  tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_runtime_event_bridge.py
  tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py`：
  5 个测试文件、15 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/usage.py team_cloud/api.py
  tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_cloud_session_history.py
  tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_backup_storage.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/usage.py team_cloud/api.py
  tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_cloud_session_history.py
  tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_backup_storage.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool
  teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- 首次 `scripts/team-cloud-foundation-smoke.sh`：业务用例均通过，但
  `tests/team_cloud/test_web_login_shell.py` 在 `tmp_path` fixture 初始化时出现
  `/private/tmp/pytest-of-changzechuan/pytest-2317` 不存在的瞬时环境错误。
- 单独复现 `scripts/run_tests.sh tests/team_cloud/test_web_login_shell.py`：
  1 个测试文件、2 个测试通过、0 失败。
- 重新运行 `scripts/team-cloud-foundation-smoke.sh`：63 个测试文件、222 个测试通过、0 失败。
- `git diff --check -- ...P3-17 touched files...`：通过。

## 完成记录

- 2026-05-22：P3-17 Usage/quotas 已完成，foundation smoke 纳入
  `usage_quotas` domain；P3-18 Backup/restore tests 待启动。
