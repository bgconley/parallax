from fastapi.testclient import TestClient
from parallax_api.main import create_app


def test_health_endpoint_reports_service_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "parallax-api",
        "status": "healthy",
        "checks": {"api": "ok"},
    }


def test_version_endpoint_reports_contract_and_app_version() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/version")

    assert response.status_code == 200
    assert response.json()["api_contract_version"] == "1.3.0"
    assert response.json()["app_version"] == "0.1.0"
