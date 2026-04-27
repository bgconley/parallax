from __future__ import annotations

from fastapi import FastAPI

from .errors import install_error_handlers
from .repositories.postgres_unit_of_work import PostgresUnitOfWorkFactory
from .repositories.unit_of_work import UnitOfWorkFactory
from .routes.activities import router as activities_router
from .routes.health import router as health_router
from .routes.sync import router as sync_router
from .routes.timing import router as timing_router
from .services.health import HealthChecker, RuntimeHealthChecker
from .settings import get_settings


def create_app(
    health_checker: HealthChecker | None = None,
    uow_factory: UnitOfWorkFactory | None = None,
) -> FastAPI:
    app = FastAPI(title="Parallax API", version="0.1.0")
    install_error_handlers(app)
    settings = get_settings()
    app.state.uow_factory = uow_factory or PostgresUnitOfWorkFactory(settings.database_url)
    app.state.health_checker = health_checker or RuntimeHealthChecker()
    app.include_router(health_router)
    app.include_router(activities_router)
    app.include_router(timing_router)
    app.include_router(sync_router)
    return app


app = create_app()
