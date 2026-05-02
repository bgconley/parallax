from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from parallax_api import app_check
from parallax_api.domain.identity import read_line_set
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_api.settings import ApiSettings
from parallax_worker.workflow_worker import WorkflowWorker
from pydantic import ValidationError


def _mutation(label: str) -> dict[str, object]:
    return {
        "client_mutation_id": f"{label}-mutation",
        "client_device_id": "firebase-auth-test",
        "client_timestamp": "2026-04-30T12:00:00Z",
        "idempotency_key": f"firebase-auth-test:{label}",
        "client_sequence": 1,
    }


def _activity_payload(label: str) -> dict[str, object]:
    return {
        "mutation": _mutation(label),
        "display_name": f"Firebase {label}",
    }


def _configure_firebase_env(
    monkeypatch: Any,
    *,
    auto_provision: bool = True,
    invite_required: bool = False,
) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "firebase")
    monkeypatch.setenv("PARALLAX_FIREBASE_PROJECT_ID", "parallax-test")
    monkeypatch.setenv("PARALLAX_FIREBASE_PROJECT_NUMBER", "123456789")
    monkeypatch.setenv("PARALLAX_AUTH_AUTO_PROVISION", "true" if auto_provision else "false")
    monkeypatch.setenv("PARALLAX_AUTH_INVITE_REQUIRED", "true" if invite_required else "false")
    monkeypatch.setenv("PARALLAX_AUTH_IDENTITY_TOMBSTONE_SECRET", "test-tombstone-secret")
    monkeypatch.setenv("PARALLAX_METRICS_TOKEN", "metrics-token")


def _install_firebase_principals(
    monkeypatch: Any,
    principals: dict[str, dict[str, object]],
) -> None:
    from parallax_api import firebase_auth
    from parallax_api.domain.identity import FirebasePrincipal

    def fake_verify(token: str, _settings: object) -> FirebasePrincipal:
        payload = principals[token]
        return FirebasePrincipal(
            provider="firebase_auth",
            issuer="https://securetoken.google.com/parallax-test",
            subject=str(payload["uid"]),
            firebase_project_id="parallax-test",
            firebase_tenant_id=str(payload.get("tenant") or ""),
            sign_in_provider=str(payload.get("sign_in_provider") or "password"),
            email=str(payload["email"]) if payload.get("email") else None,
            email_verified=bool(payload.get("email_verified", False)),
            display_name=str(payload["display_name"]) if payload.get("display_name") else None,
            photo_url=str(payload["photo_url"]) if payload.get("photo_url") else None,
            auth_time=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        )

    monkeypatch.setattr(firebase_auth, "verify_firebase_id_token_sync", fake_verify)


def _client_and_store() -> tuple[TestClient, InMemoryStore]:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    return client, store


def test_firebase_uid_maps_to_one_parallax_user_across_linked_sign_in_providers(
    monkeypatch: Any,
) -> None:
    _configure_firebase_env(monkeypatch)
    _install_firebase_principals(
        monkeypatch,
        {
            "apple-token": {
                "uid": "firebase-linked-uid",
                "sign_in_provider": "apple.com",
                "email": "linked@example.com",
                "email_verified": True,
                "display_name": "Linked User",
            },
            "google-token": {
                "uid": "firebase-linked-uid",
                "sign_in_provider": "google.com",
                "email": "linked@example.com",
                "email_verified": True,
                "display_name": "Linked User",
            },
        },
    )
    client, store = _client_and_store()

    created = client.post(
        "/v1/activities",
        headers={
            "Authorization": "Bearer apple-token",
            "X-Parallax-User-Id": "00000000-0000-0000-0000-000000000999",
        },
        json=_activity_payload("linked"),
    )
    listed = client.get("/v1/activities", headers={"Authorization": "Bearer google-token"})

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == created.json()["id"]
    assert created.json()["user_id"] == listed.json()[0]["user_id"]
    assert len(store.external_identities) == 1
    identity = next(iter(store.external_identities.values()))
    assert identity.provider == "firebase_auth"
    assert identity.sign_in_provider == "google.com"


def test_private_alpha_first_login_requires_allowed_firebase_uid(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    allowed_file = tmp_path / "allowed-uids.txt"
    allowed_file.write_text("allowed-firebase-uid\n")
    _configure_firebase_env(monkeypatch, auto_provision=False, invite_required=True)
    monkeypatch.setenv("PARALLAX_AUTH_ALLOWED_FIREBASE_UIDS_FILE", str(allowed_file))
    _install_firebase_principals(
        monkeypatch,
        {
            "allowed-token": {
                "uid": "allowed-firebase-uid",
                "sign_in_provider": "apple.com",
                "email": "allowed@example.com",
                "email_verified": True,
            },
            "blocked-token": {
                "uid": "blocked-firebase-uid",
                "sign_in_provider": "apple.com",
                "email": "blocked@example.com",
                "email_verified": True,
            },
        },
    )
    client, _store = _client_and_store()

    blocked = client.get("/v1/activities", headers={"Authorization": "Bearer blocked-token"})
    allowed = client.get("/v1/activities", headers={"Authorization": "Bearer allowed-token"})

    assert blocked.status_code == 403
    assert blocked.json()["error_code"] == "auth_not_allowed"
    assert allowed.status_code == 200


def test_verified_email_conflict_returns_409_without_creating_second_identity(
    monkeypatch: Any,
) -> None:
    _configure_firebase_env(monkeypatch)
    _install_firebase_principals(
        monkeypatch,
        {
            "first-token": {
                "uid": "firebase-uid-one",
                "sign_in_provider": "apple.com",
                "email": "conflict@example.com",
                "email_verified": True,
            },
            "second-token": {
                "uid": "firebase-uid-two",
                "sign_in_provider": "google.com",
                "email": "conflict@example.com",
                "email_verified": True,
            },
        },
    )
    client, store = _client_and_store()

    first = client.get("/v1/activities", headers={"Authorization": "Bearer first-token"})
    second = client.get("/v1/activities", headers={"Authorization": "Bearer second-token"})

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error_code"] == "auth_identity_conflict"
    assert len(store.external_identities) == 1


def test_account_delete_tombstone_blocks_silent_reprovisioning(monkeypatch: Any) -> None:
    _configure_firebase_env(monkeypatch)
    _install_firebase_principals(
        monkeypatch,
        {
            "account-token": {
                "uid": "firebase-delete-uid",
                "sign_in_provider": "apple.com",
                "email": "deleted@example.com",
                "email_verified": True,
            },
        },
    )
    client, store = _client_and_store()
    created = client.post(
        "/v1/activities",
        headers={"Authorization": "Bearer account-token"},
        json=_activity_payload("deleted-account"),
    )
    delete_response = client.post(
        "/v1/privacy/delete",
        headers={"Authorization": "Bearer account-token"},
        json={
            "mutation": _mutation("delete-account"),
            "delete_scope": "account",
            "confirm": True,
        },
    )

    assert created.status_code == 201
    assert delete_response.status_code == 202
    assert WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once() == 1

    relogin = client.get("/v1/activities", headers={"Authorization": "Bearer account-token"})

    assert relogin.status_code == 403
    assert relogin.json()["error_code"] == "auth_identity_deleted"


def test_app_check_enforce_rejects_missing_or_unallowed_app_id(monkeypatch: Any) -> None:
    _configure_firebase_env(monkeypatch)
    monkeypatch.setenv("PARALLAX_FIREBASE_APP_CHECK_MODE", "enforce")
    monkeypatch.setenv("PARALLAX_FIREBASE_APP_CHECK_ALLOWED_APP_IDS", '["ios-app-1"]')
    _install_firebase_principals(
        monkeypatch,
        {
            "token": {
                "uid": "firebase-app-check-uid",
                "sign_in_provider": "apple.com",
                "email": "app-check@example.com",
                "email_verified": True,
            },
        },
    )
    from parallax_api import app_check

    def fake_app_check(token: str, _settings: object) -> str:
        return {"bad-app-check": "ios-app-2", "good-app-check": "ios-app-1"}[token]

    monkeypatch.setattr(app_check, "verify_app_check_token_sync", fake_app_check)
    client, _store = _client_and_store()

    missing = client.get("/v1/activities", headers={"Authorization": "Bearer token"})
    wrong_app = client.get(
        "/v1/activities",
        headers={
            "Authorization": "Bearer token",
            "X-Firebase-AppCheck": "bad-app-check",
        },
    )
    good_app = client.get(
        "/v1/activities",
        headers={
            "Authorization": "Bearer token",
            "X-Firebase-AppCheck": "good-app-check",
        },
    )
    live = client.get("/v1/live")

    assert missing.status_code == 403
    assert missing.json()["error_code"] == "app_check_missing"
    assert wrong_app.status_code == 403
    assert wrong_app.json()["error_code"] == "app_check_app_not_allowed"
    assert good_app.status_code == 200
    assert live.status_code == 200


def test_app_check_monitor_allows_missing_token(monkeypatch: Any) -> None:
    _configure_firebase_env(monkeypatch)
    monkeypatch.setenv("PARALLAX_FIREBASE_APP_CHECK_MODE", "monitor")
    _install_firebase_principals(
        monkeypatch,
        {
            "token": {
                "uid": "firebase-monitor-uid",
                "sign_in_provider": "apple.com",
                "email": "monitor@example.com",
                "email_verified": True,
            },
        },
    )
    client, _store = _client_and_store()

    response = client.get("/v1/activities", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200


def test_production_refuses_dev_header_auth_mode(monkeypatch: Any) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "dev_header")

    def try_create_app() -> object:
        return create_app(uow_factory=InMemoryUnitOfWorkFactory())

    try:
        try_create_app()
    except RuntimeError as exc:
        assert "dev_header" in str(exc)
    else:
        raise AssertionError("expected production dev_header startup guard")


def test_production_refuses_firebase_auth_emulator(monkeypatch: Any) -> None:
    _configure_firebase_env(monkeypatch)
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")

    try:
        create_app(uow_factory=InMemoryUnitOfWorkFactory())
    except RuntimeError as exc:
        assert "FIREBASE_AUTH_EMULATOR_HOST" in str(exc)
    else:
        raise AssertionError("expected production Firebase emulator startup guard")


def test_email_conflict_policy_is_reject_only(monkeypatch: Any) -> None:
    monkeypatch.setenv("PARALLAX_AUTH_EMAIL_CONFLICT_POLICY", "ignore_email")

    with pytest.raises(ValidationError):
        ApiSettings()


def test_firebase_provider_configuration_errors_return_service_unavailable() -> None:
    from parallax_api import firebase_auth

    firebase_auth._APP_CACHE.clear()
    settings = ApiSettings(
        auth_mode="firebase",
        firebase_project_id="parallax-test",
        firebase_credentials_json="{not-json",
    )

    with pytest.raises(HTTPException) as exc_info:
        firebase_auth.verify_firebase_id_token_sync("not-a-real-token", settings)

    assert exc_info.value.status_code == 503
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["error_code"] == "auth_provider_not_configured"


def test_file_backed_allowlists_refresh_when_file_changes(tmp_path: Path) -> None:
    allowlist = tmp_path / "allowed-uids.txt"
    allowlist.write_text("first-firebase-uid\n")
    assert read_line_set(str(allowlist), casefold=False) == frozenset({"first-firebase-uid"})

    allowlist.write_text("second-firebase-uid\n")

    assert read_line_set(str(allowlist), casefold=False) == frozenset({"second-firebase-uid"})


def test_app_check_monitor_mode_emits_sanitized_warning_for_missing_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = ApiSettings(firebase_app_check_mode="monitor")

    with caplog.at_level(logging.WARNING, logger="parallax_api.app_check"):
        assert app_check.verify_app_check_header(settings, None) is None

    assert "app_check_missing" in caplog.text
    assert "X-Firebase-AppCheck" not in caplog.text
