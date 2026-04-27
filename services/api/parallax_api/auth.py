from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header

from .settings import get_settings


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID


def get_auth_context(x_parallax_user_id: str | None = Header(default=None)) -> AuthContext:
    if x_parallax_user_id:
        return AuthContext(user_id=UUID(x_parallax_user_id))
    return AuthContext(user_id=get_settings().dev_user_id)
