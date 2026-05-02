from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARALLAX_", env_file=".env", extra="ignore")

    env: str = "development"
    api_version: str = "0.1.0"
    contract_version: str = "1.3.0"
    database_url: str = "postgresql://parallax:parallax_dev_password@localhost:5432/parallax"
    redis_url: str = "redis://localhost:6379/0"
    temporal_address: str = "localhost:7233"
    object_storage_endpoint: str = "http://localhost:9000"
    auth_mode: Literal["dev_header", "external_bearer", "firebase"] = "external_bearer"
    auth_jwt_secret: str | None = None
    auth_jwks_url: str | None = None
    auth_jwt_algorithm: Literal["HS256", "RS256", "ES256"] = "HS256"
    auth_jwt_user_id_claim: str = "sub"
    auth_jwt_issuer: str | None = None
    auth_jwt_audience: str | None = None
    firebase_project_id: str | None = None
    firebase_project_number: str | None = None
    firebase_credentials_file: str | None = None
    firebase_credentials_json: str | None = None
    firebase_check_revoked: bool = False
    firebase_app_check_mode: Literal["off", "monitor", "enforce"] = "off"
    firebase_app_check_project_number: str | None = None
    firebase_app_check_allowed_app_ids: list[str] = Field(default_factory=list)
    auth_auto_provision: bool = False
    auth_invite_required: bool = True
    auth_allowed_email_domains: list[str] = Field(default_factory=list)
    auth_allowed_emails_file: str | None = None
    auth_allowed_firebase_uids_file: str | None = None
    auth_email_conflict_policy: Literal["reject"] = "reject"
    auth_identity_tombstone_secret: str | None = None
    metrics_enabled: bool = True
    metrics_token: str | None = None


def validate_runtime_settings(settings: ApiSettings) -> None:
    production_like = settings.env in {"production", "private-alpha", "private_alpha"}
    if production_like and settings.auth_mode == "dev_header":
        raise RuntimeError("PARALLAX_AUTH_MODE=dev_header is not allowed outside development/test")
    if production_like and settings.auth_mode == "external_bearer":
        if settings.auth_jwt_algorithm == "HS256":
            raise RuntimeError(
                "PARALLAX_AUTH_JWT_ALGORITHM=HS256 is not allowed for production "
                "external_bearer auth"
            )
        if not (
            settings.auth_jwks_url
            and settings.auth_jwt_issuer
            and settings.auth_jwt_audience
        ):
            raise RuntimeError(
                "production external_bearer auth requires PARALLAX_AUTH_JWKS_URL, "
                "PARALLAX_AUTH_JWT_ISSUER, and PARALLAX_AUTH_JWT_AUDIENCE"
            )
    if production_like and os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
        raise RuntimeError("FIREBASE_AUTH_EMULATOR_HOST is not allowed outside development/test")
    if settings.auth_mode == "firebase" and not settings.firebase_project_id:
        raise RuntimeError("PARALLAX_FIREBASE_PROJECT_ID is required for firebase auth mode")
    if (
        production_like
        and settings.auth_mode == "firebase"
        and not settings.auth_identity_tombstone_secret
    ):
        raise RuntimeError(
            "PARALLAX_AUTH_IDENTITY_TOMBSTONE_SECRET is required for production firebase auth"
        )
    if settings.firebase_app_check_mode == "enforce" and not (
        settings.firebase_app_check_project_number or settings.firebase_project_number
    ):
        raise RuntimeError(
            "PARALLAX_FIREBASE_PROJECT_NUMBER or "
            "PARALLAX_FIREBASE_APP_CHECK_PROJECT_NUMBER is required for App Check enforce mode"
        )
    if production_like and settings.metrics_enabled and not settings.metrics_token:
        raise RuntimeError("PARALLAX_METRICS_TOKEN is required when metrics are enabled")


def get_settings() -> ApiSettings:
    return ApiSettings()
