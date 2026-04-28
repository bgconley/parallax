from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.temporal import (
    CreatePredictionRequest,
    PredictionOutcome,
    RecordPredictionOutcomeRequest,
    TemporalPrediction,
    TemporalQueryAnswer,
    TemporalQueryEvidenceItem,
    TemporalQueryRequest,
)


class PostgresTemporalRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create_prediction(
        self,
        user_id: UUID,
        request: CreatePredictionRequest,
    ) -> TemporalPrediction:
        stats = self._latest_stats(user_id, request.activity_id)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into temporal_prediction (
                  user_id, activity_id, prediction_type, work_mode, actor_mode,
                  active_p50_seconds, active_p80_seconds, wall_p50_seconds,
                  wall_p80_seconds, start_latency_p80_seconds, deadline,
                  basis, sample_size, confidence, warnings
                )
                values (%s, %s, %s, %s, 'unknown', %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s)
                returning id, user_id, activity_id, prediction_type, work_mode, actor_mode,
                  active_p50_seconds, active_p80_seconds, wall_p50_seconds,
                  wall_p80_seconds, setup_risk_seconds_p80, start_latency_p80_seconds,
                  basis, sample_size, confidence, warnings, evidence_bundle_id
                """,
                (
                    user_id,
                    request.activity_id,
                    request.prediction_type,
                    request.work_mode,
                    stats.get("active_p50_seconds"),
                    stats.get("active_p80_seconds"),
                    stats.get("wall_p50_seconds"),
                    stats.get("wall_p80_seconds"),
                    stats.get("start_latency_p80_seconds"),
                    request.deadline,
                    "personal_rolling_stats" if stats["sample_size"] else "insufficient_data",
                    stats["sample_size"],
                    stats["confidence"],
                    Jsonb([] if stats["sample_size"] else ["insufficient reviewed timing history"]),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("temporal prediction insert returned no row")
        return TemporalPrediction.model_validate(dict(row))

    def record_prediction_outcome(
        self,
        user_id: UUID,
        prediction_id: UUID,
        request: RecordPredictionOutcomeRequest,
    ) -> PredictionOutcome:
        with self._connection.cursor() as cursor:
            cursor.execute(
                "select 1 from temporal_prediction where user_id = %s and id = %s",
                (user_id, prediction_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(prediction_id)
            cursor.execute(
                """
                insert into prediction_outcome (
                  user_id, prediction_id, session_id, outcome_type,
                  actual_active_seconds, actual_wall_seconds
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id, user_id, prediction_id, session_id, outcome_type,
                  actual_active_seconds, actual_wall_seconds, created_at
                """,
                (
                    user_id,
                    prediction_id,
                    request.session_id,
                    request.outcome_type,
                    request.actual_active_seconds,
                    request.actual_wall_seconds,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("prediction outcome insert returned no row")
        return PredictionOutcome.model_validate(dict(row))

    def create_query_answer(
        self,
        user_id: UUID,
        request: TemporalQueryRequest,
    ) -> TemporalQueryAnswer:
        evidence = self._activity_evidence(user_id, request.activity_id)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into temporal_query_answer (
                  user_id, question, answer, confidence, sample_size, time_window,
                  status, completed_at
                )
                values (%s, %s, %s, %s, %s, %s, 'complete', now())
                returning id, user_id, question, answer, confidence, sample_size,
                  time_window, status
                """,
                (
                    user_id,
                    request.question,
                    "Deterministic facts are available in computed_facts.",
                    "low" if evidence else "very_low",
                    len(evidence),
                    request.time_window,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("temporal query answer insert returned no row")
        return _query_answer_from_row(row, evidence)

    def get_query_answer(self, user_id: UUID, answer_id: UUID) -> TemporalQueryAnswer | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, question, answer, confidence, sample_size,
                  time_window, status
                from temporal_query_answer
                where user_id = %s and id = %s
                """,
                (user_id, answer_id),
            )
            row = cursor.fetchone()
        return _query_answer_from_row(row, []) if row is not None else None

    def _latest_stats(self, user_id: UUID, activity_id: UUID) -> dict[str, object]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select useful_run_count as sample_size, confidence, active_p50_seconds,
                  active_p80_seconds, wall_p50_seconds, wall_p80_seconds,
                  start_latency_p80_seconds
                from activity_stats_snapshot
                where user_id = %s and activity_id = %s
                order by computed_at desc
                limit 1
                """,
                (user_id, activity_id),
            )
            row = cursor.fetchone()
        if row is None:
            return {"sample_size": 0, "confidence": "very_low"}
        return dict(row)

    def _activity_evidence(
        self,
        user_id: UUID,
        activity_id: UUID | None,
    ) -> list[TemporalQueryEvidenceItem]:
        params: tuple[object, ...]
        if activity_id is not None:
            query = """
                select id, display_name, created_at
                from activity
                where user_id = %s and id = %s
                order by created_at desc
                limit 5
                """
            params = (user_id, activity_id)
        else:
            query = """
                select id, display_name, created_at
                from activity
                where user_id = %s
                order by created_at desc
                limit 5
                """
            params = (user_id,)
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [
            TemporalQueryEvidenceItem(
                entity_type="activity",
                entity_id=row["id"],
                summary=f"Activity: {row['display_name']}",
                occurred_at=row["created_at"],
                score=1.0,
            )
            for row in rows
        ]


def _query_answer_from_row(
    row: Mapping[str, Any],
    evidence: list[TemporalQueryEvidenceItem],
) -> TemporalQueryAnswer:
    return TemporalQueryAnswer(
        id=row["id"],
        user_id=row["user_id"],
        question=row["question"],
        answer=row["answer"],
        confidence=row["confidence"],
        sample_size=row["sample_size"],
        time_window=row["time_window"],
        computed_facts={"evidence_count": len(evidence)},
        limitations=["baseline deterministic query path"],
        evidence=evidence,
        status=row["status"],
    )
