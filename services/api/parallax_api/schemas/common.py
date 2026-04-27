from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MutationEnvelope(ApiModel):
    client_mutation_id: str = Field(min_length=1)
    client_device_id: str = Field(min_length=1)
    client_timestamp: datetime
    idempotency_key: str = Field(min_length=1)
    client_sequence: int | None = Field(default=None, ge=0)


class ApiError(ApiModel):
    error_code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    request_id: str
    retryable: bool
    docs_ref: str | None = None
