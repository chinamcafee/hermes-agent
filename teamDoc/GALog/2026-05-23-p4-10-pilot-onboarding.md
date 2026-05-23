# P4-10 Pilot onboarding 工作日志

## 背景

- 工作包：`P4-10 | Pilot onboarding | 试点团队导入、培训、反馈表 | P4-01 | 1.5`
- 当前阶段：P4 Beta 验证，P4-01 到 P4-09 已完成。
- 设计依据：P4 试点要求选择 3 个团队、导入成员和初始项目、配置 Gateway 平台、连续运行 2 周并收集反馈。

## 执行计划

1. 用 contract 测试定义 pilot onboarding plan、artifact、脚本和 smoke 注册。
2. 新增 pilot onboarding builder 和生成脚本。
3. 新增 P4-10 文档和 JSON artifact。
4. 运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P4-10 已在进度表中标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_pilot_onboarding.py` 出现 2 个预期失败，指向 `team_cloud.pilot` 缺失和 pilot onboarding artifact/docs/smoke 注册缺口。
- 2026-05-23：新增 `team_cloud/pilot.py`、`scripts/team-cloud-pilot-onboarding.py`、P4-10 文档和 pilot onboarding artifact，覆盖 3 个试点团队、Gateway 平台、Casdoor group 导入、14 天运行和周反馈节奏。
- 2026-05-23：pilot onboarding 生成脚本通过，`scripts/team-cloud-pilot-onboarding.py --output teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json` 输出 `status=written`。
- 2026-05-23：首次绿灯尝试发现 P4-10 文档缺少 `pilot_teams` 字段名，已补齐文档 contract。
- 2026-05-23：绿灯验证通过，`scripts/run_tests.sh tests/team_cloud/test_pilot_onboarding.py` 结果为 1 个文件、2 个测试通过。
- 2026-05-23：相关回归通过，`scripts/run_tests.sh tests/team_cloud/test_pilot_onboarding.py tests/team_cloud/test_platform_foundation_suite.py` 结果为 2 个文件、5 个测试通过。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/pilot/team-cloud-pilot-onboarding-v0.json >/dev/null`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null` 和 `git diff --check ...` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 结果为 78 个文件、265 个测试通过。
