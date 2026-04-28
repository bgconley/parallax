from __future__ import annotations

from typing import Literal

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
    auth_mode: Literal["dev_header", "external_bearer"] = "dev_header"
    auth_jwt_secret: str | None = None
    auth_jwt_algorithm: Literal["HS256"] = "HS256"
    auth_jwt_user_id_claim: str = "sub"
    auth_jwt_issuer: str | None = None
    auth_jwt_audience: str | None = None


def get_settings() -> ApiSettings:
    return ApiSettings()
