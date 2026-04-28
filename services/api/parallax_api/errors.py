from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .validation_errors import safe_validation_errors


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return _api_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            fallback_code=_status_error_code(exc.status_code),
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _api_error_response(
            status_code=400,
            detail={
                "error_code": "validation_error",
                "message": "request validation failed",
                "details": {"errors": safe_validation_errors(exc.errors())},
                "retryable": False,
            },
            fallback_code="validation_error",
            request=request,
        )


def _api_error_response(
    *,
    status_code: int,
    detail: object,
    fallback_code: str,
    request: Request,
) -> JSONResponse:
    if isinstance(detail, dict):
        error_code = str(detail.get("error_code", fallback_code))
        message = str(detail.get("message", _default_message(status_code)))
        details = detail.get("details", {})
        retryable = bool(detail.get("retryable", status_code >= 500))
        docs_ref = detail.get("docs_ref")
    else:
        error_code = fallback_code
        message = str(detail)
        details = {}
        retryable = status_code >= 500
        docs_ref = None

    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "retryable": retryable,
            "docs_ref": docs_ref,
        },
    )


def _status_error_code(status_code: int) -> str:
    if status_code == 404:
        return "not_found"
    if status_code == 400:
        return "bad_request"
    return "http_error"


def _default_message(status_code: int) -> str:
    if status_code == 404:
        return "resource not found"
    if status_code == 400:
        return "bad request"
    return "request failed"
