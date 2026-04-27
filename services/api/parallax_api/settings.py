from __future__ import annotations

from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARALLAX_", env_file=".env", extra="ignore")

    env: str = "development"
    api_version: str = "0.1.0"
    contract_version: str = "1.3.0"
    dev_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    database_url: str = "postgresql://parallax:parallax_dev_password@localhost:5432/parallax"
    redis_url: str = "redis://localhost:6379/0"
    temporal_address: str = "localhost:7233"


def get_settings() -> ApiSettings:
    return ApiSettings()
