from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory


def make_app() -> FastAPI:
    return create_app(uow_factory=InMemoryUnitOfWorkFactory())


def test_validation_errors_do_not_echo_raw_sensitive_input() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": "00000000-0000-0000-0000-0000000000e1"},
        json={
            "mutation": {
                "client_mutation_id": "leak-probe",
                "client_device_id": "leak-probe-device",
                "client_timestamp": "2026-04-27T12:00:00Z",
                "idempotency_key": "leak-probe-device:leak-probe",
            },
            "display_name": "Leak probe",
            "raw_note": "PRIVATE_RAW_NOTE_SHOULD_NOT_ECHO",
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "validation_error"
    assert "PRIVATE_RAW_NOTE_SHOULD_NOT_ECHO" not in response.text
    errors = response.json()["details"]["errors"]
    assert errors == [
        {
            "type": "extra_forbidden",
            "loc": ["body", "raw_note"],
            "msg": "Extra inputs are not permitted",
        }
    ]
