from __future__ import annotations

import argparse
import os

import httpx
from release_auth_helpers import release_bearer_token


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove release auth with the configured bearer/Firebase provider."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--bearer-token", default=os.getenv("PARALLAX_RELEASE_BEARER_TOKEN"))
    parser.add_argument(
        "--app-check-token",
        default=os.getenv("PARALLAX_RELEASE_APP_CHECK_TOKEN"),
    )
    args = parser.parse_args()

    try:
        bearer_token = release_bearer_token(args.bearer_token)
    except ValueError as exc:
        print(f"auth provider probe failed: {exc}")
        return 2
    except httpx.HTTPError:
        print("auth provider probe failed: Firebase release token mint request failed")
        return 1
    if not bearer_token:
        print("auth provider probe failed: PARALLAX_RELEASE_BEARER_TOKEN is required")
        return 2

    headers = {"Authorization": f"Bearer {bearer_token}"}
    if args.app_check_token:
        headers["X-Firebase-AppCheck"] = args.app_check_token
    with httpx.Client(base_url=args.api_url, timeout=10.0, headers=headers) as client:
        health = client.get("/v1/health")
        health.raise_for_status()
        response = client.get("/v1/activities")
    if response.status_code != 200:
        print(
            "auth provider probe failed: "
            f"GET /v1/activities returned {response.status_code}: {response.text}"
        )
        return 1
    print("auth provider probe passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
