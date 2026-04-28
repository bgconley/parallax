from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.settings import ApiSettings


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


def encode_hs256_jwt(claims: dict[str, object], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            base64url_json(header),
            base64url_json(claims),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256)
    return f"{signing_input}.{base64url(signature.digest())}"


def base64url_json(value: Mapping[str, object]) -> str:
    return base64url(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def test_missing_auth_header_is_rejected_with_structured_error() -> None:
    client = TestClient(make_app())

    response = client.post("/v1/activities", json=activity_payload())

    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_required"
    assert response.json()["retryable"] is False


def test_default_auth_mode_is_external_bearer(monkeypatch) -> None:
    monkeypatch.delenv("PARALLAX_AUTH_MODE", raising=False)

    assert ApiSettings().auth_mode == "external_bearer"


def test_invalid_auth_header_is_rejected_without_internal_error() -> None:
    client = TestClient(make_app(), raise_server_exceptions=False)

    response = client.get("/v1/activities", headers={"X-Parallax-User-Id": "not-a-uuid"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_auth_context"
    assert "request_id" in response.json()


def test_dev_header_auth_is_rejected_outside_development(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    client = TestClient(make_app())

    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": "00000000-0000-0000-0000-0000000000f1"},
        json=activity_payload(),
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == "auth_provider_not_configured"


def test_external_bearer_auth_accepts_signed_jwt_in_production(monkeypatch) -> None:
    user_id = "00000000-0000-0000-0000-0000000000f2"
    secret = "private-alpha-test-secret-32-bytes-min"
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", secret)
    token = encode_hs256_jwt({"sub": user_id, "exp": int(time.time()) + 300}, secret)
    client = TestClient(make_app())

    response = client.post(
        "/v1/activities",
        headers={"Authorization": f"Bearer {token}"},
        json=activity_payload(),
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == user_id


def test_external_bearer_auth_rejects_expired_jwt(monkeypatch) -> None:
    secret = "private-alpha-test-secret-32-bytes-min"
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", secret)
    token = encode_hs256_jwt(
        {"sub": "00000000-0000-0000-0000-0000000000f3", "exp": int(time.time()) - 60},
        secret,
    )
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "auth_token_expired"


def test_external_bearer_auth_rejects_invalid_signature_without_echoing_token(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", "expected-secret-32-bytes-minimum")
    token = encode_hs256_jwt(
        {"sub": "00000000-0000-0000-0000-0000000000f4", "exp": int(time.time()) + 300},
        "wrong-secret-32-bytes-minimum!!",
    )
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "invalid_auth_token"
    assert token not in json.dumps(body)


def test_external_bearer_auth_verifies_configured_issuer_and_audience(monkeypatch) -> None:
    user_id = "00000000-0000-0000-0000-0000000000f5"
    secret = "issuer-audience-test-secret-32-bytes"
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("PARALLAX_AUTH_JWT_ISSUER", "https://auth.parallax.test")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_AUDIENCE", "parallax-api")
    token = encode_hs256_jwt(
        {
            "sub": user_id,
            "exp": int(time.time()) + 300,
            "iss": "https://auth.parallax.test",
            "aud": "parallax-api",
        },
        secret,
    )
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_external_bearer_auth_rejects_wrong_audience(monkeypatch) -> None:
    secret = "issuer-audience-test-secret-32-bytes"
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("PARALLAX_AUTH_JWT_AUDIENCE", "parallax-api")
    token = encode_hs256_jwt(
        {
            "sub": "00000000-0000-0000-0000-0000000000f6",
            "exp": int(time.time()) + 300,
            "aud": "other-api",
        },
        secret,
    )
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_auth_token"


def test_external_bearer_auth_requires_secret_configuration(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.delenv("PARALLAX_AUTH_JWT_SECRET", raising=False)
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": "Bearer token"})

    assert response.status_code == 503
    assert response.json()["error_code"] == "auth_provider_not_configured"


def test_external_bearer_auth_rejects_short_hs256_secret(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_SECRET", "too-short")
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": "Bearer token"})

    assert response.status_code == 503
    assert response.json()["error_code"] == "auth_provider_not_configured"


def test_external_bearer_auth_accepts_rs256_jwks_token(monkeypatch) -> None:
    user_id = "00000000-0000-0000-0000-0000000000f7"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "test-key-1", "alg": "RS256", "use": "sig"})

    def fetch_data(_client: object) -> dict[str, object]:
        return {"keys": [jwk]}

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch_data)
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWKS_URL", "https://auth.parallax.test/.well-known/jwks.json")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_ISSUER", "https://auth.parallax.test")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_AUDIENCE", "parallax-api")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_ALGORITHM", "RS256")
    token = jwt.encode(
        {
            "sub": user_id,
            "exp": int(time.time()) + 300,
            "iss": "https://auth.parallax.test",
            "aud": "parallax-api",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_external_bearer_auth_requires_jwks_or_secret_in_production(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "external_bearer")
    monkeypatch.setenv("PARALLAX_AUTH_JWT_ALGORITHM", "RS256")
    monkeypatch.delenv("PARALLAX_AUTH_JWKS_URL", raising=False)
    monkeypatch.delenv("PARALLAX_AUTH_JWT_SECRET", raising=False)
    client = TestClient(make_app())

    response = client.get("/v1/activities", headers={"Authorization": "Bearer token"})

    assert response.status_code == 503
    assert response.json()["error_code"] == "auth_provider_not_configured"
