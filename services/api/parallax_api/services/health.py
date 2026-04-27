from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..settings import ApiSettings, get_settings


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, str]


class HealthChecker(Protocol):
    def check(self) -> HealthReport: ...


class RuntimeHealthChecker:
    """Checks only Phase 0 runtime dependencies required by the canonical plan."""

    def __init__(self, settings: ApiSettings | None = None) -> None:
        self._settings = settings or get_settings()

    def check(self) -> HealthReport:
        checks = {
            "api": "ok",
            "postgres": self._check_postgres(),
            "redis": self._check_redis(),
        }
        status = "healthy" if all(value == "ok" for value in checks.values()) else "unhealthy"
        return HealthReport(status=status, checks=checks)

    def _check_postgres(self) -> str:
        import psycopg

        try:
            with psycopg.connect(self._settings.database_url, connect_timeout=2) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select 1")
                    cursor.fetchone()
            return "ok"
        except Exception:
            return "error"

    def _check_redis(self) -> str:
        from redis import Redis

        try:
            client = Redis.from_url(
                self._settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            return "ok" if client.ping() else "error"
        except Exception:
            return "error"
