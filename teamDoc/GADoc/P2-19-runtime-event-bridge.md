# P2-19 Runtime event bridge

日期：2026-05-22
状态：Implemented
前置：`P2-18 云会话历史`

## 目标

本步骤为 Team Cloud 增加 runtime event bridge，使 Hermes runtime 产生的 message/tool 事件能进入同一条 Web Chat run event viewer，并同步写入 P2-18 的云会话历史模型。该桥接层为后续真实流式 runtime 接入保留稳定 API。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/runtime_events.py` | `RuntimeEventBridge`，归一化 runtime event 并写入 chat run events、cloud messages 和 cloud tool calls。 |
| `team_cloud/chat.py` | 新增 `append_event()`，支持 run event viewer 追加 runtime events。 |
| `team_cloud/api.py` | 新增 `POST /api/runtime/events`，返回 `202 Accepted`。 |
| `tests/team_cloud/test_runtime_event_bridge.py` | 覆盖 assistant message、tool completed 和未知 session fail-closed。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 runtime event bridge 测试纳入平台 smoke。 |
| `teamDoc/GALog/2026-05-22-p2-19-runtime-event-bridge.md` | TDD 红绿记录和回归证据。 |

## API

`POST /api/runtime/events`

Request：

- `org_id`: organization id。
- `run_id`: Chat run id。
- `cloud_session_id`: Cloud session id。
- `type`: runtime event type。
- `payload`: event payload object。

支持的写入行为：

- `message.completed`、`assistant.message`、`tool.message`
  - 追加 Chat run event。
  - 写入 cloud message，默认 role 为 `assistant`。
- `tool.completed`、`tool.failed`
  - 追加 Chat run event。
  - 写入 cloud tool call。

## 失败语义

- 未知 cloud session：`404 cloud_session_not_found`。
- 未知 chat run：`404 chat_run_not_found`。
- org mismatch 或 payload 非对象：`400`。
- 未识别 event type：仍追加 run event，但不写 cloud message/tool call，便于后续扩展。

## 非目标

- 不直接调用 Hermes runtime 或 Gateway；本步骤只提供 Team Cloud 接收桥。
- 不实现 SSE/WebSocket 持续流；P2-17 event viewer 当前通过事件列表读取。
- 不实现 P3 工具风险审批；这里只保存 runtime 传入的 risk/decision 快照。

## 验证

- 红灯：`POST /api/runtime/events` 返回 404，runtime events 不写历史也不追加 run events。
- 绿灯：补齐 bridge、API 和 chat run event append 后，P2-19 焦点测试通过。
