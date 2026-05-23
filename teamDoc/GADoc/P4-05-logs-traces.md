# P4-05 Logs/traces

日期：2026-05-23
状态：Implemented
前置：`P4-04 Metrics dashboard`

## 目标

本步骤固定 Team Cloud Beta/GA 的日志和 trace 相关性 contract。每个关键事件需要能通过 `request_id`、`run_id`、`trace_id` 和 `correlation_id` 串联 HTTP request、Chat Run、runtime event 与 audit event。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/correlation.py` | 统一生成 request/run/audit/trace 相关性字段。 |
| `team_cloud/context.py` | 从 `x-request-id` 和 `x-trace-id` 生成请求上下文。 |
| `team_cloud/observability.py` | 在结构化 request event 中记录 run、audit、trace 和 correlation 字段。 |
| `team_cloud/audit.py` | 在 audit event 中记录并过滤 request/run/trace/correlation 字段。 |
| `team_cloud/chat.py` | 在 Chat Run 和 run event 中保留 request/run/trace/correlation 字段。 |
| `team_cloud/runtime_events.py` | Runtime event ingest 保留 payload 或 header 传入的相关性字段。 |
| `tests/team_cloud/test_logs_traces.py` | P4-05 contract 测试。 |

## 相关性规则

`correlation_id` 的优先级为：

1. 显式传入的 `correlation_id`
2. `trace_id`
3. `run_id`
4. `request_id`
5. `audit_event_id`

该规则保证运行链路、审计事件和 HTTP request 至少有一个可聚合的稳定 ID。

## 非目标

- 不引入 OpenTelemetry SDK 或外部 collector。
- 不改变现有 Prometheus 指标格式。
- 不把完整 prompt、tool input 或敏感内容写入日志。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_logs_traces.py
scripts/run_tests.sh tests/team_cloud/test_logs_traces.py tests/team_cloud/test_observability_baseline.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/correlation.py team_cloud/context.py team_cloud/observability.py team_cloud/audit.py team_cloud/chat.py team_cloud/runtime_events.py team_cloud/api.py tests/team_cloud/test_logs_traces.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/correlation.py team_cloud/context.py team_cloud/observability.py team_cloud/audit.py team_cloud/chat.py team_cloud/runtime_events.py team_cloud/api.py tests/team_cloud/test_logs_traces.py tests/team_cloud/test_platform_foundation_suite.py
scripts/team-cloud-foundation-smoke.sh
```
