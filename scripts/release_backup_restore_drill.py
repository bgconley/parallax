from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import cast

import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Parallax backup/restore drill.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--postgres-container", default="parallax-postgres")
    parser.add_argument("--postgres-user", default="parallax")
    parser.add_argument("--postgres-db", default="parallax")
    parser.add_argument("--object-root", default="/srv/parallax/objects")
    args = parser.parse_args()

    migration_count = _verify_database_state(args.database_url)
    dump_bytes = _verify_logical_dump(
        args.postgres_container,
        args.postgres_user,
        args.postgres_db,
    )
    object_bytes = _verify_object_copy_restore(Path(args.object_root))

    print(
        "backup/restore drill passed "
        f"migrations={migration_count} logical_dump_bytes={dump_bytes} "
        f"object_bytes={object_bytes}"
    )
    return 0


def _verify_database_state(database_url: str) -> int:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from migration_version")
            raw_count = _fetch_one(cursor)[0]
            if not isinstance(raw_count, int):
                raise RuntimeError("migration count query returned a non-integer value")
            migration_count = raw_count
            cursor.execute(
                "select to_jsonb(array_agg(version order by version)) from migration_version"
            )
            backup_manifest = _fetch_one(cursor)[0]
            cursor.execute(
                "create temporary table parallax_restore_drill(manifest jsonb) on commit drop"
            )
            cursor.execute(
                "insert into parallax_restore_drill(manifest) values (%s)",
                (backup_manifest,),
            )
            cursor.execute("select manifest from parallax_restore_drill")
            restored_manifest = _fetch_one(cursor)[0]

    if backup_manifest != restored_manifest:
        raise RuntimeError(
            "restore drill failed: restored migration manifest does not match backup"
        )
    return migration_count


def _verify_logical_dump(container: str, user: str, database: str) -> int:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker executable is required for the logical backup drill")
    result = subprocess.run(
        [
            docker,
            "exec",
            container,
            "pg_dump",
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            "--username",
            user,
            "--dbname",
            database,
        ],
        check=False,
        capture_output=True,
    )  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    if b"CREATE TABLE" not in result.stdout or b"migration_version" not in result.stdout:
        raise RuntimeError("logical backup did not contain expected Parallax schema")
    return len(result.stdout)


def _verify_object_copy_restore(object_root: Path) -> int:
    if not object_root.exists():
        raise RuntimeError(f"object root does not exist: {object_root}")
    payload = b"parallax object backup restore drill\n"
    with tempfile.TemporaryDirectory(prefix="parallax-backup-drill-", dir=object_root) as tempdir:
        workspace = Path(tempdir)
        source = workspace / "source.bin"
        backup = workspace / "backup.bin"
        restored = workspace / "restored.bin"
        source.write_bytes(payload)
        shutil.copyfile(source, backup)
        shutil.copyfile(backup, restored)
        restored_payload = restored.read_bytes()
    if restored_payload != payload:
        raise RuntimeError("object restore drill failed: restored bytes do not match backup")
    return len(restored_payload)


def _fetch_one(cursor: psycopg.Cursor[object]) -> tuple[object, ...]:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("database query returned no row")
    return cast(tuple[object, ...], row)


if __name__ == "__main__":
    raise SystemExit(main())
