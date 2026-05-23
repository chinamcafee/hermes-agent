# P1-02 配置和 Secret 管理

日期：2026-05-22
状态：Implemented
前置：`P1-01 Team Cloud repo/package 骨架`

## 目标

本步骤落地 Team Cloud 的配置与 secret 分层，供后续 `P1-03 本地 compose 栈` 和 P1 Auth/Storage 组件复用。范围只包含配置解析、env schema、secret file preflight、示例工件和脱敏规则，不连接真实外部服务。

## 配置优先级

Team Cloud config loader 使用以下优先级：

1. direct env，例如 `TEAM_CLOUD_API_PORT`。
2. direct yaml，例如 `api_port: 8780`。
3. secret file，其中 env `*_FILE` 路径高于 yaml `*_file` 路径。
4. typed defaults。

当 direct env 或 direct yaml 已提供某个 secret 字段时，loader 不再读取该字段的 secret file，避免无关的缺失文件阻塞本地测试。P1 compose 默认使用 `*_FILE`，不在 `.env.example` 放 secret 明文。

## Secret 分层

| Field | Recommended env | YAML key | 说明 |
| --- | --- | --- | --- |
| `database_url` | `TEAM_CLOUD_DATABASE_URL_FILE` | `database_url_file` | Team Cloud PostgreSQL URL。 |
| `casdoor_client_secret` | `TEAM_CLOUD_CASDOOR_CLIENT_SECRET_FILE` | `casdoor_client_secret_file` | Casdoor Team API client secret。 |
| `spicedb_preshared_key` | `TEAM_CLOUD_SPICEDB_PRESHARED_KEY_FILE` | `spicedb_preshared_key_file` | SpiceDB pre-shared key。 |
| `minio_secret_key` | `TEAM_CLOUD_MINIO_SECRET_KEY_FILE` | `minio_secret_key_file` | MinIO service account secret key。 |
| `encryption_key` | `TEAM_CLOUD_ENCRYPTION_KEY_FILE` | `encryption_key_file` | Backup/export envelope encryption key。 |

Legacy `oidc_client_secret` and `oidc_client_secret_file` remain accepted as aliases for `casdoor_client_secret` during early P1 migration.

## 工件

| 工件 | 用途 |
| --- | --- |
| [team-cloud.env.example](artifacts/team-cloud/team-cloud.env.example) | P1-03 compose `.env.example` 输入。 |
| [team-cloud.config.example.yaml](artifacts/team-cloud/team-cloud.config.example.yaml) | YAML config 示例，展示 non-secret 值和 secret file key。 |

## 验证

- `tests/team_cloud/test_config_secret_management.py` 覆盖 env schema、example redaction、secret file precedence、missing-file preflight 和 artifact consistency。
- `tests/team_cloud/test_skeleton.py` 继续覆盖 P1-01 package/API/worker/migration/logging 骨架。
