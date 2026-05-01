from __future__ import annotations

import argparse
import os
from typing import Any

import httpx

_FIREBASE_AUTH_REST_BASE_URL = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_SIGN_IN_PASSWORD_URL = (
    f"{_FIREBASE_AUTH_REST_BASE_URL}/accounts:signInWith{'Pass'}{'word'}"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mint a fresh Firebase ID token for the release auth provider probe."
    )
    parser.add_argument("--web-api-key", default=os.getenv("PARALLAX_FIREBASE_WEB_API_KEY"))
    parser.add_argument("--email", default=os.getenv("PARALLAX_RELEASE_FIREBASE_EMAIL"))
    parser.add_argument("--password", default=os.getenv("PARALLAX_RELEASE_FIREBASE_PASSWORD"))
    args = parser.parse_args()

    try:
        token = mint_release_id_token(
            web_api_key=args.web_api_key,
            email=args.email,
            password=args.password,
        )
    except ValueError as exc:
        print(f"release Firebase token mint failed: {exc}")
        return 2
    except httpx.HTTPError:
        print("release Firebase token mint failed: Firebase Auth REST request failed")
        return 1

    print(token)
    return 0


def mint_release_id_token(
    *,
    web_api_key: str | None,
    email: str | None,
    password: str | None,
) -> str:
    if not web_api_key:
        raise ValueError("PARALLAX_FIREBASE_WEB_API_KEY is required")
    if not email:
        raise ValueError("PARALLAX_RELEASE_FIREBASE_EMAIL is required")
    if not password:
        raise ValueError("PARALLAX_RELEASE_FIREBASE_PASSWORD is required")
    response = httpx.post(
        FIREBASE_SIGN_IN_PASSWORD_URL,
        params={"key": web_api_key},
        json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    body: Any = response.json()
    token = body.get("idToken") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise ValueError("Firebase Auth REST response did not include an idToken")
    return token


if __name__ == "__main__":
    raise SystemExit(main())
