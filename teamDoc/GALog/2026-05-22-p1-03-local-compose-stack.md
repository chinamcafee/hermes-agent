# P1-03 本地 compose 栈

## 工作目标

- 按 `teamDoc/GAStep/02-phase-0-1-foundation-steps.md` 的 P1 第 2 项执行。
- 创建 `deploy/team-cloud/compose.yaml`。
- 加入 Casdoor、SpiceDB、PostgreSQL+pgvector、MinIO、Team API、worker、web shell。
- 加入初始化 job：PostgreSQL role/db、SpiceDB schema load、MinIO buckets。
- 写 smoke test 入口：登录、permission check、pgvector query、MinIO upload。

## 2026-05-22 执行记录

### 1. 启动 P1-03

- 前置确认：P1-01、P1-02 已在 `progress-tracker.md` 标记 `Done`。
- 规格输入：`teamDoc/GADoc/P0-05-local-topology-design.md`、`P0-04` 版本冻结、`P0-07` SpiceDB schema、`P0-08` PostgreSQL schema、`P0-09` MinIO manifest。
- 当前边界：本步骤落地本地 compose 和脚本工件，不实现 Casdoor OIDC callback/JWT middleware，也不把 P1-04 migration runner 扩展为完整 Alembic。

### 2. 红灯测试设计

- 新增 `tests/team_cloud/test_local_compose_stack.py`，覆盖：
  - compose 文件存在且定义 P0-05 服务。
  - 端口、网络、volumes、secrets 符合 P0-05。
  - Team API/worker 使用 `*_FILE` secret 注入。
  - image 不使用 `latest` tag。
  - `.env.example` 不包含 secret 明文。
  - secrets 生成脚本和 smoke 脚本存在。
  - GADoc 与 compose 工件互相引用。

### 3. 最小实现

- 新增 `deploy/team-cloud/compose.yaml`：
  - 服务：`postgres`、`postgres-init`、`casdoor-init`、`casdoor`、`mailpit`、`spicedb-migrate`、`spicedb`、`spicedb-schema-load`、`minio`、`minio-init`、`team-api`、`team-worker`、`team-web`、`hermes-runtime`。
  - 网络：`team-edge`、`team-control`、`team-data`。
  - volumes：`team_postgres_data`、`team_minio_data`、`team_casdoor_conf`、`team_spicedb_cache`、`team_runtime_home`。
  - secrets：Team Cloud DB URL、Casdoor client secret、SpiceDB key、MinIO secret、encryption key、service DB passwords、MinIO root password。
- 新增 `deploy/team-cloud/.env.example`，只包含非敏感默认值和 image tag。
- 新增 `deploy/team-cloud/team-cloud.Dockerfile` 供 Team API/worker/runtime placeholder 本地构建。
- 新增初始化工件：
  - `deploy/team-cloud/init/postgres-init.sh`
  - `deploy/team-cloud/casdoor/app.conf.template`
  - `deploy/team-cloud/web-shell/index.html`
  - `deploy/team-cloud/web-shell/nginx.conf`
- 新增运维脚本：
  - `scripts/team-cloud-secrets.sh`
  - `scripts/team-cloud-smoke.sh`
- 增强 `team_cloud.worker`，支持 `python -m team_cloud.worker` heartbeat loop。
- 新增 `teamDoc/GADoc/P1-03-local-compose-stack.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py`
  - 结果：`7 tests failed`。
  - 失败点：`deploy/team-cloud/compose.yaml`、`.env.example`、P1-03 GADoc、secrets 生成脚本和 smoke 脚本尚未创建。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py`
  - 结果：`7 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py`
  - 结果：`26 tests passed, 0 failed`。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
- Compose 解析：`scripts/team-cloud-secrets.sh && docker compose -f deploy/team-cloud/compose.yaml --env-file deploy/team-cloud/.env.example config >/tmp/hermes-team-cloud-compose-config.yaml && wc -l /tmp/hermes-team-cloud-compose-config.yaml`
  - 结果：生成本地 secrets；Docker Compose config 成功，标准化输出 `503` 行。
