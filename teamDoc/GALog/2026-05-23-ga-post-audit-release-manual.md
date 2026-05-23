# GA post-audit releaseManual 工作日志

## 背景

- 用户要求：复盘 P1~P5 是否完整达到 GA；确认后在 `teamDoc/releaseManual` 编写所有新增功能使用手册。
- 当前基线：`progress-tracker.md` 已显示 P5 100% Done，M5 GA Sign-off Done。

## 执行计划

1. 并行复盘 P1/P2、P3/P4、P5/M5 证据和 smoke 覆盖。
2. 用红灯测试固定 releaseManual 覆盖范围。
3. 编写 `teamDoc/releaseManual/README.md` 和 `team-cloud-ga-release-manual.md`。
4. 将 release manual 验收测试注册到 foundation smoke。
5. 运行 release manual 绿灯、关联回归、静态检查、JSON 校验、完整 smoke。

## 实时记录

- 2026-05-23：新增红灯测试 `tests/team_cloud/test_release_manual.py`，确认失败原因为 `teamDoc/releaseManual/README.md` 和 `team-cloud-ga-release-manual.md` 缺失。
- 2026-05-23：新增 releaseManual 索引和 Team Cloud GA 使用手册，覆盖企业版团队功能、个人记忆环境、团队共享记忆、本地记忆定时备份、权限治理、迁移、部署验证和运维支持。
- 2026-05-23：根据并行复盘反馈新增红灯覆盖：P4-18 必须逐项引用 GA matrix，P5-13 必须包含 fresh environment smoke 契约，GA release checklist 必须同步 M5 signed 状态。
- 2026-05-23：本机执行 `docker compose -f deploy/team-cloud/compose.yaml config` 通过；`helm` 本地缺失，P5-13 artifact 记录为 `blocked_local_tool_missing` 并要求 CI/发布环境补跑 Helm lint/upgrade/rollback。
- 2026-05-23：本机 fresh Compose smoke 首次执行失败，Docker 报告 `minio/mc:RELEASE.2025-09-07T16-13-09Z` manifest 不存在。新增红灯测试后将 compose/offline manifest/offline bundle script 的 mc client tag 修正为 `minio/mc:RELEASE.2025-08-13T08-35-41Z`。
- 2026-05-23：P5/M5 复盘继续发现 P5-13 证据缺口：Python base、Alpine init、应用镜像 tag、SpiceDB/zed 镜像和 offline manifest 缺少 registry-limited 覆盖；新增红灯测试后完成镜像覆盖变量、offline manifest 全量覆盖、bundle script 从 manifest 生成 `images.txt`。
- 2026-05-23：fresh Compose smoke 第二轮失败于 `.dockerignore` 排除 `README.md`，导致 Docker build 无法复制 package metadata；新增红灯测试后加入 `!README.md` 例外。
- 2026-05-23：fresh Compose smoke 第三轮失败于 PostgreSQL 18 数据卷挂载 `/var/lib/postgresql/data`；新增红灯测试后改为 `/var/lib/postgresql`。
- 2026-05-23：fresh Compose smoke 第四轮暴露 SpiceDB/zed slim 镜像无 shell、Casdoor 缺少 `team-data` 网络、SpiceDB healthcheck 依赖缺失 `nc`、nginx healthcheck 使用 `localhost` 连接拒绝；新增红灯测试后切换同版本 `ghcr.io/authzed/*:*debug` 本地 compose 镜像、补 Casdoor data 网络、改 healthcheck，并移除 `zed context set` 以避免 keyring TTY 提示。
- 2026-05-23：`docker compose -p hermes-team-cloud-ga-smoke -f deploy/team-cloud/compose.yaml up --build --wait --wait-timeout 300` 通过，PostgreSQL、Casdoor、SpiceDB、MinIO、Mailpit、Team API、Team worker、Team Web、Hermes runtime 全部 healthy。
- 2026-05-23：`helm lint deploy/team-cloud/helm/hermes-team-cloud` 通过；创建 `kind-hermes-ga-smoke` 后执行 Helm install、upgrade 和 rollback 通过，P5-13 artifact 更新为 `helm_lint_status=passed` 和 `helm_runtime_status=passed`。
- 2026-05-23：P4-18 beta exit 把 `GA-REL-002` 更正为 P5 followup，并补齐 final regression、legal compliance、admin/user manuals、API docs、runbook summary、releaseManual、deployment smoke Helm runtime validation 等 P5 followups。
- 2026-05-23：`teamDoc/16-ga-test-release-checklist.md` 补齐 `Release operations | Release | signed`，与 P5-08 GA sign-off artifact 对齐。
- 2026-05-23：GA 最终复盘发现 P5-13 artifact 对 Helm runtime 真实序列记录不完整；新增红灯断言 `config.logLevel=DEBUG` 必须同时出现在 `helm_runtime_command` 和 `helm_upgrade_rollback.command`，确认失败后修正 `team_cloud/deployment_smoke.py`、重新生成 `team-cloud-deployment-smoke-v0.json`，并同步 `P5-13-deployment-smoke.md`。
- 2026-05-23：受子代理线程上限影响，仅成功启动一个 P1~P2 只读审计代理；P3~P5 由主会话按进度表、foundation smoke 矩阵、releaseManual 验收和 artifact 契约继续复盘。
- 2026-05-23：取回上一轮 5 个复盘子代理结果。子代理早前指出的 registry-limited 镜像覆盖、offline manifest、P4-18 GA matrix coverage、P5-13 fresh/Helm 证据、releaseManual、GA checklist sign-off 缺口，当前工作区均已通过文件核对和新鲜测试闭环；P1/P2 子代理结论为无 P1/P2 GA 阻塞。

## 验证记录

- `scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py`：8 files，30 tests passed，0 failed。
- `scripts/team-cloud-foundation-smoke.sh`：103 files，322 tests passed，0 failed。
- `venv/bin/ruff check team_cloud/deployment_smoke.py team_cloud/beta_exit.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
- `venv/bin/python -m py_compile ...`：通过。
- JSON 校验：`team-cloud-beta-exit-report-v0.json`、`team-cloud-deployment-smoke-v0.json`、`platform-foundation-smoke-v0.json` 均通过。
- Fresh compose：`docker compose ... config` 生成 626 行配置；`docker compose ... up --build --wait --wait-timeout 300` 通过。
- Helm：`helm lint` 0 failed；`helm upgrade --install`、二次 `helm upgrade`、`helm rollback ... 1` 均通过，最终 release status 为 `deployed`。
- GA 最终 artifact 修正后新鲜验证：
  - `scripts/run_tests.sh tests/team_cloud/test_deployment_smoke.py`：2 tests passed，0 failed。
  - `scripts/run_tests.sh tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py`：8 files，30 tests passed，0 failed。
  - `scripts/team-cloud-foundation-smoke.sh`：103 files，322 tests passed，0 failed。
  - `venv/bin/ruff check team_cloud/deployment_smoke.py team_cloud/beta_exit.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py`：All checks passed。
  - `venv/bin/python -m py_compile team_cloud/deployment_smoke.py team_cloud/beta_exit.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_compose_hardening.py tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_deployment_smoke.py tests/team_cloud/test_beta_exit_report.py tests/team_cloud/test_ga_release_checklist.py tests/team_cloud/test_release_manual.py tests/team_cloud/test_platform_foundation_suite.py scripts/team-cloud-deployment-smoke.py`：通过。
  - `venv/bin/python -m json.tool` 校验 `team-cloud-beta-exit-report-v0.json`、`team-cloud-deployment-smoke-v0.json`、`platform-foundation-smoke-v0.json`：通过。
  - `docker compose -f deploy/team-cloud/compose.yaml config`：生成 625 行配置。
  - `helm lint deploy/team-cloud/helm/hermes-team-cloud`：1 chart linted，0 failed。
  - `git diff --check -- . ':!uv.lock'`：通过。
