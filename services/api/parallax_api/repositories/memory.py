from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pydantic import BaseModel

from ..schemas.activity import Activity
from ..schemas.common import MutationEnvelope
from ..schemas.context import (
    CaptureContextSnapshot,
    ContextCapturePolicy,
    InferredPlaceObservation,
    TemporalContextAnnotation,
    TimingReviewFlag,
    UserPlace,
)
from ..schemas.extraction import (
    ExtractedContextEvent,
    ModelInvocationRecord,
    TemporalCorrection,
)
from ..schemas.profile import ActivityProfileStats
from ..schemas.timing import ModelUpdateDecision, TimingEvent, TimingEventSpan, TimingSession
from .mutation_log import StoredMutation

DeviceMutationKey = tuple[UUID, str, str]
IdempotencyMutationKey = tuple[UUID, str]


@dataclass
class MutationRecord:
    mutation_type: str
    entity_type: str
    entity_id: UUID | None
    result: object


@dataclass
class InMemoryStore:
    activities: dict[UUID, Activity] = field(default_factory=dict)
    activity_keys: dict[tuple[UUID, str], UUID] = field(default_factory=dict)
    sessions: dict[UUID, TimingSession] = field(default_factory=dict)
    session_events: dict[UUID, list[TimingEvent]] = field(default_factory=dict)
    session_spans: dict[UUID, list[TimingEventSpan]] = field(default_factory=dict)
    annotations: dict[UUID, TemporalContextAnnotation] = field(default_factory=dict)
    session_annotations: dict[UUID, list[UUID]] = field(default_factory=dict)
    context_policies: dict[UUID, ContextCapturePolicy] = field(default_factory=dict)
    capture_snapshots: dict[UUID, CaptureContextSnapshot] = field(default_factory=dict)
    session_snapshots: dict[UUID, list[UUID]] = field(default_factory=dict)
    places: dict[UUID, UserPlace] = field(default_factory=dict)
    inferred_place_observations: dict[UUID, InferredPlaceObservation] = field(default_factory=dict)
    review_flags: dict[UUID, TimingReviewFlag] = field(default_factory=dict)
    model_invocations: dict[UUID, ModelInvocationRecord] = field(default_factory=dict)
    extracted_events: dict[UUID, ExtractedContextEvent] = field(default_factory=dict)
    temporal_corrections: dict[UUID, TemporalCorrection] = field(default_factory=dict)
    review_decisions: dict[UUID, list[ModelUpdateDecision]] = field(default_factory=dict)
    activity_stats: dict[UUID, ActivityProfileStats] = field(default_factory=dict)
    mutation_records: dict[DeviceMutationKey, MutationRecord] = field(default_factory=dict)
    idempotency_records: dict[IdempotencyMutationKey, MutationRecord] = field(default_factory=dict)


class InMemoryMutationLogRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def lock(self, user_id: UUID, mutation: MutationEnvelope) -> None:
        return None

    def get(self, user_id: UUID, mutation: MutationEnvelope) -> StoredMutation | None:
        record = self._store.mutation_records.get(
            _device_key(user_id, mutation)
        ) or self._store.idempotency_records.get(_idempotency_key(user_id, mutation))
        if record is None:
            return None
        return StoredMutation(
            mutation_type=record.mutation_type,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            result=record.result,
        )

    def save(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        entity_id: UUID | None,
        result: BaseModel,
    ) -> None:
        record = MutationRecord(
            mutation_type=mutation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
        )
        self._store.mutation_records[_device_key(user_id, mutation)] = record
        self._store.idempotency_records[_idempotency_key(user_id, mutation)] = record


def _device_key(user_id: UUID, mutation: MutationEnvelope) -> DeviceMutationKey:
    return (user_id, mutation.client_device_id, mutation.client_mutation_id)


def _idempotency_key(user_id: UUID, mutation: MutationEnvelope) -> IdempotencyMutationKey:
    return (user_id, mutation.idempotency_key)
