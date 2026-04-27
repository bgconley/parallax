from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.services.health import HealthReport


class HealthyChecker:
    def check(self) -> HealthReport:
        return HealthReport(status="healthy", checks={"api": "ok", "postgres": "ok", "redis": "ok"})


class UnhealthyChecker:
    def check(self) -> HealthReport:
        return HealthReport(
            status="unhealthy",
            checks={"api": "ok", "postgres": "error", "redis": "ok"},
        )


def test_health_endpoint_reports_runtime_dependencies() -> None:
    client = TestClient(create_app(health_checker=HealthyChecker()))

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "parallax-api",
        "status": "healthy",
        "checks": {"api": "ok", "postgres": "ok", "redis": "ok"},
    }


def test_health_endpoint_returns_503_when_runtime_dependency_is_unhealthy() -> None:
    client = TestClient(create_app(health_checker=UnhealthyChecker()))

    response = client.get("/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["postgres"] == "error"


def test_version_endpoint_reports_contract_and_app_version() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/version")

    assert response.status_code == 200
    assert response.json()["api_contract_version"] == "1.3.0"
    assert response.json()["app_version"] == "0.1.0"
