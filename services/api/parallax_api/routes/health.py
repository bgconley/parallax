from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..services.health import HealthChecker
from ..settings import get_settings

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
def get_health(request: Request) -> JSONResponse:
    checker: HealthChecker = request.app.state.health_checker
    report = checker.check()
    status_code = 200 if report.status == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={
        "service": "parallax-api",
            "status": report.status,
            "checks": report.checks,
        },
    )


@router.get("/version")
def get_version() -> dict[str, str]:
    settings = get_settings()
    return {
        "app_version": settings.api_version,
        "api_contract_version": settings.contract_version,
    }
