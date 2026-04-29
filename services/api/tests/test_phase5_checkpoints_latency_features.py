from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from httpx import Response
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_worker.workflow_worker import WorkflowWorker
from test_phase4_structured_extraction import USER_ID, create_activity, mutation

HEADERS = {"X-Parallax-User-Id": USER_ID}


def test_checkpointed_run_tracks_expanded_and_skipped_phases_without_sequence_corruption() -> None:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    activity_id = create_activity(client, "Phase 5 checkpoints")

    checkpoints = client.put(
        f"/v1/activities/{activity_id}/checkpoints",
        headers=HEADERS,
        json={
            "mutation": mutation("phase5-checkpoints", 1),
            "checkpoints": [
                {"label": "Prep", "sequence_order": 1},
                {"label": "Wash", "sequence_order": 2, "optional": True},
                {"label": "Dry", "sequence_order": 3},
            ],
        },
    )
    assert checkpoints.status_code == 200

    session_id = _create_session(
        client,
        activity_id,
        mutation_id="phase5-checkpoint-session",
        client_session_id="phase5-checkpoint-session",
        mode="checkpointed",
    )
    _append_event(
        client,
        session_id,
        "checkpoint-start-prep",
        2,
        "session_started",
        "2026-04-29T12:00:00Z",
    )
    _append_event(
        client,
        session_id,
        "checkpoint-prep-start",
        3,
        "checkpoint_started",
        "2026-04-29T12:00:00Z",
        payload={"sequence_order": 1},
    )
    _append_event(
        client,
        session_id,
        "checkpoint-prep-complete",
        4,
        "checkpoint_completed",
        "2026-04-29T12:05:00Z",
        payload={"sequence_order": 1},
    )
    _append_event(
        client,
        session_id,
        "checkpoint-wash-skip",
        5,
        "checkpoint_skipped",
        "2026-04-29T12:05:00Z",
        payload={"sequence_order": 2},
    )
    _append_event(
        client,
        session_id,
        "checkpoint-dry-start",
        6,
        "checkpoint_started",
        "2026-04-29T12:05:00Z",
        payload={"sequence_order": 3},
    )
    _append_event(
        client,
        session_id,
        "checkpoint-dry-complete",
        7,
        "checkpoint_completed",
        "2026-04-29T12:20:00Z",
        payload={"sequence_order": 3},
    )
    _complete_session(client, session_id, "checkpoint-complete", 8, "2026-04-29T12:20:00Z")

    reviewed = _review_session(
        client,
        session_id,
        mutation_id="checkpoint-review",
        decision="save_partial",
        model_inclusion="active_duration_only",
    )
    assert reviewed.status_code == 200

    fetched = client.get(f"/v1/timing/sessions/{session_id}", headers=HEADERS).json()
    checkpoint_spans = [
        span
        for span in fetched["spans"]
        if span["span_type"] == "active_work" and span["checkpoint_run_id"] is not None
    ]
    assert [span["duration_seconds"] for span in checkpoint_spans] == [300, 900]
    assert fetched["active_seconds"] == 1200
    assert fetched["wall_seconds"] == 1200

    runs_by_order = {
        checkpoint.sequence_order: checkpoint
        for checkpoint in store.checkpoint_runs.values()
        if str(checkpoint.session_id) == session_id
    }
    assert runs_by_order[1].status == "completed"
    assert runs_by_order[2].status == "skipped"
    assert runs_by_order[3].status == "completed"

    refreshed_templates = client.get(
        f"/v1/activities/{activity_id}/checkpoints",
        headers=HEADERS,
    ).json()
    stats_by_label = {checkpoint["label"]: checkpoint for checkpoint in refreshed_templates}
    assert stats_by_label["Prep"]["usual_active_p50_seconds"] == 300
    assert stats_by_label["Dry"]["usual_active_p80_seconds"] == 900
    assert stats_by_label["Wash"]["usual_active_p50_seconds"] is None


def test_start_and_transition_latency_are_separate_from_active_duration() -> None:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    activity_id = create_activity(client, "Phase 5 latency")
    session_id = _create_session(
        client,
        activity_id,
        mutation_id="latency-session",
        client_session_id="latency-session",
        mode="whole_task",
        intended_start_at="2026-04-29T11:45:00Z",
    )
    _append_event(
        client,
        session_id,
        "latency-start",
        2,
        "session_started",
        "2026-04-29T12:00:00Z",
    )
    _complete_session(client, session_id, "latency-complete", 3, "2026-04-29T12:30:00Z")
    _append_event(
        client,
        session_id,
        "transition-start",
        4,
        "transition_started",
        "2026-04-29T12:30:00Z",
        payload={"reason_category": "transition"},
    )
    _append_event(
        client,
        session_id,
        "transition-complete",
        5,
        "transition_completed",
        "2026-04-29T12:40:00Z",
        payload={"reason_category": "transition"},
    )

    reviewed = _review_session(client, session_id, mutation_id="latency-review")
    assert reviewed.status_code == 200

    fetched = client.get(f"/v1/timing/sessions/{session_id}", headers=HEADERS).json()
    assert fetched["wall_seconds"] == 1800
    assert fetched["active_seconds"] == 1800
    assert fetched["start_latency_seconds"] == 900
    assert fetched["transition_seconds"] == 600

    spans_by_type = {span["span_type"]: span for span in fetched["spans"]}
    assert spans_by_type["start_latency"]["count_policy"] == "separate_start_latency"
    assert spans_by_type["start_latency"]["count_in_active_time"] is False
    assert spans_by_type["transition"]["count_policy"] == "separate_transition"
    assert spans_by_type["transition"]["count_in_active_time"] is False
    assert len(store.start_latency_observations) == 1
    assert len(store.transition_observations) == 1

    profile = client.get(f"/v1/activities/{activity_id}/profile", headers=HEADERS).json()
    assert profile["latest_stats"]["start_latency_p80_seconds"] == 900


def test_feature_vector_recompute_generates_reviewed_and_privacy_filtered_vectors() -> None:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    activity_id = create_activity(client, "Phase 5 feature vectors")
    session_id = _create_session(
        client,
        activity_id,
        mutation_id="feature-session",
        client_session_id="feature-session",
        mode="whole_task",
        intended_start_at="2026-04-29T09:45:00Z",
    )
    _append_event(
        client,
        session_id,
        "feature-start",
        2,
        "session_started",
        "2026-04-29T10:00:00Z",
    )
    _complete_session(client, session_id, "feature-complete", 3, "2026-04-29T10:20:00Z")
    _review_session(client, session_id, mutation_id="feature-review")

    queued = client.post(
        "/v1/analytics/feature-vectors/recompute",
        headers=HEADERS,
        json={
            "mutation": mutation("feature-recompute", 40),
            "activity_id": activity_id,
            "feature_families": [
                "duration_prediction",
                "start_latency",
                "place_inference",
            ],
            "reason": "phase5-test",
        },
    )
    assert queued.status_code == 202

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    workflow = store.workflow_runs[UUID(queued.json()["workflow_run_id"])]
    assert workflow.status == "succeeded"
    assert workflow.result_ref["generated_vectors"] == 3
    vectors_by_family = {
        vector.feature_family: vector for vector in store.temporal_feature_vectors.values()
    }
    assert vectors_by_family["duration_prediction"].model_eligible is True
    assert vectors_by_family["duration_prediction"].features["sample_size"] == 1
    assert vectors_by_family["start_latency"].features["start_latency_p80_seconds"] == 900
    assert vectors_by_family["place_inference"].model_eligible is False
    assert vectors_by_family["place_inference"].exclusion_reason == "context_disabled_by_policy"


def _create_session(
    client: TestClient,
    activity_id: str,
    *,
    mutation_id: str,
    client_session_id: str,
    mode: str,
    intended_start_at: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "mutation": mutation(mutation_id, 1),
        "activity_id": activity_id,
        "client_session_id": client_session_id,
        "mode": mode,
    }
    if intended_start_at is not None:
        payload["intended_start_at"] = intended_start_at
    response = client.post("/v1/timing/sessions", headers=HEADERS, json=payload)
    assert response.status_code == 201
    return str(response.json()["id"])


def _append_event(
    client: TestClient,
    session_id: str,
    mutation_id: str,
    sequence: int,
    event_type: str,
    client_time: str,
    *,
    payload: dict[str, object] | None = None,
) -> None:
    response = client.post(
        f"/v1/timing/sessions/{session_id}/events",
        headers=HEADERS,
        json={
            "mutation": mutation(mutation_id, sequence),
            "event_type": event_type,
            "client_time": client_time,
            "payload": payload or {},
        },
    )
    assert response.status_code == 201


def _complete_session(
    client: TestClient,
    session_id: str,
    mutation_id: str,
    sequence: int,
    completed_at: str,
) -> None:
    response = client.post(
        f"/v1/timing/sessions/{session_id}/complete",
        headers=HEADERS,
        json={
            "mutation": mutation(mutation_id, sequence),
            "completed_at": completed_at,
        },
    )
    assert response.status_code == 200


def _review_session(
    client: TestClient,
    session_id: str,
    *,
    mutation_id: str,
    decision: str = "save_useful_run",
    model_inclusion: str = "full",
) -> Response:
    return client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers=HEADERS,
        json={
            "mutation": mutation(mutation_id, 30),
            "decision": decision,
            "model_inclusion": model_inclusion,
            "scopes": [
                "active_duration",
                "wall_duration",
                "friction_patterns",
                "start_latency",
                "transition_latency",
            ],
        },
    )
