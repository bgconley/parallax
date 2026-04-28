from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from .settings import ApiSettings, get_settings


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID


def get_auth_context(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    x_parallax_user_id: Annotated[str | None, Header()] = None,
) -> AuthContext:
    if settings.auth_mode != "dev_header":
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "auth_provider_not_configured",
                "message": "configured auth provider is not implemented in Phase 1",
                "details": {"auth_mode": settings.auth_mode},
                "retryable": False,
            },
        )
    if settings.auth_mode == "dev_header" and settings.env not in {"development", "test"}:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "auth_provider_not_configured",
                "message": "development header auth is disabled outside development",
                "details": {"auth_mode": settings.auth_mode, "environment": settings.env},
                "retryable": False,
            },
        )
    if not x_parallax_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "authentication_required",
                "message": "authentication is required",
                "details": {},
                "retryable": False,
            },
        )
    try:
        return AuthContext(user_id=UUID(x_parallax_user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "invalid_auth_context",
                "message": "authentication context is invalid",
                "details": {"header": "X-Parallax-User-Id"},
                "retryable": False,
            },
        ) from exc
