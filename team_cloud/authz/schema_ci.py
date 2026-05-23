"""Static and zed-based SpiceDB schema CI helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Iterable

import yaml

from .spicedb import PRODUCT_PERMISSION_MAP


ZED_IMAGE = "authzed/zed:v1.1.1"
ASSERTION_RE = re.compile(r"^(?P<resource_type>[a-z_]+):[^#]+#(?P<permission>[a-z_]+)@")
DEFINITION_RE = re.compile(r"^definition\s+(?P<name>[a-z_]+)\s+\{")
PERMISSION_RE = re.compile(r"^\s*permission\s+(?P<name>[a-z_]+)\s*=")


class SchemaCIError(RuntimeError):
    """Raised when schema CI static validation fails."""


@dataclass(frozen=True)
class SchemaValidationReport:
    schema_path: Path
    validation_path: Path
    assert_true_count: int
    assert_false_count: int
    checked_permissions: tuple[str, ...]
    missing_permissions: tuple[str, ...]
    product_mapping_permissions: tuple[str, ...]
    product_mapping_missing: tuple[str, ...]


@dataclass(frozen=True)
class SchemaValidationPlan:
    schema_path: Path
    validation_path: Path
    zed_image: str = ZED_IMAGE

    @classmethod
    def default(cls, repo_root: Path | None = None) -> "SchemaValidationPlan":
        root = repo_root or Path(__file__).resolve().parents[2]
        artifact_dir = root / "teamDoc" / "GADoc" / "artifacts" / "spicedb"
        return cls(
            schema_path=artifact_dir / "schema-v0.zed",
            validation_path=artifact_dir / "schema-v0-validation.yaml",
        )

    def validate_static(self) -> SchemaValidationReport:
        schema_permissions = _parse_schema_permissions(self.schema_path.read_text())
        validation = _load_validation(self.validation_path)
        schema_file = validation.get("schemaFile")
        if schema_file != self.schema_path.name:
            raise SchemaCIError(
                f"validation schemaFile must be {self.schema_path.name}: {schema_file}"
            )

        true_assertions = _assertions(validation, "assertTrue")
        false_assertions = _assertions(validation, "assertFalse")
        checked_permissions = _checked_permissions(true_assertions + false_assertions)
        missing = tuple(
            sorted(
                permission
                for permission in checked_permissions
                if not _schema_has_permission(schema_permissions, permission)
            )
        )
        product_permissions = _product_mapping_permissions()
        product_missing = tuple(
            sorted(
                permission
                for permission in product_permissions
                if not _schema_has_permission(schema_permissions, permission)
            )
        )

        report = SchemaValidationReport(
            schema_path=self.schema_path,
            validation_path=self.validation_path,
            assert_true_count=len(true_assertions),
            assert_false_count=len(false_assertions),
            checked_permissions=tuple(sorted(checked_permissions)),
            missing_permissions=missing,
            product_mapping_permissions=tuple(sorted(product_permissions)),
            product_mapping_missing=product_missing,
        )
        if report.assert_true_count == 0 or report.assert_false_count == 0:
            raise SchemaCIError("validation fixture must include positive and negative assertions")
        if missing or product_missing:
            raise SchemaCIError(
                "schema validation references missing permissions: "
                + ", ".join(missing + product_missing)
            )
        return report

    def zed_validate_command(self) -> tuple[str, ...]:
        artifact_dir = self.schema_path.parent
        return (
            "docker",
            "run",
            "--rm",
            "-v",
            f"{artifact_dir}:/work",
            "-w",
            "/work",
            self.zed_image,
            "validate",
            "--type",
            "yaml",
            self.validation_path.name,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Team Cloud SpiceDB schema.")
    parser.add_argument("--check", action="store_true", help="Run static validation.")
    parser.add_argument(
        "--print-zed-command",
        action="store_true",
        help="Print the pinned dockerized zed validate command.",
    )
    parser.add_argument(
        "--run-zed",
        action="store_true",
        help="Run dockerized zed validate after static validation.",
    )
    args = parser.parse_args(argv)
    if not (args.check or args.print_zed_command or args.run_zed):
        args.check = True

    plan = SchemaValidationPlan.default()
    try:
        if args.check or args.run_zed:
            report = plan.validate_static()
            print(
                "static schema validation passed: "
                f"{report.assert_true_count} true, {report.assert_false_count} false"
            )
        if args.print_zed_command:
            print(shlex.join(plan.zed_validate_command()))
        if args.run_zed:
            subprocess.run(plan.zed_validate_command(), check=True)
    except (OSError, SchemaCIError, subprocess.CalledProcessError) as exc:
        print(f"schema validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _load_validation(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SchemaCIError(f"validation fixture must be a mapping: {path}")
    return payload


def _parse_schema_permissions(schema_text: str) -> dict[str, set[str]]:
    current_definition: str | None = None
    permissions: dict[str, set[str]] = {}
    for line in schema_text.splitlines():
        definition_match = DEFINITION_RE.match(line.strip())
        if definition_match:
            current_definition = definition_match.group("name")
            permissions.setdefault(current_definition, set())
            continue
        if line.strip() == "}":
            current_definition = None
            continue
        if current_definition is None:
            continue
        permission_match = PERMISSION_RE.match(line)
        if permission_match:
            permissions[current_definition].add(permission_match.group("name"))
    return permissions


def _assertions(validation: dict[str, object], key: str) -> list[str]:
    assertions = validation.get("assertions", {})
    if not isinstance(assertions, dict):
        raise SchemaCIError("validation assertions must be a mapping")
    values = assertions.get(key, [])
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise SchemaCIError(f"validation assertions.{key} must be a string list")
    return values


def _checked_permissions(assertions: Iterable[str]) -> set[str]:
    permissions = set()
    for assertion in assertions:
        match = ASSERTION_RE.match(assertion)
        if not match:
            raise SchemaCIError(f"invalid assertion format: {assertion}")
        permissions.add(f"{match.group('resource_type')}#{match.group('permission')}")
    return permissions


def _product_mapping_permissions() -> set[str]:
    permissions = set()
    for by_resource in PRODUCT_PERMISSION_MAP.values():
        for resource_type, permission in by_resource.items():
            permissions.add(f"{resource_type}#{permission}")
    return permissions


def _schema_has_permission(schema_permissions: dict[str, set[str]], permission: str) -> bool:
    resource_type, _, permission_name = permission.partition("#")
    return permission_name in schema_permissions.get(resource_type, set())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
