from __future__ import annotations

import socket
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection
from typing import Protocol
from urllib.parse import urlparse

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
            "temporal": self._check_temporal(),
            "object_storage": self._check_object_storage(),
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

    def _check_temporal(self) -> str:
        try:
            host, port_text = self._settings.temporal_address.rsplit(":", 1)
            with socket.create_connection((host, int(port_text)), timeout=2):
                return "ok"
        except Exception:
            return "error"

    def _check_object_storage(self) -> str:
        parsed = urlparse(self._settings.object_storage_endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "error"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        connection_type = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        path_prefix = parsed.path.rstrip("/")
        health_path = f"{path_prefix}/minio/health/live" if path_prefix else "/minio/health/live"
        connection = connection_type(parsed.hostname, port, timeout=2)
        try:
            connection.request("GET", health_path)
            response = connection.getresponse()
            response.read()
            return "ok" if 200 <= response.status < 300 else "error"
        except Exception:
            return "error"
        finally:
            connection.close()

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
