from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.temporal import (
    CreatePredictionRequest,
    PredictionOutcome,
    RecordPredictionOutcomeRequest,
    TemporalPrediction,
    TemporalQueryAnswer,
    TemporalQueryEvidenceItem,
    TemporalQueryRequest,
)
from .memory import InMemoryStore


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
