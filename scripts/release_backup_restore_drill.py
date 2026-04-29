from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg

DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
TABLE_COUNT_SQL = {
    "schema_migration": "select count(*) from schema_migration",
    "app_user": "select count(*) from app_user",
    "activity": "select count(*) from activity",
    "timing_session": "select count(*) from timing_session",
    "temporal_context_annotation": "select count(*) from temporal_context_annotation",
    "capture_context_snapshot": "select count(*) from capture_context_snapshot",
    "workflow_run": "select count(*) from workflow_run",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Parallax backup/restore drill.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--postgres-container", default="parallax-postgres")
    parser.add_argument("--postgres-user", default="parallax")
    parser.add_argument("--postgres-db", default="parallax")
    parser.add_argument("--restore-database-name")
    parser.add_argument("--object-root", default="/srv/parallax/objects")
    parser.add_argument("--restore-root")
    args = parser.parse_args()

    restore_database = _safe_database_name(
        args.restore_database_name or f"parallax_restore_{uuid4().hex[:12]}"
    )
    live_manifest = _migration_manifest(args.database_url)
    dump_bytes = _logical_dump(
        args.postgres_container,
        args.postgres_user,
        args.postgres_db,
    )
    _restore_database(
        args.postgres_container,
        args.postgres_user,
        restore_database,
        dump_bytes,
    )
    try:
        restored_url = _database_url_for_name(args.database_url, restore_database)
        restored_manifest = _migration_manifest(restored_url)
        if restored_manifest != live_manifest:
            raise RuntimeError("restored migration manifest does not match live manifest")
        restored_rows = _table_counts(restored_url)
    finally:
        _drop_restore_database(args.postgres_container, args.postgres_user, restore_database)

    object_manifest = _verify_object_restore(
        Path(args.object_root),
        Path(args.restore_root) if args.restore_root else None,
    )
    print(
        "backup/restore drill passed "
        f"migrations={len(live_manifest)} logical_dump_bytes={len(dump_bytes)} "
        f"restored_tables={len(restored_rows)} object_manifest={object_manifest}"
    )
    return 0


def _migration_manifest(database_url: str) -> tuple[str, ...]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select name from schema_migration order by name")
            return tuple(str(row[0]) for row in cursor.fetchall())


def _table_counts(database_url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for table, sql in TABLE_COUNT_SQL.items():
                cursor.execute(sql)
                row = _fetch_one(cursor)
                raw_count = row[0]
                if not isinstance(raw_count, int):
                    raise RuntimeError(f"count query for {table} returned a non-integer value")
                counts[table] = raw_count
    return counts


def _logical_dump(container: str, user: str, database: str) -> bytes:
    docker = _docker()
    result = subprocess.run(
        [
            docker,
            "exec",
            container,
            "pg_dump",
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
    if b"schema_migration" not in result.stdout or b"CREATE TABLE" not in result.stdout:
        raise RuntimeError("logical backup did not contain expected Parallax data/schema")
    return result.stdout


def _restore_database(
    container: str,
    user: str,
    restore_database: str,
    dump_bytes: bytes,
) -> None:
    _create_restore_database(container, user, restore_database)
    docker = _docker()
    result = subprocess.run(
        [
            docker,
            "exec",
            "-i",
            container,
            "psql",
            "--set",
            "ON_ERROR_STOP=1",
            "--username",
            user,
            "--dbname",
            restore_database,
        ],
        input=dump_bytes,
        check=False,
        capture_output=True,
    )  # nosec B603
    if result.returncode != 0:
        _drop_restore_database(container, user, restore_database)
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())


def _create_restore_database(container: str, user: str, restore_database: str) -> None:
    docker = _docker()
    _run_container_command(
        [
            docker,
            "exec",
            container,
            "dropdb",
            "--if-exists",
            "--username",
            user,
            restore_database,
        ]
    )
    _run_container_command(
        [
            docker,
            "exec",
            container,
            "createdb",
            "--username",
            user,
            restore_database,
        ]
    )


def _drop_restore_database(container: str, user: str, restore_database: str) -> None:
    docker = _docker()
    _run_container_command(
        [
            docker,
            "exec",
            container,
            "dropdb",
            "--if-exists",
            "--username",
            user,
            restore_database,
        ]
    )


def _verify_object_restore(object_root: Path, restore_root: Path | None) -> dict[str, object]:
    if not object_root.exists():
        raise RuntimeError(f"object root does not exist: {object_root}")
    payload = b"parallax object backup restore drill\n"
    source = object_root / f"parallax-backup-source-{uuid4().hex}.bin"
    restore_parent = restore_root or object_root.parent
    restore_parent.mkdir(parents=True, exist_ok=True)
    object_manifest: dict[str, object]
    source.write_bytes(payload)
    try:
        with tempfile.TemporaryDirectory(prefix="parallax-object-backup-") as backup_dir:
            backup = Path(backup_dir) / source.name
            shutil.copy2(source, backup)
            with tempfile.TemporaryDirectory(
                prefix="parallax-object-restore-",
                dir=restore_parent,
            ) as restore_dir:
                restored = Path(restore_dir) / source.name
                shutil.copy2(backup, restored)
                object_manifest = {
                    "source_name": source.name,
                    "restored_name": restored.name,
                    "bytes": restored.stat().st_size,
                    "sha256": hashlib.sha256(restored.read_bytes()).hexdigest(),
                }
    finally:
        source.unlink(missing_ok=True)
    if object_manifest["sha256"] != hashlib.sha256(payload).hexdigest():
        raise RuntimeError("object restore drill failed: restored bytes do not match backup")
    return object_manifest


def _database_url_for_name(database_url: str, database_name: str) -> str:
    parts = urlsplit(database_url)
    return urlunsplit(
        (parts.scheme, parts.netloc, f"/{database_name}", parts.query, parts.fragment)
    )


def _safe_database_name(database_name: str) -> str:
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("restore database name may contain only letters, numbers, and underscores")
    return database_name


def _docker() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker executable is required for the restore drill")
    return docker


def _run_container_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())


def _fetch_one(cursor: psycopg.Cursor[object]) -> tuple[object, ...]:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("database query returned no row")
    return cast(tuple[object, ...], row)


if __name__ == "__main__":
    raise SystemExit(main())
