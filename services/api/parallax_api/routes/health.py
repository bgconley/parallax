from __future__ import annotations

from fastapi import APIRouter

from ..settings import get_settings

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
def get_health() -> dict[str, object]:
    return {
        "service": "parallax-api",
        "status": "healthy",
        "checks": {"api": "ok"},
    }


@router.get("/version")
def get_version() -> dict[str, str]:
    settings = get_settings()
    return {
        "app_version": settings.api_version,
        "api_contract_version": settings.contract_version,
    }
