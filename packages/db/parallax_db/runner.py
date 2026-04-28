from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import psycopg

from .migrations import discover_baseline_migrations


@dataclass(frozen=True)
class AppliedMigration:
    name: str
    checksum: str


@dataclass(frozen=True)
class SchemaSmokeCheck:
    name: str
    sql: str
    params: tuple[str, ...] = ()


def phase0_schema_smoke_checks() -> list[SchemaSmokeCheck]:
    return [
        *(_table_check(name) for name in _PHASE0_TABLES),
        *(_enum_check(name) for name in _PHASE0_ENUMS),
    ]


def current_schema_smoke_checks() -> list[SchemaSmokeCheck]:
    return [
        *phase0_schema_smoke_checks(),
        *(_table_check(name) for name in _PHASE2_TABLES),
        *(_table_check(name) for name in _PHASE3_TABLES),
        *(_table_check(name) for name in _PHASE4_TABLES),
        *(_enum_check(name) for name in _PHASE3_ENUMS),
        *(_enum_check(name) for name in _PHASE4_ENUMS),
    ]


def apply_baseline_migrations(database_url: str, migrations_dir: Path) -> list[AppliedMigration]:
    applied: list[AppliedMigration] = []
    migrations = discover_baseline_migrations(migrations_dir)
    with psycopg.connect(database_url, autocommit=False) as connection:
        _ensure_migration_table(connection)
        for migration in migrations:
            name = migration.name
            content = migration.read_text()
            checksum = _sha256(content)
            if _migration_already_applied(connection, name, checksum):
                continue

            with connection.cursor() as cursor:
                cursor.execute(content)
                cursor.execute(
                    """
                    insert into schema_migration (name, checksum)
                    values (%s, %s)
                    """,
                    (name, checksum),
                )
            connection.commit()
            applied.append(AppliedMigration(name=name, checksum=checksum))
    return applied


def run_schema_smoke_checks(
    database_url: str,
    checks: Iterable[SchemaSmokeCheck] | None = None,
) -> list[str]:
    failures: list[str] = []
    selected_checks = list(checks or current_schema_smoke_checks())
    with psycopg.connect(database_url, autocommit=True) as connection:
        for check in selected_checks:
            with connection.cursor() as cursor:
                cursor.execute(check.sql, check.params)
                exists = cursor.fetchone()
            if not exists or not exists[0]:
                failures.append(check.name)
    return failures


def _ensure_migration_table(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            create table if not exists schema_migration (
              name text primary key,
              checksum text not null,
              applied_at timestamptz not null default now()
            )
            """
        )
    connection.commit()


def _migration_already_applied(
    connection: psycopg.Connection,
    name: str,
    checksum: str,
) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("select checksum from schema_migration where name = %s", (name,))
        row = cursor.fetchone()
    if row is None:
        return False
    if row[0] != checksum:
        raise ValueError(f"Applied migration checksum changed: {name}")
    return True


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _table_check(name: str) -> SchemaSmokeCheck:
    return SchemaSmokeCheck(
        name=f"table:{name}",
        sql="""
            select exists (
            select 1 from information_schema.tables
            where table_schema = 'public' and table_name = %s
            )
        """,
        params=(name,),
    )


def _enum_check(name: str) -> SchemaSmokeCheck:
    return SchemaSmokeCheck(
        name=f"enum:{name}",
        sql="""
            select exists (
            select 1 from pg_type t
            join pg_namespace n on n.oid = t.typnamespace
            where n.nspname = 'public' and t.typtype = 'e' and t.typname = %s
            )
        """,
        params=(name,),
    )


_PHASE0_TABLES = (
    "app_user",
    "privacy_settings",
    "audit_log",
    "activity",
    "timing_session",
    "timing_event",
    "temporal_context_annotation",
    "model_update_decision",
    "client_mutation_log",
    "sync_cursor",
    "outbox_event",
)

_PHASE0_ENUMS = (
    "timing_mode",
    "timing_session_status",
    "timing_event_type",
    "model_update_decision_type",
    "job_status",
)

_PHASE2_TABLES = (
    "timing_event_span",
    "activity_stats_snapshot",
)

_PHASE3_TABLES = (
    "context_capture_policy",
    "capture_context_snapshot",
    "geospatial_observation",
    "radio_observation",
    "device_context_observation",
    "inferred_place_observation",
    "temporal_feature_vector",
    "user_place",
    "timing_review_flag",
)

_PHASE3_ENUMS = (
    "capture_method",
    "capture_trigger",
    "geospatial_source_type",
    "radio_source_type",
    "motion_state",
    "place_category",
    "sensor_availability_state",
    "sensor_retention_policy",
    "timing_review_flag_type",
    "timing_review_flag_status",
)

_PHASE4_TABLES = (
    "model_invocation",
    "temporal_extracted_context_event",
    "temporal_correction",
    "resource_dependency",
    "preflight_check",
)

_PHASE4_ENUMS = (
    "confirmation_state",
    "model_role",
)
