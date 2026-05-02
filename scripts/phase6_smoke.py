from __future__ import annotations

import argparse
import json
import time
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg.types.json import Jsonb


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 6 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase6-smoke-{user_id.hex[:8]}"
    api_url = args.api_url.rstrip("/")
    headers = {"X-Parallax-User-Id": str(user_id)}
    summary: dict[str, object] = {"user_id": str(user_id), "device_id": device_id}

    try:
        with httpx.Client(base_url=api_url, headers=headers, timeout=10) as client:
            _wait_for_health(client)
            source_activity = _create_activity(client, device_id, "Clean skillet", 1)
            target_activity = _create_activity(client, device_id, "Wash pans", 2)
            source_activity_id = _string_value(source_activity, "id")
            target_activity_id = _string_value(target_activity, "id")
            source_session_id = _create_started_session(
                client,
                device_id,
                source_activity_id,
                "merge-source",
                3,
            )

            alias = _expect(
                client.post(
                    f"/v1/activities/{target_activity_id}/aliases",
                    json={
                        "mutation": _mutation(device_id, "alias-suggested", 5),
                        "alias_text": "scrub pans",
                        "user_confirmed": False,
                    },
                ),
                201,
            )
            unresolved = _expect(
                client.post("/v1/activities/resolve", json={"query": "scrub pans", "limit": 5}),
                200,
            )
            if unresolved["recommended_activity_id"] is not None:
                raise AssertionError(f"suggested alias resolved before confirmation: {unresolved}")
            accepted_alias = _expect(
                client.post(
                    f"/v1/activities/{target_activity_id}/aliases/{alias['id']}/decision",
                    json={
                        "mutation": _mutation(device_id, "alias-accept", 6),
                        "decision": "accept",
                    },
                ),
                200,
            )
            if not accepted_alias["user_confirmed"] or accepted_alias["rejected"]:
                raise AssertionError(f"alias was not accepted: {accepted_alias}")
            resolved = _expect(
                client.post("/v1/activities/resolve", json={"query": "scrub pans", "limit": 5}),
                200,
            )
            if resolved["recommended_activity_id"] != target_activity_id:
                raise AssertionError(f"confirmed alias did not resolve: {resolved}")

            relationship = _expect(
                client.post(
                    f"/v1/activities/{target_activity_id}/relationships",
                    json={
                        "mutation": _mutation(device_id, "relationship-suggested", 7),
                        "to_activity_id": source_activity_id,
                        "kind": "related_to",
                        "user_confirmed": False,
                    },
                ),
                201,
            )
            accepted_relationship = _expect(
                client.post(
                    (
                        f"/v1/activities/{target_activity_id}/relationships/"
                        f"{relationship['id']}/decision"
                    ),
                    json={
                        "mutation": _mutation(device_id, "relationship-accept", 8),
                        "decision": "accept",
                    },
                ),
                200,
            )
            if accepted_relationship["state"] != "confirmed":
                raise AssertionError(f"relationship decision failed: {accepted_relationship}")

            preview = _expect(
                client.post(
                    f"/v1/activities/{source_activity_id}/merge-preview",
                    json={"target_activity_id": target_activity_id},
                ),
                200,
            )
            if preview["affected_session_count"] != 1:
                raise AssertionError(f"merge preview did not see source history: {preview}")
            merge = _expect(
                client.post(
                    f"/v1/activities/{source_activity_id}/merge",
                    json={
                        "mutation": _mutation(device_id, "merge", 9),
                        "target_activity_id": target_activity_id,
                        "reason": "Phase 6 smoke duplicate.",
                    },
                ),
                200,
            )
            if not merge["audit_id"]:
                raise AssertionError(f"merge did not return audit id: {merge}")
            source_after = _expect(client.get(f"/v1/activities/{source_activity_id}"), 200)
            if source_after["status"] != "merged":
                raise AssertionError(f"source activity was not soft merged: {source_after}")
            source_session = _expect(client.get(f"/v1/timing/sessions/{source_session_id}"), 200)
            if source_session["activity_id"] != source_activity_id:
                raise AssertionError(f"source session history moved unexpectedly: {source_session}")

            confirmed_event_ids: set[str] = set()
            for index, suffix in enumerate(("one", "two"), start=12):
                session_id = _create_started_session(
                    client,
                    device_id,
                    target_activity_id,
                    f"sponge-{suffix}",
                    index,
                )
                annotation = _expect(
                    client.post(
                        f"/v1/timing/sessions/{session_id}/annotations",
                        json={
                            "mutation": _mutation(device_id, f"note-{suffix}", index + 10),
                            "input_mode": "text",
                            "raw_text": (
                                "I had to stop and find the sponge, which took about 10 minutes."
                            ),
                            "timer_elapsed_seconds": 600,
                            "timer_active_seconds": 0,
                            "occurred_at": "2026-04-28T12:10:00Z",
                            "privacy_class": "normal",
                            "metadata": {},
                        },
                    ),
                    201,
                )
                _expect(
                    client.post(
                        f"/v1/timing/annotations/{annotation['id']}/extract",
                        json={
                            "mutation": _mutation(device_id, f"extract-{suffix}", index + 20),
                            "force": False,
                        },
                    ),
                    202,
                )
                event = _wait_for_extracted_event(
                    args.database_url,
                    user_id,
                    UUID(str(annotation["id"])),
                )
                _expect(
                    client.post(
                        f"/v1/timing/extracted-events/{event['id']}/confirm",
                        json={
                            "mutation": _mutation(device_id, f"confirm-{suffix}", index + 30),
                            "confirmation_state": "confirmed",
                        },
                    ),
                    200,
                )
                confirmed_event_ids.add(str(event["id"]))
                if suffix == "one":
                    _expect(
                        client.post(
                            f"/v1/timing/extracted-events/{event['id']}/confirm",
                            json={
                                "mutation": _mutation(
                                    device_id,
                                    "confirm-one-duplicate",
                                    index + 31,
                                ),
                                "confirmation_state": "confirmed",
                            },
                        ),
                        200,
                    )
                    duplicate_dependencies = _expect_list(
                        client.get(
                            f"/v1/activities/{target_activity_id}/resource-dependencies"
                        ),
                        200,
                    )
                    sponge_dependency = _dependency_by_name(
                        duplicate_dependencies,
                        "sponge",
                    )
                    if sponge_dependency is None or sponge_dependency["failure_count"] != 1:
                        raise AssertionError(
                            "duplicate confirmation changed dependency count: "
                            f"{duplicate_dependencies}"
                        )
                    duplicate_checks = _expect_list(
                        client.get(f"/v1/activities/{target_activity_id}/preflight-checks"),
                        200,
                    )
                    if any(
                        check["source"] == "resource_dependency"
                        for check in duplicate_checks
                    ):
                        raise AssertionError(
                            "duplicate confirmation created resource preflight: "
                            f"{duplicate_checks}"
                        )

            if len(confirmed_event_ids) != 2:
                raise AssertionError(
                    f"expected two distinct extracted events: {confirmed_event_ids}"
                )

            dependencies = _expect_list(
                client.get(f"/v1/activities/{target_activity_id}/resource-dependencies"),
                200,
            )
            sponge_dependency = _dependency_by_name(dependencies, "sponge")
            failure_count = (
                _int_value(sponge_dependency, "failure_count")
                if sponge_dependency is not None
                else 0
            )
            if failure_count != 2:
                raise AssertionError(
                    f"resource dependency threshold did not aggregate: {dependencies}"
                )
            checks = _expect_list(
                client.get(f"/v1/activities/{target_activity_id}/preflight-checks"),
                200,
            )
            resource_check = next(
                check for check in checks if check["source"] == "resource_dependency"
            )
            if resource_check["check_text"] != "Check sponge/scrubber before washing pans.":
                raise AssertionError(f"preflight suggestion text drifted: {resource_check}")

            resource_only_session_id = _create_started_session(
                client,
                device_id,
                target_activity_id,
                "resource-only",
                45,
            )
            resource_only_annotation = _expect(
                client.post(
                    f"/v1/timing/sessions/{resource_only_session_id}/annotations",
                    json={
                        "mutation": _mutation(device_id, "note-resource-only", 47),
                        "input_mode": "text",
                        "raw_text": "I had to stop and look for the pan scraper.",
                        "timer_elapsed_seconds": 420,
                        "timer_active_seconds": 0,
                        "occurred_at": "2026-04-28T12:10:00Z",
                        "privacy_class": "normal",
                        "metadata": {},
                    },
                ),
                201,
            )
            resource_only_event_id = _insert_resource_only_event(
                args.database_url,
                user_id,
                UUID(str(resource_only_annotation["id"])),
                UUID(resource_only_session_id),
            )
            _expect(
                client.post(
                    f"/v1/timing/extracted-events/{resource_only_event_id}/confirm",
                    json={
                        "mutation": _mutation(device_id, "confirm-resource-only", 48),
                        "confirmation_state": "confirmed",
                    },
                ),
                200,
            )
            resource_only_dependencies = _expect_list(
                client.get(f"/v1/activities/{target_activity_id}/resource-dependencies"),
                200,
            )
            pan_scraper_dependency = _dependency_by_name(
                resource_only_dependencies,
                "pan scraper",
            )
            if pan_scraper_dependency is None or pan_scraper_dependency["failure_count"] != 1:
                raise AssertionError(
                    "resource-only evidence did not aggregate: "
                    f"{resource_only_dependencies}"
                )
            resource_only_checks = _expect_list(
                client.get(f"/v1/activities/{target_activity_id}/preflight-checks"),
                200,
            )
            if any(
                check["source"] == "model_suggested"
                and check.get("source_event_id") == str(resource_only_event_id)
                for check in resource_only_checks
            ):
                raise AssertionError(
                    "resource-only evidence created model-suggested preflight: "
                    f"{resource_only_checks}"
                )

            state_checks = [resource_check]
            for index, text in enumerate(("Hide", "Snooze", "Retire"), start=50):
                state_checks.append(
                    _expect(
                        client.post(
                            f"/v1/activities/{target_activity_id}/preflight-checks",
                            json={
                                "mutation": _mutation(device_id, f"preflight-{text}", index),
                                "check_text": f"Check {text}.",
                                "source": "model_suggested",
                            },
                        ),
                        201,
                    )
                )
            expected = [
                ("accept", "active", None),
                ("hide", "hidden", None),
                ("snooze", "snoozed", "2026-05-02T12:00:00Z"),
                ("retire", "retired", None),
            ]
            for index, (decision, state, snoozed_until) in enumerate(expected, start=60):
                body: dict[str, object] = {
                    "mutation": _mutation(device_id, f"preflight-{decision}", index),
                    "decision": decision,
                }
                if snoozed_until is not None:
                    body["snoozed_until"] = snoozed_until
                decided = _expect(
                    client.post(
                        (
                            f"/v1/activities/{target_activity_id}/preflight-checks/"
                            f"{state_checks[index - 60]['id']}/decision"
                        ),
                        json=body,
                    ),
                    200,
                )
                if decided["state"] != state:
                    raise AssertionError(f"preflight state decision failed: {decided}")

        counts = _phase6_counts(args.database_url, user_id)
        if counts["activity_identity_changes"] != 1 or counts["merge_audits"] != 1:
            raise AssertionError(f"merge audit counts are wrong: {counts}")
        if counts["activity_aliases"] != 1 or counts["activity_relationships"] < 2:
            raise AssertionError(f"identity endpoint counts are wrong: {counts}")
        if counts["resource_dependencies"] < 1 or counts["preflight_checks"] < 4:
            raise AssertionError(f"resource/preflight counts are wrong: {counts}")
        summary.update(
            {
                "source_activity_id": source_activity_id,
                "target_activity_id": target_activity_id,
                "source_session_id": source_session_id,
                **counts,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase6", "summary": summary}, indent=2))
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


def _create_started_session(
    client: httpx.Client,
    device_id: str,
    activity_id: str,
    suffix: str,
    sequence: int,
) -> str:
    session = _expect(
        client.post(
            "/v1/timing/sessions",
            json={
                "mutation": _mutation(device_id, f"session-{suffix}", sequence),
                "activity_id": activity_id,
                "client_session_id": f"phase6-{suffix}-{uuid4().hex}",
                "mode": "whole_task",
            },
        ),
        201,
    )
    session_id = _string_value(session, "id")
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/events",
            json={
                "mutation": _mutation(device_id, f"start-{suffix}", sequence + 1),
                "event_type": "session_started",
                "client_time": "2026-04-28T12:00:00Z",
            },
        ),
        201,
    )
    return session_id


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


def _wait_for_extracted_event(
    database_url: str,
    user_id: UUID,
    annotation_id: UUID,
) -> dict[str, object]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, count_policy, suggested_preflight_text
                    from temporal_extracted_context_event
                    where user_id = %s and annotation_id = %s
                    order by created_at desc
                    limit 1
                    """,
                    (user_id, annotation_id),
                )
                row = cursor.fetchone()
        if row is not None:
            return {
                "id": str(row[0]),
                "count_policy": row[1],
                "suggested_preflight_text": row[2],
            }
        time.sleep(0.5)
    raise TimeoutError("extracted event did not appear")


def _insert_resource_only_event(
    database_url: str,
    user_id: UUID,
    annotation_id: UUID,
    session_id: UUID,
) -> UUID:
    event_id = uuid4()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into temporal_extracted_context_event (
                  id, user_id, annotation_id, session_id, span_type,
                  friction_category, resource_name, duration_seconds,
                  count_policy, count_in_wall_time, count_in_active_time,
                  model_update_scopes, suggested_preflight_text, confidence,
                  confirmation_state, sensitive_data_detected, source_json,
                  user_correction_json
                )
                values (
                  %s, %s, %s, %s, 'resource_detour', 'resource', 'pan scraper',
                  420, 'wall_only', true, false, %s, null, 0.910,
                  'needs_confirmation', false, %s, %s
                )
                """,
                (
                    event_id,
                    user_id,
                    annotation_id,
                    session_id,
                    ["friction_patterns"],
                    Jsonb({"evidence": "resource_only_smoke"}),
                    Jsonb({}),
                ),
            )
        connection.commit()
    return event_id


def _phase6_counts(database_url: str, user_id: UUID) -> dict[str, int]:
    queries = {
        "activity_aliases": "select count(*) from activity_alias where user_id = %s",
        "activity_relationships": "select count(*) from activity_relationship where user_id = %s",
        "activity_identity_changes": (
            "select count(*) from activity_identity_change where user_id = %s"
        ),
        "merge_audits": (
            "select count(*) from audit_log where user_id = %s and event_name = 'activity.merged'"
        ),
        "resource_dependencies": "select count(*) from resource_dependency where user_id = %s",
        "preflight_checks": "select count(*) from preflight_check where user_id = %s",
    }
    with psycopg.connect(database_url) as connection:
        counts: dict[str, int] = {}
        with connection.cursor() as cursor:
            for key, sql in queries.items():
                cursor.execute(sql, (user_id,))
                row = cursor.fetchone()
                counts[key] = int(row[0]) if row is not None else 0
    return counts


def _dependency_by_name(
    dependencies: list[dict[str, object]],
    resource_name: str,
) -> dict[str, object] | None:
    for dependency in dependencies:
        if dependency.get("resource_name") == resource_name:
            return dependency
    return None


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))
        connection.commit()


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": f"{mutation_id}-{uuid4().hex[:8]}",
        "client_device_id": device_id,
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"idem-{mutation_id}-{uuid4().hex[:8]}",
        "client_sequence": sequence,
    }


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


def _expect_list(response: httpx.Response, status_code: int) -> list[dict[str, object]]:
    if response.status_code != status_code:
        raise AssertionError(
            f"expected {status_code} for {response.request.method} "
            f"{response.request.url}, got {response.status_code}: {response.text}"
        )
    body = response.json()
    if not isinstance(body, list) or not all(isinstance(item, dict) for item in body):
        raise AssertionError(f"expected list response: {body}")
    return body


def _string_value(body: dict[str, object], key: str) -> str:
    value = body[key]
    if not isinstance(value, str):
        raise AssertionError(f"expected string {key}: {body}")
    return value


def _int_value(body: dict[str, object], key: str) -> int:
    value = body[key]
    if not isinstance(value, int):
        raise AssertionError(f"expected int {key}: {body}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
