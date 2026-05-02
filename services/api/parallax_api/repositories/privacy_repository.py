from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.activity import Activity
from ..schemas.context import (
    InferredPlaceObservation,
    TemporalContextAnnotation,
    UserPlace,
)
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
        return uuid4()

    def request_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> UUID:
        return uuid4()

    def complete_export(self, user_id: UUID, request: PrivacyExportRequest) -> dict[str, object]:
        return {
            "export_manifest": {
                "activities": sum(
                    1 for item in self._store.activities.values() if item.user_id == user_id
                ),
                "annotations": sum(
                    1 for item in self._store.annotations.values() if item.user_id == user_id
                ),
                "places": sum(1 for item in self._store.places.values() if item.user_id == user_id),
                "snapshots": sum(
                    1 for item in self._store.capture_snapshots.values() if item.user_id == user_id
                ),
                "include_raw_context": request.include_raw_context,
                "include_audio": request.include_audio,
            }
        }

    def complete_redact(self, user_id: UUID, request: PrivacyRedactRequest) -> dict[str, object]:
        count = _redact_entity(self._store, user_id, request.entity_type, request.entity_id)
        derived_artifacts = (
            _invalidate_temporal_query_artifacts(self._store, user_id) if count else {}
        )
        return {
            "redacted": {
                "entity_type": request.entity_type,
                "entity_id": str(request.entity_id),
                "count": count,
                "derived_artifacts": derived_artifacts,
            }
        }

    def complete_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> dict[str, object]:
        deleted: dict[str, int] = _invalidate_temporal_query_artifacts(self._store, user_id)
        if request.delete_scope in {"raw_context", "account"}:
            deleted["annotations"] = _delete_annotations(self._store, user_id, request.entity_id)
        elif request.delete_scope == "location_context":
            deleted.update(_delete_location_context(self._store, user_id, request.entity_id))
        elif request.delete_scope == "radio_context":
            deleted.update(_delete_radio_context(self._store, user_id, request.entity_id))
        elif request.delete_scope == "place_context":
            deleted.update(_delete_place_context(self._store, user_id, request.entity_id))
        elif request.delete_scope == "audio":
            deleted["audio_refs"] = _delete_audio_refs(self._store, user_id, request.entity_id)
        elif request.delete_scope == "activity":
            deleted["activities"] = _delete_activities(self._store, user_id, request.entity_id)
        elif request.delete_scope == "context_features":
            deleted["feature_vectors"] = _delete_feature_vectors(
                self._store,
                user_id,
                request.entity_id,
            )
        if request.delete_scope == "account":
            deleted.update(_delete_location_context(self._store, user_id, None))
            deleted.update(_delete_radio_context(self._store, user_id, None))
            deleted.update(_delete_place_context(self._store, user_id, None))
            deleted["audio_refs"] = _delete_audio_refs(self._store, user_id, None)
            deleted["activities"] = _delete_activities(self._store, user_id, None)
        return {"deleted": deleted}


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


def _redact_entity(store: InMemoryStore, user_id: UUID, entity_type: str, entity_id: UUID) -> int:
    if entity_type == "temporal_context_annotation":
        annotation = store.annotations.get(entity_id)
        if annotation is not None and annotation.user_id == user_id:
            store.annotations[entity_id] = annotation.model_copy(
                update={
                    "raw_text": None,
                    "redacted_text": None,
                    "audio_object_ref": None,
                    "status": "redacted",
                }
            )
            return 1
    if entity_type == "user_place":
        place = store.places.get(entity_id)
        if place is not None and place.user_id == user_id:
            store.places[entity_id] = _redacted_place(place, label="Redacted place")
            return 1
    return 0


def _delete_annotations(store: InMemoryStore, user_id: UUID, entity_id: UUID | None) -> int:
    count = 0
    for annotation_id, annotation in list(store.annotations.items()):
        if annotation.user_id != user_id or (entity_id is not None and annotation.id != entity_id):
            continue
        store.annotations[annotation_id] = _deleted_annotation(annotation)
        count += 1
    return count


def _delete_audio_refs(store: InMemoryStore, user_id: UUID, entity_id: UUID | None) -> int:
    count = 0
    for annotation_id, annotation in list(store.annotations.items()):
        if annotation.user_id != user_id or (entity_id is not None and annotation.id != entity_id):
            continue
        if annotation.audio_object_ref is not None:
            count += 1
        store.annotations[annotation_id] = annotation.model_copy(update={"audio_object_ref": None})
    return count


def _delete_location_context(
    store: InMemoryStore,
    user_id: UUID,
    entity_id: UUID | None,
) -> dict[str, int]:
    count = 0
    for snapshot_id, snapshot in list(store.capture_snapshots.items()):
        if snapshot.user_id != user_id or (entity_id is not None and snapshot.id != entity_id):
            continue
        count += len(snapshot.geospatial_observations)
        store.capture_snapshots[snapshot_id] = snapshot.model_copy(
            update={"geospatial_observations": [], "location_state": "unavailable"}
        )
    feature_vectors = _delete_feature_vectors(store, user_id, entity_id)
    return {"location_observations": count, "feature_vectors": feature_vectors}


def _delete_radio_context(
    store: InMemoryStore,
    user_id: UUID,
    entity_id: UUID | None,
) -> dict[str, int]:
    count = 0
    for snapshot_id, snapshot in list(store.capture_snapshots.items()):
        if snapshot.user_id != user_id or (entity_id is not None and snapshot.id != entity_id):
            continue
        count += len(snapshot.radio_observations)
        store.capture_snapshots[snapshot_id] = snapshot.model_copy(
            update={"radio_observations": [], "radio_state": "unavailable"}
        )
    feature_vectors = _delete_feature_vectors(store, user_id, entity_id)
    return {"radio_observations": count, "feature_vectors": feature_vectors}


def _delete_place_context(
    store: InMemoryStore,
    user_id: UUID,
    entity_id: UUID | None,
) -> dict[str, int]:
    places = 0
    for place_id, place in list(store.places.items()):
        if place.user_id != user_id or (entity_id is not None and place.id != entity_id):
            continue
        store.places[place_id] = _redacted_place(place, label="Deleted place")
        places += 1
    inferred = 0
    for observation_id, observation in list(store.inferred_place_observations.items()):
        if observation.user_id != user_id:
            continue
        if entity_id is not None and observation.user_place_id != entity_id:
            continue
        store.inferred_place_observations[observation_id] = _redacted_inferred_place(observation)
        inferred += 1
    for snapshot_id, snapshot in list(store.capture_snapshots.items()):
        if snapshot.user_id != user_id:
            continue
        if entity_id is not None and snapshot.user_place_id != entity_id:
            continue
        store.capture_snapshots[snapshot_id] = snapshot.model_copy(update={"user_place_id": None})
    feature_vectors = _delete_feature_vectors(store, user_id, entity_id)
    return {"places": places, "inferred_places": inferred, "feature_vectors": feature_vectors}


def _delete_activities(store: InMemoryStore, user_id: UUID, entity_id: UUID | None) -> int:
    count = 0
    for activity_id, activity in list(store.activities.items()):
        if activity.user_id != user_id or (entity_id is not None and activity.id != entity_id):
            continue
        store.activities[activity_id] = _deleted_activity(activity)
        count += 1
    store.activity_keys = {
        key: value
        for key, value in store.activity_keys.items()
        if not (key[0] == user_id and (entity_id is None or value == entity_id))
    }
    return count


def _delete_feature_vectors(store: InMemoryStore, user_id: UUID, entity_id: UUID | None) -> int:
    count = 0
    for vector_id, vector in list(store.temporal_feature_vectors.items()):
        if vector.user_id != user_id:
            continue
        if (
            entity_id is not None
            and vector.activity_id != entity_id
            and vector.session_id != entity_id
        ):
            continue
        del store.temporal_feature_vectors[vector_id]
        count += 1
    return count


def _invalidate_temporal_query_artifacts(store: InMemoryStore, user_id: UUID) -> dict[str, int]:
    count = 0
    for answer_id, answer in list(store.temporal_query_answers.items()):
        if answer.user_id != user_id:
            continue
        del store.temporal_query_answers[answer_id]
        count += 1
    return {
        "query_answers": count,
        "query_retrieval_documents": 0,
        "query_evidence_items": 0,
        "query_evidence_bundles": 0,
        "query_outbox_events": 0,
    }


def _deleted_annotation(annotation: TemporalContextAnnotation) -> TemporalContextAnnotation:
    return annotation.model_copy(
        update={
            "raw_text": None,
            "redacted_text": None,
            "audio_object_ref": None,
            "status": "deleted",
        }
    )


def _redacted_place(place: UserPlace, *, label: str) -> UserPlace:
    return place.model_copy(
        update={
            "display_name": label,
            "latitude": None,
            "longitude": None,
            "radius_meters": None,
            "privacy_class": "private",
            "confirmed_by_user": False,
            "is_sensitive": True,
            "aliases": [],
            "metadata": {"privacy_redacted": True},
            "updated_at": datetime.now(UTC),
        }
    )


def _redacted_inferred_place(observation: InferredPlaceObservation) -> InferredPlaceObservation:
    return observation.model_copy(
        update={
            "user_place_id": None,
            "candidate_label": None,
            "evidence": {},
            "sensitive_label_detected": False,
        }
    )


def _deleted_activity(activity: Activity) -> Activity:
    return activity.model_copy(
        update={
            "display_name": "Deleted activity",
            "canonical_key": None,
            "description": None,
            "status": "archived",
            "privacy_class": "private",
            "updated_at": datetime.now(UTC),
        }
    )
