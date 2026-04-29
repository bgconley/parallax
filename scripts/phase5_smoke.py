from __future__ import annotations

import argparse
import json
import time
from uuid import UUID, uuid4

import httpx
import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 5 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase5-smoke-{user_id.hex[:8]}"
    api_url = args.api_url.rstrip("/")
    headers = {"X-Parallax-User-Id": str(user_id)}
    summary: dict[str, object] = {"user_id": str(user_id), "device_id": device_id}

    try:
        with httpx.Client(base_url=api_url, headers=headers, timeout=10) as client:
            _wait_for_health(client)
            activity = _expect(
                client.post(
                    "/v1/activities",
                    json={
                        "mutation": _mutation(device_id, "activity", 1),
                        "display_name": f"Phase 5 smoke {user_id.hex[:8]}",
                    },
                ),
                201,
            )
            activity_id = _string_value(activity, "id")
            checkpoints = _expect(
                client.put(
                    f"/v1/activities/{activity_id}/checkpoints",
                    json={
                        "mutation": _mutation(device_id, "checkpoints", 2),
                        "checkpoints": [
                            {"label": "Prep", "sequence_order": 1},
                            {"label": "Wash", "sequence_order": 2, "optional": True},
                            {"label": "Dry", "sequence_order": 3},
                        ],
                    },
                ),
                200,
            )
            if len(_object_list(checkpoints)) != 3:
                raise AssertionError(f"checkpoint template write failed: {checkpoints}")

            session = _expect(
                client.post(
                    "/v1/timing/sessions",
                    json={
                        "mutation": _mutation(device_id, "session", 3),
                        "activity_id": activity_id,
                        "client_session_id": f"phase5-{uuid4().hex}",
                        "mode": "checkpointed",
                        "intended_start_at": "2026-04-29T11:55:00Z",
                    },
                ),
                201,
            )
            session_id = _string_value(session, "id")
            _append_event(client, session_id, device_id, "session-started", 4, "session_started")
            _append_checkpoint(
                client,
                session_id,
                device_id,
                "prep-start",
                5,
                "checkpoint_started",
                "2026-04-29T12:00:00Z",
                1,
            )
            _append_checkpoint(
                client,
                session_id,
                device_id,
                "prep-complete",
                6,
                "checkpoint_completed",
                "2026-04-29T12:05:00Z",
                1,
            )
            _append_checkpoint(
                client,
                session_id,
                device_id,
                "wash-skip",
                7,
                "checkpoint_skipped",
                "2026-04-29T12:05:00Z",
                2,
            )
            _append_checkpoint(
                client,
                session_id,
                device_id,
                "dry-start",
                8,
                "checkpoint_started",
                "2026-04-29T12:05:00Z",
                3,
            )
            _append_checkpoint(
                client,
                session_id,
                device_id,
                "dry-complete",
                9,
                "checkpoint_completed",
                "2026-04-29T12:20:00Z",
                3,
            )
            _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/complete",
                    json={
                        "mutation": _mutation(device_id, "complete", 10),
                        "completed_at": "2026-04-29T12:20:00Z",
                    },
                ),
                200,
            )
            _append_event(
                client,
                session_id,
                device_id,
                "transition-start",
                11,
                "transition_started",
                "2026-04-29T12:20:00Z",
            )
            _append_event(
                client,
                session_id,
                device_id,
                "transition-complete",
                12,
                "transition_completed",
                "2026-04-29T12:25:00Z",
            )
            _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/review",
                    json={
                        "mutation": _mutation(device_id, "review", 13),
                        "decision": "save_partial",
                        "model_inclusion": "active_duration_only",
                        "scopes": [
                            "active_duration",
                            "wall_duration",
                            "start_latency",
                            "transition_latency",
                        ],
                    },
                ),
                200,
            )

            reviewed = _object_value(_expect(client.get(f"/v1/timing/sessions/{session_id}"), 200))
            _assert_reviewed_session(reviewed)
            refreshed_checkpoints = _object_list(
                _expect(client.get(f"/v1/activities/{activity_id}/checkpoints"), 200)
            )
            _assert_checkpoint_stats(refreshed_checkpoints)

            feature_job = _expect(
                client.post(
                    "/v1/analytics/feature-vectors/recompute",
                    json={
                        "mutation": _mutation(device_id, "features", 14),
                        "activity_id": activity_id,
                        "feature_families": [
                            "duration_prediction",
                            "start_latency",
                            "place_inference",
                        ],
                        "reason": "phase5-smoke",
                    },
                ),
                202,
            )
            workflow_id = UUID(_string_value(feature_job, "workflow_run_id"))

        counts = _wait_for_phase5_counts(args.database_url, user_id, workflow_id)
        feature_vectors = _fetch_feature_vectors(args.database_url, user_id)
        _assert_feature_vectors(feature_vectors)
        summary.update(
            {
                "activity_id": activity_id,
                "session_id": session_id,
                "workflow_run_id": str(workflow_id),
                **counts,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase5", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _append_event(
    client: httpx.Client,
    session_id: str,
    device_id: str,
    mutation_id: str,
    sequence: int,
    event_type: str,
    client_time: str = "2026-04-29T12:00:00Z",
) -> None:
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/events",
            json={
                "mutation": _mutation(device_id, mutation_id, sequence),
                "event_type": event_type,
                "client_time": client_time,
            },
        ),
        201,
    )


def _append_checkpoint(
    client: httpx.Client,
    session_id: str,
    device_id: str,
    mutation_id: str,
    sequence: int,
    event_type: str,
    client_time: str,
    sequence_order: int,
) -> None:
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/events",
            json={
                "mutation": _mutation(device_id, mutation_id, sequence),
                "event_type": event_type,
                "client_time": client_time,
                "payload": {"sequence_order": sequence_order},
            },
        ),
        201,
    )


def _assert_reviewed_session(session: dict[str, object]) -> None:
    if session["active_seconds"] != 1200 or session["wall_seconds"] != 1200:
        raise AssertionError(f"checkpoint timing totals are wrong: {session}")
    if session["start_latency_seconds"] != 300 or session["transition_seconds"] != 300:
        raise AssertionError(f"latency totals are not separated: {session}")
    checkpoint_spans = [
        span
        for span in _list_value(session, "spans")
        if span["span_type"] == "active_work" and span["checkpoint_run_id"] is not None
    ]
    durations = [span["duration_seconds"] for span in checkpoint_spans]
    if durations != [300, 900]:
        raise AssertionError(f"checkpoint spans are wrong: {session}")


def _assert_checkpoint_stats(checkpoints: list[dict[str, object]]) -> None:
    by_label = {checkpoint["label"]: checkpoint for checkpoint in checkpoints}
    if by_label["Prep"]["usual_active_p50_seconds"] != 300:
        raise AssertionError(f"Prep stats were not recomputed: {checkpoints}")
    if by_label["Dry"]["usual_active_p80_seconds"] != 900:
        raise AssertionError(f"Dry stats were not recomputed: {checkpoints}")
    if by_label["Wash"]["usual_active_p50_seconds"] is not None:
        raise AssertionError(f"Skipped checkpoint corrupted stats: {checkpoints}")


def _assert_feature_vectors(vectors: dict[str, dict[str, object]]) -> None:
    expected = {"duration_prediction", "start_latency", "place_inference"}
    if set(vectors) != expected:
        raise AssertionError(f"unexpected feature vector families: {vectors}")
    if vectors["duration_prediction"]["model_eligible"] is not True:
        raise AssertionError(f"duration vector is not eligible: {vectors}")
    start_latency_features = vectors["start_latency"]["features"]
    if (
        not isinstance(start_latency_features, dict)
        or start_latency_features.get("start_latency_p80_seconds") != 300
    ):
        raise AssertionError(f"start-latency vector is wrong: {vectors}")
    if vectors["place_inference"]["model_eligible"] is not False:
        raise AssertionError(f"place vector should be privacy-disabled: {vectors}")
    if vectors["place_inference"]["exclusion_reason"] != "context_disabled_by_policy":
        raise AssertionError(f"place vector exclusion is wrong: {vectors}")


def _wait_for_health(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = client.get("/v1/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"API did not become healthy: {last_error}")


def _wait_for_phase5_counts(
    database_url: str,
    user_id: UUID,
    workflow_id: UUID,
) -> dict[str, int]:
    deadline = time.monotonic() + 30
    latest: dict[str, int] = {}
    while time.monotonic() < deadline:
        latest = _phase5_counts(database_url, user_id, workflow_id)
        if (
            latest["checkpoint_runs"] == 3
            and latest["start_latency_observations"] == 1
            and latest["transition_observations"] == 1
            and latest["feature_vectors"] == 3
            and latest["succeeded_workflows"] == 1
        ):
            return latest
        time.sleep(1)
    raise AssertionError(f"timed out waiting for Phase 5 derived data: {latest}")


def _phase5_counts(database_url: str, user_id: UUID, workflow_id: UUID) -> dict[str, int]:
    queries: dict[str, tuple[str, tuple[object, ...]]] = {
        "checkpoint_runs": ("select count(*) from checkpoint_run where user_id = %s", (user_id,)),
        "start_latency_observations": (
            "select count(*) from start_latency_observation where user_id = %s",
            (user_id,),
        ),
        "transition_observations": (
            "select count(*) from transition_observation where user_id = %s",
            (user_id,),
        ),
        "feature_vectors": (
            "select count(*) from temporal_feature_vector where user_id = %s",
            (user_id,),
        ),
        "succeeded_workflows": (
            "select count(*) from workflow_run where user_id = %s and id = %s "
            "and status = 'succeeded'",
            (user_id, workflow_id),
        ),
    }
    counts: dict[str, int] = {}
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for key, (sql, params) in queries.items():
                cursor.execute(sql, params)
                row = cursor.fetchone()
                counts[key] = int(row[0]) if row is not None else 0
    return counts


def _fetch_feature_vectors(database_url: str, user_id: UUID) -> dict[str, dict[str, object]]:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select feature_family, features, model_eligible, exclusion_reason
                from temporal_feature_vector
                where user_id = %s
                order by feature_family
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
    return {
        str(row[0]): {
            "features": row[1],
            "model_eligible": row[2],
            "exclusion_reason": row[3],
        }
        for row in rows
    }


def _expect(response: httpx.Response, status_code: int) -> dict[str, object] | list[object]:
    if response.status_code != status_code:
        raise AssertionError(
            f"expected {status_code} from {response.request.method} {response.request.url}, "
            f"got {response.status_code}: {response.text}"
        )
    body = response.json()
    if not isinstance(body, dict | list):
        raise AssertionError(f"expected object/list response, got {body!r}")
    return body


def _object_list(body: dict[str, object] | list[object]) -> list[dict[str, object]]:
    if not isinstance(body, list):
        raise AssertionError(f"expected list response, got {body}")
    items: list[dict[str, object]] = []
    for item in body:
        if not isinstance(item, dict):
            raise AssertionError(f"expected object entries, got {body}")
        items.append(item)
    return items


def _object_value(body: dict[str, object] | list[object]) -> dict[str, object]:
    if not isinstance(body, dict):
        raise AssertionError(f"expected object response, got {body}")
    return body


def _list_value(body: dict[str, object], key: str) -> list[dict[str, object]]:
    value = body.get(key)
    if not isinstance(value, list):
        raise AssertionError(f"expected list {key}, got {body}")
    items: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise AssertionError(f"expected object entries in {key}, got {body}")
        items.append(item)
    return items


def _string_value(body: dict[str, object] | list[object], key: str) -> str:
    if not isinstance(body, dict):
        raise AssertionError(f"expected object response, got {body}")
    value = body.get(key)
    if not isinstance(value, str):
        raise AssertionError(f"expected string {key}, got {body}")
    return value


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": f"{mutation_id}-{uuid4().hex[:8]}",
        "client_device_id": device_id,
        "client_timestamp": "2026-04-29T12:00:00Z",
        "idempotency_key": f"idem-{mutation_id}-{uuid4().hex[:8]}",
        "client_sequence": sequence,
    }


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
