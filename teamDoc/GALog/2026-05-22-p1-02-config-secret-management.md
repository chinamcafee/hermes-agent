# P1-02 配置和 secret 管理

## 工作目标

- 按 `teamDoc/GAStep/01-work-package-register.md` 的 P1-02 执行。
- 主要产出：config loader、env schema、secret 分层。
- 遵循 `teamDoc/GADoc/P0-05-local-topology-design.md` 的 secret 注入规则：
  - `.env.example` 只放非敏感默认值、端口和 image tag。
  - Team API 使用 `*_FILE` 读取 sensitive values。
  - 禁止在 compose、日志、health output 中打印 secret 值。

## 2026-05-22 执行记录

### 1. 启动 P1-02

- 前置确认：P1-01 已在 `progress-tracker.md` 标记 `Done`。
- 当前边界：不实现 compose、不连接真实外部服务、不新增依赖。
- 本粒度只增强 Team Cloud 配置/secret 层，输出可供 P1-03 compose 复用的 schema 和示例工件。

### 2. 红灯测试设计

- 新增 `tests/team_cloud/test_config_secret_management.py`，覆盖：
  - env schema 覆盖 P0-05 指定的 `TEAM_CLOUD_*_FILE` secret 变量。
  - `.env.example` 生成器不输出 secret 明文或 direct secret env。
  - env file secret path 可覆盖 yaml secret file path，但 direct yaml value 仍高于 secret file。
  - missing secret file 可被 preflight 报告，`load_config()` fail fast 且不泄露 secret 内容。
  - GADoc artifact 示例与 env schema 保持一致。

### 3. 最小实现

- 增强 `team_cloud.config`：
  - 新增 `ENV_SCHEMA` 和 `EnvVarSpec`，覆盖 P0-05 指定的 file secret env。
  - 新增 `render_env_example()`，只输出 non-secret defaults 和 `*_FILE` 路径。
  - 新增 `SecretFileError`、`SecretFileStatus`、`validate_secret_files()`。
  - 支持 env `*_FILE` secret path 覆盖 yaml `*_file` secret path。
  - 支持 direct yaml/direct env 高于 secret file，便于本地测试和显式覆盖。
  - 保留 `oidc_client_secret`/`oidc_client_secret_file` 作为 early P1 alias。
- 新增 GADoc：
  - `teamDoc/GADoc/P1-02-config-secret-management.md`
  - `teamDoc/GADoc/artifacts/team-cloud/team-cloud.env.example`
  - `teamDoc/GADoc/artifacts/team-cloud/team-cloud.config.example.yaml`

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_config_secret_management.py`
  - 结果：`5 tests` 中 `4 failed, 1 passed`。
  - 失败点：缺少 `ENV_SCHEMA`、`render_env_example`、`SecretFileError`、`validate_secret_files`，以及 env file secret path 尚未覆盖 yaml secret file path。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py`
  - 结果：`13 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py`
  - 结果：`19 tests passed, 0 failed`。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
