from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from release_auth_helpers import release_auth_headers


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan release logs for sensitive payload echoes.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--log-dir", default="/srv/parallax/logs")
    parser.add_argument("--user-id", default="00000000-0000-0000-0000-0000000000a2")
    parser.add_argument("--bearer-token")
    parser.add_argument("--app-check-token")
    args = parser.parse_args()

    marker = f"parallax-sensitive-marker-{uuid4()}"
    headers = release_auth_headers(
        fallback_user_id=UUID(args.user_id),
        bearer_token=args.bearer_token,
        app_check_token=args.app_check_token,
    )
    body_text = _probe_validation_error(args.api_url, headers, marker)
    if marker in body_text:
        print("privacy scan failed: sensitive marker appeared in structured error response")
        return 1

    leaked_files = _files_containing_marker(Path(args.log_dir), marker)
    if leaked_files:
        print("privacy scan failed: sensitive marker appeared in logs")
        for path in leaked_files:
            print(path)
        return 1

    print("privacy log scan passed")
    return 0


def _probe_validation_error(api_url: str, headers: dict[str, str], marker: str) -> str:
    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        response = client.post(
            "/v1/activities",
            headers=headers,
            json={
                "mutation": {
                    "client_mutation_id": f"privacy-scan-{uuid4()}",
                    "client_device_id": "release-privacy-scan",
                    "client_timestamp": "2026-04-28T12:00:00Z",
                    "idempotency_key": f"privacy-scan:{uuid4()}",
                    "client_sequence": 1,
                },
                "display_name": f"Privacy scan {uuid4()}",
                "raw_private_note": marker,
            },
        )
    if response.status_code != 400:
        raise RuntimeError(f"expected validation failure, got {response.status_code}")
    if response.json().get("error_code") != "validation_error":
        raise RuntimeError("expected structured validation_error response")
    return response.text


def _files_containing_marker(log_dir: Path, marker: str) -> list[Path]:
    if not log_dir.exists():
        return []
    leaked: list[Path] = []
    for path in log_dir.rglob("*"):
        if not path.is_file() or path.stat().st_size > 10_000_000:
            continue
        try:
            if marker in path.read_text(encoding="utf-8", errors="ignore"):
                leaked.append(path)
        except OSError:
            continue
    return leaked


if __name__ == "__main__":
    raise SystemExit(main())
