from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 7 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--eval-cases",
        default="parallax_v1_3_artifact_pack/tests_or_eval/query_grounding_eval_cases.jsonl",
    )
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase7-smoke-{user_id.hex[:8]}"
    api_url = args.api_url.rstrip("/")
    headers = {"X-Parallax-User-Id": str(user_id)}
    summary: dict[str, object] = {"user_id": str(user_id), "device_id": device_id}

    try:
        with httpx.Client(base_url=api_url, headers=headers, timeout=10) as client:
            _wait_for_health(client)
            activity = _create_activity(client, device_id, "Clean pots and pans", 1)
            activity_id = _string_value(activity, "id")
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "one",
                10,
                detour_start="2026-04-28T12:05:00Z",
                detour_end="2026-04-28T12:15:00Z",
                completed_at="2026-04-28T12:30:00Z",
            )
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "two",
                30,
                detour_start="2026-04-29T12:04:00Z",
                detour_end="2026-04-29T12:14:00Z",
                completed_at="2026-04-29T12:30:00Z",
            )
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "active-only",
                50,
                detour_start="2026-04-30T12:05:00Z",
                detour_end="2026-04-30T12:15:00Z",
                completed_at="2026-04-30T13:00:00Z",
                decision="active_only",
                model_inclusion="active_duration_only",
            )
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "wall-only",
                70,
                detour_start="2026-04-30T14:05:00Z",
                detour_end="2026-04-30T14:15:00Z",
                completed_at="2026-04-30T16:00:00Z",
                decision="mark_unusual",
                model_inclusion="wall_envelope_only",
            )
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "friction-only",
                90,
                detour_start="2026-05-01T10:05:00Z",
                detour_end="2026-05-01T10:15:00Z",
                completed_at="2026-05-01T10:30:00Z",
                decision="friction_only",
                model_inclusion="friction_patterns_only",
            )
            _create_reviewed_run(
                client,
                device_id,
                activity_id,
                "query-only",
                110,
                detour_start="2026-05-01T11:05:00Z",
                detour_end="2026-05-01T11:15:00Z",
                completed_at="2026-05-01T11:30:00Z",
                decision="query_evidence_only",
                model_inclusion="query_evidence_only",
            )

            duration_answer = _expect(
                client.post(
                    "/v1/temporal/query",
                    json={
                        "mutation": _mutation(device_id, "duration-query", 60),
                        "question": "How long does cleaning pots and pans usually take?",
                    },
                ),
                202,
            )
            _assert_duration_answer(duration_answer, activity_id)
            fetched = _expect(
                client.get(f"/v1/temporal/query/{duration_answer['id']}"),
                200,
            )
            if fetched != duration_answer:
                raise AssertionError("fetched temporal query answer did not preserve evidence")

            delay_answer = _expect(
                client.post(
                    "/v1/temporal/query",
                    json={
                        "mutation": _mutation(device_id, "delay-query", 61),
                        "question": "What usually delays pots and pans?",
                        "activity_id": activity_id,
                        "include_raw_quotes": True,
                    },
                ),
                202,
            )
            _assert_delay_answer(delay_answer, activity_id)
            _assert_eval_cases(Path(args.eval_cases), [duration_answer, delay_answer])

        db_counts = _phase7_counts(args.database_url, user_id)
        if db_counts["evidence_bundles"] < 2 or db_counts["evidence_items"] < 4:
            raise AssertionError(f"evidence bundle persistence failed: {db_counts}")
        if db_counts["retrieval_documents"] < 2:
            raise AssertionError(f"retrieval document persistence failed: {db_counts}")
        if db_counts["query_outbox_events"] < 4:
            raise AssertionError(f"query outbox events missing: {db_counts}")
        summary.update(
            {
                "activity_id": activity_id,
                "duration_answer_id": duration_answer["id"],
                "delay_answer_id": delay_answer["id"],
                **db_counts,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase7", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _create_activity(
    client: httpx.Client,
    device_id: str,
    display_name: str,
    sequence: int,
) -> dict[str, object]:
    return _expect(
        client.post(
            "/v1/activities",
            json={
                "mutation": _mutation(device_id, f"activity-{sequence}", sequence),
                "display_name": display_name,
            },
        ),
        201,
    )


def _create_reviewed_run(
    client: httpx.Client,
    device_id: str,
    activity_id: str,
    suffix: str,
    sequence: int,
    *,
    detour_start: str,
    detour_end: str,
    completed_at: str,
    decision: str = "save_useful_run",
    model_inclusion: str = "full",
) -> str:
    session = _expect(
        client.post(
            "/v1/timing/sessions",
            json={
                "mutation": _mutation(device_id, f"session-{suffix}", sequence),
                "activity_id": activity_id,
                "client_session_id": f"phase7-{suffix}-{uuid4().hex}",
                "mode": "whole_task",
            },
        ),
        201,
    )
    session_id = _string_value(session, "id")
    for label, offset, event_type, client_time in (
        ("start", 1, "session_started", detour_start.replace(":05:", ":00:")),
        ("detour-start", 2, "resource_detour_started", detour_start),
        ("detour-end", 3, "resource_detour_completed", detour_end),
    ):
        _expect(
            client.post(
                f"/v1/timing/sessions/{session_id}/events",
                json={
                    "mutation": _mutation(device_id, f"{suffix}-{label}", sequence + offset),
                    "event_type": event_type,
                    "client_time": client_time,
                },
            ),
            201,
        )
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/complete",
            json={
                "mutation": _mutation(device_id, f"{suffix}-complete", sequence + 10),
                "completed_at": completed_at,
            },
        ),
        200,
    )
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/review",
            json={
                "mutation": _mutation(device_id, f"{suffix}-review", sequence + 11),
                "decision": decision,
                "model_inclusion": model_inclusion,
                "scopes": _review_scopes(model_inclusion),
                "user_note": "Phase 7 smoke reviewed run.",
            },
        ),
        200,
    )
    return session_id


def _assert_duration_answer(answer: dict[str, object], activity_id: str) -> None:
    facts = _dict_value(answer, "computed_facts")
    if answer["status"] != "complete":
        raise AssertionError(f"query did not complete: {answer}")
    if answer["sample_size"] != 3 or facts["sample_size"] != 3:
        raise AssertionError(f"duration sample size drifted: {answer}")
    if facts.get("active_sample_size") != 3 or facts.get("wall_sample_size") != 3:
        raise AssertionError(f"duration metric scope counts drifted: {facts}")
    if facts["intent"] != "duration_summary" or facts["activity_id"] != activity_id:
        raise AssertionError(f"duration query plan drifted: {facts}")
    if "friction_patterns_only" in json.dumps(answer) or "query_evidence_only" in json.dumps(
        answer
    ):
        raise AssertionError(f"duration answer included non-duration evidence: {answer}")
    for key in ("active_p50_seconds", "active_p80_seconds", "wall_p80_seconds"):
        if key not in facts or facts[key] is None:
            raise AssertionError(f"duration fact missing {key}: {facts}")
    if not answer["evidence"]:
        raise AssertionError(f"duration answer missing evidence: {answer}")
    if "LLM" not in " ".join(_list_value(answer, "limitations")):
        raise AssertionError(f"duration answer missing deterministic limitation: {answer}")


def _assert_delay_answer(answer: dict[str, object], activity_id: str) -> None:
    facts = _dict_value(answer, "computed_facts")
    categories = facts.get("friction_categories")
    if facts["intent"] != "delay_drivers" or facts["activity_id"] != activity_id:
        raise AssertionError(f"delay query plan drifted: {facts}")
    if not isinstance(categories, list) or not any(
        isinstance(item, dict) and item.get("friction_category") == "resource"
        for item in categories
    ):
        raise AssertionError(f"delay answer missing resource friction facts: {facts}")
    if answer["sample_size"] != 4:
        raise AssertionError(f"delay sample size drifted: {answer}")
    resource = next(
        item
        for item in categories
        if isinstance(item, dict) and item.get("friction_category") == "resource"
    )
    if resource.get("event_count") != 4:
        raise AssertionError(f"delay friction scope count drifted: {facts}")
    if not any("Raw quotes are disabled" in item for item in _list_value(answer, "limitations")):
        raise AssertionError(f"delay answer did not respect raw quote privacy: {answer}")
    if "Phase 7 smoke reviewed run" in json.dumps(answer):
        raise AssertionError(f"delay answer leaked raw review note: {answer}")
    if not all(
        item.get("entity_type") == "timing_event_span"
        for item in _object_list_value(answer, "evidence")
    ):
        raise AssertionError(f"delay evidence is not span-grounded: {answer}")


def _assert_eval_cases(
    eval_path: Path,
    answers: list[dict[str, object]],
) -> None:
    serialized = [json.dumps(answer, sort_keys=True) for answer in answers]
    for line in eval_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        haystack = serialized[0] if case["case_id"] == "QG-001" else serialized[1]
        for needle in case["must_include"]:
            if needle not in haystack:
                raise AssertionError(f"{case['case_id']} missing {needle}: {haystack}")
        for forbidden in case["must_not_include"]:
            if forbidden in haystack:
                raise AssertionError(f"{case['case_id']} included forbidden text: {forbidden}")


def _phase7_counts(database_url: str, user_id: UUID) -> dict[str, int]:
    queries = {
        "temporal_query_answers": "select count(*) from temporal_query_answer where user_id = %s",
        "evidence_bundles": (
            "select count(*) from evidence_bundle "
            "where user_id = %s and purpose = 'temporal_query_answer'"
        ),
        "evidence_items": "select count(*) from evidence_item where user_id = %s",
        "retrieval_documents": (
            "select count(*) from retrieval_document "
            "where user_id = %s and entity_type = 'temporal_query_answer'"
        ),
        "query_outbox_events": (
            "select count(*) from outbox_event "
            "where user_id = %s and event_name like 'temporal_query.%%'"
        ),
    }
    with psycopg.connect(database_url) as connection:
        counts: dict[str, int] = {}
        with connection.cursor() as cursor:
            for key, query in queries.items():
                cursor.execute(query, (user_id,))
                row = cursor.fetchone()
                counts[key] = int(row[0]) if row is not None else 0
    return counts


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))
        connection.commit()


def _wait_for_health(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            response = client.get("/v1/health")
            if response.status_code == 200 and response.json().get("status") == "healthy":
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise TimeoutError("API did not become healthy")


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": f"{mutation_id}-{uuid4().hex[:8]}",
        "client_device_id": device_id,
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"idem-{mutation_id}-{uuid4().hex[:8]}",
        "client_sequence": sequence,
    }


def _review_scopes(model_inclusion: str) -> list[str]:
    if model_inclusion == "active_duration_only":
        return ["active_duration"]
    if model_inclusion == "wall_envelope_only":
        return ["wall_duration"]
    if model_inclusion == "friction_patterns_only":
        return ["friction_patterns"]
    if model_inclusion == "query_evidence_only":
        return ["query_evidence"]
    return ["active_duration", "wall_duration", "friction_patterns"]


def _expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise AssertionError(
            f"expected {status_code} for {response.request.method} "
            f"{response.request.url}, got {response.status_code}: {response.text}"
        )
    body = response.json()
    if not isinstance(body, dict):
        raise AssertionError(f"expected object response: {body}")
    return body


def _string_value(body: dict[str, object], key: str) -> str:
    value = body[key]
    if not isinstance(value, str):
        raise AssertionError(f"expected string {key}: {body}")
    return value


def _dict_value(body: dict[str, object], key: str) -> dict[str, object]:
    value = body[key]
    if not isinstance(value, dict):
        raise AssertionError(f"expected object {key}: {body}")
    return value


def _list_value(body: dict[str, object], key: str) -> list[str]:
    value = body[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"expected string list {key}: {body}")
    return value


def _object_list_value(body: dict[str, object], key: str) -> list[dict[str, object]]:
    value = body[key]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise AssertionError(f"expected object list {key}: {body}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
