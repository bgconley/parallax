from __future__ import annotations

import json
import os
import threading
from typing import Any

from fastapi import HTTPException

from .domain.identity import FirebasePrincipal
from .settings import ApiSettings

_APP_LOCK = threading.Lock()
_APP_CACHE: dict[str, object] = {}


def verify_firebase_id_token_sync(token: str, settings: ApiSettings) -> FirebasePrincipal:
    try:
        auth_module = _firebase_auth_module()
        decoded = auth_module.verify_id_token(
            token,
            app=_firebase_app(settings),
            check_revoked=settings.firebase_check_revoked,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _firebase_auth_exception(exc) from exc
    if not isinstance(decoded, dict):
        raise _auth_error("auth_invalid")
    principal = FirebasePrincipal.from_decoded(decoded)
    _validate_firebase_principal(principal, decoded, settings)
    return principal


def _validate_firebase_principal(
    principal: FirebasePrincipal,
    decoded: dict[str, object],
    settings: ApiSettings,
) -> None:
    expected_project = settings.firebase_project_id
    if expected_project is None:
        raise _auth_provider_unavailable()
    expected_issuer = f"https://securetoken.google.com/{expected_project}"
    if principal.issuer != expected_issuer or principal.firebase_project_id != expected_project:
        raise _auth_error("auth_invalid")
    raw_sub = decoded.get("sub")
    raw_uid = decoded.get("uid")
    if not raw_sub or not raw_uid or str(raw_sub) != str(raw_uid):
        raise _auth_error("auth_invalid")
    if principal.subject != str(raw_uid):
        raise _auth_error("auth_invalid")


def _firebase_app(settings: ApiSettings) -> object:
    if settings.firebase_project_id is None:
        raise _auth_provider_unavailable()
    cache_key = _firebase_app_cache_key(settings)
    cached = _APP_CACHE.get(cache_key)
    if cached is not None:
        return cached
    with _APP_LOCK:
        cached = _APP_CACHE.get(cache_key)
        if cached is not None:
            return cached
        firebase_admin = _firebase_admin_module()
        app_name = f"parallax-{settings.firebase_project_id}-{_cache_key_fingerprint(cache_key)}"
        try:
            credential = _firebase_credential(settings)
            options = {"projectId": settings.firebase_project_id}
            app = firebase_admin.initialize_app(credential, options=options, name=app_name)
        except (json.JSONDecodeError, OSError) as exc:
            raise _auth_provider_unavailable() from exc
        except ValueError as exc:
            if "already exists" not in str(exc):
                raise _auth_provider_unavailable() from exc
            try:
                app = firebase_admin.get_app(app_name)
            except Exception as exc:
                raise _auth_provider_unavailable() from exc
        _APP_CACHE[cache_key] = app
        return app


def _firebase_app_cache_key(settings: ApiSettings) -> str:
    credential_source = "adc"
    if settings.firebase_credentials_file:
        credential_source = f"file:{settings.firebase_credentials_file}"
    elif settings.firebase_credentials_json:
        digest = _cache_key_fingerprint(settings.firebase_credentials_json)
        credential_source = f"json:{digest}"
    emulator_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST", "")
    return "\x1f".join((settings.firebase_project_id or "", credential_source, emulator_host))


def _cache_key_fingerprint(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _firebase_credential(settings: ApiSettings) -> object | None:
    credentials_module = _firebase_credentials_module()
    if settings.firebase_credentials_file:
        return credentials_module.Certificate(settings.firebase_credentials_file)
    if settings.firebase_credentials_json:
        return credentials_module.Certificate(json.loads(settings.firebase_credentials_json))
    return None


def _firebase_admin_module() -> Any:
    try:
        import firebase_admin  # type: ignore[import-untyped]
    except ImportError as exc:
        raise _auth_provider_unavailable() from exc
    return firebase_admin


def _firebase_auth_module() -> Any:
    try:
        from firebase_admin import auth  # type: ignore[import-untyped]
    except ImportError as exc:
        raise _auth_provider_unavailable() from exc
    return auth


def _firebase_credentials_module() -> Any:
    try:
        from firebase_admin import credentials  # type: ignore[import-untyped]
    except ImportError as exc:
        raise _auth_provider_unavailable() from exc
    return credentials


def _firebase_auth_exception(exc: Exception) -> HTTPException:
    name = exc.__class__.__name__
    if name == "ExpiredIdTokenError":
        return _auth_error("auth_token_expired")
    if name == "RevokedIdTokenError":
        return _auth_error("auth_token_revoked")
    if name == "UserDisabledError":
        return _auth_error("auth_user_disabled", status_code=403)
    if name in {"CertificateFetchError", "TransportError", "RefreshError"}:
        return _auth_provider_unavailable(retryable=True)
    return _auth_error("auth_invalid")


def _auth_error(error_code: str, *, status_code: int = 401) -> HTTPException:
    message = "authentication failed"
    if error_code == "auth_invalid":
        message = "authentication is invalid"
    elif error_code.endswith("_expired"):
        message = "authentication has expired"
    elif error_code.endswith("_revoked"):
        message = "authentication has been revoked"
    elif error_code == "auth_user_disabled":
        message = "authenticated user is disabled"
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "details": {},
            "retryable": False,
        },
    )


def _auth_provider_unavailable(*, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error_code": "auth_provider_not_configured",
            "message": "configured auth provider is unavailable",
            "details": {"auth_mode": "firebase"},
            "retryable": retryable,
        },
    )
