from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Callable
from uuid import UUID, uuid4

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lightweight Parallax release SLO smoke.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--p95-ms", type=float, default=750.0)
    parser.add_argument("--user-id", default="00000000-0000-0000-0000-0000000000a1")
    parser.add_argument("--bearer-token")
    args = parser.parse_args()

    user_id = UUID(args.user_id)
    headers = _auth_headers(user_id, args.bearer_token)
    latencies: list[tuple[str, float]] = []

    with httpx.Client(base_url=args.api_url, timeout=10.0) as client:
        setup = _create_timed_annotation(client, headers, user_id)
        probes = _probes(headers, setup, user_id)
        for _ in range(args.samples):
            for name, probe in probes:
                started = time.perf_counter()
                response = probe(client)
                response.raise_for_status()
                latencies.append((name, (time.perf_counter() - started) * 1000))

    values = [latency for _, latency in latencies]
    p95 = statistics.quantiles(values, n=20, method="inclusive")[18]
    slowest = max(latencies, key=lambda item: item[1])
    print(
        f"release slo p95_ms={p95:.2f} samples={len(values)} "
        f"slowest={slowest[0]}:{slowest[1]:.2f}ms"
    )
    return 0 if p95 <= args.p95_ms else 1


def _auth_headers(user_id: UUID, bearer_token: str | None) -> dict[str, str]:
    if bearer_token:
        return {"Authorization": f"Bearer {bearer_token}"}
    return {"X-Parallax-User-Id": str(user_id)}


def _create_timed_annotation(
    client: httpx.Client,
    headers: dict[str, str],
    user_id: UUID,
) -> dict[str, str]:
    activity = client.post(
        "/v1/activities",
        headers=headers,
        json={
            "mutation": _mutation(user_id, "activity", 1),
            "display_name": f"Release SLO {uuid4()}",
        },
    )
    activity.raise_for_status()
    activity_id = activity.json()["id"]

    session = client.post(
        "/v1/timing/sessions",
        headers=headers,
        json={
            "mutation": _mutation(user_id, "session", 2),
            "activity_id": activity_id,
            "client_session_id": f"release-slo-session-{uuid4()}",
        },
    )
    session.raise_for_status()
    session_id = session.json()["id"]

    annotation = client.post(
        f"/v1/timing/sessions/{session_id}/annotations",
        headers=headers,
        json={
            "mutation": _mutation(user_id, "annotation", 3),
            "input_mode": "text",
            "raw_text": "Started setup, then paused to clear the counter.",
            "occurred_at": "2026-04-28T12:02:00Z",
        },
    )
    annotation.raise_for_status()
    return {
        "activity_id": activity_id,
        "session_id": session_id,
        "annotation_id": annotation.json()["id"],
    }


def _probes(
    headers: dict[str, str],
    setup: dict[str, str],
    user_id: UUID,
) -> list[tuple[str, Callable[[httpx.Client], httpx.Response]]]:
    session_id = setup["session_id"]
    annotation_id = setup["annotation_id"]
    return [
        ("health", lambda client: client.get("/v1/health")),
        ("ready", lambda client: client.get("/v1/ready")),
        ("live", lambda client: client.get("/v1/live")),
        ("activities", lambda client: client.get("/v1/activities", headers=headers)),
        (
            "timing_session",
            lambda client: client.get(f"/v1/timing/sessions/{session_id}", headers=headers),
        ),
        (
            "annotation",
            lambda client: client.get(f"/v1/timing/annotations/{annotation_id}", headers=headers),
        ),
        (
            "extract",
            lambda client: client.post(
                f"/v1/timing/annotations/{annotation_id}/extract",
                headers=headers,
                json={
                    "mutation": _mutation(user_id, "extract", uuid4().int % 1_000_000),
                    "force": True,
                },
            ),
        ),
    ]


def _mutation(user_id: UUID, label: str, sequence: int) -> dict[str, object]:
    mutation_id = f"release-slo-{label}-{uuid4()}"
    return {
        "client_mutation_id": mutation_id,
        "client_device_id": "release-slo-smoke",
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"{user_id}:{mutation_id}",
        "client_sequence": sequence,
    }


if __name__ == "__main__":
    raise SystemExit(main())
