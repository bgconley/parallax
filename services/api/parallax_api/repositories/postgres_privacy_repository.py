from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
)
from .postgres_identity import ensure_app_user


class PostgresPrivacyRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def get_settings(self, user_id: UUID) -> PrivacySettings:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                select user_id, retain_raw_context, retain_transcripts, retain_audio,
                  allow_cloud_llm_fallback, allow_raw_notes_in_query_answers,
                  allow_embedding_of_sensitive_notes, community_aggregation_opt_in,
                  raw_context_retention_days, audio_retention_days, updated_at
                from privacy_settings
                where user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("privacy settings missing after user bootstrap")
        return PrivacySettings.model_validate(dict(row))

    def update_settings(self, user_id: UUID, settings: PrivacySettings) -> PrivacySettings:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                update privacy_settings
                set retain_raw_context = %s,
                    retain_transcripts = %s,
                    retain_audio = %s,
                    allow_cloud_llm_fallback = %s,
                    allow_raw_notes_in_query_answers = %s,
                    allow_embedding_of_sensitive_notes = %s,
                    community_aggregation_opt_in = %s,
                    raw_context_retention_days = %s,
                    audio_retention_days = %s,
                    updated_at = now()
                where user_id = %s
                returning user_id, retain_raw_context, retain_transcripts, retain_audio,
                  allow_cloud_llm_fallback, allow_raw_notes_in_query_answers,
                  allow_embedding_of_sensitive_notes, community_aggregation_opt_in,
                  raw_context_retention_days, audio_retention_days, updated_at
                """,
                (
                    settings.retain_raw_context,
                    settings.retain_transcripts,
                    settings.retain_audio,
                    settings.allow_cloud_llm_fallback,
                    settings.allow_raw_notes_in_query_answers,
                    settings.allow_embedding_of_sensitive_notes,
                    settings.community_aggregation_opt_in,
                    settings.raw_context_retention_days,
                    settings.audio_retention_days,
                    user_id,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("privacy settings update returned no row")
        return PrivacySettings.model_validate(dict(row))

    def request_export(self, user_id: UUID, request: PrivacyExportRequest) -> UUID:
        return self._record_audit(user_id, "privacy_export_requested", None, None, request)

    def request_redact(self, user_id: UUID, request: PrivacyRedactRequest) -> UUID:
        with self._connection.cursor() as cursor:
            if request.entity_type == "temporal_context_annotation":
                cursor.execute(
                    """
                    update temporal_context_annotation
                    set raw_text = null, redacted_text = null, status = 'redacted'
                    where user_id = %s and id = %s
                    """,
                    (user_id, request.entity_id),
                )
        return self._record_audit(
            user_id,
            "privacy_redact_requested",
            request.entity_type,
            request.entity_id,
            request,
        )

    def request_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> UUID:
        if request.delete_scope in {"raw_context", "account"}:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    update temporal_context_annotation
                    set raw_text = null, redacted_text = null, status = 'deleted'
                    where user_id = %s
                    """,
                    (user_id,),
                )
        return self._record_audit(
            user_id,
            "privacy_delete_requested",
            None,
            request.entity_id,
            request,
        )

    def _record_audit(
        self,
        user_id: UUID,
        event_name: str,
        entity_type: str | None,
        entity_id: UUID | None,
        request: object,
    ) -> UUID:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into audit_log (
                  user_id, actor_user_id, event_name, entity_type, entity_id, metadata
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    user_id,
                    user_id,
                    event_name,
                    entity_type,
                    entity_id,
                    Jsonb({"request": _safe_json(request)}),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("audit log insert returned no row")
        return UUID(str(row["id"]))


def _safe_json(request: object) -> dict[str, object]:
    if hasattr(request, "model_dump"):
        data = request.model_dump(mode="json")
        data.pop("mutation", None)
        return data
    return {}
