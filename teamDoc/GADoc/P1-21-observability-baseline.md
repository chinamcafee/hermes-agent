# P1-21 观测基线

日期：2026-05-22
状态：Implemented
前置：`P1-01 Team Cloud repo/package 骨架`

## 目标

本步骤为 Team Cloud API 增加最小可测试观测基线：健康检查、Prometheus 风格请求计数和结构化请求事件。当前实现使用内存统计，避免在 P1 阶段引入外部 Prometheus、OpenTelemetry collector 或日志后端依赖。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/observability.py` | 内存请求计数、结构化事件和 Prometheus 文本渲染。 |
| `team_cloud/api.py` | 安装 observability middleware 并新增 `/metrics`。 |
| `tests/team_cloud/test_observability_baseline.py` | metrics、request events、readyz checks 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | smoke matrix 增加 observability domain。 |
| `scripts/team-cloud-foundation-smoke.sh` | P1 smoke 增加观测基线测试。 |

## 行为

- `/healthz`：
  - 返回 service、status、version。
- `/readyz`：
  - 保留 `checks.config` 和 `checks.migrations`。
- `/metrics`：
  - 返回 `text/plain; version=0.0.4`。
  - 暴露 `team_cloud_http_requests_total{method,path,status}` counter。
- Structured events：
  - `app.state.observability.events` 记录 `http.request`。
  - 字段包含 method、path、status_code、duration_ms、request_id。

## 非目标

- 不接入真实 Prometheus registry。
- 不引入 OpenTelemetry SDK。
- 不实现分布式 tracing。
- 不实现日志后端或 dashboard。

## 后续衔接

- `P4-04/P4-05`：扩展为真实 metrics dashboard、logs 和 traces。
- `P5-06`：将观测指标纳入 runbook。
