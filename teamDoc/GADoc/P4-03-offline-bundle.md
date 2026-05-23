# P4-03 Offline bundle

日期：2026-05-23
状态：Implemented
前置：`P4-02 Helm chart`

## 目标

本步骤固定 Team Cloud air-gapped 交付包 contract。离线包包含镜像归档、Helm chart archive、checksum manifest 和安装脚本，为无公网环境安装与 P5 deployment smoke 提供输入。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/offline/manifest.yaml` | 离线包 schema、chart、镜像和 checksum contract。 |
| `deploy/team-cloud/offline/install.sh` | 离线主机安装脚本，校验 checksum、加载镜像并执行 Helm install/upgrade。 |
| `deploy/team-cloud/offline/README.md` | air-gapped build/install 操作说明。 |
| `scripts/team-cloud-offline-bundle.sh` | 在线构建侧脚本，生成 chart archive、`images.txt`、image tar 和 `SHA256SUMS`。 |
| `tests/team_cloud/test_offline_bundle.py` | 静态 contract 测试。 |

## Bundle Contract

- `manifest.yaml` 必须列出 chart path、chart archive、install script、checksum 文件和所有镜像。
- 构建脚本必须执行 `helm package`、`docker save` 和 `sha256sum`。
- 安装脚本必须执行 `sha256sum -c SHA256SUMS`、`docker load` 和 `helm upgrade --install`。
- 生成物目录默认是 `deploy/team-cloud/offline/dist/hermes-team-cloud-offline`，不入库。

## 非目标

- 不在 CI 中真实拉取或保存镜像。
- 不要求本地安装 Helm/Docker 才能通过静态 contract 测试。
- 不执行新环境安装；P5-13 处理 deployment smoke。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py
scripts/run_tests.sh tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile tests/team_cloud/test_offline_bundle.py tests/team_cloud/test_helm_chart.py tests/team_cloud/test_platform_foundation_suite.py
scripts/team-cloud-foundation-smoke.sh
```
