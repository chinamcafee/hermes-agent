from __future__ import annotations

from pathlib import Path


INDEX = Path("teamDoc/releaseManual/README.md")
MANUAL = Path("teamDoc/releaseManual/team-cloud-ga-release-manual.md")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_release_manual_covers_all_ga_team_cloud_workflows():
    content = MANUAL.read_text(encoding="utf-8")

    required_sections = [
        "企业版团队功能开箱即用",
        "安装和首次登录",
        "组织、团队和成员管理",
        "设置团队成员的个人记忆环境",
        "配置团队共享记忆",
        "个人记忆与团队记忆两重记忆序列",
        "本地记忆定时备份",
        "备份恢复和组织导出",
        "权限、角色和 Permission Explorer",
        "工具策略、高危审批和 break-glass",
        "迁移 SessionDB 和 legacy memory provider",
        "Deployment smoke 和 GA 验证",
        "运维、支持和 Post-GA backlog",
    ]
    for section in required_sections:
        assert section in content

    required_terms = [
        "Casdoor",
        "SpiceDB",
        "PostgreSQL/pgvector",
        "MinIO",
        "TeamMemoryProvider",
        "personal",
        "team_shared",
        "identity_map",
        "personal_memory_enabled",
        "scripts/team-cloud-foundation-smoke.sh",
    ]
    for term in required_terms:
        assert term in content


def test_release_manual_index_and_smoke_registration():
    index = INDEX.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = SMOKE_MATRIX.read_text(encoding="utf-8")

    assert "team-cloud-ga-release-manual.md" in index
    assert "企业版团队功能" in index
    assert "tests/team_cloud/test_release_manual.py" in smoke
    assert "release_manual" in matrix
