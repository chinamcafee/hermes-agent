from __future__ import annotations

from pathlib import Path


DOC = Path("teamDoc/GADoc/P2-23-memory-runtime-docs.md")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")


def test_memory_runtime_docs_cover_api_provider_migration_and_ops():
    content = DOC.read_text(encoding="utf-8")

    assert "# P2-23 记忆和 runtime 文档" in content
    assert "## API" in content
    assert "/v1/memory/prefetch" in content
    assert "/api/chat/runs" in content
    assert "/api/runtime/events" in content
    assert "## Provider" in content
    assert "team_cloud/memory/provider.py" in content
    assert "personal" in content
    assert "team_shared" in content
    assert "## Migration" in content
    assert "scripts/team-cloud-import-sessiondb.py" in content
    assert "identity_map" in content
    assert "## Operations" in content
    assert "scripts/team-cloud-foundation-smoke.sh" in content
    assert "scripts/team-cloud-isolation-smoke.sh" in content
    assert "memory-performance-baseline-v0.json" in content


def test_memory_runtime_docs_link_p2_runtime_artifacts():
    content = DOC.read_text(encoding="utf-8")

    for expected in (
        "P2-11-team-memory-provider.md",
        "P2-18-cloud-session-history.md",
        "P2-19-runtime-event-bridge.md",
        "P2-20-isolation-test-suite.md",
        "P2-21-memory-performance-baseline.md",
        "P2-22-sessiondb-import.md",
    ):
        assert expected in content


def test_foundation_smoke_includes_memory_runtime_docs_check():
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "tests/team_cloud/test_memory_runtime_docs.py" in content
