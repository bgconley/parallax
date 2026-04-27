from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RETIRED_PATTERNS = (
    r"lumentask",
    r"lumen task",
    r"\[APP_NAME\]",
    r"temporal_app",
    r"temporal-app",
    r"Temporal App",
)

READ_ONLY_POST_OPERATION_IDS = {"resolveActivity", "resolveUserPlace"}


@dataclass(frozen=True)
class ContractValidationResult:
    checked_files: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_artifact_contracts(artifact_root: Path) -> ContractValidationResult:
    root = artifact_root.resolve()
    errors: list[str] = []
    checked_files = 0

    required = [
        "contracts/openapi/parallax_api_v1_3.yaml",
        "contracts/events/parallax_event_contracts_v1_3.yaml",
        "contracts/jobs/parallax_workflows_v1_3.yaml",
    ]
    for rel_path in required:
        path = root / rel_path
        checked_files += 1
        if not path.exists():
            errors.append(f"missing required contract: {rel_path}")

    for path in root.rglob("*.json"):
        checked_files += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - exact parser message is platform-specific
            errors.append(f"json parse failure: {path.relative_to(root)}: {exc}")

    for path in [*root.rglob("*.yaml"), *root.rglob("*.yml")]:
        checked_files += 1
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            errors.append(f"yaml parse failure: {path.relative_to(root)}: {exc}")

    for path in root.rglob("*.py"):
        checked_files += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            errors.append(f"python parse failure: {path.relative_to(root)}: {exc}")

    openapi_path = root / "contracts/openapi/parallax_api_v1_3.yaml"
    if openapi_path.exists():
        openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
        errors.extend(_validate_mutation_envelopes(openapi))

    for path in _text_contract_files(root):
        checked_files += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in RETIRED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"retired naming pattern found in {path.relative_to(root)}")

    return ContractValidationResult(checked_files=checked_files, errors=errors)


def _text_contract_files(root: Path) -> list[Path]:
    suffixes = {".md", ".txt", ".yaml", ".yml", ".json", ".sql", ".py", ".sh", ".css"}
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "validate_pack.py" and path.suffix.lower() in suffixes
    ]


def _validate_mutation_envelopes(openapi: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for path, path_item in openapi.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in {"post", "put", "patch", "delete"}:
                continue
            operation_id = operation.get("operationId", f"{method.upper()} {path}")
            request_body = operation.get("requestBody")
            if operation_id in READ_ONLY_POST_OPERATION_IDS:
                if request_body and _operation_requires_mutation(openapi, request_body):
                    errors.append(
                        f"read-only resolver unexpectedly requires mutation: {operation_id}"
                    )
                continue
            if not request_body:
                errors.append(f"mutating operation missing requestBody: {operation_id}")
                continue
            if not _operation_requires_mutation(openapi, request_body):
                errors.append(
                    f"mutating operation missing required mutation envelope: {operation_id}"
                )
    return errors


def _operation_requires_mutation(openapi: dict[str, Any], request_body: dict[str, Any]) -> bool:
    schema = (
        request_body.get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    resolved = _resolve_schema_ref(openapi, schema)
    properties = resolved.get("properties", {})
    required = set(resolved.get("required", []))
    return "mutation" in properties and "mutation" in required


def _resolve_schema_ref(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref or not ref.startswith("#/components/schemas/"):
        return schema
    name = ref.rsplit("/", 1)[-1]
    return openapi.get("components", {}).get("schemas", {}).get(name, schema)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Parallax artifact contracts.")
    parser.add_argument("artifact_root", type=Path)
    args = parser.parse_args()

    result = validate_artifact_contracts(args.artifact_root)
    if result.errors:
        print("CONTRACT VALIDATION FAILED")
        for error in result.errors:
            print(f"- {error}")
        return 1
    print(f"CONTRACT VALIDATION PASSED ({result.checked_files} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
