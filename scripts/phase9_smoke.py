from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess  # nosec B404
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import UUID, uuid4

import psycopg
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PACKAGE_ROOT = REPO_ROOT / "packages" / "db"
if str(DB_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(DB_PACKAGE_ROOT))

from parallax_db.runner import apply_baseline_migrations  # noqa: E402

DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "migrations"
DEFAULT_PROFILE_DIR = REPO_ROOT / "database" / "optional_profiles"
DEFAULT_K3S_DIR = REPO_ROOT / "infra" / "k3s" / "base"

POSTGRES_USER = "parallax"
POSTGRES_PASSWORD = "parallax_phase9_smoke_password"  # nosec B105
POSTGRES_DB = "parallax"


@dataclass(frozen=True)
class ContainerConfig:
    name: str
    image: str
    extension_name: str


@dataclass(frozen=True)
class RunningDatabase:
    name: str
    database_url: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Parallax Phase 9 optional-profile smoke.")
    parser.add_argument("--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--k3s-dir", type=Path, default=DEFAULT_K3S_DIR)
    parser.add_argument(
        "--pgvector-image",
        default=os.environ.get("PARALLAX_PHASE9_PGVECTOR_IMAGE", "pgvector/pgvector:pg16"),
    )
    parser.add_argument(
        "--paradedb-image",
        default=os.environ.get("PARALLAX_PHASE9_PARADEDB_IMAGE", "paradedb/paradedb:0.22.6"),
    )
    parser.add_argument(
        "--postgis-image",
        default=os.environ.get("PARALLAX_PHASE9_POSTGIS_IMAGE", "postgis/postgis:16-3.5"),
    )
    parser.add_argument(
        "--timescale-image",
        default=os.environ.get(
            "PARALLAX_PHASE9_TIMESCALE_IMAGE",
            "timescale/timescaledb:latest-pg16",
        ),
    )
    args = parser.parse_args()

    docker = _docker()
    phase_summary: dict[str, object] = {}

    pgvector = ContainerConfig("pgvector", args.pgvector_image, "vector")
    paradedb = ContainerConfig("paradedb", args.paradedb_image, "pg_search")
    postgis = ContainerConfig("postgis", args.postgis_image, "postgis")
    timescale = ContainerConfig("timescale", args.timescale_image, "timescaledb")

    with _postgres_container(docker, pgvector) as database:
        apply_baseline_migrations(database.database_url, args.migrations_dir)
        phase_summary |= _prove_pgvector(database.database_url)

    with _postgres_container(docker, paradedb) as database:
        apply_baseline_migrations(database.database_url, args.migrations_dir)
        _apply_sql(
            database.database_url,
            args.profile_dir / "0010_paradedb_optional_search_profile.sql",
        )
        phase_summary |= _prove_paradedb(database.database_url)

    with _postgres_container(docker, postgis) as database:
        apply_baseline_migrations(database.database_url, args.migrations_dir)
        phase_summary |= _prove_postgis_baseline(database.database_url)
        _apply_sql(
            database.database_url,
            args.profile_dir / "0012_postgis_optional_geospatial_profile.sql",
        )
        phase_summary |= _prove_postgis_optional(database.database_url)

    with _postgres_container(docker, timescale) as database:
        apply_baseline_migrations(database.database_url, args.migrations_dir)
        _apply_sql(
            database.database_url,
            args.profile_dir / "0009_timescale_optional_analytics_profile.sql",
        )
        phase_summary |= _prove_timescale_analytics(database.database_url)
        _apply_sql(
            database.database_url,
            args.profile_dir / "0013_timescale_capture_context_profile.sql",
        )
        phase_summary |= _prove_timescale_capture(database.database_url)
        phase_summary |= _prove_backup_restore(docker, database.name)

    phase_summary |= _prove_k3s_manifests(args.k3s_dir)
    summary = {
        "status": "passed",
        "phase": "phase9",
        "summary": phase_summary,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


@contextmanager
def _postgres_container(docker: str, config: ContainerConfig) -> Iterator[RunningDatabase]:
    port = _free_port()
    name = f"parallax-phase9-{config.name}-{uuid4().hex[:10]}"
    command = [
        docker,
        "run",
        "--rm",
        "-d",
        "--name",
        name,
        "-e",
        f"POSTGRES_USER={POSTGRES_USER}",
        "-e",
        f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
        "-e",
        f"POSTGRES_DB={POSTGRES_DB}",
        "-p",
        f"127.0.0.1:{port}:5432",
        config.image,
    ]
    _run(command)
    database_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@127.0.0.1:{port}/{POSTGRES_DB}"
    try:
        _wait_for_database(database_url, config.extension_name)
        yield RunningDatabase(name=name, database_url=database_url)
    finally:
        subprocess.run([docker, "rm", "-f", name], check=False, capture_output=True)  # nosec B603


def _prove_pgvector(database_url: str) -> dict[str, object]:
    vector_1024 = _vector_literal(1024, 0.01)
    vector_1536 = _vector_literal(1536, 0.01)
    target_1024 = _vector_literal(1024, 0.99)
    target_1536 = _vector_literal(1536, 0.99)
    other_1024 = _vector_literal(1024, -0.2)
    other_1536 = _vector_literal(1536, -0.2)
    with psycopg.connect(database_url) as connection:
        user_id = _create_user(connection)
        model_1024 = _create_embedding_model(connection, 1024)
        model_1536 = _create_embedding_model(connection, 1536)
        target_doc = _create_retrieval_document(
            connection,
            user_id,
            "resource_dependency",
            "sponge scrubber before washing pans",
        )
        other_doc = _create_retrieval_document(
            connection,
            user_id,
            "activity_profile",
            "clean desk archive loose receipts",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "insert into retrieval_embedding_1024 values (%s, %s, %s::vector, now())",
                (target_doc, model_1024, target_1024),
            )
            cursor.execute(
                "insert into retrieval_embedding_1024 values (%s, %s, %s::vector, now())",
                (other_doc, model_1024, other_1024),
            )
            cursor.execute(
                "insert into retrieval_embedding_1536 values (%s, %s, %s::vector, now())",
                (target_doc, model_1536, target_1536),
            )
            cursor.execute(
                "insert into retrieval_embedding_1536 values (%s, %s, %s::vector, now())",
                (other_doc, model_1536, other_1536),
            )
        connection.commit()
        top_1024 = _vector_top_document(connection, 1024, vector_1024)
        top_1536 = _vector_top_document(connection, 1536, vector_1536)
        if top_1024 != target_doc or top_1536 != target_doc:
            raise RuntimeError("pgvector dual-read comparison did not return matching evidence")
        hnsw_indexes = _count_indexes(connection, "%hnsw%", "retrieval_embedding_%")
        if hnsw_indexes < 2:
            raise RuntimeError("pgvector HNSW indexes were not created for both embedding tables")
    return {
        "pgvector_hnsw_indexes": hnsw_indexes,
        "pgvector_dual_read_agreement": True,
    }


def _prove_paradedb(database_url: str) -> dict[str, object]:
    with psycopg.connect(database_url) as connection:
        user_id = _create_user(connection)
        target_doc = _create_retrieval_document(
            connection,
            user_id,
            "resource_dependency",
            "sponge scrubber missing before washing pans",
        )
        _create_retrieval_document(connection, user_id, "activity_profile", "fold laundry towels")
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id
                from retrieval_document
                where text_content @@@ 'sponge scrubber'
                order by pdb.score(id) desc
                limit 1
                """
            )
            row = cursor.fetchone()
        if row is None or row[0] != target_doc:
            raise RuntimeError("ParadeDB BM25 did not rank the expected evidence first")
        bm25_indexes = _count_indexes(connection, "%USING bm25%", "retrieval_document")
        if bm25_indexes < 1:
            raise RuntimeError("ParadeDB BM25 index was not created")
    return {
        "paradedb_bm25_indexes": bm25_indexes,
        "paradedb_bm25_top_match": "resource_dependency",
    }


def _prove_postgis_baseline(database_url: str) -> dict[str, object]:
    with psycopg.connect(database_url) as connection:
        user_id = _create_user(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into user_place (user_id, display_name, latitude, longitude, radius_meters)
                values (%s, 'Kitchen', 40.712800, -74.006000, 30)
                returning id
                """,
                (user_id,),
            )
            place_id = _single_uuid(cursor)
            cursor.execute(
                """
                select id
                from user_place
                where user_id = %s
                  and latitude between 40.712700 and 40.712900
                  and longitude between -74.006100 and -74.005900
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None or row[0] != place_id:
            raise RuntimeError("baseline numeric geospatial lookup failed before PostGIS")
    return {"postgis_baseline_numeric_lookup": True}


def _prove_postgis_optional(database_url: str) -> dict[str, object]:
    with psycopg.connect(database_url) as connection:
        user_id = _create_user(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into user_place (user_id, display_name, latitude, longitude, radius_meters)
                values (%s, 'Garage', 40.713000, -74.006000, 50)
                returning id
                """,
                (user_id,),
            )
            place_id = _single_uuid(cursor)
            cursor.execute(
                """
                select id
                from user_place
                where user_id = %s
                  and geog is not null
                  and ST_DWithin(
                    geog,
                    ST_SetSRID(ST_MakePoint(-74.006000, 40.713000), 4326)::geography,
                    25
                  )
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            gist_indexes = _count_index_definitions(connection, "%USING gist%", "%geog%")
        if row is None or row[0] != place_id:
            raise RuntimeError("PostGIS ST_DWithin lookup failed")
        if gist_indexes < 2:
            raise RuntimeError("PostGIS GiST indexes were not created for geography columns")
    return {
        "postgis_gist_indexes": gist_indexes,
        "postgis_stdwithin_lookup": True,
    }


def _prove_timescale_analytics(database_url: str) -> dict[str, object]:
    with psycopg.connect(database_url, autocommit=True) as connection:
        user_id = _create_user(connection)
        activity_id = _create_activity(connection, user_id)
        with connection.cursor() as cursor:
            for offset, seconds in enumerate((1200, 1500, 1800), start=1):
                cursor.execute(
                    """
                    insert into temporal_metric_point (
                      observed_at, user_id, activity_id, metric_name,
                      metric_value_seconds, source_table, source_id
                    )
                    values (
                      date_trunc('day', now()) - interval '3 days'
                        + (%s || ' hours')::interval,
                      %s, %s,
                      'wall_seconds', %s, 'timing_session', gen_random_uuid()
                    )
                    """,
                    (offset, user_id, activity_id, seconds),
                )
            cursor.execute(
                """
                call refresh_continuous_aggregate(
                  'activity_duration_daily',
                  date_trunc('day', now()) - interval '4 days',
                  date_trunc('day', now()) - interval '2 days'
                )
                """
            )
            cursor.execute(
                """
                select sample_count, p50_seconds, p80_seconds
                from activity_duration_daily
                where user_id = %s and activity_id = %s and metric_name = 'wall_seconds'
                """,
                (user_id, activity_id),
            )
            row = cursor.fetchone()
            hypertables = _count_timescale_hypertables(connection)
        if row is None or row[0] != 3:
            raise RuntimeError("Timescale activity continuous aggregate did not backfill samples")
    return {
        "timescale_hypertables": hypertables,
        "timescale_activity_daily_samples": int(row[0]),
        "timescale_activity_daily_p80_seconds": int(row[2]),
    }


def _prove_timescale_capture(database_url: str) -> dict[str, object]:
    with psycopg.connect(database_url, autocommit=True) as connection:
        user_id = _create_user(connection)
        with connection.cursor() as cursor:
            for offset, quality in enumerate((0.4, 0.7, 0.9), start=1):
                cursor.execute(
                    """
                    insert into capture_context_metric_point (
                      observed_at, user_id, metric_name, metric_value_numeric,
                      source_table, source_id
                    )
                    values (
                      date_trunc('day', now()) - interval '3 days'
                        + (%s || ' hours')::interval,
                      %s,
                      'context_quality_score', %s, 'capture_context_snapshot', gen_random_uuid()
                    )
                    """,
                    (offset, user_id, quality),
                )
            cursor.execute(
                """
                call refresh_continuous_aggregate(
                  'capture_context_daily',
                  date_trunc('day', now()) - interval '4 days',
                  date_trunc('day', now()) - interval '2 days'
                )
                """
            )
            cursor.execute(
                """
                select sample_count, avg_value
                from capture_context_daily
                where user_id = %s and metric_name = 'context_quality_score'
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            hypertables = _count_timescale_hypertables(connection)
        if row is None or row[0] != 3:
            raise RuntimeError("Timescale capture-context continuous aggregate did not backfill")
    return {
        "timescale_capture_daily_samples": int(row[0]),
        "timescale_hypertables_after_capture_profile": hypertables,
    }


def _prove_backup_restore(docker: str, container_name: str) -> dict[str, object]:
    restore_db = f"parallax_phase9_restore_{uuid4().hex[:8]}"
    dump_path = str(PurePosixPath("/", "tmp", f"{restore_db}.bak"))
    _run(
        [
            docker,
            "exec",
            container_name,
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--username",
            POSTGRES_USER,
            "--dbname",
            POSTGRES_DB,
            "--file",
            dump_path,
        ]
    )
    dump_size = _run_capture([docker, "exec", container_name, "stat", "-c", "%s", dump_path])
    _run([docker, "exec", container_name, "createdb", "--username", POSTGRES_USER, restore_db])
    try:
        _run(
            [
                docker,
                "exec",
                container_name,
                "psql",
                "--set",
                "ON_ERROR_STOP=1",
                "--username",
                POSTGRES_USER,
                "--dbname",
                restore_db,
                "--command",
                "create extension if not exists timescaledb;",
            ]
        )
        _run(
            [
                docker,
                "exec",
                container_name,
                "psql",
                "--set",
                "ON_ERROR_STOP=1",
                "--username",
                POSTGRES_USER,
                "--dbname",
                restore_db,
                "--command",
                "select timescaledb_pre_restore();",
            ]
        )
        _run(
            [
                docker,
                "exec",
                container_name,
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--username",
                POSTGRES_USER,
                "--dbname",
                restore_db,
                dump_path,
            ]
        )
        _run(
            [
                docker,
                "exec",
                container_name,
                "psql",
                "--set",
                "ON_ERROR_STOP=1",
                "--username",
                POSTGRES_USER,
                "--dbname",
                restore_db,
                "--command",
                "select timescaledb_post_restore();",
            ],
        )
        _run(
            [
                docker,
                "exec",
                container_name,
                "psql",
                "--username",
                POSTGRES_USER,
                "--dbname",
                restore_db,
                "--tuples-only",
                "--command",
                (
                    "select count(*) from temporal_metric_point; "
                    "select count(*) from capture_context_metric_point;"
                ),
            ]
        )
    finally:
        _run([docker, "exec", container_name, "rm", "-f", dump_path])
        _run(
            [
                docker,
                "exec",
                container_name,
                "dropdb",
                "--if-exists",
                "--username",
                POSTGRES_USER,
                restore_db,
            ]
        )
    return {
        "timescale_backup_restore_bytes": int(dump_size.strip()),
        "timescale_backup_restore_checked": True,
    }


def _prove_k3s_manifests(k3s_dir: Path) -> dict[str, object]:
    manifests = list(_load_yaml_documents(k3s_dir))
    if not manifests:
        raise RuntimeError(f"no k3s manifests found in {k3s_dir}")
    services = [doc for doc in manifests if doc.get("kind") == "Service"]
    service_types = {
        doc["metadata"]["name"]: doc.get("spec", {}).get("type", "ClusterIP")
        for doc in services
    }
    exposed_model_services = [
        name
        for name, service_type in service_types.items()
        if "model" in name and service_type != "ClusterIP"
    ]
    if exposed_model_services:
        raise RuntimeError(f"model services must be ClusterIP only: {exposed_model_services}")
    workloads = [
        doc
        for doc in manifests
        if doc.get("kind") in {"Deployment", "StatefulSet"}
    ]
    missing_probes = [
        doc["metadata"]["name"]
        for doc in workloads
        if not _workload_has_probe(doc, "readinessProbe")
        or not _workload_has_probe(doc, "livenessProbe")
    ]
    if missing_probes:
        raise RuntimeError(f"k3s workloads missing health probes: {missing_probes}")
    if not any(doc.get("kind") == "Secret" for doc in manifests):
        raise RuntimeError("k3s manifests must include a Secret contract")
    pvc_count = sum(1 for doc in manifests if doc.get("kind") == "PersistentVolumeClaim")
    if pvc_count < 3:
        raise RuntimeError("k3s manifests must include persistent volume claims")
    _prove_k3s_external_bearer_config(manifests)
    _prove_k3s_api_probe_paths(manifests)
    return {
        "k3s_manifest_documents": len(manifests),
        "k3s_external_bearer_config": True,
        "k3s_services_cluster_ip": sum(
            1 for service_type in service_types.values() if service_type == "ClusterIP"
        ),
        "k3s_api_readiness_path": "/v1/ready",
        "k3s_api_liveness_path": "/v1/live",
        "k3s_persistent_volume_claims": pvc_count,
        "k3s_workloads_with_probes": len(workloads),
    }


def _prove_k3s_external_bearer_config(manifests: list[dict[str, Any]]) -> None:
    config = _find_manifest(manifests, "ConfigMap", "parallax-config")
    data = cast(dict[str, str], config.get("data", {}))
    required = {
        "PARALLAX_AUTH_JWT_ALGORITHM",
        "PARALLAX_AUTH_JWKS_URL",
        "PARALLAX_AUTH_JWT_ISSUER",
        "PARALLAX_AUTH_JWT_AUDIENCE",
    }
    missing = sorted(name for name in required if not data.get(name))
    production_external_bearer = (
        data.get("PARALLAX_ENV") == "production"
        and data.get("PARALLAX_AUTH_MODE") == "external_bearer"
    )
    if production_external_bearer:
        if data.get("PARALLAX_AUTH_JWT_ALGORITHM") == "HS256" or missing:
            raise RuntimeError(
                "production external_bearer k3s config must set RS/ES JWT auth with "
                f"JWKS, issuer, and audience; missing={missing}"
            )


def _prove_k3s_api_probe_paths(manifests: list[dict[str, Any]]) -> None:
    api = _find_manifest(manifests, "Deployment", "parallax-api")
    containers = cast(
        list[dict[str, Any]],
        api["spec"]["template"]["spec"]["containers"],
    )
    if not containers:
        raise RuntimeError("parallax-api deployment must include an API container")
    container = containers[0]
    readiness_path = container.get("readinessProbe", {}).get("httpGet", {}).get("path")
    liveness_path = container.get("livenessProbe", {}).get("httpGet", {}).get("path")
    if readiness_path != "/v1/ready":
        raise RuntimeError("parallax-api readinessProbe must use /v1/ready")
    if liveness_path != "/v1/live":
        raise RuntimeError("parallax-api livenessProbe must use /v1/live")


def _find_manifest(
    manifests: list[dict[str, Any]],
    kind: str,
    name: str,
) -> dict[str, Any]:
    for doc in manifests:
        metadata = cast(dict[str, Any], doc.get("metadata", {}))
        if doc.get("kind") == kind and metadata.get("name") == name:
            return doc
    raise RuntimeError(f"k3s manifest is missing {kind}/{name}")


def _apply_sql(database_url: str, path: Path) -> None:
    sql = path.read_text()
    with psycopg.connect(database_url, autocommit=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()


def _wait_for_database(database_url: str, extension_name: str) -> None:
    deadline = time.monotonic() + 90
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(database_url, connect_timeout=3) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select 1")
                    cursor.fetchone()
                    cursor.execute(
                        "select exists (select 1 from pg_available_extensions where name = %s)",
                        (extension_name,),
                    )
                    row = cursor.fetchone()
                    if row is None or row[0] is not True:
                        raise RuntimeError(f"extension is not available: {extension_name}")
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"database did not become ready: {last_error}")


def _docker() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker executable is required for Phase 9 smoke")
    return docker


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run(command: list[str], input_bytes: bytes | None = None) -> None:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        input=input_bytes,
    )  # nosec B603
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or stdout or f"command failed: {command}")


def _run_capture(command: list[str]) -> bytes:
    result = subprocess.run(command, check=False, capture_output=True)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def _create_user(connection: psycopg.Connection[Any]) -> UUID:
    with connection.cursor() as cursor:
        cursor.execute("insert into app_user default values returning id")
        return _single_uuid(cursor)


def _create_activity(connection: psycopg.Connection[Any], user_id: UUID) -> UUID:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into activity (user_id, display_name, canonical_key)
            values (%s, %s, %s)
            returning id
            """,
            (user_id, f"Phase 9 activity {uuid4().hex[:6]}", f"phase9-{uuid4().hex}"),
        )
        return _single_uuid(cursor)


def _create_embedding_model(connection: psycopg.Connection[Any], dimension: int) -> UUID:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into embedding_model (provider, model_name, model_version, dimension, purpose)
            values ('phase9', %s, '1', %s, 'retrieval')
            returning id
            """,
            (f"test-{dimension}", dimension),
        )
        return _single_uuid(cursor)


def _create_retrieval_document(
    connection: psycopg.Connection[Any],
    user_id: UUID,
    entity_type: str,
    text_content: str,
) -> UUID:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into retrieval_document (
              user_id, entity_type, entity_id, document_kind, text_content, privacy_class
            )
            values (%s, %s, gen_random_uuid(), 'phase9_smoke', %s, 'normal')
            returning id
            """,
            (user_id, entity_type, text_content),
        )
        return _single_uuid(cursor)


def _vector_top_document(connection: psycopg.Connection[Any], dimension: int, query: str) -> UUID:
    with connection.cursor() as cursor:
        if dimension == 1024:
            cursor.execute(
                """
            select rd.id
            from retrieval_embedding_1024 re
            join retrieval_document rd on rd.id = re.document_id
            order by re.embedding <=> %s::vector
            limit 1
                """,
                (query,),
            )
        elif dimension == 1536:
            cursor.execute(
                """
            select rd.id
            from retrieval_embedding_1536 re
            join retrieval_document rd on rd.id = re.document_id
            order by re.embedding <=> %s::vector
            limit 1
                """,
                (query,),
            )
        else:
            raise ValueError(f"unsupported retrieval embedding dimension: {dimension}")
        return _single_uuid(cursor)


def _count_indexes(
    connection: psycopg.Connection[Any],
    indexdef_like: str,
    tablename_like: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)
            from pg_indexes
            where schemaname = 'public'
              and indexdef ilike %s
              and tablename like %s
            """,
            (indexdef_like, tablename_like),
        )
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _count_index_definitions(
    connection: psycopg.Connection[Any],
    first_pattern: str,
    second_pattern: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*)
            from pg_indexes
            where schemaname = 'public'
              and indexdef ilike %s
              and indexdef ilike %s
            """,
            (first_pattern, second_pattern),
        )
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _count_timescale_hypertables(connection: psycopg.Connection[Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from timescaledb_information.hypertables")
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _single_uuid(cursor: psycopg.Cursor[Any]) -> UUID:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("expected a row")
    value = row[0]
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _vector_literal(dimension: int, value: float) -> str:
    return "[" + ",".join(f"{value:.3f}" for _ in range(dimension)) + "]"


def _load_yaml_documents(k3s_dir: Path) -> Iterator[dict[str, Any]]:
    for path in sorted(k3s_dir.glob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if doc:
                yield cast(dict[str, Any], doc)


def _workload_has_probe(workload: dict[str, Any], probe_name: str) -> bool:
    template = workload.get("spec", {}).get("template", {})
    containers = template.get("spec", {}).get("containers", [])
    return any(probe_name in container for container in containers)


if __name__ == "__main__":
    raise SystemExit(main())
