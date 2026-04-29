from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.privacy import PrivacyDeleteRequest, PrivacyExportRequest, PrivacyRedactRequest

_COUNT_SQL = {
    "activity": "select count(*) from activity where user_id = %s",
    "temporal_context_annotation": (
        "select count(*) from temporal_context_annotation where user_id = %s"
    ),
    "user_place": "select count(*) from user_place where user_id = %s",
    "capture_context_snapshot": (
        "select count(*) from capture_context_snapshot where user_id = %s"
    ),
    "model_invocation": "select count(*) from model_invocation where user_id = %s",
}

_SNAPSHOT_CHILD_DELETE_SQL = {
    "geospatial_observation": """
        delete from geospatial_observation
        where user_id = %s
          and (%s::uuid is null or id = %s::uuid or snapshot_id = %s::uuid)
        returning id
        """,
    "radio_observation": """
        delete from radio_observation
        where user_id = %s
          and (%s::uuid is null or id = %s::uuid or snapshot_id = %s::uuid)
        returning id
        """,
    "device_context_observation": """
        delete from device_context_observation
        where user_id = %s
          and (%s::uuid is null or id = %s::uuid or snapshot_id = %s::uuid)
        returning id
        """,
}


class PostgresPrivacyLifecycleRepository:
    """Completes privacy workflows against source and derived PostgreSQL data."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def complete_export(self, user_id: UUID, request: PrivacyExportRequest) -> dict[str, object]:
        counts: dict[str, object] = {
            "activities": self._count("activity", user_id),
            "annotations": self._count("temporal_context_annotation", user_id)
            if request.include_raw_context
            else 0,
            "places": self._count("user_place", user_id),
            "snapshots": self._count("capture_context_snapshot", user_id),
            "model_invocations": self._count("model_invocation", user_id),
        }
        manifest = {
            **counts,
            "include_raw_context": request.include_raw_context,
            "include_audio": request.include_audio,
        }
        self._record_completion(user_id, "privacy_export_completed", manifest)
        return {"export_manifest": manifest}

    def complete_redact(self, user_id: UUID, request: PrivacyRedactRequest) -> dict[str, object]:
        if request.entity_type == "temporal_context_annotation":
            count = self._redact_annotation(user_id, request.entity_id, status="redacted")
        elif request.entity_type == "user_place":
            count = self._redact_places(user_id, request.entity_id)
        elif request.entity_type == "activity":
            count = self._redact_activities(user_id, request.entity_id)
        else:
            count = 0
        redacted = {
            "entity_type": request.entity_type,
            "entity_id": str(request.entity_id),
            "count": count,
        }
        self._record_completion(user_id, "privacy_redact_completed", redacted)
        return {"redacted": redacted}

    def complete_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> dict[str, object]:
        deleted: dict[str, int] = {}
        if request.delete_scope in {"raw_context", "account"}:
            deleted["annotations"] = self._redact_annotation(
                user_id,
                request.entity_id,
                status="deleted",
            )
            deleted["evidence_items"] = self._delete_evidence_items(user_id, request.entity_id)
            deleted["feature_vectors"] = self._delete_feature_vectors(user_id, request.entity_id)
        elif request.delete_scope == "location_context":
            deleted["location_observations"] = self._delete_snapshot_child_rows(
                "geospatial_observation",
                user_id,
                request.entity_id,
            )
            deleted["feature_vectors"] = self._delete_feature_vectors(user_id, request.entity_id)
            deleted["evidence_items"] = self._delete_evidence_items(user_id, request.entity_id)
        elif request.delete_scope == "radio_context":
            deleted["radio_observations"] = self._delete_snapshot_child_rows(
                "radio_observation",
                user_id,
                request.entity_id,
            )
            deleted["feature_vectors"] = self._delete_feature_vectors(user_id, request.entity_id)
            deleted["evidence_items"] = self._delete_evidence_items(user_id, request.entity_id)
        elif request.delete_scope == "place_context":
            deleted["places"] = self._redact_places(user_id, request.entity_id)
            deleted["inferred_places"] = self._redact_inferred_places(user_id, request.entity_id)
            deleted["snapshot_place_refs"] = self._clear_snapshot_place_refs(
                user_id,
                request.entity_id,
            )
            deleted["feature_vectors"] = self._delete_feature_vectors(user_id, request.entity_id)
            deleted["evidence_items"] = self._delete_evidence_items(user_id, request.entity_id)
        elif request.delete_scope == "context_features":
            deleted["feature_vectors"] = self._delete_feature_vectors(user_id, request.entity_id)
            deleted["evidence_items"] = self._delete_evidence_items(user_id, request.entity_id)
        elif request.delete_scope == "audio":
            deleted["audio_refs"] = self._clear_audio_refs(user_id, request.entity_id)
        elif request.delete_scope == "activity":
            deleted["activities"] = self._redact_activities(user_id, request.entity_id)
        if request.delete_scope == "account":
            deleted["location_observations"] = self._delete_snapshot_child_rows(
                "geospatial_observation",
                user_id,
                None,
            )
            deleted["radio_observations"] = self._delete_snapshot_child_rows(
                "radio_observation",
                user_id,
                None,
            )
            deleted["device_context_observations"] = self._delete_snapshot_child_rows(
                "device_context_observation",
                user_id,
                None,
            )
            deleted["places"] = self._redact_places(user_id, None)
            deleted["inferred_places"] = self._redact_inferred_places(user_id, None)
            deleted["snapshot_place_refs"] = self._clear_snapshot_place_refs(user_id, None)
            deleted["audio_refs"] = self._clear_audio_refs(user_id, None)
            deleted["activities"] = self._redact_activities(user_id, None)
        self._record_completion(user_id, "privacy_delete_completed", deleted)
        return {"deleted": deleted}

    def _count(self, table: str, user_id: UUID) -> int:
        sql = _COUNT_SQL[table]
        with self._connection.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
        return int(row["count"]) if row is not None else 0

    def _redact_annotation(self, user_id: UUID, entity_id: UUID | None, *, status: str) -> int:
        return self._execute_count(
            """
            update temporal_context_annotation
            set raw_text = null,
                redacted_text = null,
                audio_object_ref = null,
                status = %s::annotation_status,
                metadata = metadata || '{"privacy_redacted": true}'::jsonb
            where user_id = %s
              and (%s::uuid is null or id = %s::uuid)
            returning id
            """,
            (status, user_id, entity_id, entity_id),
        )

    def _clear_audio_refs(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            update temporal_context_annotation
            set audio_object_ref = null,
                metadata = metadata || '{"audio_deleted": true}'::jsonb
            where user_id = %s
              and audio_object_ref is not null
              and (%s::uuid is null or id = %s::uuid)
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _redact_places(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            update user_place
            set display_name = 'Deleted place',
                latitude = null,
                longitude = null,
                radius_meters = null,
                privacy_class = 'private',
                confirmed_by_user = false,
                is_sensitive = true,
                aliases = '{}'::text[],
                metadata = '{"privacy_redacted": true}'::jsonb,
                updated_at = now()
            where user_id = %s
              and (%s::uuid is null or id = %s::uuid)
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _redact_inferred_places(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            update inferred_place_observation
            set user_place_id = null,
                candidate_label = null,
                evidence = '{}'::jsonb,
                sensitive_label_detected = false
            where user_id = %s
              and (%s::uuid is null or user_place_id = %s::uuid)
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _clear_snapshot_place_refs(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            update capture_context_snapshot
            set user_place_id = null
            where user_id = %s
              and user_place_id is not null
              and (%s::uuid is null or user_place_id = %s::uuid)
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _delete_snapshot_child_rows(
        self,
        table: str,
        user_id: UUID,
        entity_id: UUID | None,
    ) -> int:
        sql = _SNAPSHOT_CHILD_DELETE_SQL[table]
        return self._execute_count(sql, (user_id, entity_id, entity_id, entity_id))

    def _delete_feature_vectors(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            delete from temporal_feature_vector
            where user_id = %s
              and (
                %s::uuid is null
                or id = %s::uuid
                or activity_id = %s::uuid
                or session_id = %s::uuid
                or snapshot_id = %s::uuid
              )
            returning id
            """,
            (user_id, entity_id, entity_id, entity_id, entity_id, entity_id),
        )

    def _delete_evidence_items(self, user_id: UUID, entity_id: UUID | None) -> int:
        return self._execute_count(
            """
            delete from evidence_item
            where user_id = %s
              and (
                %s::uuid is null
                or entity_id = %s::uuid
                or entity_type in (
                  'temporal_context_annotation',
                  'capture_context_snapshot',
                  'geospatial_observation',
                  'radio_observation',
                  'device_context_observation',
                  'inferred_place_observation',
                  'temporal_feature_vector'
                )
              )
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _redact_activities(self, user_id: UUID, entity_id: UUID | None) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                delete from activity_alias
                where user_id = %s
                  and (%s::uuid is null or activity_id = %s::uuid)
                """,
                (user_id, entity_id, entity_id),
            )
            cursor.execute(
                """
                delete from activity_relationship
                where user_id = %s
                  and (
                    %s::uuid is null
                    or from_activity_id = %s::uuid
                    or to_activity_id = %s::uuid
                  )
                """,
                (user_id, entity_id, entity_id, entity_id),
            )
            cursor.execute(
                """
                update preflight_check
                set state = 'retired',
                    metadata = metadata || '{"privacy_redacted": true}'::jsonb,
                    updated_at = now()
                where user_id = %s
                  and (%s::uuid is null or activity_id = %s::uuid)
                """,
                (user_id, entity_id, entity_id),
            )
        return self._execute_count(
            """
            update activity
            set display_name = 'Deleted activity',
                canonical_key = null,
                description = null,
                status = 'archived',
                privacy_class = 'private',
                metadata = metadata || '{"privacy_redacted": true}'::jsonb,
                updated_at = now()
            where user_id = %s
              and (%s::uuid is null or id = %s::uuid)
            returning id
            """,
            (user_id, entity_id, entity_id),
        )

    def _execute_count(self, sql: str, params: tuple[object, ...]) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            return len(cursor.fetchall())

    def _record_completion(
        self,
        user_id: UUID,
        event_name: str,
        metadata: Mapping[str, object],
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into audit_log (user_id, actor_user_id, event_name, metadata)
                values (%s, %s, %s, %s)
                """,
                (user_id, user_id, event_name, Jsonb(metadata)),
            )
