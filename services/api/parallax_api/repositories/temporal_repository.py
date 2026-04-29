from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from ..domain.feature_vectors import build_temporal_feature_vectors
from ..schemas.temporal import (
    CreatePredictionRequest,
    FeatureFamily,
    PredictionOutcome,
    RecordPredictionOutcomeRequest,
    TemporalFeatureVector,
    TemporalPrediction,
    TemporalQueryAnswer,
    TemporalQueryEvidenceItem,
    TemporalQueryRequest,
)
from ..schemas.timing import TimingSession
from .context_policy_defaults import default_context_capture_policy
from .memory import InMemoryStore
from .timing_repository import TimingRepository


class TemporalRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_prediction(
        self,
        user_id: UUID,
        request: CreatePredictionRequest,
    ) -> TemporalPrediction:
        stats = self._store.activity_stats.get(request.activity_id)
        prediction = TemporalPrediction(
            id=uuid4(),
            user_id=user_id,
            activity_id=request.activity_id,
            prediction_type=request.prediction_type,
            work_mode=request.work_mode,
            actor_mode="unknown",
            active_p50_seconds=stats.active_p50_seconds if stats else None,
            active_p80_seconds=stats.active_p80_seconds if stats else None,
            wall_p50_seconds=stats.wall_p50_seconds if stats else None,
            wall_p80_seconds=stats.wall_p80_seconds if stats else None,
            start_latency_p80_seconds=stats.start_latency_p80_seconds if stats else None,
            setup_risk_seconds_p80=None,
            basis="personal_rolling_stats" if stats else "insufficient_data",
            sample_size=stats.sample_size if stats else 0,
            confidence=stats.confidence if stats else "very_low",
            warnings=[] if stats else ["insufficient reviewed timing history"],
            evidence_bundle_id=None,
        )
        self._store.temporal_predictions[prediction.id] = prediction
        return prediction

    def record_prediction_outcome(
        self,
        user_id: UUID,
        prediction_id: UUID,
        request: RecordPredictionOutcomeRequest,
    ) -> PredictionOutcome:
        prediction = self._store.temporal_predictions.get(prediction_id)
        if prediction is None or prediction.user_id != user_id:
            raise KeyError(prediction_id)
        outcome = PredictionOutcome(
            id=uuid4(),
            user_id=user_id,
            prediction_id=prediction_id,
            session_id=request.session_id,
            outcome_type=request.outcome_type,
            actual_active_seconds=request.actual_active_seconds,
            actual_wall_seconds=request.actual_wall_seconds,
            created_at=datetime.now(UTC),
        )
        self._store.prediction_outcomes[outcome.id] = outcome
        return outcome

    def create_query_answer(
        self,
        user_id: UUID,
        request: TemporalQueryRequest,
    ) -> TemporalQueryAnswer:
        evidence = [
            TemporalQueryEvidenceItem(
                entity_type="activity",
                entity_id=activity.id,
                summary=f"Activity: {activity.display_name}",
                occurred_at=activity.created_at,
                score=1.0,
            )
            for activity in self._store.activities.values()
            if activity.user_id == user_id
            and (request.activity_id is None or activity.id == request.activity_id)
        ][:5]
        answer = TemporalQueryAnswer(
            id=uuid4(),
            user_id=user_id,
            question=request.question,
            answer="Deterministic facts are available in computed_facts.",
            confidence="low" if evidence else "very_low",
            sample_size=len(evidence),
            time_window=request.time_window,
            computed_facts={"evidence_count": len(evidence)},
            limitations=["baseline deterministic query path"],
            evidence=evidence,
            status="complete",
        )
        self._store.temporal_query_answers[answer.id] = answer
        return answer

    def get_query_answer(self, user_id: UUID, answer_id: UUID) -> TemporalQueryAnswer | None:
        answer = self._store.temporal_query_answers.get(answer_id)
        if answer is None or answer.user_id != user_id:
            return None
        return answer

    def generate_feature_vectors(
        self,
        user_id: UUID,
        *,
        activity_id: UUID | None,
        session_id: UUID | None,
        feature_families: list[str],
    ) -> list[TemporalFeatureVector]:
        families = [cast(FeatureFamily, family) for family in feature_families]
        reviewed_sessions = self._reviewed_sessions(user_id, activity_id, session_id)
        if activity_id is None and reviewed_sessions:
            activity_id = reviewed_sessions[0].activity_id
        policy = self._store.context_policies.get(user_id) or default_context_capture_policy(
            user_id
        )
        snapshot_count = self._eligible_snapshot_count(user_id, reviewed_sessions)
        drafts = build_temporal_feature_vectors(
            activity_id=activity_id,
            session_id=session_id,
            feature_families=families,
            reviewed_sessions=reviewed_sessions,
            context_policy=policy,
            eligible_snapshot_count=snapshot_count,
        )
        self._delete_existing_vectors(user_id, activity_id, session_id, families)
        vectors = [
            TemporalFeatureVector(
                id=uuid4(),
                user_id=user_id,
                activity_id=draft.activity_id,
                session_id=draft.session_id,
                snapshot_id=draft.snapshot_id,
                feature_schema_version=draft.feature_schema_version,
                feature_family=draft.feature_family,
                features=draft.features,
                source_entity_refs=draft.source_entity_refs,
                privacy_class=draft.privacy_class,
                model_eligible=draft.model_eligible,
                exclusion_reason=draft.exclusion_reason,
                generated_at=draft.generated_at,
            )
            for draft in drafts
        ]
        for vector in vectors:
            self._store.temporal_feature_vectors[vector.id] = vector
        return vectors

    def _reviewed_sessions(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        session_id: UUID | None,
    ) -> list[TimingSession]:
        timing = TimingRepository(self._store)
        sessions = [
            timing.get_session(user_id, session.id)
            for session in self._store.sessions.values()
            if session.user_id == user_id
            and (activity_id is None or session.activity_id == activity_id)
            and (session_id is None or session.id == session_id)
            and session.status == "reviewed"
        ]
        return [
            session
            for session in sessions
            if session is not None and session.model_inclusion != "exclude"
        ]

    def _eligible_snapshot_count(self, user_id: UUID, sessions: list[TimingSession]) -> int:
        session_ids = {session.id for session in sessions}
        return sum(
            1
            for snapshot in self._store.capture_snapshots.values()
            if snapshot.user_id == user_id and snapshot.session_id in session_ids
        )

    def _delete_existing_vectors(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        session_id: UUID | None,
        families: list[FeatureFamily],
    ) -> None:
        self._store.temporal_feature_vectors = {
            vector_id: vector
            for vector_id, vector in self._store.temporal_feature_vectors.items()
            if not (
                vector.user_id == user_id
                and (activity_id is None or vector.activity_id == activity_id)
                and (session_id is None or vector.session_id == session_id)
                and vector.feature_family in families
            )
        }
