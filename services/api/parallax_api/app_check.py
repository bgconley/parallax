from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from .firebase_auth import _firebase_app
from .settings import ApiSettings

_LOGGER = logging.getLogger(__name__)


def verify_app_check_header(
    settings: ApiSettings,
    token: str | None,
) -> str | None:
    mode = settings.firebase_app_check_mode
    if mode == "off":
        return None
    if not token:
        if mode == "monitor":
            _log_monitor_event("app_check_missing")
            return None
        raise _app_check_error("app_check_missing")
    try:
        app_id = verify_app_check_token_sync(token, settings)
    except HTTPException:
        if mode == "monitor":
            _log_monitor_event("app_check_invalid")
            return None
        raise
    allowed = set(settings.firebase_app_check_allowed_app_ids)
    if allowed and app_id not in allowed:
        if mode == "monitor":
            _log_monitor_event("app_check_app_not_allowed")
            return None
        raise _app_check_error("app_check_app_not_allowed")
    return app_id


def verify_app_check_token_sync(token: str, settings: ApiSettings) -> str:
    try:
        app_check = _firebase_app_check_module()
        decoded = app_check.verify_token(token, app=_firebase_app(settings))
    except Exception as exc:
        raise _app_check_error("app_check_invalid") from exc
    if not isinstance(decoded, dict):
        raise _app_check_error("app_check_invalid")
    app_id = decoded.get("app_id") or decoded.get("sub")
    if not isinstance(app_id, str) or not app_id:
        raise _app_check_error("app_check_invalid")
    return app_id


def _firebase_app_check_module() -> Any:
    try:
        from firebase_admin import app_check  # type: ignore[import-untyped]
    except ImportError as exc:
        raise _app_check_error("app_check_invalid") from exc
    return app_check


def _app_check_error(error_code: str) -> HTTPException:
    messages = {
        "app_check_missing": "app attestation token is required",
        "app_check_invalid": "app attestation token is invalid",
        "app_check_app_not_allowed": "app attestation token is not from an allowed app",
    }
    return HTTPException(
        status_code=403,
        detail={
            "error_code": error_code,
            "message": messages[error_code],
            "details": {},
            "retryable": False,
        },
    )


def _log_monitor_event(error_code: str) -> None:
    _LOGGER.warning(
        "firebase_app_check_monitor %s",
        error_code,
        extra={"app_check_result": error_code},
    )
