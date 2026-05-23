# P4-04 Metrics dashboard

日期：2026-05-23
状态：Implemented
前置：`P3 数据治理与权限硬化`

## 目标

本步骤固定 Team Cloud Beta/GA 的 metrics dashboard contract。P1-21 已提供 Team API 请求计数，本步骤补充 dashboard 必须覆盖的监控域：Team API、SpiceDB、PostgreSQL pgvector、MinIO、worker lag、audit/security。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/observability.py` | 新增 `METRICS_CATALOG`，固定 dashboard 依赖的指标名称、domain 和类型。 |
| `teamDoc/GADoc/artifacts/observability/team-cloud-grafana-dashboard-v0.json` | Grafana dashboard JSON artifact。 |
| `tests/team_cloud/test_metrics_dashboard.py` | 静态 contract 测试。 |

## 指标域

| Domain | 指标 |
| --- | --- |
| Team API | `team_cloud_http_requests_total` |
| SpiceDB | `team_cloud_spicedb_check_latency_ms`、`team_cloud_spicedb_denies_total` |
| PostgreSQL pgvector | `team_cloud_pgvector_query_latency_ms` |
| MinIO | `team_cloud_minio_operation_latency_ms` |
| Worker | `team_cloud_worker_lag_seconds` |
| Audit/security | `team_cloud_audit_events_total` |

## 非目标

- 不部署真实 Grafana/Prometheus。
- 不引入 OpenTelemetry SDK。
- 不保证所有指标已由 runtime emit；P4-05/P4-16 可继续接入真实采集点。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_metrics_dashboard.py
scripts/run_tests.sh tests/team_cloud/test_metrics_dashboard.py tests/team_cloud/test_observability_baseline.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/observability.py tests/team_cloud/test_metrics_dashboard.py tests/team_cloud/test_observability_baseline.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/observability.py tests/team_cloud/test_metrics_dashboard.py tests/team_cloud/test_observability_baseline.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/observability/team-cloud-grafana-dashboard-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
