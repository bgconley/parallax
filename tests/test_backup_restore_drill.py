from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_backup_restore_drill_restores_into_fresh_database_namespace() -> None:
    script = (REPO_ROOT / "scripts/release_backup_restore_drill.py").read_text()

    assert "_create_restore_database" in script
    assert "_drop_restore_database" in script
    assert "psql" in script
    assert "--dbname" in script
    assert "pg_dump" in script


def test_backup_restore_drill_uses_separate_object_restore_directory() -> None:
    script = (REPO_ROOT / "scripts/release_backup_restore_drill.py").read_text()

    assert "restore-root" in script
    assert "parallax-object-restore-" in script
    assert "object_manifest" in script


def test_backup_restore_make_target_passes_writable_restore_roots() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "--object-root \"$${PARALLAX_OBJECTS_DIR:-/srv/parallax/objects}\"" in makefile
    assert (
        "--restore-root "
        "\"$${PARALLAX_RESTORE_DRILL_ROOT:-/srv/parallax/exports/release-restore-drill}\""
        in makefile
    )
