from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_postgres_context_persistence_is_split_by_responsibility() -> None:
    facade = REPO_ROOT / "services/api/parallax_api/repositories/postgres_context_repository.py"
    expected_modules = [
        "postgres_context_annotations.py",
        "postgres_context_policies.py",
        "postgres_context_snapshots.py",
        "postgres_context_places.py",
        "postgres_context_review_flags.py",
        "postgres_context_extraction.py",
        "postgres_context_place_inference.py",
    ]

    assert len(facade.read_text().splitlines()) <= 260
    for module_name in expected_modules:
        assert (facade.parent / module_name).is_file()


def test_in_memory_context_persistence_keeps_phase4_boundaries_split() -> None:
    repository = REPO_ROOT / "services/api/parallax_api/repositories/context_repository.py"
    expected_modules = [
        "context_annotation_state.py",
        "context_extraction_repository.py",
        "context_place_inference.py",
        "context_policy_defaults.py",
    ]

    assert len(repository.read_text().splitlines()) <= 500
    for module_name in expected_modules:
        assert (repository.parent / module_name).is_file()
