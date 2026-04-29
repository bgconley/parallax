from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.timing import AppendTimingEventRequest, CheckpointRun, TimingEvent, TimingSession
from .memory import InMemoryStore


def create_checkpoint_runs_for_session(
    store: InMemoryStore,
    user_id: UUID,
    session: TimingSession,
) -> None:
    if session.mode != "checkpointed":
        return
    templates = [
        checkpoint
        for checkpoint in store.checkpoint_templates.values()
        if checkpoint.user_id == user_id and checkpoint.activity_id == session.activity_id
    ]
    now = datetime.now(UTC)
    for template in sorted(templates, key=lambda item: item.sequence_order):
        run = CheckpointRun(
            id=uuid4(),
            user_id=user_id,
            session_id=session.id,
            checkpoint_template_id=template.id,
            sequence_order=template.sequence_order,
            label=template.label,
            status="planned",
            user_corrected=False,
            metadata={
                "phase_type": template.phase_type,
                "optional": template.optional,
            },
            created_at=now,
        )
        store.checkpoint_runs[run.id] = run


def checkpoint_event_payload(
    store: InMemoryStore,
    user_id: UUID,
    session: TimingSession,
    request: AppendTimingEventRequest,
) -> dict[str, object]:
    if not request.event_type.startswith("checkpoint_"):
        return request.payload
    run = _resolve_checkpoint_run(store, user_id, session, request.payload)
    if run is None:
        return request.payload
    return {**request.payload, "checkpoint_run_id": str(run.id)}


def apply_checkpoint_event(store: InMemoryStore, event: TimingEvent) -> None:
    run_id = _payload_uuid(event.payload, "checkpoint_run_id")
    if run_id is None:
        return
    run = store.checkpoint_runs.get(run_id)
    if run is None:
        return
    if event.event_type == "checkpoint_started":
        store.checkpoint_runs[run.id] = run.model_copy(
            update={"status": "running", "started_at": run.started_at or event.client_time}
        )
        return
    if event.event_type == "checkpoint_completed":
        started_at = run.started_at or event.client_time
        duration = _non_negative_seconds(started_at, event.client_time)
        store.checkpoint_runs[run.id] = run.model_copy(
            update={
                "status": "completed",
                "started_at": started_at,
                "completed_at": event.client_time,
                "active_seconds": duration,
                "wall_seconds": duration,
            }
        )
        return
    if event.event_type == "checkpoint_skipped":
        store.checkpoint_runs[run.id] = run.model_copy(
            update={
                "status": "skipped",
                "completed_at": event.client_time,
                "active_seconds": 0,
                "wall_seconds": 0,
            }
        )


def _resolve_checkpoint_run(
    store: InMemoryStore,
    user_id: UUID,
    session: TimingSession,
    payload: dict[str, object],
) -> CheckpointRun | None:
    run_id = _payload_uuid(payload, "checkpoint_run_id")
    template_id = _payload_uuid(payload, "checkpoint_template_id")
    sequence_order = _payload_int(payload, "sequence_order")
    for run in store.checkpoint_runs.values():
        if run.user_id != user_id or run.session_id != session.id:
            continue
        if run_id is not None and run.id == run_id:
            return run
        if template_id is not None and run.checkpoint_template_id == template_id:
            return run
        if sequence_order is not None and run.sequence_order == sequence_order:
            return run
    if sequence_order is None:
        return None
    return _create_ad_hoc_checkpoint_run(
        store,
        user_id,
        session,
        sequence_order,
        template_id,
        payload,
    )


def _create_ad_hoc_checkpoint_run(
    store: InMemoryStore,
    user_id: UUID,
    session: TimingSession,
    sequence_order: int,
    template_id: UUID | None,
    payload: dict[str, object],
) -> CheckpointRun:
    run = CheckpointRun(
        id=uuid4(),
        user_id=user_id,
        session_id=session.id,
        checkpoint_template_id=template_id,
        sequence_order=sequence_order,
        label=str(payload.get("label") or f"Checkpoint {sequence_order}"),
        status="planned",
        user_corrected=False,
        metadata={"ad_hoc": True},
        created_at=datetime.now(UTC),
    )
    store.checkpoint_runs[run.id] = run
    return run


def _payload_uuid(payload: dict[str, object], key: str) -> UUID | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _payload_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except ValueError:
        return None
    return parsed if parsed >= 1 else None


def _non_negative_seconds(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds()))
