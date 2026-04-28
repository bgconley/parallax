from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient, PyJWKClientError

from .settings import ApiSettings, get_settings

_MIN_HS256_SECRET_BYTES = 32


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID


def get_auth_context(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_parallax_user_id: Annotated[str | None, Header()] = None,
) -> AuthContext:
    if settings.auth_mode == "dev_header":
        return _auth_from_development_header(settings, x_parallax_user_id)
    if settings.auth_mode == "external_bearer":
        return _auth_from_bearer_token(settings, authorization)
    raise _auth_provider_unavailable(settings)


def _auth_from_development_header(
    settings: ApiSettings,
    x_parallax_user_id: str | None,
) -> AuthContext:
    if settings.env not in {"development", "test"}:
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
        raise _authentication_required()
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


def _auth_from_bearer_token(
    settings: ApiSettings,
    authorization: str | None,
) -> AuthContext:
    token = _extract_bearer_token(authorization)
    issuer = settings.auth_jwt_issuer or None
    audience = settings.auth_jwt_audience or None
    key = _verification_key(settings, token)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[settings.auth_jwt_algorithm],
            issuer=issuer,
            audience=audience,
            options={
                "require": ["exp", settings.auth_jwt_user_id_claim],
                "verify_aud": audience is not None,
            },
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "auth_token_expired",
                "message": "authentication token has expired",
                "details": {},
                "retryable": False,
            },
        ) from exc
    except InvalidTokenError as exc:
        raise _invalid_auth_token() from exc

    return AuthContext(user_id=_user_id_from_claims(claims, settings.auth_jwt_user_id_claim))


def _verification_key(settings: ApiSettings, token: str) -> Any:
    if settings.auth_jwt_algorithm == "HS256":
        if not settings.auth_jwt_secret or len(settings.auth_jwt_secret.encode("utf-8")) < (
            _MIN_HS256_SECRET_BYTES
        ):
            raise _auth_provider_unavailable(settings)
        return settings.auth_jwt_secret
    if not settings.auth_jwks_url:
        raise _auth_provider_unavailable(settings)
    try:
        return PyJWKClient(settings.auth_jwks_url).get_signing_key_from_jwt(token).key
    except PyJWKClientError as exc:
        raise _invalid_auth_token() from exc


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _authentication_required()
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise _invalid_auth_token()
    return token.strip()


def _user_id_from_claims(claims: dict[str, Any], claim_name: str) -> UUID:
    raw_user_id = claims.get(claim_name)
    if not isinstance(raw_user_id, str):
        raise _invalid_auth_token()
    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise _invalid_auth_token() from exc


def _authentication_required() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error_code": "authentication_required",
            "message": "authentication is required",
            "details": {},
            "retryable": False,
        },
    )


def _invalid_auth_token() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error_code": "invalid_auth_token",
            "message": "authentication token is invalid",
            "details": {},
            "retryable": False,
        },
    )


def _auth_provider_unavailable(settings: ApiSettings) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error_code": "auth_provider_not_configured",
            "message": "configured auth provider is unavailable",
            "details": {"auth_mode": settings.auth_mode},
            "retryable": False,
        },
    )
