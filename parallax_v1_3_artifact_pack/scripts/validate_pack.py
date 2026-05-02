#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "AGENT_START_HERE.md",
    "docs/01_app_system_spec.md",
    "docs/02_temporal_domain_model.md",
    "docs/03_phased_implementation_plan.md",
    "database/README.md",
    "contracts/openapi/parallax_api_v1_3.yaml",
    "contracts/events/parallax_event_contracts_v1_3.yaml",
    "contracts/jobs/parallax_workflows_v1_3.yaml",
    "contracts/json_schema/context_capture_policy.schema.json",
    "contracts/json_schema/timing_review_flag.schema.json",
    "contracts/design/design_tokens.json",
    "database/migrations/0014_timing_review_flags.sql",
    "database/migrations/0015_firebase_external_identity.sql",
    "database/optional_profiles/0009_timescale_optional_analytics_profile.sql",
    "database/optional_profiles/0010_paradedb_optional_search_profile.sql",
    "database/optional_profiles/0012_postgis_optional_geospatial_profile.sql",
    "database/optional_profiles/0013_timescale_capture_context_profile.sql",
    "docs/23_agentic_implementation_guardrails.md",
]

RETIRED_PATTERNS = [
    r"lumentask",
    r"lumen task",
    r"\[APP_NAME\]",
    r"temporal_app",
    r"temporal-app",
    r"Temporal App",
]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def parse_manifest() -> dict[str, tuple[int, str]]:
    manifest = ROOT / "MANIFEST.txt"
    rows: dict[str, tuple[int, str]] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        rel, size, checksum = [part.strip() for part in line.split("|")]
        rows[rel] = (int(size), checksum)
    return rows

def resolve_openapi_ref(openapi: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/components/schemas/"):
        return schema
    name = ref.rsplit("/", 1)[-1]
    return openapi.get("components", {}).get("schemas", {}).get(name, schema)

def schema_requires_mutation(openapi: dict, schema: dict) -> bool:
    resolved = resolve_openapi_ref(openapi, schema)
    properties = resolved.get("properties", {})
    required = set(resolved.get("required", []))
    return "mutation" in properties and "mutation" in required

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Parallax v1.3 artifact pack.")
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Optional explicit path to parallax_v1_3_artifact_pack.zip for ZIP content validation.",
    )
    parser.add_argument(
        "--skip-zip-check",
        action="store_true",
        help="Skip ZIP content validation. Useful after extracting the pack into another repository.",
    )
    parser.add_argument(
        "--require-zip",
        action="store_true",
        help="Fail when no ZIP is available. By default a missing sibling ZIP is advisory.",
    )
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        p = ROOT / rel
        if not p.exists():
            errors.append(f"missing required file: {rel}")
        elif p.stat().st_size == 0:
            errors.append(f"empty required file: {rel}")

    for p in ROOT.rglob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"json parse failure: {p.relative_to(ROOT)}: {exc}")

    if yaml is not None:
        for p in list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml")):
            try:
                yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"yaml parse failure: {p.relative_to(ROOT)}: {exc}")

    for p in ROOT.rglob("*.py"):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"python parse failure: {p.relative_to(ROOT)}: {exc}")

    sql_files = sorted((ROOT / "database/migrations").glob("*.sql"))
    expected_prefixes = [
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
        "0007",
        "0008",
        "0011",
        "0014",
        "0015",
        "0016",
        "0017",
        "0018",
        "9999",
    ]
    found_prefixes = [p.name[:4] for p in sql_files]
    for prefix in expected_prefixes:
        if prefix not in found_prefixes:
            errors.append(f"missing migration prefix: {prefix}")

    optional_files = sorted((ROOT / "database/optional_profiles").glob("*.sql"))
    expected_optional_prefixes = ["0009","0010","0012","0013"]
    found_optional_prefixes = [p.name[:4] for p in optional_files]
    for prefix in expected_optional_prefixes:
        if prefix not in found_optional_prefixes:
            errors.append(f"missing optional profile prefix: {prefix}")

    for p in sql_files:
        text = p.read_text(encoding="utf-8")
        if not text.strip().endswith(";"):
            errors.append(f"sql file does not end with semicolon: {p.relative_to(ROOT)}")
        if "BEGIN;" in text and "COMMIT;" not in text:
            errors.append(f"sql file has BEGIN without COMMIT: {p.relative_to(ROOT)}")

    for p in optional_files:
        text = p.read_text(encoding="utf-8")
        if not text.strip().endswith(";"):
            errors.append(f"optional profile sql file does not end with semicolon: {p.relative_to(ROOT)}")
        if "BEGIN;" in text and "COMMIT;" not in text:
            errors.append(f"optional profile sql file has BEGIN without COMMIT: {p.relative_to(ROOT)}")

    if yaml is not None:
        openapi_path = ROOT / "contracts/openapi/parallax_api_v1_3.yaml"
        openapi = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
        read_only_post_exceptions = {
            "resolveActivity",
            "resolveUserPlace",
            "previewActivityMerge",
            "previewActivitySplit",
        }
        for path, path_item in openapi.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in {"post", "put", "patch", "delete"}:
                    continue
                operation_id = operation.get("operationId", f"{method.upper()} {path}")
                request_body = operation.get("requestBody")
                if operation_id in read_only_post_exceptions:
                    if request_body:
                        content = request_body.get("content", {})
                        schema = content.get("application/json", {}).get("schema", {})
                        if schema_requires_mutation(openapi, schema):
                            errors.append(f"read-only resolver unexpectedly requires mutation: {operation_id}")
                    continue
                if not request_body:
                    errors.append(f"mutating operation missing requestBody: {operation_id}")
                    continue
                content = request_body.get("content", {})
                schema = content.get("application/json", {}).get("schema", {})
                if not schema_requires_mutation(openapi, schema):
                    errors.append(f"mutating operation missing required mutation envelope: {operation_id}")

    for p in ROOT.rglob("*"):
        if p.name == "validate_pack.py":
            continue
        if p.is_file() and p.suffix.lower() in {".md",".txt",".yaml",".yml",".json",".sql",".py",".sh",".css"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat in RETIRED_PATTERNS:
                if re.search(pat, text, re.IGNORECASE):
                    errors.append(f"retired naming pattern found in {p.relative_to(ROOT)}")

    manifest = ROOT / "MANIFEST.txt"
    if manifest.exists():
        rows = parse_manifest()
        actual = {
            p.relative_to(ROOT).as_posix(): (p.stat().st_size, sha(p))
            for p in ROOT.rglob("*")
            if p.is_file() and p.name != "MANIFEST.txt"
        }
        if rows != actual:
            missing = sorted(set(actual) - set(rows))
            extra = sorted(set(rows) - set(actual))
            changed = sorted(k for k in set(rows) & set(actual) if rows[k] != actual[k])
            if missing:
                errors.append(f"manifest missing entries: {missing[:10]}")
            if extra:
                errors.append(f"manifest extra entries: {extra[:10]}")
            if changed:
                errors.append(f"manifest changed entries: {changed[:10]}")
    else:
        errors.append("MANIFEST.txt missing")

    zip_path = args.zip_path or (ROOT.parent / "parallax_v1_3_artifact_pack.zip")
    if args.skip_zip_check:
        warnings.append("zip content check skipped by --skip-zip-check")
    elif zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zip_names = {name for name in zf.namelist() if not name.endswith("/")}
        expected_names = {
            f"{ROOT.name}/{p.relative_to(ROOT).as_posix()}"
            for p in ROOT.rglob("*")
            if p.is_file()
        }
        if zip_names != expected_names:
            errors.append("zip contents do not match artifact folder")
    else:
        message = f"zip file missing at {zip_path}"
        if args.require_zip or args.zip_path is not None:
            errors.append(message)
        else:
            warnings.append(f"{message}; zip content check skipped")

    if errors:
        print("VALIDATION FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("VALIDATION PASSED")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
