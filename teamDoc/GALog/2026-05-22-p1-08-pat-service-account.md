# P1-08 PAT 和 service account 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-08。
- 实现 human PAT 和 service account token 的创建、hash 存储、scope 校验、过期、撤销和审计服务层。
- 当前阶段不直接连接 PostgreSQL；使用 repository 协议和内存实现承接后续 API/DB 接入。

## 执行记录

- 2026-05-22：启动 P1-08，读取工作包登记、auth permission design、schema v0 中 `service_accounts` 和 `api_tokens` 表。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_pat_service_accounts.py`，覆盖 PAT hash/redaction、scope 校验、过期、撤销、service account token 和 owner/service-account 互斥约束。
- 2026-05-22：红灯确认后新增 `team_cloud/auth/tokens.py`，实现 PBKDF2 token hash、constant-time verify、PAT/service account 签发、认证、撤销和审计。
- 2026-05-22：更新 `team_cloud/auth/__init__.py` 导出 token primitives。
- 2026-05-22：新增 `teamDoc/GADoc/P1-08-pat-service-account.md`。

## 调试记录

- 首次实现后 `test_authenticate_token_enforces_expiry_revocation_and_scope` 失败：
  - 根因：`authenticate()` 复用了签发用 scope 规范化函数；签发必须至少一个 scope，但认证时 `required_scopes` 允许为空。
  - 修复：拆分 `_normalize_required_scopes()`，只保留白名单校验，不要求非空。
- 第二次失败显示 expired case 得到 `revoked`：
  - 根因：测试 `token_factory` 对两个 token 生成了相同明文，认证迭代先命中已撤销记录。
  - 修复：测试改为顺序生成不同明文 token，保留真实场景的唯一 token 前提。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_pat_service_accounts.py`
  - 结果：`4 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.auth.tokens'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_pat_service_accounts.py`
  - 结果：`4 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/auth/tokens.py team_cloud/auth/__init__.py tests/team_cloud/test_pat_service_accounts.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py`
  - 结果：`52 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
