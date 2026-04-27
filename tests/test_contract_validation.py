from pathlib import Path

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
        "0008",
    ]
    assert all("optional_profiles" not in path.as_posix() for path in migrations)
