from pathlib import Path

import yaml
from parallax_api.schemas.workflows import WorkflowType
from parallax_contracts.validation import validate_artifact_contracts
from parallax_db.migrations import discover_baseline_migrations

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "parallax_v1_3_artifact_pack"


def test_artifact_contracts_validate_against_mutation_envelope_rules() -> None:
    result = validate_artifact_contracts(ARTIFACT_ROOT)

    assert result.errors == []
    assert result.checked_files > 25


def test_baseline_migration_discovery_excludes_optional_profiles() -> None:
    migrations = discover_baseline_migrations(ROOT / "migrations")

    assert [path.name[:4] for path in migrations] == [
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
    ]
    assert all("optional_profiles" not in path.as_posix() for path in migrations)


def test_prototype_compose_passes_documented_firebase_credentials_json_setting() -> None:
    compose = (ROOT / "infra/compose/docker-compose.parallax.prototype.yml").read_text()

    assert "PARALLAX_FIREBASE_CREDENTIALS_JSON" in compose


def test_runtime_workflow_types_are_canonical_contract_names() -> None:
    jobs = yaml.safe_load(
        (ARTIFACT_ROOT / "contracts/jobs/parallax_workflows_v1_3.yaml").read_text()
    )
    runtime_names = set(WorkflowType.__args__)
    canonical_names = {workflow["name"] for workflow in jobs["workflows"]}

    assert runtime_names == canonical_names


def test_workflow_payload_schema_uses_canonical_workflow_names() -> None:
    jobs = yaml.safe_load(
        (ARTIFACT_ROOT / "contracts/jobs/parallax_workflows_v1_3.yaml").read_text()
    )
    schema = yaml.safe_load(
        (ARTIFACT_ROOT / "contracts/json_schema/workflow_payloads.schema.json").read_text()
    )

    canonical_names = {workflow["name"] for workflow in jobs["workflows"]}
    schema_names = set(schema["properties"]["workflow_type"]["enum"])

    assert schema_names == canonical_names
