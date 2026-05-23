# P1-20 平台安全负测工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-20。
- 覆盖伪造 token、禁用用户和跨 org 管理拒绝三类平台基础安全负测。
- 将 AuthZ middleware 可选接入组织/团队/成员管理 API，保持 fail-closed。

## 执行记录

- 2026-05-22：启动 P1-20，读取 JWT middleware、AuthZ middleware、P1-13 管理 API 和 P1-19 smoke suite。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_platform_security_negative.py`，覆盖伪造 token 不泄漏、禁用用户拒绝和跨 org member invite 拒绝。
- 2026-05-22：红灯确认后扩展 `team_cloud/api.py`，新增 `enable_authz_middleware`、`authz_subject_resolver`、`authz_outbox_pending`，并为组织作用域管理 API 安装 AuthZ rules。
- 2026-05-22：更新 `platform-foundation-smoke-v0.json` 和 `scripts/team-cloud-foundation-smoke.sh`，纳入 security negative 测试。
- 2026-05-22：新增 `teamDoc/GADoc/P1-20-platform-security-negative.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py`
  - 结果：`1 test failed, 2 passed`。
  - 失败点：`create_app()` 尚不支持 `enable_authz_middleware`，跨 org member invite 无法安装 AuthZ gate。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_platform_security_negative.py`
  - 结果：`3 tests passed, 0 failed`。
- Smoke 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`94 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
