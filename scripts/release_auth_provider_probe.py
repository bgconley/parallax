from __future__ import annotations

import argparse
import os

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove release auth with the configured bearer/JWKS provider."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--bearer-token", default=os.getenv("PARALLAX_RELEASE_BEARER_TOKEN"))
    args = parser.parse_args()

    if not args.bearer_token:
        print("auth provider probe failed: PARALLAX_RELEASE_BEARER_TOKEN is required")
        return 2

    headers = {"Authorization": f"Bearer {args.bearer_token}"}
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
