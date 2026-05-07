from __future__ import annotations

from typing import overload
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..domain.latency_observations import (
    derive_start_latency_observation,
    derive_transition_observations,
)
from ..domain.review_decisions import is_discard_decision, is_model_inclusion_allowed
from ..domain.timing_spans import derive_timing_spans, summarize_timing_spans
from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.extraction import ExtractedContextEvent
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingEventSpanRequest,
    CreateTimingSessionRequest,
    ModelUpdateDecision,
    ReviewTimingSessionRequest,
    TimingEvent,
    TimingEventSpan,
    TimingSession,
)
from .mutations import MutationReplayService


class TimingService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        with self._uow_factory() as uow:
            return create_session_in_uow(uow, user_id, request)

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession:
        with self._uow_factory() as uow:
            session = uow.timing.get_session(user_id, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="timing session not found")
        return session

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        with self._uow_factory() as uow:
            return append_event_in_uow(uow, user_id, session_id, request)

    def create_or_correct_span(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateTimingEventSpanRequest,
    ) -> TimingEventSpan:
        with self._uow_factory() as uow:
            return create_or_correct_span_in_uow(uow, user_id, session_id, request)

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession:
        with self._uow_factory() as uow:
            return complete_session_in_uow(uow, user_id, session_id, request)

    def review_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
    ) -> ModelUpdateDecision:
        return self._save_review_decision(user_id, session_id, request, discard_endpoint=False)

    def discard_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
    ) -> ModelUpdateDecision:
        return self._save_review_decision(user_id, session_id, request, discard_endpoint=True)

    def _save_review_decision(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
        *,
        discard_endpoint: bool,
    ) -> ModelUpdateDecision:
        if not is_model_inclusion_allowed(request):
            raise HTTPException(
                status_code=400,
                detail="model_inclusion is not valid for review decision",
            )
        if discard_endpoint and not is_discard_decision(request.decision):
            raise HTTPException(
                status_code=400,
                detail="discard endpoint requires discard decision",
            )
        if not discard_endpoint and is_discard_decision(request.decision):
            raise HTTPException(status_code=400, detail="discard decisions use discard endpoint")

        with self._uow_factory() as uow:
            return save_review_decision_in_uow(
                uow,
                user_id,
                session_id,
                request,
                discard_endpoint=discard_endpoint,
            )


def create_session_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: CreateTimingSessionRequest,
) -> TimingSession:
    if uow.activities.get(user_id, request.activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingSession]:
        session = uow.timing.create_session(user_id, request)
        return session.id, session

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_timing_session",
        entity_type="timing_session",
        result_type=TimingSession,
        apply=apply,
    )


def append_event_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: AppendTimingEventRequest,
) -> TimingEvent:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    resolved_request = _with_resolved_context_snapshot(uow, user_id, request)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingEvent]:
        event = uow.timing.append_event(user_id, session_id, resolved_request)
        _materialize_client_extracted_event_if_needed(uow, user_id, event)
        return event.id, event

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=resolved_request.mutation,
        mutation_type="append_timing_event",
        entity_type="timing_event",
        result_type=TimingEvent,
        apply=apply,
    )


def _materialize_client_extracted_event_if_needed(
    uow: UnitOfWork,
    user_id: UUID,
    event: TimingEvent,
) -> None:
    if event.event_type != "extracted_event_created":
        return

    annotation_id = _payload_uuid(event.payload, "annotation_id")
    if annotation_id is None:
        return
    annotation = uow.contexts.get_annotation(user_id, annotation_id)
    if annotation is None or annotation.session_id != event.session_id:
        raise HTTPException(status_code=400, detail="extracted event annotation scope mismatch")

    count_policy = str(event.payload.get("count_policy") or "review_required")
    extracted = ExtractedContextEvent(
        id=uuid4(),
        user_id=user_id,
        annotation_id=annotation.id,
        session_id=event.session_id,
        checkpoint_run_id=annotation.checkpoint_run_id,
        span_type=str(event.payload.get("span_type") or "other"),
        friction_category=str(event.payload.get("friction_category") or "unknown"),
        friction_subtype=_payload_string(event.payload, "friction_subtype"),
        resource_name=_payload_string(event.payload, "resource_name"),
        location_from=_payload_string(event.payload, "location_from"),
        location_to=_payload_string(event.payload, "location_to"),
        duration_seconds=_payload_int(event.payload, "duration_seconds"),
        count_policy=count_policy,
        count_in_wall_time=_count_in_wall_time(count_policy),
        count_in_active_time=_count_in_active_time(count_policy),
        model_update_scopes=_payload_scopes(event.payload),
        suggested_preflight_text=_payload_string(event.payload, "suggested_preflight_text"),
        confidence=_payload_float(event.payload, "confidence") or 0.82,
        confirmation_state=_confirmation_state(event.payload),
        sensitive_data_detected=False,
        model_invocation_id=None,
        source_json={
            "source": "client_confirmed_extracted_event",
            "source_timing_event_id": str(event.id),
            "payload": event.payload,
        },
        user_correction_json={},
    )
    created = uow.contexts.create_extracted_event(extracted)
    if created.confirmation_state == "confirmed":
        uow.timing.upsert_extracted_event_span(user_id, created, user_corrected=False)
        if created.suggested_preflight_text or created.resource_name:
            session = uow.timing.get_session(user_id, created.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="timing session not found")
            uow.contexts.create_preflight_check(user_id, session.activity_id, created)
            uow.profiles.recompute_activity_stats(user_id, session.activity_id)


def _payload_uuid(payload: dict[str, object], key: str) -> UUID | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {key}") from exc


def _payload_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _payload_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {key}") from exc


def _payload_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {key}") from exc


def _payload_scopes(payload: dict[str, object]) -> list[str]:
    raw = payload.get("model_update_scopes")
    if raw is None:
        if payload.get("friction_category") == "resource":
            return ["friction_patterns", "preflight_suggestions"]
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return [scope.strip() for scope in str(raw).split(",") if scope.strip()]


def _confirmation_state(payload: dict[str, object]) -> str:
    value = str(payload.get("confirmation_state") or "confirmed")
    if value == "user_confirmed":
        return "confirmed"
    if value in {"confirmed", "ignored", "needs_confirmation", "deferred_to_review"}:
        return value
    return "confirmed"


def _count_in_wall_time(count_policy: str) -> bool:
    return count_policy in {
        "wall_and_active",
        "wall_only",
        "separate_start_latency",
        "separate_transition",
        "review_required",
    }


def _count_in_active_time(count_policy: str) -> bool:
    return count_policy in {"wall_and_active", "active_only"}


def create_or_correct_span_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: CreateTimingEventSpanRequest,
) -> TimingEventSpan:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    if request.span.user_id != user_id or request.span.session_id != session_id:
        raise HTTPException(status_code=400, detail="span scope does not match request")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingEventSpan]:
        span = uow.timing.create_or_correct_span(user_id, session_id, request.span)
        return span.id, span

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_timing_event_span",
        entity_type="timing_event_span",
        result_type=TimingEventSpan,
        apply=apply,
    )


def complete_session_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: CompleteTimingSessionRequest,
) -> TimingSession:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    resolved_request = _with_resolved_context_snapshot(uow, user_id, request)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingSession]:
        session = uow.timing.complete_session(user_id, session_id, resolved_request)
        span_drafts = derive_timing_spans(session, session.events)
        totals = summarize_timing_spans(session, span_drafts)
        uow.timing.replace_derived_spans_and_totals(
            user_id,
            session_id,
            span_drafts,
            totals,
        )
        finalized_session = uow.timing.get_session(user_id, session_id) or session
        return finalized_session.id, finalized_session

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=resolved_request.mutation,
        mutation_type="complete_timing_session",
        entity_type="timing_session",
        result_type=TimingSession,
        apply=apply,
    )


def save_review_decision_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: ReviewTimingSessionRequest,
    *,
    discard_endpoint: bool,
) -> ModelUpdateDecision:
    if not is_model_inclusion_allowed(request):
        raise HTTPException(
            status_code=400,
            detail="model_inclusion is not valid for review decision",
        )
    if discard_endpoint and not is_discard_decision(request.decision):
        raise HTTPException(
            status_code=400,
            detail="discard endpoint requires discard decision",
        )
    if not discard_endpoint and is_discard_decision(request.decision):
        raise HTTPException(status_code=400, detail="discard decisions use discard endpoint")

    session = uow.timing.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    if session.completed_at is None:
        raise HTTPException(status_code=400, detail="timing session is not complete")

    span_drafts = derive_timing_spans(session, session.events)
    totals = summarize_timing_spans(session, span_drafts)
    start_latency = derive_start_latency_observation(session)
    transitions = derive_transition_observations(session, span_drafts)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ModelUpdateDecision]:
        decision = uow.timing.review_session(
            user_id,
            session_id,
            request,
            span_drafts,
            totals,
        )
        uow.timing.replace_latency_observations(
            user_id,
            session,
            start_latency,
            transitions,
        )
        uow.profiles.recompute_activity_stats(user_id, session.activity_id)
        uow.profiles.recompute_checkpoint_stats(user_id, session.activity_id)
        return decision.id, decision

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="discard_timing_session" if discard_endpoint else "review_timing_session",
        entity_type="model_update_decision",
        result_type=ModelUpdateDecision,
        apply=apply,
    )


@overload
def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: AppendTimingEventRequest,
) -> AppendTimingEventRequest: ...


@overload
def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: CompleteTimingSessionRequest,
) -> CompleteTimingSessionRequest: ...


def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: AppendTimingEventRequest | CompleteTimingSessionRequest,
) -> AppendTimingEventRequest | CompleteTimingSessionRequest:
    if (
        request.capture_context_snapshot_id is not None
        or request.capture_context_snapshot_ref is None
    ):
        return request
    snapshot_id = uow.contexts.snapshot_id_for_reference(
        user_id,
        request.capture_context_snapshot_ref,
    )
    if snapshot_id is None:
        return request
    return request.model_copy(update={"capture_context_snapshot_id": snapshot_id})
