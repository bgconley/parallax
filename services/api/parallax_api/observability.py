from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .settings import ApiSettings

_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str, str], int] = defaultdict(int)
        self._latency_buckets: dict[tuple[str, str, str, float], int] = defaultdict(int)
        self._latency_count: dict[tuple[str, str, str], int] = defaultdict(int)
        self._latency_sum: dict[tuple[str, str, str], float] = defaultdict(float)

    def record_request(self, method: str, route: str, status_code: int, elapsed: float) -> None:
        status_class = f"{status_code // 100}xx"
        key = (method, route, status_class)
        with self._lock:
            self._requests[key] += 1
            self._latency_count[key] += 1
            self._latency_sum[key] += elapsed
            for bucket in _LATENCY_BUCKETS:
                if elapsed <= bucket:
                    self._latency_buckets[(*key, bucket)] += 1
            self._latency_buckets[(*key, float("inf"))] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP parallax_api_requests_total Total API requests by route and status class.",
            "# TYPE parallax_api_requests_total counter",
        ]
        with self._lock:
            for (method, route, status_class), value in sorted(self._requests.items()):
                lines.append(
                    "parallax_api_requests_total"
                    f'{{method="{method}",route="{route}",status_class="{status_class}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP parallax_api_request_latency_seconds API request latency histogram.",
                    "# TYPE parallax_api_request_latency_seconds histogram",
                ]
            )
            for (method, route, status_class), count in sorted(self._latency_count.items()):
                for bucket in (*_LATENCY_BUCKETS, float("inf")):
                    bucket_count = self._latency_buckets[(method, route, status_class, bucket)]
                    le = "+Inf" if bucket == float("inf") else str(bucket)
                    lines.append(
                        "parallax_api_request_latency_seconds_bucket"
                        f'{{method="{method}",route="{route}",status_class="{status_class}",'
                        f'le="{le}"}} {bucket_count}'
                    )
                latency_sum = self._latency_sum[(method, route, status_class)]
                labels = f'{{method="{method}",route="{route}",status_class="{status_class}"}}'
                lines.append(f"parallax_api_request_latency_seconds_count{labels} {count}")
                lines.append(f"parallax_api_request_latency_seconds_sum{labels} {latency_sum:.9f}")
        return "\n".join(lines) + "\n"


def install_observability(app: FastAPI, settings: ApiSettings) -> None:
    if not settings.metrics_enabled:
        return
    registry = MetricsRegistry()
    app.state.metrics_registry = registry

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            registry.record_request(
                request.method,
                _route_label(request),
                status_code,
                time.perf_counter() - started,
            )

    @app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
    def metrics(
        x_parallax_metrics_token: str | None = Header(default=None),
    ) -> PlainTextResponse:
        if settings.metrics_token and x_parallax_metrics_token != settings.metrics_token:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "metrics_forbidden",
                    "message": "metrics token is invalid",
                    "details": {},
                    "retryable": False,
                },
            )
        return PlainTextResponse(registry.render_prometheus() + _runtime_metrics(settings))


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return "unmatched"


def _runtime_metrics(settings: ApiSettings) -> str:
    try:
        return _workflow_metrics(settings)
    except Exception:
        return (
            "# HELP parallax_metrics_dependency_errors_total Metrics dependency read errors.\n"
            "# TYPE parallax_metrics_dependency_errors_total counter\n"
            'parallax_metrics_dependency_errors_total{dependency="postgres"} 1\n'
        )


def _workflow_metrics(settings: ApiSettings) -> str:
    import psycopg

    with psycopg.connect(settings.database_url, connect_timeout=1) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select workflow_type, status::text as status, count(*) as run_count,
                  coalesce(sum(attempts), 0) as attempts
                from workflow_run
                group by workflow_type, status
                order by workflow_type, status
                """
            )
            rows = cursor.fetchall()
            cursor.execute(
                """
                select count(*)
                from workflow_run
                where status = 'queued' and next_run_at <= now()
                """
            )
            due_row = cursor.fetchone()
    due_count = int(due_row[0]) if due_row else 0
    lines = [
        "# HELP parallax_workflow_runs Workflow runs by type and status.",
        "# TYPE parallax_workflow_runs gauge",
    ]
    for workflow_type, status, run_count, attempts in rows:
        labels = f'workflow_type="{_label(workflow_type)}",status="{_label(status)}"'
        lines.append(f"parallax_workflow_runs{{{labels}}} {int(run_count)}")
        lines.append(f"parallax_workflow_attempts_total{{{labels}}} {int(attempts)}")
    lines.extend(
        [
            "# HELP parallax_workflow_due_queued Queued workflows due to run now.",
            "# TYPE parallax_workflow_due_queued gauge",
            f"parallax_workflow_due_queued {due_count}",
        ]
    )
    return "\n".join(lines) + "\n"


def _label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
