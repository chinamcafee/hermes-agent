# P1-01 Team Cloud repo/package 骨架

## 工作目标

- 按 `teamDoc/GAStep/02-phase-0-1-foundation-steps.md` 的 P1 第 1 项执行。
- 建立 `team_cloud/` package。
- 建立 API app、worker app、migration runner、test fixtures。
- 定义配置加载优先级：env > yaml > secret file > defaults。
- 建立 request context：`request_id/org_id/member_id/actor_type`。
- 加入 structured logging 和 health endpoints。

## 2026-05-22 执行记录

### 1. 启动 P1-01

- 输入原则：P0 文档和 P1-01 GAStep。
- 当前边界：只做 Team Cloud 骨架，不提前实现 Casdoor、SpiceDB、PostgreSQL 连接、MinIO 操作或 Web 管理页。
- 测试策略：先新增 focused tests，验证红灯，再补最小生产代码。

### 2. 红灯测试设计

- `tests/team_cloud/conftest.py` 提供临时 YAML 配置、secret file 和 `TeamCloudConfig` fixture。
- `tests/team_cloud/test_skeleton.py` 覆盖：
  - package 可导入并暴露版本。
  - env > yaml > secret file > defaults 的配置优先级。
  - secret 字段的安全导出不泄露明文。
  - `RequestContext` 的 actor 类型校验和 header 构造。
  - FastAPI app 的 `/healthz`、`/readyz`。
  - worker heartbeat。
  - migration runner dry-run 发现 P0 PostgreSQL schema artifact。
  - JSON structured logging 携带事件字段并隐藏 secret。

### 3. 最小实现

- 新增 `team_cloud/` package：
  - `__init__.py` 暴露 package version。
  - `config.py` 实现 `TeamCloudConfig` 和 `load_config()`。
  - `context.py` 实现 `RequestContext` 和 header 构造。
  - `api.py` 实现 FastAPI `create_app()`、`/healthz`、`/readyz`。
  - `worker.py` 实现 `TeamCloudWorker` 和 `create_worker()`。
  - `migrations.py` 实现 migration discovery 和 dry-run。
  - `logging.py` 实现 JSON structured logging 和 secret redaction。
  - `py.typed` 标记 typed package。
- 更新 `pyproject.toml` package finder include，确保 `team_cloud` 会被打包。
- 未引入新依赖；复用既有 `pydantic`、`pyyaml`、FastAPI web extra。

### 4. 进度同步

- `teamDoc/GAStep/progress-tracker.md` 已将 P1-01 标记为 `Done`。
- P1 总体进度更新为 `2.0 / 47` 人周，完成率 `4.3%`，状态 `In Progress`。
- M1 状态更新为 `In Progress`。
- 当前待启动项更新为 P1-02 配置和 secret 管理。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_skeleton.py`
  - 结果：失败，`ModuleNotFoundError: No module named 'team_cloud'`。
  - 解释：测试已描述 P1-01 预期行为，生产包尚未建立。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_skeleton.py`
  - 结果：`8 tests passed, 0 failed`。
  - 覆盖：Team Cloud package、配置优先级、secret redaction、request context、API health/readiness、worker heartbeat、migration dry-run、structured logging。
- 元数据回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_skeleton.py`
  - 结果：`14 tests passed, 0 failed`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 最终复验：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_skeleton.py`
  - 结果：`14 tests passed, 0 failed`。
- Tracker 核对：`rg -n "P1 平台基础|M1 平台基础可用|P1-01|P1-02 配置和 secret 管理待启动" teamDoc/GAStep/progress-tracker.md`
  - 结果：确认 P1-01 `Done`，P1/M1 `In Progress`，下一项 P1-02。
