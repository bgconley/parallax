from __future__ import annotations

from fastapi import FastAPI

from .repositories.memory import InMemoryStore
from .routes.activities import router as activities_router
from .routes.health import router as health_router
from .routes.timing import router as timing_router


def create_app() -> FastAPI:
    app = FastAPI(title="Parallax API", version="0.1.0")
    app.state.store = InMemoryStore()
    app.include_router(health_router)
    app.include_router(activities_router)
    app.include_router(timing_router)
    return app


app = create_app()
