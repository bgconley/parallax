from __future__ import annotations

import os
from uuid import UUID

from mint_release_firebase_id_token import mint_release_id_token


def release_bearer_token(explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token
    if not (
        os.getenv("PARALLAX_FIREBASE_WEB_API_KEY")
        and os.getenv("PARALLAX_RELEASE_FIREBASE_EMAIL")
        and os.getenv("PARALLAX_RELEASE_FIREBASE_PASSWORD")
    ):
        return None
    return mint_release_id_token(
        web_api_key=os.getenv("PARALLAX_FIREBASE_WEB_API_KEY"),
        email=os.getenv("PARALLAX_RELEASE_FIREBASE_EMAIL"),
        password=os.getenv("PARALLAX_RELEASE_FIREBASE_PASSWORD"),
    )


def release_auth_headers(
    *,
    fallback_user_id: UUID,
    bearer_token: str | None,
    app_check_token: str | None = None,
) -> dict[str, str]:
    token = release_bearer_token(bearer_token)
    headers = (
        {"Authorization": f"Bearer {token}"}
        if token
        else {"X-Parallax-User-Id": str(fallback_user_id)}
    )
    if app_check_token:
        headers["X-Firebase-AppCheck"] = app_check_token
    return headers
