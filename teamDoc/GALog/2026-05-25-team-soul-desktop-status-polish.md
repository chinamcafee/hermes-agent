# 2026-05-25 Team Soul / Desktop Team 状态打磨

## 背景

本轮针对验收反馈修复四类问题：

- Team Cloud Dashboard 中团队父人格配置中心不够显性。
- Desktop/CLI 在 team mode 下的 Persona 展示需要稳定区分团队父人格、本地人格和合并后人格。
- Desktop Team 状态必须把 Team Cloud URL 和成员帐号登录作为整体校验。
- Desktop Chat 主动取消请求时不应显示 `Stream error: aborted`。

## 代码调整

- `hermes_cli/team_cloud.py`：`team_status()` 增加 `connection_configured`、`token_configured`、`account_authenticated`、`login_required`、`saved_context`，并把可用 Team mode 收敛到成功校验 Team Cloud session。
- `hermes_cli/team_soul.py`：父人格未配置时，只要 Team context 可用仍返回 `mode=team`，并返回空 `team_parent_soul`、`merge_status=team_parent_missing`。
- `team_cloud/dashboard/src/app/page.tsx`：Dashboard 导航改为“团队父人格中心”，概览页增加团队父人格配置中心说明。
- `hermes-desktop/src/main/team-bridge.ts`：本地 API Bridge 返回 stale local 状态时，读取 CLI fallback 并优先使用更完整的已登录 Team 状态。
- `hermes-desktop/src/renderer/src/screens/Team/Team.tsx` 与 `Layout.tsx`：按 URL + 有效成员 session + context 判断团队模式；URL 已配置但未登录时显示 `Team login required`。
- `hermes-desktop/src/renderer/src/screens/Chat/hooks/useLocalCommands.ts`：`/persona` 在 team mode 下展示三段人格。
- `hermes-desktop/src/main/hermes.ts`：主动 abort API stream 时静默完成，不再上报 `Stream error: aborted`。

## 测试记录

- `./scripts/run_tests.sh tests/hermes_cli/test_team_soul.py tests/hermes_cli/test_team_cloud_cli.py`：通过。
- `npm test -- tests/team-bridge-api.test.ts src/renderer/src/screens/Team/Team.test.tsx src/renderer/src/screens/Chat/hooks/useLocalCommands.test.tsx tests/hermes-api-abort.test.ts`：通过。
- `cd team_cloud/dashboard && npm test -- src/app/page.test.tsx`：通过。

## 部署记录

- 使用 `minikube image build -t hermes-team-cloud-go:gtc90-20260525193713 team_cloud` 构建新镜像。
- 使用 `kubectl -n hermes-team-cloud set image deployment/hermes-team-cloud-go team-cloud-go=hermes-team-cloud-go:gtc90-20260525193713` 做非破坏性滚动更新。
- `kubectl rollout status` 完成，Deployment `hermes-team-cloud-go` 为 `2/2 ready`。
- PostgreSQL、Redis、MinIO PVC 保持 Bound，未删除初始化数据。
- `curl http://127.0.0.1:8780/healthz` 返回 `status=ok`，`/v1/bootstrap/status` 返回 `initialized=true`。
