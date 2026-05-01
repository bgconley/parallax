from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient, PyJWKClientError

from . import app_check, firebase_auth
from .domain.identity import (
    FirebasePrincipal,
    IdentityConflictError,
    IdentityDeletedError,
    IdentityNotAllowedError,
    IdentityProvisioningPolicy,
    read_line_set,
)
from .settings import ApiSettings, get_settings

_MIN_HS256_SECRET_BYTES = 32


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    provider: str | None = None
    provider_subject: str | None = None
    app_check_app_id: str | None = None


def get_auth_context(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_parallax_user_id: Annotated[str | None, Header()] = None,
    x_firebase_appcheck: Annotated[str | None, Header()] = None,
) -> AuthContext:
    app_check_app_id = app_check.verify_app_check_header(settings, x_firebase_appcheck)
    request.state.app_check_app_id = app_check_app_id
    if settings.auth_mode == "dev_header":
        return _auth_from_development_header(settings, x_parallax_user_id)
    if settings.auth_mode == "external_bearer":
        return _auth_from_bearer_token(settings, authorization)
    if settings.auth_mode == "firebase":
        return _auth_from_firebase_token(request, settings, authorization, app_check_app_id)
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
        return AuthContext(user_id=UUID(x_parallax_user_id), provider="dev_header")
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

    return AuthContext(
        user_id=_user_id_from_claims(claims, settings.auth_jwt_user_id_claim),
        provider="external_bearer",
    )


def _auth_from_firebase_token(
    request: Request,
    settings: ApiSettings,
    authorization: str | None,
    app_check_app_id: str | None,
) -> AuthContext:
    token = _extract_bearer_token(authorization)
    principal = firebase_auth.verify_firebase_id_token_sync(token, settings)
    policy = _identity_policy(settings)
    try:
        with request.app.state.uow_factory() as uow:
            user_id = uow.identities.resolve_or_create_external_identity(principal, policy)
    except IdentityNotAllowedError as exc:
        raise _auth_forbidden("auth_not_allowed", "authenticated identity is not allowed") from exc
    except IdentityDeletedError as exc:
        raise _auth_forbidden(
            "auth_identity_deleted",
            "authenticated identity is no longer active",
        ) from exc
    except IdentityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "auth_identity_conflict",
                "message": "authenticated identity conflicts with an existing account",
                "details": {},
                "retryable": False,
            },
        ) from exc
    return AuthContext(
        user_id=user_id,
        provider=principal.provider,
        provider_subject=_safe_provider_subject(principal),
        app_check_app_id=app_check_app_id,
    )


def _identity_policy(settings: ApiSettings) -> IdentityProvisioningPolicy:
    allowed_domains = frozenset(domain.casefold() for domain in settings.auth_allowed_email_domains)
    allowed_emails = read_line_set(settings.auth_allowed_emails_file, casefold=True)
    allowed_uids = read_line_set(settings.auth_allowed_firebase_uids_file, casefold=False)
    return IdentityProvisioningPolicy(
        auto_provision=settings.auth_auto_provision,
        invite_required=settings.auth_invite_required,
        allowed_email_domains=allowed_domains,
        allowed_emails=allowed_emails,
        allowed_firebase_uids=allowed_uids,
        email_conflict_policy=settings.auth_email_conflict_policy,
        tombstone_secret=settings.auth_identity_tombstone_secret,
    )


def _safe_provider_subject(principal: FirebasePrincipal) -> str:
    return f"{principal.issuer}#firebase_uid"


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
        raise _invalid_auth_scheme()
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
            "error_code": "auth_missing",
            "message": "authentication is required",
            "details": {},
            "retryable": False,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def _invalid_auth_scheme() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error_code": "auth_invalid_scheme",
            "message": "authorization header must use bearer authentication",
            "details": {},
            "retryable": False,
        },
        headers={"WWW-Authenticate": "Bearer"},
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


def _auth_forbidden(error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error_code": error_code,
            "message": message,
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
