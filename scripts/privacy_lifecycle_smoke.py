from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg.rows import dict_row


def main() -> int:
    parser = argparse.ArgumentParser(description="Run privacy lifecycle workflow smoke checks.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"privacy-smoke-{user_id.hex[:8]}"
    headers = {"X-Parallax-User-Id": str(user_id)}
    summary: dict[str, object] = {"user_id": str(user_id), "device_id": device_id}

    try:
        with httpx.Client(
            base_url=args.api_url.rstrip("/"),
            headers=headers,
            timeout=10.0,
        ) as client:
            place = _expect(
                client.post(
                    "/v1/places",
                    json={
                        "mutation": _mutation(device_id, "place", 1),
                        "display_name": "Private Home Label",
                        "category": "home",
                        "latitude": 40.0,
                        "longitude": -70.0,
                        "radius_meters": 50,
                        "source": "manual_place",
                        "privacy_class": "private",
                        "confirmed_by_user": True,
                        "is_sensitive": True,
                        "aliases": ["home alias"],
                        "metadata": {"source": "privacy-smoke"},
                    },
                ),
                201,
            )
            delete = _expect(
                client.post(
                    "/v1/privacy/delete",
                    json={
                        "mutation": _mutation(device_id, "delete-place-context", 2),
                        "delete_scope": "place_context",
                        "entity_id": place["id"],
                        "confirm": True,
                    },
                ),
                202,
            )
            if delete["status"] != "queued":
                raise AssertionError(f"expected queued privacy delete, got {delete}")
            _wait_for_workflow(args.database_url, UUID(str(delete["workflow_run_id"])))
            redacted_place = _place_row(args.database_url, user_id, UUID(str(place["id"])))
            if (
                redacted_place["display_name"] != "Deleted place"
                or redacted_place["latitude"] is not None
            ):
                raise AssertionError(f"place_context delete did not redact place: {redacted_place}")

            activity = _expect(
                client.post(
                    "/v1/activities",
                    json={
                        "mutation": _mutation(device_id, "activity", 3),
                        "display_name": "Privacy lifecycle activity",
                    },
                ),
                201,
            )
            session = _expect(
                client.post(
                    "/v1/timing/sessions",
                    json={
                        "mutation": _mutation(device_id, "session", 4),
                        "activity_id": activity["id"],
                        "client_session_id": f"privacy-smoke-{uuid4()}",
                    },
                ),
                201,
            )
            annotation = _expect(
                client.post(
                    f"/v1/timing/sessions/{session['id']}/annotations",
                    json={
                        "mutation": _mutation(device_id, "annotation", 5),
                        "input_mode": "text",
                        "raw_text": "PRIVATE_PRIVACY_SMOKE_TEXT",
                        "audio_object_ref": "audio/privacy-smoke.wav",
                        "occurred_at": "2026-04-28T12:10:00Z",
                        "privacy_class": "private",
                    },
                ),
                201,
            )
            redact = _expect(
                client.post(
                    "/v1/privacy/redact",
                    json={
                        "mutation": _mutation(device_id, "redact-annotation", 6),
                        "entity_type": "temporal_context_annotation",
                        "entity_id": annotation["id"],
                        "reason": "privacy smoke",
                    },
                ),
                202,
            )
            if redact["status"] != "queued":
                raise AssertionError(f"expected queued privacy redact, got {redact}")
            _wait_for_workflow(args.database_url, UUID(str(redact["workflow_run_id"])))
            redacted_annotation = _annotation_row(
                args.database_url,
                user_id,
                UUID(str(annotation["id"])),
            )
            if (
                redacted_annotation["status"] != "redacted"
                or redacted_annotation["raw_text"] is not None
                or redacted_annotation["audio_object_ref"] is not None
            ):
                raise AssertionError(
                    f"privacy redact did not redact annotation: {redacted_annotation}"
                )

            export = _expect(
                client.post(
                    "/v1/privacy/export",
                    json={
                        "mutation": _mutation(device_id, "export", 7),
                        "include_raw_context": True,
                        "include_audio": False,
                    },
                ),
                202,
            )
            if export["status"] != "queued":
                raise AssertionError(f"expected queued privacy export, got {export}")
            export_result = _wait_for_workflow(
                args.database_url,
                UUID(str(export["workflow_run_id"])),
            )
            manifest = export_result.get("export_manifest")
            if not isinstance(manifest, dict) or int(manifest.get("activities", 0)) < 1:
                raise AssertionError(f"privacy export manifest is incomplete: {export_result}")

        summary.update(
            {
                "place_id": place["id"],
                "annotation_id": annotation["id"],
                "delete_workflow_id": delete["workflow_run_id"],
                "redact_workflow_id": redact["workflow_run_id"],
                "export_workflow_id": export["workflow_run_id"],
            }
        )
        print(json.dumps({"status": "passed", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": f"{mutation_id}-{uuid4().hex[:8]}",
        "client_device_id": device_id,
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"privacy-smoke:{mutation_id}:{uuid4().hex[:8]}",
        "client_sequence": sequence,
    }


def _expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise AssertionError(
            f"expected {status_code} from {response.request.method} {response.request.url}, "
            f"got {response.status_code}: {response.text}"
        )
    body = response.json()
    if not isinstance(body, dict):
        raise AssertionError(f"expected object response, got {body!r}")
    return body


def _wait_for_workflow(database_url: str, workflow_id: UUID) -> dict[str, object]:
    return _wait_for(
        lambda: _workflow_result(database_url, workflow_id),
        f"workflow {workflow_id}",
    )


def _wait_for(
    fetch: Callable[[], dict[str, object] | None],
    label: str,
) -> dict[str, object]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = fetch()
        if result is not None:
            return result
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {label}")


def _workflow_result(database_url: str, workflow_id: UUID) -> dict[str, object] | None:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status, error_code, error_message, result_ref
                from workflow_run
                where id = %s
                """,
                (workflow_id,),
            )
            row = cursor.fetchone()
    if row is None or row["status"] in {"queued", "running"}:
        return None
    if row["status"] != "succeeded":
        raise AssertionError(
            f"workflow {workflow_id} failed: {row['error_code']} {row['error_message']}"
        )
    result = row["result_ref"]
    if not isinstance(result, dict):
        raise AssertionError(f"workflow {workflow_id} returned non-object result_ref")
    return result


def _place_row(database_url: str, user_id: UUID, place_id: UUID) -> dict[str, object]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select display_name, latitude, longitude, aliases
                from user_place
                where user_id = %s and id = %s
                """,
                (user_id, place_id),
            )
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"place not found after delete workflow: {place_id}")
    return dict(row)


def _annotation_row(database_url: str, user_id: UUID, annotation_id: UUID) -> dict[str, object]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status::text, raw_text, audio_object_ref
                from temporal_context_annotation
                where user_id = %s and id = %s
                """,
                (user_id, annotation_id),
            )
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"annotation not found after redact workflow: {annotation_id}")
    return dict(row)


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
