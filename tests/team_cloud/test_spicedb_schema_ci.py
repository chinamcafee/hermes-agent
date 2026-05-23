from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_schema_ci_static_validation_covers_positive_and_negative_fixtures():
    from team_cloud.authz.schema_ci import SchemaValidationPlan

    report = SchemaValidationPlan.default().validate_static()

    assert report.schema_path.name == "schema-v0.zed"
    assert report.validation_path.name == "schema-v0-validation.yaml"
    assert report.assert_true_count >= 10
    assert report.assert_false_count >= 8
    assert "memory#read_personal" in report.checked_permissions
    assert "tool#terminal_execute" in report.checked_permissions
    assert report.missing_permissions == ()


def test_schema_ci_validates_product_permission_map_against_schema():
    from team_cloud.authz.schema_ci import SchemaValidationPlan

    report = SchemaValidationPlan.default().validate_static()

    assert report.product_mapping_missing == ()
    assert "project#run_agent" in report.product_mapping_permissions
    assert "session#run" in report.product_mapping_permissions


def test_zed_validate_command_uses_pinned_image_and_fixture():
    from team_cloud.authz.schema_ci import SchemaValidationPlan

    command = SchemaValidationPlan.default().zed_validate_command()

    assert "authzed/zed:v1.1.1" in command
    assert "validate" in command
    assert "--type" in command
    assert "schema-v0-validation.yaml" in command


def test_schema_ci_script_runs_static_check():
    script = Path("scripts/team-cloud-spicedb-schema-ci.sh")

    assert script.exists()
    assert os.access(script, os.X_OK)

    result = subprocess.run(
        [str(script), "--static-only"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "static schema validation passed" in result.stdout
