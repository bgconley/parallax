from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..domain.temporal_query import (
    base_query_limitations,
    build_temporal_query_plan,
    confidence_for_sample_size,
    deterministic_delay_answer,
    deterministic_duration_answer,
)
from ..schemas.temporal import (
    TemporalQueryAnswer,
    TemporalQueryEvidenceItem,
    TemporalQueryRequest,
)

_ACTIVE_DURATION_INCLUSIONS = ("full", "active_duration_only")
_WALL_DURATION_INCLUSIONS = ("full", "wall_envelope_only")


class PostgresTemporalQueryRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create_query_answer(
        self,
        user_id: UUID,
        request: TemporalQueryRequest,
    ) -> TemporalQueryAnswer:
        activity_name = self._activity_name(user_id, request.activity_id)
        plan = build_temporal_query_plan(
            question=request.question,
            activity_id=request.activity_id,
            activity_name=activity_name,
            time_window=request.time_window,
        )
        raw_quotes_allowed = self._raw_quotes_allowed(user_id)
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
        limitations = base_query_limitations(
            sample_size=sample_size,
            include_raw_quotes=request.include_raw_quotes,
            raw_quotes_allowed=raw_quotes_allowed,
        )

        with self._connection.cursor() as cursor:
            bundle_id = self._create_evidence_bundle(
                cursor,
                user_id,
                request.question,
                facts,
                limitations,
            )
            self._create_evidence_items(cursor, user_id, bundle_id, evidence)
            cursor.execute(
                """
                insert into temporal_query_answer (
                  user_id, question, normalized_intent, answer, confidence,
                  sample_size, time_window, evidence_bundle_id, status, completed_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'complete', now())
                returning id, user_id, question, answer, confidence, sample_size,
                  time_window, evidence_bundle_id, status
                """,
                (
                    user_id,
                    request.question,
                    plan.intent,
                    answer_text,
                    confidence,
                    sample_size,
                    plan.window.label,
                    bundle_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("temporal query answer insert returned no row")
            answer = _query_answer_from_row(row, facts, limitations, evidence)
            self._upsert_retrieval_document(cursor, answer)
            self._emit_query_events(cursor, answer, request.activity_id)
        return answer

    def get_query_answer(self, user_id: UUID, answer_id: UUID) -> TemporalQueryAnswer | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, question, answer, confidence, sample_size,
                  time_window, evidence_bundle_id, status
                from temporal_query_answer
                where user_id = %s and id = %s
                """,
                (user_id, answer_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            facts, limitations, evidence = self._load_evidence_bundle(
                cursor,
                user_id,
                row["evidence_bundle_id"],
            )
        return _query_answer_from_row(row, facts, limitations, evidence)

    def _duration_facts(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> tuple[dict[str, object], list[TemporalQueryEvidenceItem]]:
        params = (user_id, activity_id, activity_id, window_days)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select (count(*) filter (
                    where model_inclusion in ('full', 'active_duration_only')
                      and active_seconds is not null
                  ))::integer as active_sample_size,
                  percentile_cont(0.5) within group (order by active_seconds)
                    filter (
                      where model_inclusion in ('full', 'active_duration_only')
                        and active_seconds is not null
                    ) as active_p50_seconds,
                  percentile_cont(0.8) within group (order by active_seconds)
                    filter (
                      where model_inclusion in ('full', 'active_duration_only')
                        and active_seconds is not null
                    ) as active_p80_seconds,
                  (count(*) filter (
                    where model_inclusion in ('full', 'wall_envelope_only')
                      and wall_seconds is not null
                  ))::integer as wall_sample_size,
                  percentile_cont(0.5) within group (order by wall_seconds)
                    filter (
                      where model_inclusion in ('full', 'wall_envelope_only')
                        and wall_seconds is not null
                    ) as wall_p50_seconds,
                  percentile_cont(0.8) within group (order by wall_seconds)
                    filter (
                      where model_inclusion in ('full', 'wall_envelope_only')
                        and wall_seconds is not null
                    ) as wall_p80_seconds
                from timing_session
                where user_id = %s
                  and (%s::uuid is null or activity_id = %s)
                  and status = 'reviewed'
                  and model_inclusion in (
                    'full',
                    'active_duration_only',
                    'wall_envelope_only'
                  )
                  and coalesce(completed_at, updated_at, created_at)
                    >= now() - make_interval(days => %s)
                """,
                params,
            )
            row = cursor.fetchone()
            evidence = self._duration_evidence(cursor, user_id, activity_id, window_days)

        active_sample_size = int(row["active_sample_size"]) if row is not None else 0
        wall_sample_size = int(row["wall_sample_size"]) if row is not None else 0
        facts: dict[str, object] = {
            "sample_size": max(active_sample_size, wall_sample_size),
            "active_sample_size": active_sample_size,
            "wall_sample_size": wall_sample_size,
            "active_p50_seconds": _int_or_none(row["active_p50_seconds"] if row else None),
            "active_p80_seconds": _int_or_none(row["active_p80_seconds"] if row else None),
            "wall_p50_seconds": _int_or_none(row["wall_p50_seconds"] if row else None),
            "wall_p80_seconds": _int_or_none(row["wall_p80_seconds"] if row else None),
        }
        return facts, evidence

    def _delay_facts(
        self,
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> tuple[dict[str, object], list[TemporalQueryEvidenceItem]]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*)::integer as sample_size
                from timing_session
                where user_id = %s
                  and (%s::uuid is null or activity_id = %s)
                  and status = 'reviewed'
                  and model_inclusion in (
                    'full',
                    'friction_patterns_only',
                    'query_evidence_only'
                  )
                  and coalesce(completed_at, updated_at, created_at)
                    >= now() - make_interval(days => %s)
                """,
                (user_id, activity_id, activity_id, window_days),
            )
            sample_row = cursor.fetchone()
            cursor.execute(
                """
                select tes.friction_category,
                  count(*)::integer as event_count,
                  coalesce(sum(tes.duration_seconds), 0)::integer as total_seconds,
                  percentile_cont(0.8) within group (order by tes.duration_seconds)
                    filter (where tes.duration_seconds is not null) as p80_seconds
                from timing_event_span tes
                join timing_session ts on ts.id = tes.session_id
                where tes.user_id = %s
                  and (%s::uuid is null or ts.activity_id = %s)
                  and ts.status = 'reviewed'
                  and ts.model_inclusion in (
                    'full',
                    'friction_patterns_only',
                    'query_evidence_only'
                  )
                  and tes.friction_category not in ('none', 'unknown')
                  and coalesce(ts.completed_at, ts.updated_at, ts.created_at)
                    >= now() - make_interval(days => %s)
                group by tes.friction_category
                order by event_count desc, total_seconds desc, tes.friction_category
                """,
                (user_id, activity_id, activity_id, window_days),
            )
            category_rows = cursor.fetchall()
            evidence = self._delay_evidence(cursor, user_id, activity_id, window_days)

        categories = [
            {
                "friction_category": row["friction_category"],
                "event_count": int(row["event_count"]),
                "total_seconds": int(row["total_seconds"]),
                "p80_seconds": _int_or_none(row["p80_seconds"]),
            }
            for row in category_rows
        ]
        return {
            "sample_size": int(sample_row["sample_size"]) if sample_row is not None else 0,
            "friction_categories": categories,
        }, evidence

    def _duration_evidence(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> list[TemporalQueryEvidenceItem]:
        cursor.execute(
            """
            select ts.id, a.display_name, ts.model_inclusion,
              ts.active_seconds, ts.wall_seconds,
              coalesce(ts.completed_at, ts.updated_at, ts.created_at) as occurred_at
            from timing_session ts
            join activity a on a.id = ts.activity_id
            where ts.user_id = %s
              and (%s::uuid is null or ts.activity_id = %s)
              and ts.status = 'reviewed'
              and ts.model_inclusion in (
                'full',
                'active_duration_only',
                'wall_envelope_only'
              )
              and coalesce(ts.completed_at, ts.updated_at, ts.created_at)
                >= now() - make_interval(days => %s)
            order by coalesce(ts.completed_at, ts.updated_at, ts.created_at) desc, ts.id
            limit 5
            """,
            (user_id, activity_id, activity_id, window_days),
        )
        return [
            TemporalQueryEvidenceItem(
                entity_type="timing_session",
                entity_id=row["id"],
                summary=_duration_evidence_summary(row),
                occurred_at=row["occurred_at"],
                score=1.0,
            )
            for row in cursor.fetchall()
        ]

    def _delay_evidence(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        activity_id: UUID | None,
        window_days: int,
    ) -> list[TemporalQueryEvidenceItem]:
        cursor.execute(
            """
            select tes.id, a.display_name, tes.friction_category, tes.duration_seconds,
              tes.count_policy, tes.started_at as occurred_at
            from timing_event_span tes
            join timing_session ts on ts.id = tes.session_id
            join activity a on a.id = ts.activity_id
            where tes.user_id = %s
              and (%s::uuid is null or ts.activity_id = %s)
              and ts.status = 'reviewed'
              and ts.model_inclusion in (
                'full',
                'friction_patterns_only',
                'query_evidence_only'
              )
              and tes.friction_category not in ('none', 'unknown')
              and coalesce(ts.completed_at, ts.updated_at, ts.created_at)
                >= now() - make_interval(days => %s)
            order by tes.started_at desc, tes.id
            limit 5
            """,
            (user_id, activity_id, activity_id, window_days),
        )
        return [
            TemporalQueryEvidenceItem(
                entity_type="timing_event_span",
                entity_id=row["id"],
                summary=(
                    f"{row['friction_category']} friction in {row['display_name']}: "
                    f"{row['duration_seconds']}s, policy={row['count_policy']}."
                ),
                occurred_at=row["occurred_at"],
                score=1.0,
            )
            for row in cursor.fetchall()
        ]

    def _create_evidence_bundle(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        question: str,
        facts: dict[str, object],
        limitations: list[str],
    ) -> UUID:
        cursor.execute(
            """
            insert into evidence_bundle (
              user_id, purpose, query_text, computed_facts, limitations, privacy_class
            )
            values (%s, 'temporal_query_answer', %s, %s, %s, 'normal')
            returning id
            """,
            (user_id, question, Jsonb(facts), Jsonb(limitations)),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("evidence bundle insert returned no row")
        return row["id"]

    def _create_evidence_items(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        bundle_id: UUID,
        evidence: list[TemporalQueryEvidenceItem],
    ) -> None:
        for item in evidence:
            cursor.execute(
                """
                insert into evidence_item (
                  bundle_id, user_id, entity_type, entity_id, summary,
                  occurred_at, score, privacy_class, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'normal', %s)
                """,
                (
                    bundle_id,
                    user_id,
                    item.entity_type,
                    item.entity_id,
                    item.summary,
                    item.occurred_at,
                    item.score,
                    Jsonb({}),
                ),
            )

    def _load_evidence_bundle(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        bundle_id: UUID | None,
    ) -> tuple[dict[str, object], list[str], list[TemporalQueryEvidenceItem]]:
        if bundle_id is None:
            return {}, [], []
        cursor.execute(
            """
            select computed_facts, limitations
            from evidence_bundle
            where user_id = %s and id = %s
            """,
            (user_id, bundle_id),
        )
        bundle = cursor.fetchone()
        if bundle is None:
            return {}, [], []
        cursor.execute(
            """
            select entity_type, entity_id, summary, occurred_at, score
            from evidence_item
            where user_id = %s and bundle_id = %s
            order by score desc nulls last, occurred_at desc nulls last, id
            """,
            (user_id, bundle_id),
        )
        evidence = [
            TemporalQueryEvidenceItem(
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                summary=row["summary"],
                occurred_at=row["occurred_at"],
                score=float(row["score"]) if row["score"] is not None else None,
            )
            for row in cursor.fetchall()
        ]
        return dict(bundle["computed_facts"]), list(bundle["limitations"]), evidence

    def _upsert_retrieval_document(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        answer: TemporalQueryAnswer,
    ) -> None:
        text_content = _retrieval_text(answer)
        cursor.execute(
            """
            insert into retrieval_document (
              user_id, entity_type, entity_id, document_kind, text_content,
              privacy_class, source_hash, metadata
            )
            values (%s, 'temporal_query_answer', %s, 'temporal_query_answer',
              %s, 'normal', %s, %s)
            on conflict (user_id, entity_type, entity_id, document_kind)
            do update set
              text_content = excluded.text_content,
              source_hash = excluded.source_hash,
              metadata = excluded.metadata,
              updated_at = now()
            """,
            (
                answer.user_id,
                answer.id,
                text_content,
                hashlib.sha256(text_content.encode("utf-8")).hexdigest(),
                Jsonb({"status": answer.status, "confidence": answer.confidence}),
            ),
        )

    def _emit_query_events(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        answer: TemporalQueryAnswer,
        activity_id: UUID | None,
    ) -> None:
        requested_payload = {
            "answer_id": str(answer.id),
            "question": answer.question,
            "activity_id": str(activity_id) if activity_id else None,
        }
        answered_payload = answer.model_dump(mode="json")
        for event_name, payload in (
            ("temporal_query.requested", requested_payload),
            ("temporal_query.answered", answered_payload),
        ):
            cursor.execute(
                """
                insert into outbox_event (
                  user_id, event_name, aggregate_type, aggregate_id, payload
                )
                values (%s, %s, 'temporal_query_answer', %s, %s)
                """,
                (answer.user_id, event_name, answer.id, Jsonb(payload)),
            )

    def _activity_name(self, user_id: UUID, activity_id: UUID | None) -> str | None:
        if activity_id is None:
            return None
        with self._connection.cursor() as cursor:
            cursor.execute(
                "select display_name from activity where user_id = %s and id = %s",
                (user_id, activity_id),
            )
            row = cursor.fetchone()
        return str(row["display_name"]) if row is not None else None

    def _raw_quotes_allowed(self, user_id: UUID) -> bool:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select allow_raw_notes_in_query_answers
                from privacy_settings
                where user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        return bool(row["allow_raw_notes_in_query_answers"]) if row is not None else False


def _query_answer_from_row(
    row: Mapping[str, Any],
    facts: dict[str, object],
    limitations: list[str],
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
        computed_facts=facts,
        limitations=limitations,
        evidence=evidence,
        status=row["status"],
    )


def _retrieval_text(answer: TemporalQueryAnswer) -> str:
    payload = {
        "question": answer.question,
        "answer": answer.answer,
        "computed_facts": answer.computed_facts,
        "limitations": answer.limitations,
        "evidence": [item.model_dump(mode="json") for item in answer.evidence],
    }
    return json.dumps(payload, sort_keys=True)


def _duration_evidence_summary(row: Mapping[str, Any]) -> str:
    model_inclusion = row["model_inclusion"]
    metrics: list[str] = []
    if model_inclusion in _ACTIVE_DURATION_INCLUSIONS:
        metrics.append(f"active={row['active_seconds']}s")
    if model_inclusion in _WALL_DURATION_INCLUSIONS:
        metrics.append(f"wall={row['wall_seconds']}s")
    return f"Reviewed run for {row['display_name']}: {', '.join(metrics)}."


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return 0
