from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
)
from .memory import InMemoryStore


class PrivacyRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_settings(self, user_id: UUID) -> PrivacySettings:
        settings = self._store.privacy_settings.get(user_id)
        if settings is not None:
            return settings
        settings = default_privacy_settings(user_id)
        self._store.privacy_settings[user_id] = settings
        return settings

    def update_settings(self, user_id: UUID, settings: PrivacySettings) -> PrivacySettings:
        updated = settings.model_copy(update={"user_id": user_id, "updated_at": datetime.now(UTC)})
        self._store.privacy_settings[user_id] = updated
        return updated

    def request_export(self, user_id: UUID, request: PrivacyExportRequest) -> UUID:
        return uuid4()

    def request_redact(self, user_id: UUID, request: PrivacyRedactRequest) -> UUID:
        _redact_entity(self._store, user_id, request.entity_type, request.entity_id)
        return uuid4()

    def request_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> UUID:
        if request.delete_scope in {"raw_context", "account"}:
            for annotation_id, annotation in list(self._store.annotations.items()):
                if annotation.user_id == user_id:
                    self._store.annotations[annotation_id] = annotation.model_copy(
                        update={"raw_text": None, "redacted_text": None, "status": "deleted"}
                    )
        return uuid4()


def default_privacy_settings(user_id: UUID) -> PrivacySettings:
    return PrivacySettings(
        user_id=user_id,
        retain_raw_context=True,
        retain_transcripts=True,
        retain_audio=False,
        allow_cloud_llm_fallback=False,
        allow_raw_notes_in_query_answers=False,
        allow_embedding_of_sensitive_notes=False,
        community_aggregation_opt_in=False,
        raw_context_retention_days=None,
        audio_retention_days=None,
        updated_at=datetime.now(UTC),
    )


def _redact_entity(store: InMemoryStore, user_id: UUID, entity_type: str, entity_id: UUID) -> None:
    if entity_type == "temporal_context_annotation":
        annotation = store.annotations.get(entity_id)
        if annotation is not None and annotation.user_id == user_id:
            store.annotations[entity_id] = annotation.model_copy(
                update={"raw_text": None, "redacted_text": None, "status": "redacted"}
            )
    if entity_type == "user_place":
        place = store.places.get(entity_id)
        if place is not None and place.user_id == user_id:
            store.places[entity_id] = place.model_copy(
                update={"display_name": "Redacted place", "is_sensitive": True}
            )
