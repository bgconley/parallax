from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID


def get_auth_context(x_parallax_user_id: str | None = Header(default=None)) -> AuthContext:
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
