from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from ..domain.feature_vectors import build_temporal_feature_vectors
from ..domain.temporal_query import (
    base_query_limitations,
    build_temporal_query_plan,
    confidence_for_sample_size,
    deterministic_delay_answer,
    deterministic_duration_answer,
)
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

_ACTIVE_DURATION_INCLUSIONS = {"full", "active_duration_only"}
_WALL_DURATION_INCLUSIONS = {"full", "wall_envelope_only"}
_DURATION_BASELINE_INCLUSIONS = _ACTIVE_DURATION_INCLUSIONS | _WALL_DURATION_INCLUSIONS
_FRICTION_INCLUSIONS = {"full", "friction_patterns_only", "query_evidence_only"}


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
        activity_name = (
            self._store.activities[request.activity_id].display_name
            if request.activity_id in self._store.activities
            else None
        )
        plan = build_temporal_query_plan(
            question=request.question,
            activity_id=request.activity_id,
            activity_name=activity_name,
            time_window=request.time_window,
        )
        if plan.intent == "delay_drivers":
            facts, evidence = self._delay_facts(user_id, plan.activity_id, plan.window.days)
            answer_text = deterministic_delay_answer(facts)
        else:
            facts, evidence = self._duration_facts(user_id, plan.activity_id, plan.window.days)
            answer_text = deterministic_duration_answer(facts)
        facts.update(
            {
                "intent": plan.intent,
                "activity_id": str(plan.activity_id) if plan.activity_id else None,
                "activity_name": plan.activity_name,
                "time_window": plan.window.label,
                "window_days": plan.window.days,
            }
        )
        sample_size = _int_value(facts.get("sample_size"))
        confidence = confidence_for_sample_size(sample_size)
        facts["confidence"] = confidence
        privacy_settings = self._store.privacy_settings.get(user_id)
        answer = TemporalQueryAnswer(
            id=uuid4(),
            user_id=user_id,
            question=request.question,
            answer=answer_text,
            confidence=confidence,
            sample_size=sample_size,
            time_window=plan.window.label,
            computed_facts=facts,
            limitations=base_query_limitations(
                sample_size=sample_size,
                include_raw_quotes=request.include_raw_quotes,
                raw_quotes_allowed=bool(
                    privacy_settings and privacy_settings.allow_raw_notes_in_query_answers
                ),
            ),
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

    def _duration_facts(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> tuple[dict[str, object], list[TemporalQueryEvidenceItem]]:
        sessions = [
            session
            for session in self._query_sessions(user_id, activity_id, window_days)
            if session.model_inclusion in _DURATION_BASELINE_INCLUSIONS
        ]
        active_values = sorted(
            session.active_seconds
            for session in sessions
            if session.model_inclusion in _ACTIVE_DURATION_INCLUSIONS
            and session.active_seconds is not None
        )
        wall_values = sorted(
            session.wall_seconds
            for session in sessions
            if session.model_inclusion in _WALL_DURATION_INCLUSIONS
            and session.wall_seconds is not None
        )
        evidence = [
            TemporalQueryEvidenceItem(
                entity_type="timing_session",
                entity_id=session.id,
                summary=_duration_evidence_summary(session),
                occurred_at=session.completed_at,
                score=1.0,
            )
            for session in sessions[:5]
        ]
        return {
            "sample_size": max(len(active_values), len(wall_values)),
            "active_sample_size": len(active_values),
            "wall_sample_size": len(wall_values),
            "active_p50_seconds": _percentile(active_values, 0.5),
            "active_p80_seconds": _percentile(active_values, 0.8),
            "wall_p50_seconds": _percentile(wall_values, 0.5),
            "wall_p80_seconds": _percentile(wall_values, 0.8),
        }, evidence

    def _delay_facts(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> tuple[dict[str, object], list[TemporalQueryEvidenceItem]]:
        sessions = [
            session
            for session in self._query_sessions(user_id, activity_id, window_days)
            if session.model_inclusion in _FRICTION_INCLUSIONS
        ]
        session_ids = {session.id for session in sessions}
        spans = [
            span
            for spans_for_session in self._store.session_spans.values()
            for span in spans_for_session
            if span.user_id == user_id
            and span.session_id in session_ids
            and span.friction_category not in {"none", "unknown"}
        ]
        grouped: dict[str, list[int]] = {}
        for span in spans:
            grouped.setdefault(span.friction_category, []).append(span.duration_seconds or 0)
        categories: list[dict[str, object]] = [
            {
                "friction_category": category,
                "event_count": len(values),
                "total_seconds": sum(values),
                "p80_seconds": _percentile(sorted(values), 0.8),
            }
            for category, values in grouped.items()
        ]
        categories.sort(
            key=lambda item: (
                -_int_value(item["event_count"]),
                -_int_value(item["total_seconds"]),
                str(item["friction_category"]),
            )
        )
        evidence = [
            TemporalQueryEvidenceItem(
                entity_type="timing_event_span",
                entity_id=span.id,
                summary=(
                    f"{span.friction_category} friction: {span.duration_seconds}s, "
                    f"policy={span.count_policy}."
                ),
                occurred_at=span.started_at,
                score=1.0,
            )
            for span in spans[:5]
        ]
        return {
            "sample_size": len(sessions),
            "friction_categories": categories,
        }, evidence

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

    def _query_sessions(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> list[TimingSession]:
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        return [
            session
            for session in self._reviewed_sessions(user_id, activity_id, None)
            if _is_at_or_after(session.completed_at, cutoff)
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


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, round((len(values) - 1) * percentile)))
    return values[index]


def _duration_evidence_summary(session: TimingSession) -> str:
    metrics: list[str] = []
    if session.model_inclusion in _ACTIVE_DURATION_INCLUSIONS:
        metrics.append(f"active={session.active_seconds}s")
    if session.model_inclusion in _WALL_DURATION_INCLUSIONS:
        metrics.append(f"wall={session.wall_seconds}s")
    return f"Reviewed run: {', '.join(metrics)}."


def _is_at_or_after(value: datetime | None, cutoff: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value >= cutoff


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return 0
