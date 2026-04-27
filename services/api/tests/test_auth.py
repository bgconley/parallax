from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory


def make_app() -> FastAPI:
    return create_app(uow_factory=InMemoryUnitOfWorkFactory())


def activity_payload() -> dict[str, object]:
    return {
        "mutation": {
            "client_mutation_id": "auth-test-activity",
            "client_device_id": "auth-test",
            "client_timestamp": "2026-04-27T12:00:00Z",
            "idempotency_key": "auth-test:auth-test-activity",
            "client_sequence": 1,
        },
        "display_name": "Auth test activity",
    }


def test_missing_auth_header_is_rejected_with_structured_error() -> None:
    client = TestClient(make_app())

    response = client.post("/v1/activities", json=activity_payload())

    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_required"
    assert response.json()["retryable"] is False


def test_invalid_auth_header_is_rejected_without_internal_error() -> None:
    client = TestClient(make_app(), raise_server_exceptions=False)

    response = client.get("/v1/activities", headers={"X-Parallax-User-Id": "not-a-uuid"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_auth_context"
    assert "request_id" in response.json()
