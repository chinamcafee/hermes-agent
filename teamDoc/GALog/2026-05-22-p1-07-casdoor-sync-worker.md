# P1-07 Casdoor 同步 worker 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-07。
- 实现 Casdoor user/org/group 的 lazy upsert、reconcile 和禁用传播编排。
- 当前阶段先落地可测试的同步服务层与 repository/client 协议，不引入 Casdoor SDK 或数据库驱动。

## 执行记录

- 2026-05-22：启动 P1-07，读取 `progress-tracker.md`、工作包登记、Phase 0-1 计划和 Casdoor/SpiceDB 集成设计。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_casdoor_sync_worker.py`，覆盖登录 lazy upsert、目录 reconcile、禁用用户传播和敏感 token 不落日志/结果。
- 2026-05-22：红灯确认后新增 `team_cloud/sync/casdoor.py` 和 `team_cloud/sync/__init__.py`。
- 2026-05-22：实现 `CasdoorSyncWorker`、`SyncCommand`、`SyncResult`、`InMemoryCasdoorSyncRepository`。
- 2026-05-22：补充 `TeamCloudWorker.run_casdoor_reconcile()`，让通用 worker 可以承载 Casdoor 定时 reconcile。
- 2026-05-22：新增 `teamDoc/GADoc/P1-07-casdoor-sync-worker.md`。

## 调试记录

- 首次实现后新增测试 2 个失败：
  - `repository.external_identities` 是 tuple-key 内存索引，测试不能直接 JSON 序列化 dict；修正为序列化 values。
  - `reconcile()` 复用 `sync_user()` 时重复计数 organization/team ensure；修正为 reconcile 的用户路径跳过已由 directory org/group 阶段覆盖的 ensure。
- worker 承载测试红灯：
  - `TeamCloudWorker.__init__()` 尚未支持 `casdoor_sync_worker`。
  - 修正：增加可选 `casdoor_sync_worker` 字段和 `run_casdoor_reconcile()`。

## 验证记录

- 红灯 1：`scripts/run_tests.sh tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`3 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.sync'`。
- 绿灯 1：`scripts/run_tests.sh tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`3 tests passed, 0 failed`。
- 红灯 2：`scripts/run_tests.sh tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`1 failed, 3 passed`。
  - 失败点：`TeamCloudWorker.__init__()` 不支持 `casdoor_sync_worker`。
- 绿灯 2：`scripts/run_tests.sh tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`4 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py`
  - 结果：`48 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
