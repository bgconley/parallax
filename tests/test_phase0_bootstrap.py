from __future__ import annotations

import subprocess
from pathlib import Path

from parallax_db.runner import current_schema_smoke_checks, phase0_schema_smoke_checks

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_artifact_pack_has_no_generated_macos_metadata() -> None:
    assert list((REPO_ROOT / "parallax_v1_3_artifact_pack").rglob(".DS_Store")) == []


def test_root_compose_renders_with_example_environment() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "--env-file", ".env.example", "config"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "parallax-api" in result.stdout
    assert "parallax-worker" in result.stdout
    assert "/srv/parallax/postgres" in result.stdout
    assert "/srv/parallax/objects" in result.stdout
    assert "DB: postgres12" in result.stdout


def test_root_compose_uses_parallax_specific_host_ports() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "--env-file", ".env.example", "config"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert 'published: "15432"' in result.stdout
    assert 'published: "16379"' in result.stdout
    assert 'published: "18000"' in result.stdout
    assert 'published: "5432"' not in result.stdout
    assert 'published: "8000"' not in result.stdout


def test_phase_docs_record_compose_derivation_and_phase_boundary() -> None:
    phase0_doc = (REPO_ROOT / "docs/architecture/phase0_bootstrap.md").read_text()
    agents_doc = (REPO_ROOT / "AGENTS.md").read_text()
    phase1_doc = (REPO_ROOT / "docs/architecture/phase1_core_loop.md").read_text()
    readme = (REPO_ROOT / "README.md").read_text()

    assert "implementation derivative of the canonical prototype Compose file" in phase0_doc
    assert (
        "Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, and Phase 6 are complete"
        in agents_doc
    )
    assert "runtime exposes the canonical" in readme
    assert "Out of scope: review decisions" in phase1_doc


def test_phase0_runtime_dockerfiles_exist() -> None:
    assert (REPO_ROOT / "services/api/Dockerfile").is_file()
    assert (REPO_ROOT / "services/worker/Dockerfile").is_file()


def test_phase0_runtime_dockerfiles_pin_base_image_and_uv_installer() -> None:
    for dockerfile in [
        REPO_ROOT / "services/api/Dockerfile",
        REPO_ROOT / "services/worker/Dockerfile",
    ]:
        content = dockerfile.read_text()
        assert "FROM python:3.12-slim@sha256:" in content
        assert "python -m pip install --no-cache-dir uv==" in content


def test_contract_validation_is_wired_into_ci() -> None:
    workflow = REPO_ROOT / ".github/workflows/ci.yml"
    assert workflow.is_file()
    content = workflow.read_text()
    assert "make validate" in content
    assert "uv run pytest" in content
    assert "uv run ruff check ." in content
    assert "make typecheck" in content


def test_static_typecheck_is_available_from_makefile() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "typecheck:" in content
    assert "uv run mypy services packages scripts" in content


def test_security_scan_includes_untracked_working_tree_files() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "--no-git-ignore" in content


def test_phase2_smoke_is_available_from_makefile() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "phase2-smoke:" in content
    assert "scripts/phase2_smoke.py" in content


def test_phase3_smoke_is_available_from_makefile() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "phase3-smoke:" in content
    assert "scripts/phase3_smoke.py" in content


def test_phase4_smoke_is_available_from_makefile() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "phase4-smoke:" in content
    assert "scripts/phase4_smoke.py" in content


def test_phase5_smoke_is_available_from_makefile() -> None:
    makefile = REPO_ROOT / "Makefile"
    content = makefile.read_text()

    assert "phase5-smoke:" in content
    assert "scripts/phase5_smoke.py" in content


def test_phase0_schema_smoke_checks_cover_core_tables_and_enums() -> None:
    check_names = {check.name for check in phase0_schema_smoke_checks()}

    assert "table:app_user" in check_names
    assert "table:client_mutation_log" in check_names
    assert "table:activity" in check_names
    assert "table:timing_session" in check_names
    assert "table:timing_event" in check_names
    assert "enum:timing_session_status" in check_names
    assert "enum:timing_event_type" in check_names


def test_current_schema_smoke_checks_cover_phase5_tables() -> None:
    check_names = {check.name for check in current_schema_smoke_checks()}

    assert "table:checkpoint_template" in check_names
    assert "table:checkpoint_run" in check_names
    assert "table:start_latency_observation" in check_names
    assert "table:transition_observation" in check_names
    assert "table:temporal_feature_vector" in check_names


def test_current_schema_smoke_checks_cover_phase4_context_tables_and_enums() -> None:
    check_names = {check.name for check in current_schema_smoke_checks()}

    assert "table:timing_event_span" in check_names
    assert "table:activity_stats_snapshot" in check_names
    assert "table:capture_context_snapshot" in check_names
    assert "table:context_capture_policy" in check_names
    assert "table:timing_review_flag" in check_names
    assert "table:model_invocation" in check_names
    assert "table:temporal_extracted_context_event" in check_names
    assert "table:temporal_correction" in check_names
    assert "table:preflight_check" in check_names
    assert "table:inferred_place_observation" in check_names
    assert "enum:capture_method" in check_names
    assert "enum:timing_review_flag_status" in check_names
    assert "enum:confirmation_state" in check_names


def test_migration_script_is_runnable_from_repo_root() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/apply_migrations.py", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Apply Parallax baseline SQL migrations" in result.stdout
    assert "Run current schema smoke checks" in result.stdout


def test_resource_dependency_uses_valid_expression_unique_index() -> None:
    migration_paths = [
        REPO_ROOT / "migrations/0005_context_extraction_preflight.sql",
        REPO_ROOT
        / "parallax_v1_3_artifact_pack/database/migrations/0005_context_extraction_preflight.sql",
    ]

    for migration_path in migration_paths:
        sql = migration_path.read_text()
        assert "UNIQUE(activity_id, lower(resource_name))" not in sql
        assert "CREATE UNIQUE INDEX ux_resource_dependency_activity_resource_name_lower" in sql
