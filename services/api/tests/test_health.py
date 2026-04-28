from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.services import health
from parallax_api.services.health import HealthReport
from parallax_db.runner import phase0_schema_smoke_checks


def test_runtime_readiness_uses_current_schema_smoke_checks() -> None:
    assert health.current_schema_smoke_checks is not phase0_schema_smoke_checks


class HealthyChecker:
    def check(self, *, readiness: bool = False) -> HealthReport:
        return HealthReport(
            status="healthy",
            checks={
                "api": "ok",
                "postgres": "ok",
                "redis": "ok",
                "temporal": "ok",
                "object_storage": "ok",
            },
            metadata={
                "app_version": "0.1.0",
                "api_contract_version": "1.3.0",
                "environment": "development",
            },
        )


class UnhealthyChecker:
    def check(self, *, readiness: bool = False) -> HealthReport:
        return HealthReport(
            status="unhealthy",
            checks={
                "api": "ok",
                "postgres": "error",
                "redis": "ok",
                "temporal": "ok",
                "object_storage": "ok",
            },
            metadata={
                "app_version": "0.1.0",
                "api_contract_version": "1.3.0",
                "environment": "development",
            },
        )


class RecordingChecker:
    def __init__(self) -> None:
        self.readiness_values: list[bool] = []

    def check(self, *, readiness: bool = False) -> HealthReport:
        self.readiness_values.append(readiness)
        return HealthReport(
            status="healthy",
            checks={"api": "ok", "postgres": "ok", "migration_state": "ok"},
            metadata={
                "app_version": "0.1.0",
                "api_contract_version": "1.3.0",
                "environment": "development",
            },
        )


def test_health_endpoint_reports_runtime_dependencies() -> None:
    client = TestClient(create_app(health_checker=HealthyChecker()))

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "parallax-api",
        "status": "healthy",
        "checks": {
            "api": "ok",
            "postgres": "ok",
            "redis": "ok",
            "temporal": "ok",
            "object_storage": "ok",
        },
        "metadata": {
            "app_version": "0.1.0",
            "api_contract_version": "1.3.0",
            "environment": "development",
        },
    }


def test_health_endpoint_returns_503_when_runtime_dependency_is_unhealthy() -> None:
    client = TestClient(create_app(health_checker=UnhealthyChecker()))

    response = client.get("/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["postgres"] == "error"


def test_readiness_uses_runtime_dependency_checks() -> None:
    client = TestClient(create_app(health_checker=UnhealthyChecker()))

    response = client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["postgres"] == "error"


def test_readiness_requests_migration_aware_check() -> None:
    checker = RecordingChecker()
    client = TestClient(create_app(health_checker=checker))

    response = client.get("/v1/ready")

    assert response.status_code == 200
    assert checker.readiness_values == [True]


def test_liveness_does_not_depend_on_downstream_services() -> None:
    client = TestClient(create_app(health_checker=UnhealthyChecker()))

    response = client.get("/v1/live")

    assert response.status_code == 200
    assert response.json() == {"service": "parallax-api", "status": "live"}


def test_version_endpoint_reports_contract_and_app_version() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/version")

    assert response.status_code == 200
    assert response.json()["api_contract_version"] == "1.3.0"
    assert response.json()["app_version"] == "0.1.0"
