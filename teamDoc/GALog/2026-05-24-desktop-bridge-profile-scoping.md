# 2026-05-24 Desktop Bridge profile scoping

## 问题

收尾自审发现 Desktop 调用 Hermes Agent Bridge 时会传 `profile` query，但新增 Bridge 端点没有使用该参数，存在多 profile 场景读写默认 profile 的风险。

## 红灯

新增 `tests/hermes_cli/test_web_server_team_bridge_profiles.py` 后，三个测试均失败：

- `/api/soul/status?profile=worker` 返回默认 `HERMES_HOME`。
- `/api/cloud-backup/status?profile=backup-worker` 返回默认 `HERMES_HOME`。
- `/api/team/status?profile=team-worker` 返回默认 `HERMES_HOME`。

## 修复

- `hermes_cli/web_server.py` 新增 `_call_with_profile_home()`。
- Bridge 端点在调用 `team_status`、`resolve_soul_state`、`save_local_soul`、`cloud_backup_status`、`run_cloud_backup_now`、`schedule_cloud_backup` 前按 query profile 设置 context-local Hermes home override。

## 绿灯

```bash
venv/bin/python -m pytest tests/hermes_cli/test_web_server_team_bridge_profiles.py -q
```

结果：`3 passed`。
